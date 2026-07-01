from abc import ABC, abstractmethod
from dotenv import load_dotenv
from config import CHROMA_COLLECTION_NAME
from typing import Optional, List
from dataclass.embedded_chunk import EmbeddedChunk
from dataclasses import dataclass
from typing import Dict, Any
import logging
import os
import chromadb
from chromadb.config import Settings

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


def get_vectordb(vector_provider: str):
    if vector_provider == "chromadb":
        return ChromadbVectorStore(CHROMA_COLLECTION_NAME)
    elif vector_provider == "postgres":
        return PgVectorStore()
    # elif EMBEDDING_PROVIDER == "OPENAI":
    #     ...

    raise ValueError(f"Unknown vector store: {vector_provider}")


class VectorStore(ABC):

    @abstractmethod
    def add_documents(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        pass

    @abstractmethod
    def search(
        self, query: str, limit, metadata_filter, min_relevance_score
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
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
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
            logger.info(f"Using EMBEDDING_MODEL: {EMBEDDING_MODEL}")
            if EMBEDDING_MODEL:
                query_embedding = self.embedding_provider.embed_query(query)
                results = self.collection.query(
                    query_embeddings=[
                        query_embedding
                    ],  # Use embeddings instead of text
                    # query_texts=[query],
                    n_results=limit,
                    where=metadata_filter,
                    include=["metadatas", "distances", "documents"],
                )
            else:
                # No embedding model given, so use default model (sentence transformer)
                query_embedding = self.embedding_provider.embed_query(query)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=metadata_filter,
                    include=["metadatas", "distances", "documents"],
                )

            # query_embedding = self._get_fake_embeddings(query)

            logger.info(f"number of raw results: {len(results['ids'][0])}")

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
                    logger.info(f"Result {idx}: ID={doc_id}, Score={score}")
                    # if score >= min_relevance_score:
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


class PgVectorStore(VectorStore):
    def __init__(self) -> None:
        super().__init__()
