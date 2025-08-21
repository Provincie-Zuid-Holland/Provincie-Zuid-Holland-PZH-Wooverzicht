"""
Healthcheck utility to verify database access and compatibility.

This script checks that the API can properly access ChromaDB and the logging database.
It's used to ensure that updates by the pipeline container don't affect the backend API.
"""

import os
import sys
import sqlite3
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


def check_logging_db():
    """
    Check if the logging database is accessible.
    """
    try:
        db_path = os.getenv("DB_PATH", "logging_database.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for the logs table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='query_logs'"
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            print("Logging database does not contain the expected table.")
            return False

        # Try to get a row count
        cursor.execute("SELECT COUNT(*) FROM query_logs")
        row_count = cursor.fetchone()[0]

        conn.close()
        print(f"Logging database check passed. Row count: {row_count}")
        return True
    except Exception as e:
        print(f"Logging database check failed: {e}")
        return False


if __name__ == "__main__":
    print("Running database health checks...")

    chromadb_ok = check_chromadb()
    logging_db_ok = check_logging_db()

    if chromadb_ok and logging_db_ok:
        print("All health checks passed.")
        sys.exit(0)
    else:
        print("Health checks failed.")
        sys.exit(1)
