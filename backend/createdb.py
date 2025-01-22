import os
import json
from config import JSON_FOLDER
from openai import OpenAI
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb.utils.embedding_functions as embedding_functions

import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings


# Load environment variables
load_dotenv()

# Set up OpenAI API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize PersistentClient
chroma_client = chromadb.PersistentClient(
    path="database",  # Directory where ChromaDB data will be persisted
    settings=Settings(),
    tenant=DEFAULT_TENANT,
    database=DEFAULT_DATABASE,
)


def load_and_chunk_json_data(json_folder, chunk_size=500, chunk_overlap=50):
    """
    Load JSON data, chunk the PDF content, and keep metadata intact.

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
    return all_chunks



def embed_chunks(chunks):
    """
    Embed text chunks using OpenAI's embedding model.

    Args:
        chunks (list): List of chunk dictionaries containing content and metadata.

    Returns:
        list: List of dictionaries with embeddings and metadata.
    """
    embedded_chunks = []

    for chunk in chunks:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk["content"]
        )
        print(response)
        embedding = response.data[0].embedding
        embedded_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "content": chunk["content"],
            "embedding": embedding,
            "metadata": chunk["metadata"]
        })
    print(embedded_chunks)
    return embedded_chunks


def load_embedded_chunks_to_chromadb(embedded_chunks, collection_name="pdf_chunks"):
    """
    Load embedded chunks into ChromaDB using PersistentClient.

    Args:
        embedded_chunks (list): List of dictionaries containing embeddings, content, and metadata.
        collection_name (str): Name of the ChromaDB collection.

    Returns:
        None
    """
    # Create or load the collection
    collection = chroma_client.get_or_create_collection(name=collection_name)

    # Add chunks to the collection
    for chunk in embedded_chunks:
        collection.add(
            documents=[chunk["content"]],
            embeddings=[chunk["embedding"]],
            metadatas=[chunk["metadata"]],
            ids=[chunk["chunk_id"]]
        )

    print(f"Loaded {len(embedded_chunks)} chunks into the ChromaDB collection '{collection_name}'.")


if __name__ == "__main__":
    # Step 1: Chunk the data
    print("Chunking JSON data...")
    chunks = load_and_chunk_json_data(JSON_FOLDER)

    # Step 2: Embed the chunks
    print("Embedding chunks using OpenAI embeddings...")
    embedded_chunks = embed_chunks(chunks)

    # Step 3: Load embedded chunks into ChromaDB
    print("Loading embedded chunks into ChromaDB...")
    load_embedded_chunks_to_chromadb(embedded_chunks)

    print("All chunks have been processed, embedded, and loaded into ChromaDB.")
