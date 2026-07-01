from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class ChunkData:
    """
    Stores a chunk of text and its associated metadata.

    Attributes:
        chunk_id (str): Unique identifier for the chunk.
        content (str): The text content of the chunk.
        metadata (Dict[str, Any]): Dictionary containing all metadata associated with the chunk.
    """

    chunk_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class EmbeddedChunk(ChunkData):
    """
    Extends ChunkData to include the embedding vector.

    Attributes:
        embedding (List[float]): Vector representation of the chunk content.
    """

    embedding: List[float]
