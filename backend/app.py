"""
Streamlit Frontend for WOO Document Search and QA System

This application provides a user interface for:
1. Searching through WOO documents
2. Asking questions about the documents
3. Viewing document sources and metadata
"""

import streamlit as st
from datetime import datetime
from conversational_rag import ConversationalRAG
from chromadb_query import ChromaDBQuery

# Initialize the RAG system
@st.cache_resource
def get_rag_system():
    return ConversationalRAG()

@st.cache_resource
def get_query_system():
    return ChromaDBQuery()

def display_chat_message(role: str, content: str):
    """Display a chat message with the appropriate styling"""
    if role == "user":
        st.write(f'🧑‍💼 **You:** {content}')
    elif role == "assistant":
        st.write(f'🤖 **Assistant:** {content}')
    else:
        st.write(content)

def display_sources(sources):
    """Display source information in an organized way"""
    with st.expander("📚 View Sources", expanded=False):
        for idx, source in enumerate(sources, 1):
            st.markdown(f"""
            **Source {idx}:**
            - File: `{source['file_name']}`
            - Date: {source['date']}
            - Theme: {source['theme']}
            - Relevance Score: {source['relevance_score']:.2f}
            """)

def main():
    # Page configuration
    st.set_page_config(
        page_title="W👀verzicht",
        page_icon="📑",
        layout="wide"
    )

    # Header
    st.title("🔍 W👀verzicht")
    st.markdown("""
    Deze applicatie helpt je bij het zoeken en analyseren van WOO-documenten.
    Je kunt zowel specifieke documenten zoeken als vragen stellen over de inhoud.
    """)

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sidebar with options
    with st.sidebar:
        st.header("⚙️ Instellingen")
        search_mode = st.radio(
            "Zoekmodus:",
            ["Vraag & Antwoord", "Document Zoeken"]
        )
        
        if search_mode == "Document Zoeken":
            st.markdown("""
            ### Filters
            Gebruik de onderstaande filters om specifieke documenten te vinden.
            """)
            
            # Add metadata filters
            year_filter = st.selectbox(
                "Jaar:",
                ["Alle jaren", "2024", "2023", "2022"]
            )
            
            theme_filter = st.selectbox(
                "WOO Thema:",
                ["Alle thema's", "overig besluit van algemene strekking", "andere thema's"]
            )

    # Main content area
    if search_mode == "Vraag & Antwoord":
        # Display chat history
        for message in st.session_state.messages:
            display_chat_message(message["role"], message["content"])
            if "sources" in message:
                display_sources(message["sources"])

        # Chat input
        user_input = st.chat_input("Stel je vraag hier (Voorbeeld:  \"Ik wil informatie over het windbeleid in provincie Overijssel\" )...")
        
        if user_input:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})
            display_chat_message("user", user_input)

            # Generate response
            rag = get_rag_system()
            with st.spinner('Even denken...'):
                response = rag.generate_response(user_input)

            # Add assistant response to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.answer,
                "sources": response.sources
            })
            
            # Display response
            display_chat_message("assistant", response.answer)
            display_sources(response.sources)

    else:  # Document Search mode
        # Search interface
        search_query = st.text_input("🔍 Zoek in documenten:", placeholder="Zoekterm...")
        
        if search_query:
            query_system = get_query_system()
            
            # Apply filters
            metadata_filter = {}
            if year_filter != "Alle jaren":
                metadata_filter["metadata.Creatie jaar"] = year_filter
            if theme_filter != "Alle thema's":
                metadata_filter["metadata.WOO thema's"] = theme_filter

            # Perform search
            with st.spinner('Zoeken...'):
                results = query_system.search(
                    query=search_query,
                    metadata_filter=metadata_filter if metadata_filter else None,
                    limit=10
                )

            # Display results
            st.subheader(f"Zoekresultaten voor: '{search_query}'")
            
            if not results:
                st.warning("Geen resultaten gevonden.")
            else:
                for idx, result in enumerate(results, 1):
                    with st.expander(
                        f"📄 {result.metadata.get('file_name', 'Onbekend document')} "
                        f"(Score: {result.score:.2f})",
                        expanded=idx == 1
                    ):
                        st.markdown(f"""
                        **Document Details:**
                        - Datum: {result.metadata.get('metadata.Creatie jaar', 'Onbekend')}
                        - Thema: {result.metadata.get("metadata.WOO thema's", 'Onbekend')}
                        
                        **Inhoud:**
                        {result.content}
                        """)

    # Footer
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )

if __name__ == "__main__":
    main()