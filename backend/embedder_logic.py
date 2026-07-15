from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from config import EMBEDDING_MODEL
import os

load_dotenv()


def get_embedder(embedding_provider: str):
    if embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbedder()
    # elif EMBEDDING_PROVIDER == "OPENAI":
    #     ...

    raise ValueError(f"Unknown embedding provider: {embedding_provider}")


class Embedder(ABC):

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_document(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass

    # def embed_batch(self, texts: list[str]) -> list[list[float]]:
    #     return [self.embed(t) for t in texts]


class SentenceTransformerEmbedder(Embedder):
    def __init__(self):
        access_token = os.getenv("HF_TOKEN", "")
        self.model = SentenceTransformer(EMBEDDING_MODEL, token=access_token)
        self.embedding_dim = self.model.get_embedding_dimension()

    def embed_query(self, text: str) -> list[float]:
        try:
            return self.model.encode_query(text).tolist()
        except Exception:
            return self.model.encode(text).tolist()

    def embed_document(self, text: str) -> list[float]:
        try:
            return self.model.encode_document(text).tolist()
        except Exception:
            return self.model.encode(text).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.model.encode_document(texts).tolist()
        except Exception:
            return self.model.encode(texts).tolist()
