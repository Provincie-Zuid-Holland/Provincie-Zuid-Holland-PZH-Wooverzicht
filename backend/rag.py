from openai import OpenAI

import faiss
import numpy as np
import os


class RAG:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        self.client = OpenAI(api_key=self.openai_api_key)
        self.index = None
        self.chunks = None

    def chunk_document(self, document, chunk_size=100):
        """Splits a document into chunks of the specified size."""
        return [document[i:i + chunk_size] for i in range(0, len(document), chunk_size)]

    def embed_chunks(self, chunks):
        """Generates embeddings for document chunks using OpenAI's embedding model."""
        embeddings = []
        for chunk in chunks:
            try:
                response = self.client.embeddings.create(input=chunk,
                model="text-embedding-ada-002")
                embeddings.append(response.data[0].embedding)
            except Exception as e:
                print(f"Error embedding chunk: {e}")
        return np.array(embeddings)

    def store_embeddings(self, embeddings):
        """Stores embeddings in a FAISS index."""
        if embeddings.size == 0:
            raise ValueError("Embeddings array is empty.")
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    def answer_question(self, question, max_chunks=3):
        """Finds the most relevant chunk and generates an answer."""
        try:
            # Embed the question
            response = self.client.embeddings.create(input=question,
            model="text-embedding-ada-002")
            question_embedding = np.array(response.data[0].embedding).reshape(1, -1)

            # Search for the most similar chunks
            distances, indices = self.index.search(question_embedding, max_chunks)
            most_similar_chunks = " ".join([self.chunks[idx] for idx in indices[0]])

            # Use the most relevant chunks to generate an answer
            response = self.client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Context: {most_similar_chunks}\nQuestion: {question}"}
            ],
            max_tokens=150)
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
    rag.chunks = chunks

    # Generate embeddings and store them
    embeddings = rag.embed_chunks(chunks)
    print(embeddings)
    rag.store_embeddings(embeddings)

    # Ask a question
    question = "Wat bevat het document?"
    answer = rag.answer_question(question)
    print(answer)
