import logging
from typing import List
from vectordb_logic import get_vectordb

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentRetriever:
    """
    DocumentRetriever class to handle document retrieval and processing.

    Attributes:
        query_engine: The engine to query documents.
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
        self.query_engine = get_vectordb()
        self.max_context_chunks = max_context_chunks

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

            meta_data = {
                "provinces": [provinces],
                "startDate": startDate,
                "endDate": endDate,
            }
            logger.info(f"Using metadata: {meta_data}")
            # Search for relevant chunks
            context_chunks = self.query_engine.search(
                query=query,
                meta_data=meta_data,
                limit=self.max_context_chunks,
                min_relevance_score=0.0,
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
