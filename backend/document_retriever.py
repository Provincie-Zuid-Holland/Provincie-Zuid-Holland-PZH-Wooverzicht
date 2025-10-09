from datetime import datetime, timezone
import logging
from typing import List, Dict, Any
from chromadb_query import ChromadbQuery
from db_scripts.chromadb import ChromaDB_database
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentRetriever:
    """
    DocumentRetriever class to handle document retrieval and processing.

    Attributes:
        query_engine (ChromaDBQuery): The engine to query documents.
        max_context_chunks (int): Maximum number of context chunks to use.
    """

    def __init__(
        self,
        max_context_chunks: int = 30,
    ):
        """
        Initialize the DocumentRetriever.

        Args:
            max_context_chunks (int): Maximum number of context chunks to retrieve.
        """
        db_path = os.environ.get("CHROMA_DB_PATH")
        collection_name = os.getenv("COLLECTION_NAME", "document_chunks")
        self.db = ChromaDB_database(
            collection_name, db_path
        )  # TODO: pass collection name and path
        self.max_context_chunks = max_context_chunks

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

    def retrieve_relevant_documents(
        self,
        query: str,
        provinces: List[str] | None = None,
        startDate: str = None,
        endDate: str = None,
    ):
        """
        Retrieve relevant documents and chunks from ChromaDB without generating a response.

        Args:
            query: User's search query
            provinces: Optional list of provinces to filter results.
            startDate: Start date in "YYYY-MM-DD" format to filter results.
            endDate: End date in "YYYY-MM-DD" format to filter results.

        Returns:
            dict: Contains both chunks (for citations) and documents (deduplicated)
        """
        try:
            logger.info(
                f"Retrieving documents for query: {query} with provinces: {provinces} and date_range: {startDate} to {endDate}"
            )

            meta_filter = self.generate_metadata_filter(
                provinces=provinces, startDate=startDate, endDate=endDate
            )
            logger.info(f"Using metadata filter: {meta_filter}")
            # Search for relevant chunks
            context_chunks = self.db.query(
                query=query,
                limit=self.max_context_chunks,
                min_relevance_score=0.52,
                metadata_filter=meta_filter,
            )

            # Format chunks for citations
            chunks = []
            for chunk in context_chunks:
                chunk_data = {
                    "id": chunk.document_id,
                    "content": chunk.content,  # or however you access chunk content
                    "relevance_score": getattr(chunk, "relevance_score", None),
                    "metadata": {
                        "url": chunk.metadata.get("url", ""),
                        "provincie": chunk.metadata.get("provincie", ""),
                        "titel": chunk.metadata.get("titel", ""),
                        "datum": chunk.metadata.get("datum", ""),
                        "type": chunk.metadata.get("type", ""),
                        "file_type": chunk.metadata.get("file_type", ""),
                        "file_name": chunk.metadata.get("file_name", ""),
                    },
                }
                chunks.append(chunk_data)

            # Deduplicate to get unique documents based on title
            seen_docs = {}
            for chunk in context_chunks:
                doc_title = chunk.metadata.get("titel", "").strip()
                # Use title as unique identifier, fallback to URL if no title
                doc_key = doc_title if doc_title else chunk.metadata.get("url", "")

                if doc_key and doc_key not in seen_docs:
                    seen_docs[doc_key] = {
                        "id": doc_key,
                        "metadata": {
                            "url": chunk.metadata.get("url", ""),
                            "provincie": chunk.metadata.get("provincie", ""),
                            "titel": chunk.metadata.get("titel", ""),
                            "datum": chunk.metadata.get("datum", ""),
                            "type": chunk.metadata.get("type", ""),
                            "file_type": chunk.metadata.get("file_type", ""),
                            "file_name": chunk.metadata.get("file_name", ""),
                            "publiekssamenvatting": chunk.metadata.get(
                                "publiekssamenvatting", ""
                            ),
                        },
                        "relevance_score": getattr(chunk, "relevance_score", None),
                    }

            documents = list(seen_docs.values())

            return {
                "chunks": chunks,
                "documents": documents,
                "total_chunks": len(chunks),
                "total_documents": len(documents),
            }

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return {
                "chunks": [],
                "documents": [],
                "total_chunks": 0,
                "total_documents": 0,
                "error": str(e),
            }
