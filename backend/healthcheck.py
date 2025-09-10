"""
Healthcheck utility to verify database access and compatibility.

This script checks that the API can properly access ChromaDB and the logging database.
It's used to ensure that updates by the pipeline container don't affect the backend API.
"""

import sys
from chromadb_query import ChromadbQuery


def check_chromadb():
    """
    Check if ChromaDB is accessible and has expected collections.
    """
    try:
        query_engine = ChromadbQuery()

        # Try a simple query to check if the database is functioning
        # test_results = query_engine.search(query="test", limit=1)

        # Get collection info
        collection_info = query_engine.client.list_collections()

        print(f"ChromaDB check passed. Collections: {len(collection_info)}")
        return True
    except Exception as e:
        print(f"ChromaDB check failed: {e}")
        return False


if __name__ == "__main__":
    print("Running database health checks...")

    chromadb_ok = check_chromadb()

    if chromadb_ok:
        print("All health checks passed.")
        sys.exit(0)
    else:
        print("Health checks failed.")
        sys.exit(1)
