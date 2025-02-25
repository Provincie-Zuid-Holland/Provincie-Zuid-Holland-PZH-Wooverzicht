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


# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "document_chunks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
JSON_FOLDER = os.getenv("JSON_FOLDER", "./json")


@dataclass
class ChunkData:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class EmbeddedChunk(ChunkData):
    embedding: List[float]


class DocumentProcessor:
    def __init__(self, json_folder: str, openai_api_key: Optional[str] = None):
        self.json_folder = Path(json_folder)
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))

        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        self.chroma_client = chromadb.PersistentClient(
            path="database",
            settings=Settings(anonymized_telemetry=False, allow_reset=False),
        )

    def load_and_chunk_json_data(self) -> List[ChunkData]:
        if not self.json_folder.exists():
            raise FileNotFoundError(f"JSON folder not found: {self.json_folder}")

        all_chunks = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )

        for file_path in self.json_folder.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                if "pdf_content" not in data:
                    logger.warning(f"No 'pdf_content' field found in {file_path}")
                    continue

                content = data["pdf_content"]
                metadata = data.get("metadata", {})
                metadata["pdf_file"] = data.get("pdf_file", "Unknown")

                chunks = text_splitter.split_text(content)

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
        embedded_chunks = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                try:
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL, input=[chunk.content for chunk in batch]
                    )

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
        self, embedded_chunks: List[EmbeddedChunk]
    ) -> None:
        collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)

        for i in range(0, len(embedded_chunks), BATCH_SIZE):
            batch = embedded_chunks[i : i + BATCH_SIZE]
            try:
                collection.add(
                    documents=[chunk.content for chunk in batch],
                    embeddings=[chunk.embedding for chunk in batch],
                    metadatas=[chunk.metadata for chunk in batch],
                    ids=[chunk.chunk_id for chunk in batch],
                )
                logger.info(f"Loaded batch {i//BATCH_SIZE + 1} into ChromaDB")
            except Exception as e:
                logger.error(f"Error loading batch to ChromaDB: {e}")
                continue


def main():
    try:
        processor = DocumentProcessor(JSON_FOLDER)

        logger.info("Chunking JSON data...")
        chunks = processor.load_and_chunk_json_data()

        if not chunks:
            logger.error("No chunks were created. Exiting.")
            return

        logger.info("Embedding chunks using OpenAI embeddings...")
        embedded_chunks = processor.embed_chunks(chunks)

        if not embedded_chunks:
            logger.error("No embeddings were created. Exiting.")
            return

        logger.info("Loading embedded chunks into ChromaDB...")
        processor.load_embedded_chunks_to_chromadb(embedded_chunks)

        logger.info("Processing completed successfully!")

    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise


if __name__ == "__main__":
    main()
