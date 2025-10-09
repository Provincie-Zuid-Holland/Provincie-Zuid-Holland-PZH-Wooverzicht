"""
Base class for vector database implementations.
"""


class VectorDatabase:
    def add_embeddings(self, embeddings):
        raise NotImplementedError

    def query(self, query_vector, top_k):
        raise NotImplementedError
