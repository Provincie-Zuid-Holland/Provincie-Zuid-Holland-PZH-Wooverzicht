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

Author: [Your name]
Date: [Date]
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging
from functools import partial

from config import JSON_FOLDER
from openai import OpenAI
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings
from chromadb.api.models import Collection

# Set up logging configuration for tracking progress and errors
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load configuration from environment variables with sensible defaults
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))  # Size of text chunks for processing
CHUNK_OVERLAP = int(
    os.getenv("CHUNK_OVERLAP", 50)
)  # Overlap between chunks to maintain context
COLLECTION_NAME = os.getenv(
    "COLLECTION_NAME", "document_chunks"
)  # ChromaDB collection name
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # OpenAI model
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))  # Number of parallel embedding workers
BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", 100)
)  # Batch size for API calls and DB operations

# List of field names that might contain the main document content
# Add more field names here if your JSON uses different keys
CONTENT_FIELDS = ["content", "pdf_content", "text", "body", "main_content"]


@dataclass
class ChunkData:
    """
    Stores a chunk of text and its associated metadata.

    Attributes:
        chunk_id (str): Unique identifier for the chunk.
        content (str): The text content of the chunk.
        metadata (Dict[str, Any]): Dictionary containing all metadata associated with the chunk.
    """

    chunk_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class EmbeddedChunk(ChunkData):
    """
    Extends ChunkData to include the embedding vector.

    Attributes:
        embedding (List[float]): Vector representation of the chunk content.
    """

    embedding: List[float]


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

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initializes the document processor.

        Args:
            openai_api_key (Optional[str]): Optional API key (falls back to environment variable).

        Raises:
            ValueError: If no OpenAI API key is available.
        """
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))

        # Verify API key availability
        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path="database",  # Local storage path
            settings=Settings(
                anonymized_telemetry=False,  # Disable usage tracking
                allow_reset=False,  # Prevent accidental database resets
            ),
        )

    def flatten_json(self, prefix: str, obj: Dict) -> Dict[str, Any]:
        """
        Converts nested JSON structures into flat dictionary with dot notation keys.

        Args:
            prefix (str): Current key prefix for nested structures.
            obj (Dict): Dictionary to flatten.

        Returns:
            Dict[str, Any]: Dictionary with flattened structure using dot notation.

        Example:
            Input: {"a": {"b": 1}}
            Output: {"a.b": 1}
        """
        flattened = {}
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else key
            # Recursively flatten nested dictionaries
            if isinstance(value, dict):
                flattened.update(self.flatten_json(new_key, value))
            # Store primitive values directly
            elif isinstance(value, (str, int, float, bool)) or value is None:
                flattened[new_key] = value
        return flattened

    def load_and_chunk_data(
        self,
        data: dict,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> List[ChunkData]:
        """
        Processes JSON files into chunks while preserving all metadata.

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
        if not data.get("content") or data.content == "":
            raise ValueError("No content field found in the JSON dict.")
        all_chunks = []

        # Initialize text splitter with multiple separators for intelligent splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],  # Try different separators in order
        )

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
        chunks = text_splitter.split_text(content)

        # Create ChunkData objects for each chunk
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{data["file_name"]}_chunk_{idx}"
            all_chunks.append(
                ChunkData(chunk_id=chunk_id, content=chunk, metadata=metadata)
            )

        logger.info(f"Processed {data["file_name"]}: {len(chunks)} chunks created")

        return all_chunks

    def load_and_chunk_json_files(
        self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
    ) -> List[ChunkData]:  # DEPRECATED NO LONGER USED IN PIPELINE SCRIPT
        """
        Processes JSON files into chunks while preserving all metadata.

        Args:
            chunk_size (int): Maximum characters per chunk.
            chunk_overlap (int): Number of overlapping characters between chunks.

        Returns:
            List[ChunkData]: List of ChunkData objects containing processed chunks.

        Raises:
            FileNotFoundError: If JSON folder doesn't exist.
        """
        if not self.json_folder.exists():
            raise FileNotFoundError(f"JSON folder not found: {self.json_folder}")

        all_chunks = []

        # Initialize text splitter with multiple separators for intelligent splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],  # Try different separators in order
        )

        # Process each JSON file in the folder
        for file_path in self.json_folder.glob("*.json"):
            try:
                # Load and parse JSON file
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                # Get metadata from data dict
                metadata = data["metadata"]

                # Find the main content field
                content = data["pdf_content"]

                if not content:
                    logger.warning(
                        f"No content field found in {file_path}. "
                        f"Available fields: {list(data.keys())}"
                    )
                    continue

                # Split content into chunks
                chunks = text_splitter.split_text(content)

                # Create ChunkData objects for each chunk
                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{file_path.stem}_chunk_{idx}"
                    all_chunks.append(
                        ChunkData(chunk_id=chunk_id, content=chunk, metadata=metadata)
                    )

                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks created")

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing {file_path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        return all_chunks

    def embed_chunks(self, chunks: List[ChunkData]) -> List[EmbeddedChunk]:
        """
        Generates embeddings for chunks using OpenAI's API in parallel.

        Args:
            chunks (List[ChunkData]): List of chunks to embed.

        Returns:
            List[EmbeddedChunk]: List of chunks with their embedding vectors.
        """
        embedded_chunks = []

        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Process chunks in batches to respect API limits
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                try:
                    # Generate embeddings for the batch
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL, input=[chunk.content for chunk in batch]
                    )

                    # Create EmbeddedChunk objects with the results
                    for idx, embedding_data in enumerate(response.data):
                        embedded_chunks.append(
                            EmbeddedChunk(
                                chunk_id=batch[idx].chunk_id,
                                content=batch[idx].content,
                                metadata=batch[idx].metadata,
                                embedding=embedding_data.embedding,
                            )
                        )
                    logger.info(
                        f"Embedded batch {i//BATCH_SIZE + 1}: {len(batch)} chunks"
                    )

                except Exception as e:
                    logger.error(f"Error embedding batch starting at index {i}: {e}")
                    continue

        return embedded_chunks

    def load_embedded_chunks_to_chromadb(
        self,
        embedded_chunks: List[EmbeddedChunk],
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        """
        Stores embedded chunks in ChromaDB for later retrieval.

        Args:
            embedded_chunks (List[EmbeddedChunk]): List of chunks with embeddings to store.
            collection_name (str): Name of the ChromaDB collection to use.
        """
        # Get or create the collection
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        # Add chunks to database in batches
        for i in range(0, len(embedded_chunks), BATCH_SIZE):
            batch = embedded_chunks[i : i + BATCH_SIZE]
            try:
                collection.add(
                    documents=[chunk.content for chunk in batch],  # The text content
                    embeddings=[
                        chunk.embedding for chunk in batch
                    ],  # The embedding vectors
                    metadatas=[chunk.metadata for chunk in batch],  # All metadata
                    ids=[chunk.chunk_id for chunk in batch],  # Unique IDs
                )
                logger.info(f"Loaded batch {i//BATCH_SIZE + 1} into ChromaDB")
            except Exception as e:
                logger.error(f"Error loading batch to ChromaDB: {e}")
                continue


def db_pipeline(data):
    """
    Function that orchestrates the document processing pipeline.

    This function coordinates the steps of:
    1. Loading and chunking JSON documents
    2. Generating embeddings
    3. Storing embedded chunks in ChromaDB

    Args:
        data (dict): Dictionary containing JSON data to process

    Raises:
        Any exceptions that occur during the processing pipeline.
    """
    # Load environment variables from .env file
    load_dotenv()
    # initalize processor
    try:
        processor = DocumentProcessor()
        # Step 1: Load and chunk the documents
        logger.info("Chunking JSON data...")
        chunks = processor.load_and_chunk_data(data)

        if not chunks:
            logger.error("No chunks were created. Exiting.")
            return

        # Step 2: Generate embeddings
        logger.info("Embedding chunks using OpenAI embeddings...")
        embedded_chunks = processor.embed_chunks(chunks)

        if not embedded_chunks:
            logger.error("No embeddings were created. Exiting.")
            return

        # Step 3: Store in database
        logger.info("Loading embedded chunks into ChromaDB...")
        processor.load_embedded_chunks_to_chromadb(embedded_chunks)

        logger.info("Processing completed successfully!")

    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise


def main():
    """
    Main execution function that orchestrates the document processing pipeline.

    This function coordinates the steps of:
    1. Loading and chunking JSON documents
    2. Generating embeddings
    3. Storing embedded chunks in ChromaDB

    Raises:
        Any exceptions that occur during the processing pipeline.
    """

    # Load environment variables from .env file
    load_dotenv()

    try:
        # Initialize processor
        processor = DocumentProcessor(JSON_FOLDER)

        # Step 1: Load and chunk the documents
        logger.info("Chunking JSON data...")
        chunks = processor.load_and_chunk_json_files()

        if not chunks:
            logger.error("No chunks were created. Exiting.")
            return

        # Step 2: Generate embeddings
        logger.info("Embedding chunks using OpenAI embeddings...")
        embedded_chunks = processor.embed_chunks(chunks)

        if not embedded_chunks:
            logger.error("No embeddings were created. Exiting.")
            return

        # Step 3: Store in database
        logger.info("Loading embedded chunks into ChromaDB...")
        processor.load_embedded_chunks_to_chromadb(embedded_chunks)

        logger.info("Processing completed successfully!")

    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise


if __name__ == "__main__":
    main()
