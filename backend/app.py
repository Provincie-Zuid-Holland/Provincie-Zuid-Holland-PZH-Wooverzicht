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
from dotenv import load_dotenv

# Initialize the RAG system
@st.cache_resource
def get_rag_system():
    return ConversationalRAG()

def display_chat_message(role: str, content: str, container=None):
    """Display a chat message with the appropriate styling"""
    if container is None:
        container = st
    
    if role == "user":
        container.write(f'🧑‍💼 **You:** {content}')
    elif role == "assistant":
        # For streaming responses, we'll use empty placeholder
        placeholder = container.empty()
        placeholder.markdown(f'🤖 **Assistant:** {content}')
        return placeholder
    else:
        container.write(content)

def display_sources(sources, container=None):
    """Display source information in an organized way"""
    if container is None:
        container = st
        
    with container.expander("📚 View Sources", expanded=False):
        for idx, source in enumerate(sources, 1):
            container.markdown(f"""
            **Source {idx}:**
            - File: `{source['file_name']}`
            - Date: {source['date']}
            - Theme: {source['theme']}"""
            # - Relevance Score: {source['relevance_score']:.2f}
            )

def main():
    load_dotenv()
    # Page configuration
    st.set_page_config(
        page_title="W👀verzicht",
        page_icon="📑",
        layout="wide"
    )

    # Header
    st.title("🔍 W👀verzicht")
    st.markdown("""
    Deze applicatie helpt je bij het analyseren van WOO-documenten.
    Je kunt vragen stellen over de inhoud van documenten.
    """)

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a container for chat messages
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            display_chat_message(message["role"], message["content"])
            if "sources" in message:
                display_sources(message["sources"])

    # Chat input
    user_input = st.chat_input("Stel je vraag hier (Voorbeeld: \"Ik wil informatie over het windbeleid in provincie Overijssel\")...")
    
    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Create a new container for the current interaction
        response_container = st.container()
        
        with response_container:
            # Display user message
            display_chat_message("user", user_input)
            
            # Create placeholder for assistant response
            assistant_placeholder = display_chat_message("assistant", "")
            sources_placeholder = st.empty()

            # Generate streaming response
            rag = get_rag_system()
            response_text = ""
            
            with st.spinner('Even denken...'):
                # Assuming ConversationalRAG has been modified to support streaming
                for chunk in rag.generate_response_stream(user_input):
                    if isinstance(chunk, str):
                        # Update text response
                        response_text += chunk
                        assistant_placeholder.markdown(f'🤖 **Assistant:** {response_text}')
                    elif isinstance(chunk, dict) and 'sources' in chunk:
                        # Display sources when they become available
                        with sources_placeholder:
                            display_sources(chunk['sources'])

            # Add complete response to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "sources": chunk.get('sources', []) if isinstance(chunk, dict) else []
            })

    # Footer
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )

if __name__ == "__main__":
    main()
