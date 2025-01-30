"""
ChromaDB Query Module

This module provides functionality to search and retrieve documents from the ChromaDB vector database.
It supports similarity-based searches with metadata filtering and returns ranked results.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from chromadb.api.models import Collection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    score: float
    document_id: str

class ChromaDBQuery:
    def __init__(
        self,
        collection_name: str = "document_chunks",
        database_path: str = "database",
        openai_api_key: Optional[str] = None
    ):
        """Initialize the query interface to ChromaDB."""
        self.collection_name = collection_name
        
        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=database_path,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Successfully connected to collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error connecting to collection: {e}")
            raise

    def _get_embeddings(self, text: str) -> List[float]:
        """Get embeddings using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",  # Use the same model as in createdb.py
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise

    def search(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        min_relevance_score: float = 0.0
    ) -> List[SearchResult]:
        """Search the database for relevant documents."""
        start_time = time.time()
        
        try:
            # Get embeddings for the query
            query_embedding = self._get_embeddings(query)
            
            # Perform the search
            results = self.collection.query(
                query_embeddings=[query_embedding],  # Use embeddings instead of text
                n_results=limit,
                where=metadata_filter,
                include=['metadatas', 'distances', 'documents']
            )
            
            # Process results
            search_results = []
            if results['ids'][0]:
                for idx, (doc_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    score = 1 - (distance / 2)
                    if score >= min_relevance_score:
                        search_results.append(SearchResult(
                            content=document,
                            metadata=metadata,
                            score=score,
                            document_id=doc_id
                        ))
            
            query_time = time.time() - start_time
            logger.info(f"Query executed in {query_time:.2f} seconds, found {len(search_results)} results")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise
            
    def search_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Search documents using only metadata filters.
        
        Args:
            metadata_filter: Filter conditions for metadata fields
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=limit,
                include=['metadatas', 'documents']
            )
            
            search_results = []
            for doc_id, document, metadata in zip(
                results['ids'],
                results['documents'],
                results['metadatas']
            ):
                search_results.append(SearchResult(
                    content=document,
                    metadata=metadata,
                    score=1.0,  # No relevance score for metadata-only queries
                    document_id=doc_id
                ))
                
            return search_results
            
        except Exception as e:
            logger.error(f"Error during metadata search: {e}")
            raise
            
    def get_similar_documents(
        self,
        document_id: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Find documents similar to a given document by ID.
        
        Args:
            document_id: ID of the reference document
            limit: Maximum number of similar documents to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            results = self.collection.get(
                ids=[document_id],
                include=['embeddings']
            )
            
            if not results['embeddings']:
                raise ValueError(f"Document with ID {document_id} not found")
                
            # Use the embedding to find similar documents
            similar_docs = self.collection.query(
                query_embeddings=results['embeddings'],
                n_results=limit + 1  # Add 1 to exclude the query document itself
            )
            
            # Process results (skip the first one if it's the query document)
            search_results = []
            start_idx = 1 if similar_docs['ids'][0][0] == document_id else 0
            
            for idx, (doc_id, document, metadata, distance) in enumerate(zip(
                similar_docs['ids'][0][start_idx:],
                similar_docs['documents'][0][start_idx:],
                similar_docs['metadatas'][0][start_idx:],
                similar_docs['distances'][0][start_idx:]
            )):
                score = 1 - (distance / 2)
                search_results.append(SearchResult(
                    content=document,
                    metadata=metadata,
                    score=score,
                    document_id=doc_id
                ))
                
            return search_results
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary containing collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise