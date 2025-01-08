from openai import OpenAI
import faiss
import numpy as np
import os
from typing import List

class DocumentChunk:
    def __init__(self, text: str, embedding: np.ndarray):
        self.text = text
        self.embedding = embedding

class Database:
    def __init__(self):
        self.index = None
        self.chunks = []

    def add_chunk(self, chunk: DocumentChunk):
        self.chunks.append(chunk)
        if self.index is None:
            dimension = chunk.embedding.shape[0]
            self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array([chunk.embedding]))

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[DocumentChunk]:
        distances, indices = self.index.search(query_embedding, top_k)
        return [self.chunks[idx] for idx in indices[0]]

class RAG:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        self.client = OpenAI(api_key=self.openai_api_key)
        self.database = Database()

    def chunk_document(self, document, chunk_size=100):
        """Splits a document into chunks of the specified size."""
        return [document[i:i + chunk_size] for i in range(0, len(document), chunk_size)]

    def embed_chunks(self, chunks):
        """Generates embeddings for document chunks using OpenAI's embedding model."""
        embeddings = []
        for chunk in chunks:
            try:
                response = self.client.embeddings.create(input=chunk, model="text-embedding-ada-002")
                embeddings.append(response.data[0].embedding)
            except Exception as e:
                print(f"Error embedding chunk: {e}")
        return np.array(embeddings)

    def store_embeddings(self, chunks, embeddings):
        """Stores embeddings in the database."""
        for chunk, embedding in zip(chunks, embeddings):
            doc_chunk = DocumentChunk(text=chunk, embedding=embedding)
            self.database.add_chunk(doc_chunk)

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generates an embedding for the given text."""
        response = self.client.embeddings.create(input=text, model="text-embedding-ada-002")
        return np.array(response.data[0].embedding)

    def answer_question(self, question, max_chunks=3):
        """Finds the most relevant chunk and generates an answer."""
        try:
            # Embed the question
            question_embedding = self.generate_embedding(question).reshape(1, -1)

            # Search for the most similar chunks
            relevant_chunks = self.database.search(question_embedding, max_chunks)
            most_similar_chunks = " ".join([chunk.text for chunk in relevant_chunks])

            # Use the most relevant chunks to generate an answer
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Context: {most_similar_chunks}\nQuestion: {question}"}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except self.client.exceptions.OpenAIError as e:
            print(f"Error generating answer: {e}")
            return "Sorry, I couldn't generate an answer."

# Example usage
if __name__ == "__main__":
    # Initialize RAG with the OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    rag = RAG(openai_api_key=api_key)

    # Example document
    document = "Dit is een voorbeeld document. Het bevat meerdere zinnen en paragrafen."

    # Chunk the document
    chunks = rag.chunk_document(document)

    # Generate embeddings and store them
    embeddings = rag.embed_chunks(chunks)
    print(embeddings)
    rag.store_embeddings(chunks, embeddings)

    # Ask a question
    question = "Wat bevat het document?"
    answer = rag.answer_question(question)
    print(answer)