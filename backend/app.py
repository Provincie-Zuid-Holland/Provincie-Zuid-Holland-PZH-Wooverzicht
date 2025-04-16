"""
Streamlit Frontend for WOO Document Search and QA System

This application provides a user interface for:
1. Searching through WOO documents
2. Asking questions about the documents
3. Viewing document sources and metadata
"""

import os, sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # Need to add to be able to import backend query logger
import uuid
import streamlit as st
from datetime import datetime
from backend.query_logger import QueryLogger
from conversational_rag import ConversationalRAG
from typing import Optional, Union  # Add this import for type hints
from dotenv import load_dotenv


# Initialize the RAG system
@st.cache_resource
def get_rag_system() -> ConversationalRAG:
    """
    Initializes and caches an instance of the ConversationalRAG system.

    Returns:
        ConversationalRAG: An instance of the document search and QA system.
    """
    return ConversationalRAG()


def display_chat_message(
    role: str, content: str, container: Optional[st.container] = None
) -> Optional[Union[st.empty, None]]:
    """
    Displays a chat message with appropriate styling.

    Args:
        role (str): The role of the message sender ("user" or "assistant").
        content (str): The content of the message.
        container (st.container, optional): The Streamlit container to display the message in.

    Returns:
        Optional[Union[st.empty, None]]: A Streamlit placeholder for the assistant message, if applicable.
    """
    if container is None:
        container = st

    if role == "user":
        container.write(f"🧑‍💼 **You:** {content}")
        return None
    elif role == "assistant":
        placeholder = container.empty()
        placeholder.markdown(f"🤖 **Assistant:** {content}")
        return placeholder
    else:
        container.write(content)
        return None


def display_sources(sources: list, container: Optional[st.container] = None) -> None:
    """
    Displays source information in an organized way.

    Args:
        sources (list): A list of source dictionaries containing metadata.
        container (st.container, optional): The Streamlit container to display sources in.
    """
    if container is None:
        container = st

    with container.expander("📚 View Sources", expanded=False):
        for idx, source in enumerate(sources, 1):
            container.markdown(
                f"""
            **Source {idx}:**
            - Titel: `{source['titel']}`
            - URL: [{source['url']}]({source['url']})
            - Provincie: {source['provincie']}
            - Datum: {source['datum']}
            - Type: {source['type']}
            """
            )


def clear_chat_history() -> None:
    """
    Clears the chat history from the session state.
    """
    get_rag_system.clear()  # Clear cache
    st.session_state.messages = []


def main() -> None:
    """
    Main function to run the Streamlit application.
    """
    load_dotenv()
    # Page configuration
    st.set_page_config(page_title="W👀verzicht", page_icon="📑", layout="wide")

    # initialize logger
    logger = QueryLogger()

    # Create a session ID for each user
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Use CSS to fix input at bottom of page
    st.markdown(
        """
    <style>
    .stApp {
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }
    
    .main {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    .block-container {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    footer {
        position: sticky;
        bottom: 0;
        background-color: white;
        padding: 10px 0;
        border-top: 1px solid #e6e6e6;
        z-index: 999;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Header
    st.title("🔍 W👀verzicht")
    st.markdown(
        """
    Deze applicatie helpt je bij het analyseren van WOO-documenten.
    Je kunt vragen stellen over de inhoud van documenten.
    """
    )

    # Main chat display area (will expand to fill available space)
    chat_container = st.container()

    if "disclaimer_shown" not in st.session_state:
        st.session_state.disclaimer_shown = False

    if not st.session_state.disclaimer_shown:
        with st.expander("ℹ️ Melding over data-gebruik", expanded=True):
            st.markdown(
                """
                Om de applicatie te verbeteren, verzamelen we gegevens over je vragen en interacties.
                Deze gegevens bevatten geen persoonlijke informatie en worden alleen gebruikt voor analyse-doeleinden.
                """
            )
            if st.button("Begrepen!"):
                st.session_state.disclaimer_shown = True
                st.rerun()

    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            display_chat_message(message["role"], message["content"])
            if "sources" in message:
                display_sources(message["sources"])

    # Process any existing user input before showing the input bar
    if "user_input" in st.session_state and st.session_state.user_input:
        user_input = st.session_state.user_input
        st.session_state.user_input = None  # Clear the stored input

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
            chunks_used = []

            with st.spinner("Even denken..."):
                # Assuming ConversationalRAG has been modified to support streaming
                start_time = datetime.now()
                for chunk in rag.generate_response_stream(user_input):
                    if isinstance(chunk, str):
                        # Update text response
                        response_text += chunk
                        assistant_placeholder.markdown(
                            f"🤖 **Assistant:** {response_text}"
                        )
                    elif isinstance(chunk, dict) and "sources" in chunk:
                        # Display sources when they become available
                        with sources_placeholder:
                            display_sources(chunk["sources"])
                        if "document_ids" in chunk:
                            # Store document IDs for later use
                            chunks_used.extend(chunk["document_ids"])

            response_time = (datetime.now() - start_time).total_seconds()

            # Add complete response to session state
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "sources": (
                        chunk.get("sources", []) if isinstance(chunk, dict) else []
                    ),
                }
            )

            # Create metadata for logging
            metadata = {
                "sources": chunk.get("sources", []),
                "response_time": response_time,
                "chunks_used": chunks_used,
                "timestamp": datetime.now().isoformat(),
            }

            # Log the interaction
            logger.log_interaction(
                st.session_state.session_id,
                user_input,
                response_text,
                metadata,
            )

        # Rerun to show the new messages and reset the input
        st.rerun()

    # # Footer with input bar (fixed at bottom)
    # st.markdown("<footer>", unsafe_allow_html=True)

    # Create columns for input and button
    col1, col2 = st.columns([5, 1])

    max_input_chars = 200
    # Chat input in left column
    with col1:
        user_input = st.chat_input(
            'Stel je vraag hier (Voorbeeld: "Ik wil informatie over het windbeleid in provincie Overijssel")...',
            max_chars=max_input_chars,
        )
        if user_input:
            if len(user_input) > max_input_chars:
                st.error("Je vraag is te lang. Probeer het opnieuw met minder tekens")
            else:
                # Store the input in session state to process it on the next rerun
                st.session_state.user_input = user_input
                st.rerun()

    # New chat button in right column
    with col2:
        if st.button("🔄 Nieuwe Chat", key="new_chat", help="Begin een nieuwe chat"):
            clear_chat_history()
            st.rerun()

    # st.markdown("</footer>", unsafe_allow_html=True)

    # App footer content
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )


if __name__ == "__main__":
    main()
