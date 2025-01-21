import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.config import Settings
from chromadb import Client
from config import JSON_FOLDER

def load_and_chunk_json_data(json_folder, chunk_size=500, chunk_overlap=50):
    """
    Load JSON data from the specified folder and chunk the content.

    Args:
        json_folder (str): Path to the folder containing JSON files.
        chunk_size (int): Maximum size of each chunk.
        chunk_overlap (int): Overlap size between consecutive chunks.

    Returns:
        list: List of dictionaries, each representing a chunk with its metadata.
    """
    all_chunks = []

    for file_name in os.listdir(json_folder):
        if file_name.endswith(".json"):
            file_path = os.path.join(json_folder, file_name)

            # Load the JSON data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract content and metadata
            pdf_content = data["pdf_content"]
            metadata = data["metadata"]
            metadata["pdf_file"] = data["pdf_file"]

            # Chunk the content using LangChain's RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_text(pdf_content)

            # Add metadata to each chunk
            for idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "chunk_id": f"{metadata['pdf_file']}_chunk_{idx}",
                    "content": chunk,
                    "metadata": metadata
                })
    print(all_chunks)
    return all_chunks


def load_chunks_to_chromadb(chunks, collection_name="pdf_chunks", persist_directory="chromadb_storage"):
    """
    Load chunks into ChromaDB.

    Args:
        chunks (list): List of chunk dictionaries with content and metadata.
        collection_name (str): Name of the ChromaDB collection.
        persist_directory (str): Directory to store the ChromaDB database.

    Returns:
        None
    """
    # Initialize ChromaDB client
    client = Client(Settings(
        persist_directory=persist_directory,
        chroma_db_impl="duckdb+parquet"
    ))

    # Create or load the collection
    collection = client.get_or_create_collection(name=collection_name)

    # Add chunks to the collection
    for chunk in chunks:
        collection.add(
            documents=[chunk["content"]],
            metadatas=[chunk["metadata"]],
            ids=[chunk["chunk_id"]]
        )

    print(f"Loaded {len(chunks)} chunks into the ChromaDB collection '{collection_name}'.")

if __name__ == "__main__":
    # Step 1: Chunk the data
    chunks = load_and_chunk_json_data(JSON_FOLDER)

    # Step 2: Load chunks into ChromaDB
    load_chunks_to_chromadb(chunks)

    print("All chunks have been processed and loaded into ChromaDB.")
