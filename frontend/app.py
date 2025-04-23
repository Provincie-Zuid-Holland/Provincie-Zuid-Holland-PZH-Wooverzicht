"""
Streamlit Frontend for WOO Document Search and QA System

This application provides a user interface for:
1. Searching through WOO documents
2. Asking questions about the documents
3. Viewing document sources and metadata
"""

import os
import uuid
import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_URL = os.getenv("API_URL", "http://backend:8000")


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
    st.session_state.messages = []


def stream_api_response(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stream a response from the API using SSE.

    Args:
        url (str): The URL of the SSE endpoint.
        data (Dict[str, Any]): The JSON data to send in the POST request.

    Returns:
        Dict[str, Any]: A dictionary containing the response text and sources.
    """
    # Set up the headers for SSE
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}

    response_text = ""
    sources = []

    try:
        # Stream the response from the API
        with requests.post(url, json=data, headers=headers, stream=True) as r:
            r.raise_for_status()

            # Process the SSE stream
            for line in r.iter_lines():
                if line:
                    # Parse the SSE line
                    line = line.decode("utf-8")

                    # Skip lines that don't contain events
                    if not line.startswith("data:") and not line.startswith("event:"):
                        continue

                    # Process event type
                    event_type = None
                    if line.startswith("event:"):
                        event_type = line.replace("event:", "").strip()
                        continue

                    # Process data
                    if line.startswith("data:"):
                        data_str = line.replace("data:", "").strip()

                        # If no event type, default to 'message'
                        if not event_type:
                            event_type = "message"

                        # Process different event types
                        if event_type == "chunk":
                            chunk = data_str
                            response_text += chunk
                            yield {
                                "type": "chunk",
                                "data": chunk,
                                "full_text": response_text,
                            }
                        elif event_type == "sources":
                            try:
                                sources_data = json.loads(data_str)
                                sources = sources_data.get("sources", [])
                                yield {"type": "sources", "data": sources}
                            except json.JSONDecodeError:
                                st.error(f"Error parsing sources: {data_str}")
                        elif event_type == "complete":
                            yield {"type": "complete", "data": json.loads(data_str)}
                        elif event_type == "error":
                            error_data = json.loads(data_str)
                            yield {"type": "error", "data": error_data}

    except requests.RequestException as e:
        yield {"type": "error", "data": {"error": str(e)}}

    # Final yield with full response
    yield {"type": "final", "data": {"text": response_text, "sources": sources}}


def main() -> None:
    """
    Main function to run the Streamlit application.
    """
    # Page configuration
    st.set_page_config(page_title="W👀verzicht", page_icon="📑", layout="wide")

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
            response_text = ""
            sources = []

            with st.spinner("Even denken..."):
                try:
                    # Configure the API request data
                    stream_data = {
                        "query": user_input,
                        "session_id": st.session_state.session_id,
                    }

                    # Connect to the streaming endpoint
                    stream_url = f"{API_URL}/api/query/stream"

                    # Process the streaming response
                    for event in stream_api_response(stream_url, stream_data):
                        event_type = event.get("type")

                        if event_type == "chunk":
                            # Update the displayed text with the new chunk
                            response_text = event.get("full_text", "")
                            assistant_placeholder.markdown(
                                f"🤖 **Assistant:** {response_text}"
                            )

                        elif event_type == "sources":
                            # Display the sources
                            sources = event.get("data", [])
                            with sources_placeholder:
                                display_sources(sources)

                        elif event_type == "error":
                            # Display any errors
                            error = event.get("data", {}).get("error", "Unknown error")
                            st.error(f"Error: {error}")

                except Exception as e:
                    st.error(f"Er is een fout opgetreden: {str(e)}")
                    response_text = f"Er is een fout opgetreden bij het verwerken van je vraag: {str(e)}"

            # Add complete response to session state
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "sources": sources,
                }
            )

        # Rerun to show the new messages and reset the input
        st.rerun()

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

    # App footer content
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )


if __name__ == "__main__":
    main()
