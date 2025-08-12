"""
FastAPI Backend for WOO Document Search and QA System

This service provides API endpoints for:
1. Querying the RAG system with streaming responses
2. Health checking
"""

import json
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from conversational_rag import ConversationalRAG
from sse_starlette.sse import EventSourceResponse
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
# Get the directory where the script is located, to prevent issues with relative paths
script_dir = Path(__file__).parent.absolute()
load_dotenv(
    dotenv_path=script_dir / ".env"
)  # This will load from .env in the backend directory
print(f"CHROMA_DB_PATH: {os.environ.get('CHROMA_DB_PATH', 'Not set')}")

print("$")
# Initialize the FastAPI app
app = FastAPI(
    title="WOOverzicht API",
    description="API for WOO document search and QA system",
    version="1.0.0",
)

# Add CORS middleware to allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system and query logger
rag_system = ConversationalRAG()


# Define data models
class QueryRequest(BaseModel):
    """Request model for queries."""

    query: str
    session_id: str


class Source(BaseModel):
    """Source document metadata."""

    titel: str
    url: str
    provincie: str
    datum: str
    type: str
    relevance_score: float
    publiekssamenvatting: str


class RetrieveDocsDict(TypedDict, total=False):
    """Type definition for dictionary structure when retrieving documents."""

    query: str
    filters: (
        dict | None
    )  # Optional field for additional filters. Elements that should be in the dict:
    # provinces: List[str] | None  # Optional field for provinces used in filtering
    # startDate: str  # Field for start date in YYYY-MM-DD format
    # endDate: str  # Field for end date in YYYY-MM-DD format


# API endpoint to add to your FastAPI app
@app.post("/api/query/documents")
async def retrieve_documents(request: RetrieveDocsDict):
    """
    Retrieve relevant documents for a query without generating a response.

    Args:
        request: Simple dict with 'query' key, 'provinces' key (optional) and 'daterange' key (optional).
                    'provinces' key is a list of provinces used for filtering.
                    'daterange' is also optional and should be a list of two date strings, format "%Y-%m-%d" (also used for filtering).

    Returns:
        JSON response with relevant documents and chunks
    """
    try:
        query = request.get("query", "")
        filters = request.get("filters", {})
        if not isinstance(filters, dict):
            raise ValueError("Filters must be a dictionary")
        provinces = filters.get("provinces", None)
        startDate = filters.get("startDate", None)
        endDate = filters.get("endDate", None)
        logger.info(
            f"Received query: {query} with provinces: {provinces}, date range: {startDate} to {endDate}"
        )
        if not query:
            return {"error": "Query is required"}
        # Validate provinces if provided
        if provinces is not None:
            if not isinstance(provinces, list):
                raise ValueError("Provinces must be a list")
            for province in provinces:
                if not isinstance(province, str):
                    raise ValueError("Each province must be a string")
        if startDate is None or endDate is None:
            raise ValueError(
                f"startDate and endDate are required, but one or both were not provided: {startDate}, {endDate}"
            )
        result = rag_system.retrieve_relevant_documents(
            query, provinces=provinces, startDate=startDate, endDate=endDate
        )
        print("Result:", result)
        print({"success": True, "query": query, **result}, flush=True)
        return {"success": True, "query": query, **result}

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "chunks": [],
            "documents": [],
            "total_chunks": 0,
            "total_documents": 0,
        }


# Define API endpoints
@app.post("/api/query/stream")
async def query_documents_stream(request: QueryRequest):
    """
    Stream a response to a user query.

    Args:
        request: The query request containing the query and session_id.

    Returns:
        EventSourceResponse: A server-sent events response with chunks of the answer.
    """

    async def event_generator():
        try:
            # print("Starting event generation")
            sources = []
            chunks_used = []
            response_text = ""
            start_time = datetime.now()

            # Generate streaming response
            for chunk in rag_system.generate_response_stream(request.query):
                if isinstance(chunk, str):
                    # Send text chunk
                    response_text += chunk
                    # print(f"Sending chunk: {chunk}")
                    yield {"event": "chunk", "data": chunk}
                    await asyncio.sleep(
                        0.01
                    )  # Small delay to avoid overwhelming client
                elif isinstance(chunk, dict) and "sources" in chunk:
                    # Send sources
                    sources = chunk["sources"]
                    if "document_ids" in chunk:
                        chunks_used = chunk["document_ids"]
                    # print(f"Sending sources: {len(sources)} items")
                    yield {
                        "event": "sources",
                        "data": json.dumps({"sources": sources}),
                    }

            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()

            # Log the interaction
            metadata = {
                "sources": sources,
                "response_time": response_time,
                "chunks_used": chunks_used,
                "timestamp": datetime.now().isoformat(),
            }

            # Send completion event
            yield {"event": "complete", "data": json.dumps({"metada": metadata})}

        except Exception as e:
            # Send error event
            yield {"event": "error", "data": {"error": str(e)}}

    return EventSourceResponse(event_generator())


@app.get("/api/health")
async def health_check():
    """
    Check if the API is healthy.

    Returns:
        dict: A simple health status message.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Run the API with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
