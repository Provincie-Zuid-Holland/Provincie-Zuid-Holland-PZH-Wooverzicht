"""
Conversational RAG Module
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from openai import OpenAI
from chromadb_query import ChromaDBQuery, SearchResult

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RAGResponse:
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
       self.query_engine = ChromaDBQuery()
       self.client = OpenAI()
       self.model = model
       self.temperature = temperature
       self.max_context_chunks = max_context_chunks

   def _format_context(self, chunks: List[SearchResult]) -> str:
       context_parts = []
       for idx, chunk in enumerate(chunks, 1):
           file_name = chunk.metadata.get("file_name", "Unknown document")
           date = chunk.metadata.get("Creatie jaar", "Unknown date")
           theme = chunk.metadata.get("metadata.WOO themas", "Unknown theme")
           context_parts.append(
               f"Document {idx}:\n"
               f"Source: {file_name}\n"
               f"Date: {date}\n"
               f"Theme: {theme}\n"
               f"Content: {chunk.content}\n"
           )
       return "\n".join(context_parts)

   def _create_system_prompt(self) -> str:
       return (
           "Je bent een WOO (Wet Open Overheid) specialist die burgers helpt bij het vinden en begrijpen van overheidsinformatie.\n\n"
           "KERNPRINCIPES:\n"
           "- Geef ALLEEN antwoord op basis van de aangeleverde documenten\n"
           "- Als er geen relevante informatie in de documenten staat, zeg dit expliciet\n"
           "- Maak NOOIT aannames of gebruik NOOIT externe kennis\n\n"
           "BRONVERWIJZING:\n"
           "- Geef aan wanneer informatie uit meerdere bronnen komt\n"
           "- Vermeld expliciet als relevante documenten ontbreken\n\n"
           "INFORMATIEVOORZIENING:\n"
           "- Leg uit wat wel/niet openbaar is gemaakt\n"
           "- Verbind informatie uit verschillende documenten\n"
           "- Geef context bij oudere vs nieuwe besluiten\n"
           "- Maak onderscheid tussen feiten en interpretaties\n\n"
           "TAALGEBRUIK:\n"
           "- Schrijf in helder, toegankelijk Nederlands\n"
           "- Vermijd ambtelijke taal\n"
           "- Structureer lange antwoorden met kopjes\n"
           "- Wees neutraal en zorgvuldig\n\n"
           "PRIVACY:\n"
           "- Bescherm persoonsgegevens\n"
           "- Let extra op bij gelakte/verwijderde informatie\n"
           "- Verwijs door bij juridische vragen"
       )

   def _format_user_prompt(self, query: str, context: str) -> str:
       return (
           f"Gebruik de volgende documenten als context om deze vraag te beantwoorden:\n\n"
           f"Context documenten:\n{context}\n\n"
           f"Vraag: {query}\n\n"
           f"Antwoord: "
       )

   def generate_response(self, query: str) -> RAGResponse:
       start_time = time.time()
       try:
           context_chunks = self.query_engine.search(query=query, limit=self.max_context_chunks)
           
           if not context_chunks:
               return RAGResponse(
                   answer="Ik kon geen relevante documenten vinden om je vraag te beantwoorden.",
                   sources=[],
                   error="No relevant documents found"
               )

           context = self._format_context(context_chunks)
           system_prompt = self._create_system_prompt()
           user_prompt = self._format_user_prompt(query, context)

           response = self.client.chat.completions.create(
               model=self.model,
               messages=[
                   {"role": "system", "content": system_prompt},
                   {"role": "user", "content": user_prompt}
               ],
               temperature=self.temperature,
               max_tokens=1000
           )

           sources = [{
               "file_name": chunk.metadata.get("file_name", "Unknown"),
               "date": chunk.metadata.get("Creatie jaar", "Unknown"),
               "theme": chunk.metadata.get("metadata.WOO themas", "Unknown"),
               "relevance_score": chunk.score
           } for chunk in context_chunks]

           return RAGResponse(
               answer=response.choices[0].message.content,
               sources=sources,
               context_used=[chunk.content for chunk in context_chunks],
               processing_time=time.time() - start_time
           )

       except Exception as e:
           logger.error(f"Error generating response: {e}")
           return RAGResponse(
               answer="Er is een fout opgetreden bij het verwerken van je vraag. Probeer het later opnieuw.",
               sources=[],
               error=str(e)
           )

   def format_response_with_sources(self, response: RAGResponse) -> str:
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