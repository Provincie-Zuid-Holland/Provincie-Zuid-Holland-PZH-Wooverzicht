from abc import ABC, abstractmethod
from dotenv import load_dotenv
from config import CHROMA_COLLECTION_NAME, EMBEDDING_PROVIDER, VECTOR_DB
from typing import List
from dataclass.embedded_chunk import EmbeddedChunk
from dataclasses import dataclass
from typing import Dict, Any
import logging
import os
import chromadb
from chromadb.config import Settings
import time
from embedder_logic import get_embedder
import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
from datetime import datetime, timezone

load_dotenv()
# Set up logging configuration for tracking progress and errors
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", 100)
)  # Batch size for API calls and DB operations


@dataclass
class SearchResult:
    """
    Represents a search result from the ChromaDB database.

    Attributes:
        content (str): The content of the document.
        metadata (Dict[str, Any]): Metadata associated with the document.
        score (float): Relevance score of the search result.
        document_id (str): Unique identifier of the document.
    """

    content: str
    metadata: Dict[str, Any]
    score: float
    document_id: str


def get_vectordb(vector_provider: str = VECTOR_DB):
    if vector_provider == "chromadb":
        return ChromadbVectorStore(CHROMA_COLLECTION_NAME)
    elif vector_provider == "postgres":
        return PgVectorStore(CHROMA_COLLECTION_NAME)
    # elif EMBEDDING_PROVIDER == "OPENAI":
    #     ...

    raise ValueError(f"Unknown vector store: {vector_provider}")


class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        pass

    @abstractmethod
    def search(
        self, query: str, meta_data, limit, min_relevance_score
    ) -> List[SearchResult]:
        pass

    # @abstractmethod
    # def delete(self, text: list[str]) -> list[list[float]]:
    #     pass


class ChromadbVectorStore(VectorStore):
    def __init__(self, collection_name: str) -> None:
        """
        Stores chunks in ChromaDB for later retrieval.

        Args:
            collection_name (str): Name of the ChromaDB collection to use.
        """
        self.collection_name = collection_name
        db_path = os.environ.get("CHROMA_DB_PATH", "database")
        logger.info(f"Using ChromaDB path: {db_path}")
        self.chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,  # Disable usage tracking
                allow_reset=False,  # Prevent accidental database resets
            ),
        )
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"Succesfully connected to collection: {collection_name}")
        except Exception:
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name
            )
            logger.info(
                f"Could not connect to collection named: {collection_name}, Creating new collection"
            )

        self.embedding_provider = get_embedder(EMBEDDING_PROVIDER)

    def add_documents(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        """
        Stores chunks in ChromaDB for later retrieval.

        Args:
            embedded_chunks Optional (List[EmbeddedChunk]): List of chunks with embeddings to store.
            to_embed (bool): Whether the chunks have embeddings or not.
            collection_name (str): Name of the ChromaDB collection to use.
        """
        # Get or create the collection
        collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )

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

    def search(
        self,
        query: str,
        meta_data: Dict[str, Any],
        limit: int = 5,
        min_relevance_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search the database for relevant documents.

        Args:
            query (str): Search query text.
            limit (int, optional): Maximum number of results to return. Defaults to 5.
            metadata_filter (Optional[Dict[str, Any]], optional): Metadata filter for narrowing search. Defaults to None.
            min_relevance_score (float, optional): Minimum relevance score to include results. Defaults to 0.0.

        Returns:
            List[SearchResult]: List of search results meeting the criteria.

        Raises:
            Exception: If there's an error during the search process.
        """
        start_time = time.time()

        try:
            # Get embeddings for the query
            query_embedding = self.embedding_provider.embed_query(query)
            metadata_filter = self.generate_metadata_filter(
                provinces=meta_data.get("provinces"),
                startDate=meta_data.get("startDate", ""),
                endDate=meta_data.get("endDate", ""),
            )
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=metadata_filter,
                include=["metadatas", "distances", "documents"],
            )

            # query_embedding = self._get_fake_embeddings(query)

            ids = results.get("ids") or []
            documents = results.get("documents") or []
            metadatas = results.get("metadatas") or []
            distances = results.get("distances") or []

            ids = ids[0] if ids and ids[0] is not None else []
            documents = documents[0] if documents and documents[0] is not None else []
            metadatas = metadatas[0] if metadatas and metadatas[0] is not None else []
            distances = distances[0] if distances and distances[0] is not None else []

            logger.info(f"number of raw results: {len(ids)}")

            # Process results
            search_results = []
            if ids:
                for idx, (doc_id, document, metadata, distance) in enumerate(
                    zip(ids, documents, metadatas, distances)
                ):
                    score = 1 - (distance / 2)
                    logger.info(f"Result {idx}: ID={doc_id}, Score={score}")
                    if score >= min_relevance_score:
                        search_results.append(
                            SearchResult(
                                content=document,
                                metadata=metadata,
                                score=score,
                                document_id=doc_id,
                            )
                        )

            query_time = time.time() - start_time
            logger.info(
                f"Query executed in {query_time:.2f} seconds, found {len(search_results)} results"
            )

            return search_results

        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise

    def generate_metadata_filter(
        self,
        provinces: List[str] | None,
        startDate: str = None,
        endDate: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a metadata filter for querying documents.

        Args:
            provinces: Optional list of provinces to filter results.
            startDate: Start date in "YYYY-MM-DD" format to filter results.
            endDate: End date in "YYYY-MM-DD" format to filter results.

        Returns:
            Dict[str, Any]: Metadata filter for querying documents. Returns None if no filters are applied.
        """
        filters = []
        if provinces and len(provinces) > 0:
            filters.append({"provincie": {"$in": provinces}})

        date_filters = []
        start_date_epoch_time = int(
            datetime.strptime(startDate, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        end_date_epoch_time = int(
            datetime.strptime(endDate, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        date_filters.append({"datum": {"$gte": start_date_epoch_time}})
        date_filters.append({"datum": {"$lte": end_date_epoch_time}})

        if date_filters:
            filters.append({"$and": date_filters})

        if not filters:
            # If no filters, return an empty filter
            return None
        if len(filters) == 1:
            # If only one filter, return it directly
            return filters[0]
        else:
            # Combine multiple filters with $and
            return {"$and": filters}


class PgVectorStore(VectorStore):
    def __init__(self, collection_name: str) -> None:
        """
        Stores chunks in PostgreSQL using pgvector for later retrieval.

        Args:
            collection_name (str): Logical collection/table namespace.
        """
        self.collection_name = collection_name

        self.host = os.environ.get("PG_HOST")
        self.port = int(os.environ.get("PG_PORT", 5432))
        self.database = os.environ.get("PG_DBNAME")
        self.user = os.environ.get("PG_USER")
        self.password = os.environ.get("PG_PASSWORD")
        self.embedding_provider = get_embedder(EMBEDDING_PROVIDER)

        if not all([self.user, self.password]):
            raise ValueError(
                "PG_USER and PG_PASSWORD environment variables must be set."
            )

        try:
            self.pool = ConnectionPool(
                conninfo="",  # can be empty since we're passing everything via kwargs
                kwargs={
                    "host": self.host,
                    "port": self.port,
                    "dbname": self.database,
                    "user": self.user,
                    "password": self.password,
                    "sslmode": "disable",
                    "autocommit": True,
                },
                min_size=1,
                max_size=10,
                open=True,
            )

            # Tabel 1: documenten
            tbl_documenten = sql.SQL(
                "CREATE TABLE IF NOT EXISTS documenten ("
                "woo_id BIGSERIAL PRIMARY KEY,"
                "file_name text NOT NULL,"
                "url text NOT NULL,"
                "provincie text,"
                "titel text NOT NULL,"
                "datum INTEGER,"
                "type text,"
                "publiekssamenvatting text,"
                "file_type text NOT NULL,"
                "created_at TIMESTAMP DEFAULT NOW(),"
                "updated_at TIMESTAMP DEFAULT NOW()"
                ")"
            )

            # Tabel 2: embeddings (met foreign key naar documenten)
            tbl_embeddings = sql.SQL(
                "CREATE TABLE IF NOT EXISTS embeddings ("
                "chunk_id BIGSERIAL PRIMARY KEY,"
                "woo_id BIGINT NOT NULL REFERENCES documenten(woo_id) ON DELETE CASCADE,"
                "content text NOT NULL,"
                "vector vector({embedding_dim}) NOT NULL,"
                "created_at TIMESTAMP DEFAULT NOW()"
                ")"
            ).format(embedding_dim=sql.Literal(self.embedding_provider.embedding_dim))

            # Index voor vector search op embeddings
            index_query_200 = sql.SQL(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_vector_200 "
                "ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 200);"
            )

            # index_query_1000 = sql.SQL(
            #     "CREATE INDEX IF NOT EXISTS idx_embeddings_vector_1000 "
            #     "ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 1000);"
            # )

            # Voer queries uit via een pooled connection
            with self.pool.connection() as conn:
                conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                register_vector(conn)

                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public';"
                    )
                    print(cursor.fetchall())
                    cursor.execute(tbl_documenten)
                    cursor.execute(tbl_embeddings)
                    cursor.execute(index_query_200)
                    # cursor.execute(index_query_1000)

            logger.info(
                f"Successfully connected to PostgreSQL table: {self.collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            if hasattr(self, "pool") and self.pool:
                self.pool.close()
            raise

    def connect_to_pg(self) -> None:
        """
        If connections fails it raises an ConnectionError
        """
        try:
            logger.info("Connecting to postgres database...")
            self.conn = psycopg.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
                sslmode="disable",
            )
            logger.info("Succesfully connected to postgres database")
        except Exception as e:
            logger.error(f"Could not connect to postgres database: {e}")
            raise ConnectionError

    def add_documents(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        # Assume all chunks belong to same woo verzoek
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                insert_doc_command = """INSERT INTO documenten (file_name, url, provincie, titel, datum, type, publiekssamenvatting, file_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING woo_id;
                """
                insert_emb_command = """INSERT INTO embeddings (woo_id, content, vector)
                VALUES (%s, %s, %s)
                RETURNING woo_id;
                """
                #####################
                # Upload to documents
                chunk = embedded_chunks[0]  # All these values SHOULD be the same
                cur.execute(
                    insert_doc_command,
                    (
                        chunk.metadata["file_name"],
                        chunk.metadata["url"],
                        chunk.metadata["provincie"],
                        chunk.metadata["titel"],
                        chunk.metadata["datum"],
                        chunk.metadata["type"],
                        chunk.metadata["publiekssamenvatting"],
                        chunk.metadata["file_type"],
                    ),
                )
                row = (
                    cur.fetchone()
                )  # Read first result from returned row, we only return woo_id
                if row is None or len(row) == 0:
                    raise ValueError("Failed to insert document or retrieve woo_id")
                woo_id = row[0]

                embeddings_data = [
                    (woo_id, chunk.content, chunk.embedding)
                    for chunk in embedded_chunks
                ]
                cur.executemany(insert_emb_command, embeddings_data)

    def search(
        self,
        query: str,
        meta_data: dict[str, Any],
        limit: int,
        min_relevance_score: float,
    ) -> List[SearchResult]:
        """
        Search for similar chunks in the embeddings table, filtered by date range, provincies, and minimum relevance score.

        Args:
            query: The user's search query.
            meta_data: Dictionary containing filters (start_date, end_date, provincies).
            limit: Maximum number of results to return.
            min_relevance_score: Minimum similarity score to include in results.

        Returns:
            List of SearchResult objects containing chunk content, metadata, and similarity score.
        """
        try:
            query_embedding = self.embedding_provider.embed_query(query)

            filter_conditions = []
            filter_params = []

            start_date = meta_data.get("start_date")
            end_date = meta_data.get("end_date")
            provincies = meta_data.get("provincies")

            if start_date is not None:
                filter_conditions.append(sql.SQL("d.datum >= %s"))
                filter_params.append(start_date)
            if end_date is not None:
                filter_conditions.append(sql.SQL("d.datum <= %s"))
                filter_params.append(end_date)
            if provincies is not None and len(provincies) > 0:
                filter_conditions.append(sql.SQL("d.provincie = ANY(%s)"))
                filter_params.append(provincies)

            where_clause = sql.SQL("")
            if filter_conditions:
                where_clause = sql.SQL("WHERE {}").format(
                    sql.SQL(" AND ").join(filter_conditions)
                )

            search_query = sql.SQL("""
                WITH scored AS (
                    SELECT
                        e.chunk_id,
                        e.content,
                        e.woo_id,
                        d.file_name,
                        d.titel,
                        d.provincie,
                        d.datum,
                        1 - (e.vector <=> %s::vector) AS similarity
                    FROM embeddings e
                    JOIN documenten d ON e.woo_id = d.woo_id
                    {where_clause}
                )
                SELECT *
                FROM scored
                WHERE similarity >= %s
                ORDER BY similarity DESC
                LIMIT %s
            """).format(where_clause=where_clause)

            params = [query_embedding, *filter_params, min_relevance_score, limit]

            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(search_query, params)
                    results = cur.fetchall()

            return [
                SearchResult(
                    content=row[1],
                    metadata={
                        "woo_id": row[2],
                        "file_name": row[3],
                        "titel": row[4],
                        "provincie": row[5],
                        "datum": row[6],
                        "chunk_id": row[0],
                    },
                    score=row[7],
                    document_id=str(row[2]),
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise LookupError
