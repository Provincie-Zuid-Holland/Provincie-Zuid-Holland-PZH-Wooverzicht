import os
import json
from config import JSON_FOLDER
from openai import OpenAI
from dotenv import load_dotenv
import chromadb.utils.embedding_functions as embedding_functions
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings


# Load environment variables
load_dotenv()

# # Set up OpenAI API key
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize PersistentClient
chroma_client = chromadb.PersistentClient(
    path="database",  
    settings=Settings(),
    tenant=DEFAULT_TENANT,
    database=DEFAULT_DATABASE,
)

collection_name = "pdf_chunks"
# collection = chroma_client.get_or_create_collection(name=collection_name)

# Define the embedding function 
embedding_function = embedding_functions.OpenAIEmbeddingFunction(api_key=os.getenv('OPENAI_API_KEY'))
collection = chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)


def find_matching_context(user_query, top_n=5):
    """
    Match the user query with the data in ChromaDB and return top_n results.
    
    :param user_query: The user's input query (str).
    :param top_n: The number of top matches to retrieve.
    :return: List of matching contexts.
    """
    # Query ChromaDB to find the most relevant documents
    results = collection.query(
        query_texts=[user_query],  # The query text
        n_results=top_n            # Number of top results to retrieve
    )
    
    # Extract the matching contexts from the results
    matching_contexts = results['documents']
    return matching_contexts

# Example usage
if __name__ == "__main__":
    user_query = "zonnepanelen"
    top_matches = find_matching_context(user_query, top_n=3)
    
    print("Top Matching Contexts:")
    for i, context in enumerate(top_matches, 1):
        print(f"{i}. {context}")
    
    # # Prepare context for LLM
    # llm_input = " ".join(top_matches)
    # print("\nContext for LLM:")
    # print(llm_input)
