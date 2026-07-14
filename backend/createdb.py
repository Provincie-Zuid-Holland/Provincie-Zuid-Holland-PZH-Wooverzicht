"""
Document Processing and Embedding Pipeline

This script creates a searchable vector database from document content stored in JSON files.
It processes any JSON structure, preserving all metadata, and creates embeddings for semantic search.

Key Features:
- Flexible JSON handling: Adapts to different JSON structures
- Complete metadata preservation: Stores all JSON fields for future reference
- Parallel processing: Uses threading for efficient embedding generation
- Batched operations: Handles large datasets efficiently
- Error resilience: Continues processing even if some files fail

Required Environment Variables:
- OPENAI_API_KEY: Your OpenAI API key
- Optional: CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, EMBEDDING_MODEL, MAX_WORKERS, BATCH_SIZE
"""

import os
from typing import List
from dataclass.embedded_chunk import EmbeddedChunk, ChunkData
from concurrent.futures import ThreadPoolExecutor
import logging
from dotenv import load_dotenv
from nltk.tokenize import sent_tokenize
from embedder_logic import get_embedder
from config import EMBEDDING_PROVIDER, VECTOR_DB
from vectordb_logic import get_vectordb

# Set up logging configuration for tracking progress and errors
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load configuration from environment variables with sensible defaults
load_dotenv()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1200))  # Size of text chunks for processing
CHUNK_OVERLAP = int(
    os.getenv("CHUNK_OVERLAP", 50)
)  # Overlap between chunks to maintain context
CHUNK_SENTENCE_OVERLAP = int(
    os.getenv("CHUNK_SENTECE_OVERLAP", 1)
)  # Overlap between sentences in chunks
COLLECTION_NAME = os.getenv(
    "COLLECTION_NAME", "document_chunks"
)  # ChromaDB collection name

MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))  # Number of parallel embedding workers
BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", 100)
)  # Batch size for API calls and DB operations


class Chunker:
    def __init__(self) -> None:
        pass

    def chunk_by_sentence_with_overlap(
        self, text, chunk_size=1000, sentence_limit_factor=10, overlap_sentences=1
    ):
        """
        Splits text into chunks based on sentences while preserving overlap.

        Args:
            text (str): The text to be chunked.
            chunk_size (int): Maximum size of each chunk in characters.
            sentence_limit_factor (int): Factor to limit how often a 'sentence'(already split by sentence tokenizer) can exceed chunk size, and still be split into smaller parts. After that, it will be skipped.
            overlap_sentences (int): Number of sentences to overlap between chunks.

        Returns:
            List[str]: List of text chunks.
        """
        sentences = sent_tokenize(text, language="dutch")
        chunks = []
        current_chunk = []  # Sentences will be stored here

        for sentence in sentences:
            if sum(len(s) for s in current_chunk) + len(sentence) <= chunk_size:
                current_chunk.append(
                    sentence
                )  # add current sentence to the chunk if char limit is not exceeded
            elif len(sentence) > sentence_limit_factor * chunk_size:
                logger.warning(
                    f"Sentence way too long even after sentence tokenization ({len(sentence)} characters), longer than chunk size limit ({chunk_size} characters), multiplied by factor {sentence_limit_factor}. Skipping."
                )
                continue
            elif len(sentence) > chunk_size:
                logger.warning(
                    f"Sentence ({len(sentence)} characters) exceeds chunk size limit ({chunk_size} characters). Splitting sentence."
                )
                # First save the current chunk if it has content
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                # Split the sentence into smaller parts if it exceeds chunk size
                for i in range(0, len(sentence), chunk_size):
                    part = sentence[i : i + chunk_size]
                    chunks.append(part)
            else:  # if chunk size would be exceeded
                chunks.append(
                    " ".join(current_chunk)
                )  # Add sentences as a single string to chunks

                current_chunk = (  # Set current chunk to the last N sentences of the previous chunk
                    current_chunk[-overlap_sentences:] if overlap_sentences > 0 else []
                )
                current_chunk.append(
                    sentence
                )  # Add the 'new' sentence to the current chunk

        if (
            current_chunk
        ):  # If we have run out of sentences but still have a chunk to add, add it
            chunks.append(" ".join(current_chunk))

        return chunks

    def load_and_chunk_data_by_sentence(
        self,
        data: dict,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_SENTENCE_OVERLAP,
    ) -> List[ChunkData]:
        """
        Processes JSON files into chunks while preserving all metadata.Chunking strategy is based on sentences.

        Args:
            data (dict): Dictionary containing JSON data to process.
            chunk_size (int): Maximum characters per chunk.
            chunk_overlap (int): Number of overlapping characters between chunks.

        Returns:
            List[ChunkData]: List of ChunkData objects containing processed chunks.

        Raises:
            ValueError: If data is empty.
        """
        # If dict is empty raise error
        if not data:
            raise ValueError("No data found in the JSON dict.")
        # Check if data.content is empty
        if not data.get("content") or data["content"] == "":
            raise ValueError("No content field found in the JSON dict.")
        all_chunks = []

        # Process data
        # Get metadata from data dict
        metadata = data["metadata"]

        # Find the main content field
        content = data["content"]

        if not content:
            logger.warning(
                f"No content field found in {data["pdf_file"]}. "
                f"Available fields: {list(data.keys())}"
            )

        # Split content into chunks
        chunks = self.chunk_by_sentence_with_overlap(
            content, chunk_size=chunk_size, overlap_sentences=chunk_overlap
        )

        # Create ChunkData objects for each chunk
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{data["file_name"]}_chunk_{idx}"
            all_chunks.append(
                ChunkData(chunk_id=chunk_id, content=chunk, metadata=metadata)
            )

        logger.info(f"Processed {data["file_name"]}: {len(chunks)} chunks created")

        return all_chunks


class Embedder:
    def __init__(self) -> None:
        self.embedding_provider = get_embedder(EMBEDDING_PROVIDER)

    def embed_chunks(
        self, chunks: List[ChunkData], to_embed: bool
    ) -> List[EmbeddedChunk]:
        """
        Creates Embeddedchunk objects. If to_embed is true includes generated embeddings for chunks.

        Args:
            chunks (List[ChunkData]): List of chunks to embed.
            to_embed (bool): Whether to generate embeddings or not.

        Returns:
            List[EmbeddedChunk]: List of chunks with their embedding vectors.
        """
        embedded_chunks = []

        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=MAX_WORKERS):
            # Process chunks in batches to respect API limits
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                try:
                    # loop through batch and create EmbeddedChunk objects without embeddings
                    for chunk in batch:
                        embedded_chunks.append(
                            EmbeddedChunk(
                                chunk_id=chunk.chunk_id,
                                content=chunk.content,
                                metadata=chunk.metadata,
                                embedding=[],
                            )
                        )

                    # Generate embeddings for the batch if to_embed is True
                    if to_embed:
                        embeddings = self.embedding_provider.embed_documents(
                            [chunk.content for chunk in batch]
                        )

                        for idx, embedding in enumerate(embeddings):
                            embedded_chunks[i + idx].embedding = embedding

                        logger.info(
                            f"Embedded batch {i//BATCH_SIZE + 1}: {len(batch)} chunks"
                        )

                except Exception as e:
                    logger.error(f"Error embedding batch starting at index {i}: {e}")
                    continue

        return embedded_chunks


class DocumentProcessor:
    """
    Processes document content from JSON files into searchable vector database entries.

    Attributes:
        json_folder (Path): Path to folder containing JSON files.
        client (OpenAI): OpenAI client for generating embeddings.
        chroma_client (chromadb.PersistentClient): ChromaDB client for vector storage.

    Functions:
        flatten_json: Converts nested JSON structures into flat dictionary.
        load_and_chunk_json_data: Processes JSON files into chunks while preserving metadata.
        embed_chunks: Generates embeddings for chunks using OpenAI's API.
        load_embedded_chunks_to_chromadb: Stores embedded chunks in ChromaDB for retrieval.
    """

    def __init__(self):
        """
        Initializes the document processor.

        Args:
            openai_api_key (Optional[str]): Optional API key (falls back to environment variable).

        Raises:
            ValueError: If no OpenAI API key is available.
        """
        self.client = get_vectordb(VECTOR_DB)

    # UNUSED, see chunker
    def chunk_by_sentence_with_overlap(
        self, text, chunk_size=1000, sentence_limit_factor=10, overlap_sentences=1
    ):
        """
        Splits text into chunks based on sentences while preserving overlap.

        Args:
            text (str): The text to be chunked.
            chunk_size (int): Maximum size of each chunk in characters.
            sentence_limit_factor (int): Factor to limit how often a 'sentence'(already split by sentence tokenizer) can exceed chunk size, and still be split into smaller parts. After that, it will be skipped.
            overlap_sentences (int): Number of sentences to overlap between chunks.

        Returns:
            List[str]: List of text chunks.
        """
        sentences = sent_tokenize(text, language="dutch")
        chunks = []
        current_chunk = []  # Sentences will be stored here

        for sentence in sentences:
            if sum(len(s) for s in current_chunk) + len(sentence) <= chunk_size:
                current_chunk.append(
                    sentence
                )  # add current sentence to the chunk if char limit is not exceeded
            elif len(sentence) > sentence_limit_factor * chunk_size:
                logger.warning(
                    f"Sentence way too long even after sentence tokenization ({len(sentence)} characters), longer than chunk size limit ({chunk_size} characters), multiplied by factor {sentence_limit_factor}. Skipping."
                )
                continue
            elif len(sentence) > chunk_size:
                logger.warning(
                    f"Sentence ({len(sentence)} characters) exceeds chunk size limit ({chunk_size} characters). Splitting sentence."
                )
                # First save the current chunk if it has content
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                # Split the sentence into smaller parts if it exceeds chunk size
                for i in range(0, len(sentence), chunk_size):
                    part = sentence[i : i + chunk_size]
                    chunks.append(part)
            else:  # if chunk size would be exceeded
                chunks.append(
                    " ".join(current_chunk)
                )  # Add sentences as a single string to chunks

                current_chunk = (  # Set current chunk to the last N sentences of the previous chunk
                    current_chunk[-overlap_sentences:] if overlap_sentences > 0 else []
                )
                current_chunk.append(
                    sentence
                )  # Add the 'new' sentence to the current chunk

        if (
            current_chunk
        ):  # If we have run out of sentences but still have a chunk to add, add it
            chunks.append(" ".join(current_chunk))

        return chunks

    # UNUSED see chunker
    def load_and_chunk_data_by_sentence(
        self,
        data: dict,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_SENTENCE_OVERLAP,
    ) -> List[ChunkData]:
        """
        Processes JSON files into chunks while preserving all metadata.Chunking strategy is based on sentences.

        Args:
            data (dict): Dictionary containing JSON data to process.
            chunk_size (int): Maximum characters per chunk.
            chunk_overlap (int): Number of overlapping characters between chunks.

        Returns:
            List[ChunkData]: List of ChunkData objects containing processed chunks.

        Raises:
            ValueError: If data is empty.
        """
        # If dict is empty raise error
        if not data:
            raise ValueError("No data found in the JSON dict.")
        # Check if data.content is empty
        if not data.get("content") or data["content"] == "":
            raise ValueError("No content field found in the JSON dict.")
        all_chunks = []

        # Process data
        # Get metadata from data dict
        metadata = data["metadata"]

        # Find the main content field
        content = data["content"]

        if not content:
            logger.warning(
                f"No content field found in {data["pdf_file"]}. "
                f"Available fields: {list(data.keys())}"
            )

        # Split content into chunks
        chunks = self.chunk_by_sentence_with_overlap(
            content, chunk_size=chunk_size, overlap_sentences=chunk_overlap
        )

        # Create ChunkData objects for each chunk
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{data["file_name"]}_chunk_{idx}"
            all_chunks.append(
                ChunkData(chunk_id=chunk_id, content=chunk, metadata=metadata)
            )

        logger.info(f"Processed {data["file_name"]}: {len(chunks)} chunks created")

        return all_chunks

    # UNUSED, see Embedder class
    def embed_chunks(
        self, chunks: List[ChunkData], to_embed: bool
    ) -> List[EmbeddedChunk]:
        """
        Creates Embeddedchunk objects. If to_embed is true includes generated embeddings for chunks.

        Args:
            chunks (List[ChunkData]): List of chunks to embed.
            to_embed (bool): Whether to generate embeddings or not.

        Returns:
            List[EmbeddedChunk]: List of chunks with their embedding vectors.
        """
        embedded_chunks = []

        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=MAX_WORKERS):
            # Process chunks in batches to respect API limits
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                try:
                    # loop through batch and create EmbeddedChunk objects without embeddings
                    for chunk in batch:
                        embedded_chunks.append(
                            EmbeddedChunk(
                                chunk_id=chunk.chunk_id,
                                content=chunk.content,
                                metadata=chunk.metadata,
                                embedding=[],
                            )
                        )

                    # Generate embeddings for the batch if to_embed is True
                    if to_embed:
                        embeddings = self.embedder.embed_documents(
                            [chunk.content for chunk in batch]
                        )

                        for idx, embedding in enumerate(embeddings):
                            embedded_chunks[i + idx].embedding = embedding

                        logger.info(
                            f"Embedded batch {i//BATCH_SIZE + 1}: {len(batch)} chunks"
                        )

                except Exception as e:
                    logger.error(f"Error embedding batch starting at index {i}: {e}")
                    continue

        return embedded_chunks

    # TODO Generalise to any db instead of chromaDB
    def load_chunks_to_vectordb(
        self,
        embedded_chunks: List[EmbeddedChunk],
    ) -> None:
        """
        Stores chunks in ChromaDB for later retrieval.

        Args:
            embedded_chunks Optional (List[EmbeddedChunk]): List of chunks with embeddings to store.
            to_embed (bool): Whether the chunks have embeddings or not.
            collection_name (str): Name of the ChromaDB collection to use.
        """
        # Get or create the collection
        self.client.add_documents(embedded_chunks)


class dbPipelineHandler:
    """
    Class that handles the logic for chunking, embedding and loading data into the database.
    """

    def __init__(self) -> None:
        load_dotenv()
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.processor = DocumentProcessor()

    def db_pipeline(self, data, to_embed: bool = True):
        try:
            # Step 1: Load and chunk the documents
            logger.info("Chunking JSON data...")
            chunks = self.chunker.load_and_chunk_data_by_sentence(data)

            if not chunks:
                raise Exception("No chunks were created. Exiting.")

            # Step 2: Generate embeddings
            logger.info("Embedding chunks...")
            embedded_chunks = self.embedder.embed_chunks(chunks, to_embed)

            if not embedded_chunks:
                raise Exception("No embeddings were created. Exiting.")

            # Step 3: store embeddings in db
            logger.info(f"Loading embedded chunks into {VECTOR_DB} database...")
            self.processor.load_chunks_to_vectordb(embedded_chunks)

            logger.info("Processing completed successfully!")

        except Exception as e:
            logger.error(f"An error occurred during processing: {e}")
            raise
