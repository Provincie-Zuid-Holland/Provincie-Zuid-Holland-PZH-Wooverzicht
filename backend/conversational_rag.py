"""
Conversational RAG (Retrieval-Augmented Generation) Module

This module combines ChromaDB document retrieval with OpenAI's API to create
a conversational interface for answering WOO-related queries with proper source citations.

The system:
1. Retrieves relevant document chunks from ChromaDB
2. Uses these chunks as context for OpenAI's API
3. Generates responses with source citations
4. Handles errors gracefully
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from openai import OpenAI
from chromadb_query import ChromaDBQuery, SearchResult

# Set up logging
logging.basicConfig(
   level=logging.INFO,
   format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RAGResponse:
   """Container for the RAG system response and its metadata"""
   answer: str
   sources: List[Dict[str, Any]]
   error: Optional[str] = None
   context_used: Optional[List[str]] = None
   processing_time: Optional[float] = None

class ConversationalRAG:
   def __init__(
       self,
       model: str = "gpt-4-turbo-preview",
       temperature: float = 0.7,
       max_context_chunks: int = 5
   ):
       """
       Initialize the conversational RAG system.
       
       Args:
           model: OpenAI model to use
           temperature: OpenAI temperature parameter
           max_context_chunks: Maximum number of context chunks to use
       """
       self.query_engine = ChromaDBQuery()
       self.client = OpenAI()
       self.model = model
       self.temperature = temperature
       self.max_context_chunks = max_context_chunks

   def _format_context(self, chunks: List[SearchResult]) -> str:
       """Format retrieved chunks with metadata for context"""
       context_parts = []
       
       for idx, chunk in enumerate(chunks, 1):
           # Extract key metadata
           file_name = chunk.metadata.get("file_name", "Unknown document")
           date = chunk.metadata.get("Creatie jaar", "Unknown date")
           theme = chunk.metadata.get("metadata.WOO thema's", "Unknown theme")
           
           # Format the context entry
           context_parts.append(
               f"Document {idx}:\n"
               f"Source: {file_name}\n"
               f"Date: {date}\n"
               f"Theme: {theme}\n"
               f"Content: {chunk.content}\n"
           )
       
       return "\n".join(context_parts)

   def _create_system_prompt(self) -> str:
       """Create the system prompt for OpenAI"""
       return (
           "Je bent een behulpzame assistent die vragen beantwoordt over WOO (Wet Open Overheid) documenten. "
           "Gebruik de gegeven documenten om de vraag te beantwoorden. "
           "- Citeer altijd je bronnen met [Bron: bestandsnaam] notatie. "
           "- Als je niet zeker bent of als de informatie niet in de documenten staat, geef dit dan aan. "
           "- Vat de informatie samen in een duidelijk, professioneel Nederlands antwoord. "
           "- Focus op feitelijke informatie uit de documenten. "
           "- Als er tegenstrijdige informatie is, geef dit dan aan."
       )

   def _format_user_prompt(self, query: str, context: str) -> str:
       """Format the user prompt with query and context"""
       return (
           f"Gebruik de volgende documenten als context om deze vraag te beantwoorden:\n\n"
           f"Context documenten:\n{context}\n\n"
           f"Vraag: {query}\n\n"
           f"Antwoord: "
       )

   def generate_response(self, query: str) -> RAGResponse:
       """
       Generate a response using RAG with source citations.
       
       Args:
           query: User's question
           
       Returns:
           RAGResponse object containing answer and sources
       """
       start_time = time.time()
       
       try:
           # Retrieve relevant chunks
           context_chunks = self.query_engine.search(
               query=query,
               limit=self.max_context_chunks
           )
           
           if not context_chunks:
               return RAGResponse(
                   answer="Ik kon geen relevante documenten vinden om je vraag te beantwoorden.",
                   sources=[],
                   error="No relevant documents found"
               )
           
           # Format context and create prompts
           context = self._format_context(context_chunks)
           system_prompt = self._create_system_prompt()
           user_prompt = self._format_user_prompt(query, context)
           
           # Generate response using OpenAI
           response = self.client.chat.completions.create(
               model=self.model,
               messages=[
                   {"role": "system", "content": system_prompt},
                   {"role": "user", "content": user_prompt}
               ],
               temperature=self.temperature,
               max_tokens=1000
           )
           
           # Format sources
           sources = [{
               "file_name": chunk.metadata.get("file_name", "Unknown"),
               "date": chunk.metadata.get("Creatie jaar", "Unknown"),
               "theme": chunk.metadata.get("metadata.WOO thema's", "Unknown"),
               "relevance_score": chunk.score
           } for chunk in context_chunks]
           
           processing_time = time.time() - start_time
           
           return RAGResponse(
               answer=response.choices[0].message.content,
               sources=sources,
               context_used=[chunk.content for chunk in context_chunks],
               processing_time=processing_time
           )
           
       except Exception as e:
           logger.error(f"Error generating response: {e}")
           return RAGResponse(
               answer="Er is een fout opgetreden bij het verwerken van je vraag. "
                      "Probeer het later opnieuw.",
               sources=[],
               error=str(e)
           )

   def format_response_with_sources(self, response: RAGResponse) -> str:
       """Format the complete response with source citations"""
       if response.error:
           return f"Error: {response.error}"
       
       formatted_response = response.answer + "\n\nBronnen:\n"
       
       for idx, source in enumerate(response.sources, 1):
           formatted_response += (
               f"{idx}. {source['file_name']}\n"
               f"   Datum: {source['date']}\n"
               f"   Thema: {source['theme']}\n"
               f"   Relevantie: {source['relevance_score']:.2f}\n"
           )
           
       if response.processing_time:
           formatted_response += f"\nVerwerkingstijd: {response.processing_time:.2f} seconden"
           
       return formatted_response