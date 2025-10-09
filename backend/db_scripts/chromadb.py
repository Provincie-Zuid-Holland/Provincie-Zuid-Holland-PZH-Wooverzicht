from base import VectorDatabase
from createdb import EmbeddedChunk
import os
import logging
import time
from typing import Any, Dict, Optional
from chromadb_query import SearchResult


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", 100)
)  # Batch size for API calls and DB operations


class ChromaDB_database(VectorDatabase):
    def __init__(self, collection_name: str, database_path: str):
        """
        Initialize the ChromaDB vector database with the specified collection name.
        """
        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=database_path,  # Use environment variable
            settings=Settings(
                anonymized_telemetry=False,  # Disable usage tracking
                allow_reset=False,  # Prevent accidental database resets
            ),
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_embeddings(self, embedded_chunks: list[EmbeddedChunk]):
        """
        Add embeddings to the ChromaDB collection.

        Args:
            embeddings (list[dict]): A list of dictionaries containing 'id', 'embedding', and 'metadata'.
        """
        """
        Stores embedded chunks in ChromaDB for later retrieval.

        Args:
            embedded_chunks (List[EmbeddedChunk]): List of chunks with embeddings to store.
        """

        # Add chunks to database in batches
        for i in range(0, len(embedded_chunks), BATCH_SIZE):
            batch = embedded_chunks[i : i + BATCH_SIZE]
            try:
                self.collection.add(
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

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        min_relevance_score: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> list[dict]:
        """
        Query the ChromaDB collection for similar embeddings.

        Args:
            query_embedding (list[float]): The embedding vector to query.
            n_results (int): The number of similar results to return.
            min_relevance_score (float, optional): Minimum relevance score to include results. Defaults to 0.0.
            metadata_filter (Optional[Dict[str, Any]], optional): Metadata filter for narrowing search. Defaults to None.

        Returns:
            List[SearchResult]: List of search results meeting the criteria.

        Raises:
            Exception: If there's an error during the search process.
        """
        try:
            start_time = time.time()
            # Perform the search
            results = self.collection.query(
                query_embeddings=[query_embedding],  # Use embeddings instead of text
                n_results=n_results,
                where=metadata_filter,
                include=["metadatas", "distances", "documents"],
            )

            # Process results
            search_results = []
            if results["ids"][0]:
                for idx, (doc_id, document, metadata, distance) in enumerate(
                    zip(
                        results["ids"][0],
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ):
                    score = 1 - (distance / 2)
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
