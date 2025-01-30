"""
Test runner script with detailed output for ChromaDB Query tests
"""

from chromadb_query import ChromaDBQuery
import time

def run_manual_tests():
    """Run manual tests with detailed output"""
    query = ChromaDBQuery()
    
    print("\n=== Testing Basic Search ===")
    test_queries = [
        "What are the requirements for project Daarle?",
        "windturbines weidevogelgebied",
        "location Daarle"
    ]
    
    for test_query in test_queries:
        print(f"\nQuery: {test_query}")
        start_time = time.time()
        results = query.search(test_query, limit=3)
        query_time = time.time() - start_time
        
        print(f"Found {len(results)} results in {query_time:.2f} seconds")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Score: {result.score:.3f}")
            print(f"Document ID: {result.document_id}")
            print(f"Content Preview: {result.content[:200]}...")
            print("Metadata:", result.metadata)
            
    print("\n=== Testing Metadata Search ===")
    metadata_filter = {"metadata.Creatie jaar": "2024"}
    results = query.search_by_metadata(metadata_filter)
    print(f"Found {len(results)} documents from 2024")
    
    print("\n=== Collection Statistics ===")
    stats = query.get_collection_stats()
    print(f"Total documents: {stats['document_count']}")
    print(f"Collection name: {stats['collection_name']}")

if __name__ == "__main__":
    print("Running detailed ChromaDB Query tests...")
    run_manual_tests()



