import os
import json
from typing import List, Dict, Any
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

# Set up logging to track the progress and errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration from environment variables
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))  # Size of each text chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))  # Overlap between chunks
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "pdf_chunks")  # ChromaDB collection name
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # OpenAI embedding model
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))  # Number of parallel workers for embedding
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))  # Batch size for embedding and ChromaDB operations

# Define a dataclass to store chunk data (content + metadata)
@dataclass
class ChunkData:
    chunk_id: str  # Unique ID for the chunk
    content: str  # The actual text content of the chunk
    metadata: Dict[str, Any]  # Metadata associated with the chunk (e.g., file name)

# Define a dataclass to store embedded chunks (content + metadata + embedding)
@dataclass
class EmbeddedChunk(ChunkData):
    embedding: List[float]  # The embedding vector for the chunk

class PDFProcessor:
    def __init__(self, json_folder: str, openai_api_key: str | None = None):
        """
        Initialize the PDFProcessor with the folder containing JSON files and the OpenAI API key.
        
        Args:
            json_folder: Path to the folder containing JSON files.
            openai_api_key: OpenAI API key (optional, falls back to environment variable).
        """
        self.json_folder = Path(json_folder)  # Convert the folder path to a Path object
        self.client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))  # Initialize OpenAI client
        
        # Validate the OpenAI API key
        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        # Initialize ChromaDB client for persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path="database",  # Directory where ChromaDB data will be stored
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry for privacy
                allow_reset=False  # Prevent accidental database resets
            )
        )
        
    def load_and_chunk_json_data(
        self, 
        chunk_size: int = CHUNK_SIZE, 
        chunk_overlap: int = CHUNK_OVERLAP
    ) -> List[ChunkData]:
        """
        Load JSON files, extract PDF content, and split it into chunks.
        
        Args:
            chunk_size: Maximum size of each chunk.
            chunk_overlap: Overlap size between consecutive chunks.
            
        Returns:
            List of ChunkData objects containing chunks and their metadata.
        
        Raises:
            FileNotFoundError: If the JSON folder doesn't exist.
            JSONDecodeError: If a JSON file is invalid.
        """
        # Check if the JSON folder exists
        if not self.json_folder.exists():
            raise FileNotFoundError(f"JSON folder not found: {self.json_folder}")
            
        all_chunks = []  # List to store all chunks
        
        # Initialize the text splitter for chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]  # Split on paragraphs, lines, and spaces
        )

        # Loop through all JSON files in the folder
        for file_path in self.json_folder.glob("*.json"):
            try:
                # Load the JSON file
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract PDF content and metadata
                pdf_content = data["pdf_content"]
                metadata = data["metadata"]
                metadata["pdf_file"] = data["pdf_file"]  # Add the PDF file name to metadata
                
                # Split the PDF content into chunks
                chunks = text_splitter.split_text(pdf_content)
                
                # Create ChunkData objects for each chunk
                for idx, chunk in enumerate(chunks):
                    all_chunks.append(ChunkData(
                        chunk_id=f"{metadata['pdf_file']}_chunk_{idx}",  # Unique ID for the chunk
                        content=chunk,  # The chunk's text content
                        metadata=metadata  # Associated metadata
                    ))
                    
                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks created")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing {file_path}: {e}")
                continue
            except KeyError as e:
                logger.error(f"Missing required key in {file_path}: {e}")
                continue
                
        return all_chunks

    def embed_chunks(self, chunks: List[ChunkData]) -> List[EmbeddedChunk]:
        """
        Embed text chunks using OpenAI's embedding model in parallel.
        
        Args:
            chunks: List of ChunkData objects to embed.
            
        Returns:
            List of EmbeddedChunk objects with embeddings.
        """
        embedded_chunks = []  # List to store embedded chunks
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Process chunks in batches to avoid hitting API rate limits
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]  # Get a batch of chunks
                try:
                    # Use OpenAI's batch embedding API to embed the batch
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=[chunk.content for chunk in batch]
                    )
                    # Create EmbeddedChunk objects for each chunk in the batch
                    for idx, embedding in enumerate(response.data):
                        embedded_chunks.append(EmbeddedChunk(
                            chunk_id=batch[idx].chunk_id,
                            content=batch[idx].content,
                            metadata=batch[idx].metadata,
                            embedding=embedding.embedding
                        ))
                    logger.info(f"Embedded batch {i//BATCH_SIZE + 1}: {len(batch)} chunks")
                except Exception as e:
                    logger.error(f"Error embedding batch starting at index {i}: {e}")
                    continue
                    
        return embedded_chunks

    def load_embedded_chunks_to_chromadb(
        self, 
        embedded_chunks: List[EmbeddedChunk], 
        collection_name: str = COLLECTION_NAME
    ) -> None:
        """
        Load embedded chunks into ChromaDB in batches.
        
        Args:
            embedded_chunks: List of EmbeddedChunk objects to load.
            collection_name: Name of the ChromaDB collection.
        """
        # Get or create the ChromaDB collection
        collection = self.chroma_client.get_or_create_collection(name=collection_name)
        
        # Load chunks into ChromaDB in batches
        for i in range(0, len(embedded_chunks), BATCH_SIZE):
            batch = embedded_chunks[i:i + BATCH_SIZE]  # Get a batch of chunks
            try:
                # Add the batch to ChromaDB
                collection.add(
                    documents=[chunk.content for chunk in batch],  # Text content
                    embeddings=[chunk.embedding for chunk in batch],  # Embeddings
                    metadatas=[chunk.metadata for chunk in batch],  # Metadata
                    ids=[chunk.chunk_id for chunk in batch]  # Unique IDs
                )
                logger.info(f"Loaded batch {i//BATCH_SIZE + 1} into ChromaDB")
            except Exception as e:
                logger.error(f"Error loading batch to ChromaDB: {e}")
                continue

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    try:
        # Initialize the PDFProcessor
        processor = PDFProcessor(JSON_FOLDER)
        
        # Step 1: Chunk the data
        logger.info("Chunking JSON data...")
        chunks = processor.load_and_chunk_json_data()
        
        if not chunks:
            logger.error("No chunks were created. Exiting.")
            return

        # Step 2: Embed the chunks
        logger.info("Embedding chunks using OpenAI embeddings...")
        embedded_chunks = processor.embed_chunks(chunks)
        
        if not embedded_chunks:
            logger.error("No embeddings were created. Exiting.")
            return

        # Step 3: Load embedded chunks into ChromaDB
        logger.info("Loading embedded chunks into ChromaDB...")
        processor.load_embedded_chunks_to_chromadb(embedded_chunks)
        
        logger.info("Processing completed successfully.")
        
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise

if __name__ == "__main__":
    main()