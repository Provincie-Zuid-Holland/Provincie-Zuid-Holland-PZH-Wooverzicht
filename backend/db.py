import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_utils

class ChromaDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.client = chromadb.Client(Settings(persist_directory=db_path))
        self.collection = self.client.create_collection(name="embeddings")

    def add_embedding(self, embedding, metadata):
        """
        Add an embedding with its metadata to the database.
        :param embedding: List of float values representing the embedding.
        :param metadata: Dictionary containing the original text and any other metadata.
        """
        self.collection.add(embedding, metadata)

    def similarity_search(self, query_embedding, top_k=5):
        """
        Perform a similarity search to find the most similar embeddings.
        :param query_embedding: List of float values representing the query embedding.
        :param top_k: Number of top similar results to return.
        :return: List of metadata for the top similar embeddings.
        """
        results = self.collection.query(query_embedding, top_k=top_k)
        return results

    def save(self):
        """
        Save the database to disk.
        """
        self.client.persist()

    def load(self):
        """
        Load the database from disk.
        """
        self.client = chromadb.Client(Settings(persist_directory=self.db_path))
        self.collection = self.client.get_collection(name="embeddings")

# Example usage
if __name__ == "__main__":
    db = ChromaDB(db_path="path/to/your/db")

    # Add an embedding with metadata
    embedding = [0.1, 0.2, 0.3]  # Example embedding
    metadata = {"text": "This is the original text", "other_info": "Additional metadata"}
    db.add_embedding(embedding, metadata)

    # Perform a similarity search
    query_embedding = [0.1, 0.2, 0.3]  # Example query embedding
    results = db.similarity_search(query_embedding)
    print("Similarity Search Results:", results)

    # Save the database to disk
    db.save()

    # Load the database from disk
    db.load()