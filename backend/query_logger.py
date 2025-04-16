import sqlite3
from datetime import datetime
import uuid
import json


class QueryLogger:
    """
    A class to log interactions with the Conversational RAG system into a SQLite database.

    This class provides methods to initialize the database, log interactions, and retrieve logs.
        sources (list): List of source documents.
        container (st.container, optional): The Streamlit container to display the sources in.

    Returns:
        None
    """

    def __init__(self, db_path="logging_database.db"):
        """
        Initializes the QueryLogger with a SQLite database.

        Args:
            db_path (str): Path to the SQLite database file. Defaults to "logging_database.db".

        Raises:
            sqlite3.Error: If there is an error connecting to the database or executing SQL commands.

        Returns:
            None

        Example:
            logger = QueryLogger("path/to/logging_database.db")
            logger.log_interaction(session_id, query, response, metadata)
        """

        # Initialize the database path
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Initializes the SQLite database and creates the logs table if it doesn't exist.
        This method is called during the initialization of the QueryLogger class.
        It creates a connection to the SQLite database and executes SQL commands to create the
        necessary table for logging interactions.
        The table structure includes columns for log ID, session ID, timestamp, query,
        response, and metadata.
        Args:
            None

        Raises:
            sqlite3.Error: If there is an error executing SQL commands.

        Returns:
            None

        Example:
            logger = QueryLogger("path/to/logging_database.db")
            # The database and table are created automatically
            # when the QueryLogger instance is initialized.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create logs table if it doesn't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS query_logs (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            query TEXT,
            response TEXT,
            metadata TEXT
        )
        """
        )

        conn.commit()
        conn.close()

    def log_interaction(self, session_id, query, response, metadata=None):
        """
                Logs a user interaction with the Conversational RAG system into the SQLite database.

                Args:
                    session_id (str): Unique identifier for the user session.
                    query (str): The user's query.
                    response (str): The system's response to the query.
                    metadata (dict, optional): Additional metadata related to the interaction. Expected keys in dictionary are:
                        - source: The source of the information (e.g., Wikipedia, etc.)
                        - response_time: The time taken to generate the response.
                        - chunks_used: The document ID's of the chunks used to give extra context when generating the response (RAG).
                        - timestamp: The time when the interaction occurred.
                        - other: Any other relevant metadata.
                This metadata is stored as a JSON string in the database.
        s
                Raises:
                    sqlite3.Error: If there is an error executing SQL commands.

                Returns:
                    str: The unique log ID for the interaction.

                Example:
                    logger = QueryLogger("path/to/logging_database.db")
                    log_id = logger.log_interaction(
                        session_id="12345",
                        query="What is the capital of France?",
                        response="The capital of France is Paris.",
                        metadata={"source": "Wikipedia"}
                    )
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        log_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})

        cursor.execute(
            "INSERT INTO query_logs VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, session_id, timestamp, query, response, metadata_json),
        )

        conn.commit()
        conn.close()

        return log_id
