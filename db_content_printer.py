from typing import List
import logging
from chromadb.config import Settings
import chromadb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# If not already configured
logging.basicConfig(level=logging.INFO)


class ChromaDBDocumentPrinter:
    def __init__(self, chroma_collection):
        self.collection = chroma_collection  # This is your ChromaDB collection object

    def print_unique_documents(self):
        try:
            logger.info("Fetching all documents from ChromaDB...")

            # Get all documents, metadata, and ids
            result = self.collection.get(include=["metadatas", "documents"])

            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            logger.info(f"Found {len(documents)} total chunks in the collection.")

            # Deduplicate to get unique documents based on title
            seen_docs = {}
            for idx, (content, metadata) in enumerate(zip(documents, metadatas)):
                doc_title = metadata.get("titel", "").strip()
                # Use title as unique identifier, fallback to URL if no title
                doc_key = doc_title if doc_title else metadata.get("url", "")

                if doc_key and doc_key not in seen_docs:
                    seen_docs[doc_key] = {
                        "id": doc_key,
                        "metadata": {
                            "url": metadata.get("url", ""),
                            "provincie": metadata.get("provincie", ""),
                            "titel": metadata.get("titel", ""),
                            "datum": metadata.get("datum", ""),
                            "type": metadata.get("type", ""),
                        },
                        "content_preview": (
                            content[:500] if content else ""
                        ),  # Store content preview
                    }

            unique_documents = list(seen_docs.values())
            logger.info(
                f"Found {len(unique_documents)} unique documents after deduplication.\n"
            )

            # Print the unique documents
            for idx, doc in enumerate(unique_documents, start=1):
                # print(f"--- Unique Document {idx} ---")
                print(f"{idx}: Title: {doc['metadata']['titel']}")
                # print(f"URL: {doc['metadata']['url']}")
                # print(f"Provincie: {doc['metadata']['provincie']}")
                # print(f"Datum: {doc['metadata']['datum']}")
                # print(f"Type: {doc['metadata']['type']}")
                # print(f"Content Preview:\n{doc['content_preview']}...")
                # print("\n")
            print("-" * 40)
            print(f"Total unique documents: {len(unique_documents)}")
            print("-" * 40)
        except Exception as e:
            logger.error(f"Failed to fetch or print documents: {e}")


# Get chroma_collection from your ChromaDB setup
client = chromadb.PersistentClient(
    path="database", settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection(name="document_chunks")
printer = ChromaDBDocumentPrinter(collection)
printer.print_unique_documents()
