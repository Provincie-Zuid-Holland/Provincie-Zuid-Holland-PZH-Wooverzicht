"""
Demo script for the Conversational RAG system
"""

from conversational_rag import ConversationalRAG

def demo_conversation():
    # Initialize the RAG system
    rag = ConversationalRAG()
    
    # Example queries to test
    test_queries = [
        "Wat zijn de belangrijkste zorgen over de windturbines in Daarle?",
        "Welke beslissingen zijn er genomen over het weidevogelgebied?",
        "Kun je de tijdlijn van het project uitleggen?"
    ]
    
    for query in test_queries:
        print(f"\nVraag: {query}")
        print("-" * 80)
        
        # Generate and format response
        response = rag.generate_response(query)
        formatted_response = rag.format_response_with_sources(response)
        
        # Print the results
        print(formatted_response)
        print("-" * 80)

if __name__ == "__main__":
    print("Starting RAG Demo...")
    demo_conversation()