
import openai
from db import ChromaDB
from typing import List, Dict

class RAG:
    def __init__(self, openai_api_key: str, db_path: str):
        openai.api_key = openai_api_key
        self.db = ChromaDB(db_path=db_path)

    def chunk_text(self, text: str, chunk_size: int = 512) -> List[str]:
        """
        Chunk the text into smaller pieces.
        :param text: The original text to be chunked.
        :param chunk_size: The maximum size of each chunk.
        :return: List of text chunks.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding for the given text using OpenAI.
        :param text: The text to be embedded.
        :return: List of float values representing the embedding.
        """
        response = openai.Embedding.create(input=text, model="text-embedding-ada-002")
        return response['data'][0]['embedding']

    def add_text(self, text: str):
        """
        Add text to the database by chunking it and creating embeddings.
        :param text: The original text to be added.
        """
        chunks = self.chunk_text(text)
        for chunk in chunks:
            embedding = self.create_embedding(chunk)
            metadata = {"text": chunk}
            self.db.add_embedding(embedding, metadata)
        self.db.save()

    def embed_query(self, query: str) -> List[float]:
        """
        Create an embedding for the query.
        :param query: The query text.
        :return: List of float values representing the query embedding.
        """
        return self.create_embedding(query)

    def generate_answer(self, query: str, top_k: int = 5) -> str:
        """
        Generate an answer using similar embeddings from the database.
        :param query: The query text.
        :param top_k: Number of top similar results to consider.
        :return: Generated answer.
        """
        query_embedding = self.embed_query(query)
        similar_texts = self.db.similarity_search(query_embedding, top_k=top_k)
        context = " ".join([item['text'] for item in similar_texts])

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Answer the question based on the following context:\n\n{context}\n\nQuestion: {query}\nAnswer:",
            max_tokens=150
        )
        return response['choices'][0]['text'].strip()

# Example usage
if __name__ == "__main__":
    rag = RAG(openai_api_key="your_openai_api_key", db_path="path/to/your/db")

    # Add text to the database
    text = "Your long text goes here..."
    rag.add_text(text)

    # Generate an answer to a query
    query = "Your query goes here..."
    answer = rag.generate_answer(query)
    print("Generated Answer:", answer)