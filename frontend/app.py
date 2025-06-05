"""
Streamlit Frontend for WOO Document Search and QA System

This application provides a user interface for:
1. Chat-based Q&A with WOO documents (legacy mode)
2. Search-based document retrieval (new mode)
3. Viewing document sources and metadata
"""

import os
import uuid
import streamlit as st
import requests
import json
from typing import Optional, Union, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_URL = os.getenv("API_URL", "http://backend:8000")


# ========== SHARED FUNCTIONS ==========


def display_sources(sources: list, container: Optional[st.container] = None) -> None:
    """
    Displays source information in an organized way (for chat mode).

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


# ========== CHAT MODE FUNCTIONS ==========


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


def clear_chat_history() -> None:
    """
    Clears the chat history from the session state.
    """
    st.session_state.messages = []


def stream_api_response(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stream a response from the API using SSE with proper parsing of the
    multi-line SSE format, preserving newlines and formatting in the content.

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
    current_event_type = None
    data_buffer = ""

    # Nested function to process events. Kept nested for clarity and encapsulation.
    # Also because response_text and sources are modified in this function,
    # and separating the function would cause pass-by-value issues.
    def process_event(event_type, data_content):
        """Helper function to process an event with its data content."""
        nonlocal response_text, sources

        if event_type == "chunk":
            # Add the chunk to the accumulated response text
            response_text += data_content
            # Yield the chunk for streaming display
            return {"type": "chunk", "data": data_content, "full_text": response_text}

        elif event_type == "sources":
            try:
                if data_content.strip():  # Only process if there's content
                    sources_data = json.loads(data_content)
                    sources = sources_data.get("sources", [])
                    return {"type": "sources", "data": sources}
            except json.JSONDecodeError as e:
                print(f"Error parsing sources: {e}")
                return {
                    "type": "error",
                    "data": {"error": f"Failed to parse sources: {str(e)}"},
                }

        elif event_type == "complete":
            try:
                if data_content.strip():  # Only process if there's content
                    completion_data = json.loads(data_content)
                    return {"type": "complete", "data": completion_data}
            except json.JSONDecodeError as e:
                print(f"Error parsing completion data: {e}")
                return None

        elif event_type == "error":
            try:
                if data_content.strip():  # Only process if there's content
                    error_data = json.loads(data_content)
                    return {"type": "error", "data": error_data}
            except json.JSONDecodeError as e:
                print(f"Error parsing error data: {e}")
                return {"type": "error", "data": {"error": str(e)}}

        return None

    try:
        # Stream the response from the API
        with requests.post(url, json=data, headers=headers, stream=True) as r:
            r.raise_for_status()

            # Process the SSE stream
            for line in r.iter_lines():

                if not line:
                    continue

                # Parse the SSE line
                line = line.decode("utf-8")
                # print(f"Raw SSE line: |{line}|")

                # Handle event type line
                if line.startswith("event:"):
                    # If we have a current event and data in the buffer, process it before moving to the next event
                    if current_event_type and data_buffer:
                        result = process_event(current_event_type, data_buffer)
                        if result:
                            # Clear the buffer and reset the event type
                            data_buffer = ""
                            current_event_type = None
                            yield result

                    # Set the new event type
                    current_event_type = line.replace("event:", "").strip()

                # Process data
                if line.startswith("data:"):
                    data_str = line.replace("data: ", "")

                    # Add to the buffer, ensuring we preserve newlines between data lines
                    if data_buffer:
                        print("Adding to data buffer, with extra newline")
                        data_buffer += "\n" + data_str
                    else:
                        data_buffer = data_str

                    # If no event type yet, continue
                    if not current_event_type:
                        continue

    except requests.RequestException as e:
        yield {"type": "error", "data": {"error": str(e)}}

    # Process any remaining data in the buffer
    if current_event_type and data_buffer:
        result = process_event(current_event_type, data_buffer)
        if result:
            # Clear the buffer and reset the event type
            data_buffer = ""
            current_event_type = None
            yield result

    # Final yield with full response
    yield {"type": "final", "data": {"text": response_text, "sources": sources}}


# ========== SEARCH MODE FUNCTIONS ==========


def display_documents(
    documents: list, container: Optional[st.container] = None
) -> None:
    """
    Displays document information in an organized way.

    Args:
        documents (list): A list of document dictionaries containing metadata.
        container (st.container, optional): The Streamlit container to display documents in.
    """
    if container is None:
        container = st

    if not documents:
        container.info("Geen documenten gevonden voor deze zoekopdracht.")
        return

    container.markdown(f"### 📚 Gevonden Documenten ({len(documents)})")

    for idx, doc in enumerate(documents, 1):
        with container.expander(
            f"📄 Document {idx}: {doc['metadata']['titel'] or 'Geen titel'}",
            expanded=False,
        ):
            col1, col2 = container.columns([1, 1])

            with col1:
                container.markdown(
                    f"**Titel:** {doc['metadata']['titel'] or 'Niet beschikbaar'}"
                )
                container.markdown(
                    f"**Type:** {doc['metadata']['type'] or 'Niet beschikbaar'}"
                )
                container.markdown(
                    f"**Provincie:** {doc['metadata']['provincie'] or 'Niet beschikbaar'}"
                )

            with col2:
                container.markdown(
                    f"**Datum:** {doc['metadata']['datum'] or 'Niet beschikbaar'}"
                )
                if doc.get("relevance_score"):
                    container.markdown(
                        f"**Relevantie Score:** {doc['relevance_score']:.3f}"
                    )

                if doc["metadata"]["url"]:
                    container.markdown(
                        f"**URL:** [{doc['metadata']['url']}]({doc['metadata']['url']})"
                    )


def display_chunks(chunks: list, container: Optional[st.container] = None) -> None:
    """
    Displays chunk information in an organized way.

    Args:
        chunks (list): A list of chunk dictionaries containing content and metadata.
        container (st.container, optional): The Streamlit container to display chunks in.
    """
    if container is None:
        container = st

    if not chunks:
        container.info("Geen chunks gevonden voor deze zoekopdracht.")
        return

    container.markdown(f"### 🔍 Relevante Tekstfragmenten ({len(chunks)})")

    for idx, chunk in enumerate(chunks, 1):
        with container.expander(
            f"📝 Fragment {idx} uit: {chunk['metadata']['titel'] or 'Onbekend document'}",
            expanded=False,
        ):

            # Show relevance score if available
            if chunk.get("relevance_score"):
                container.markdown(
                    f"**Relevantie Score:** {chunk['relevance_score']:.3f}"
                )

            # Show content if available
            if chunk.get("content"):
                container.markdown("**Tekstfragment:**")
                container.text_area(
                    "Inhoud van tekstfragment",
                    value=chunk["content"],
                    height=100,
                    disabled=True,
                    key=f"chunk_{idx}",
                    label_visibility="collapsed",
                )

            # Show metadata in columns
            col1, col2 = container.columns([1, 1])
            with col1:
                container.markdown(
                    f"**Document:** {chunk['metadata']['titel'] or 'Niet beschikbaar'}"
                )
                container.markdown(
                    f"**Type:** {chunk['metadata']['type'] or 'Niet beschikbaar'}"
                )

            with col2:
                container.markdown(
                    f"**Provincie:** {chunk['metadata']['provincie'] or 'Niet beschikbaar'}"
                )
                container.markdown(
                    f"**Datum:** {chunk['metadata']['datum'] or 'Niet beschikbaar'}"
                )

            if chunk["metadata"]["url"]:
                container.markdown(
                    f"**Bron:** [{chunk['metadata']['url']}]({chunk['metadata']['url']})"
                )


def search_documents(query: str) -> Dict[str, Any]:
    """
    Search for documents using the API.

    Args:
        query (str): The search query.

    Returns:
        Dict[str, Any]: The API response containing documents and chunks.
    """
    try:
        # Make API call to retrieve documents
        response = requests.post(
            f"{API_URL}/api/query/documents",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "documents": [],
            "chunks": [],
            "total_documents": 0,
            "total_chunks": 0,
        }


# ========== MAIN APPLICATION ==========


def render_chat_mode():
    """Render the chat-based Q&A interface."""

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a session ID for each user
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    st.markdown(
        """
    Deze modus biedt een chat-interface waar je vragen kunt stellen over de inhoud van WOO-documenten.
    Het systeem genereert antwoorden op basis van de gevonden documenten.
    """
    )

    # Main chat display area
    chat_container = st.container()

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


def render_search_mode():
    """Render the search-based document retrieval interface."""

    st.markdown(
        """
    Deze modus helpt je bij het zoeken in WOO-documenten.
    Voer een zoekopdracht in om relevante documenten en tekstfragmenten te vinden.
    """
    )

    # Search interface
    st.markdown("### 🔎 Zoeken")

    # Create search form
    with st.form(key="search_form", clear_on_submit=False):
        query = st.text_input(
            "Zoektermen:",
            placeholder='Bijvoorbeeld: "windbeleid provincie Overijssel"',
            help="Voer je zoekopdracht in om relevante WOO-documenten te vinden",
        )

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            search_button = st.form_submit_button("🔍 Zoeken", type="primary")
        with col2:
            clear_button = st.form_submit_button("🗑️ Wissen")

    # Handle clear button
    if clear_button:
        st.session_state.pop("search_results", None)
        st.rerun()

    # Handle search
    if search_button and query.strip():
        with st.spinner("Zoeken in documenten..."):
            results = search_documents(query.strip())
            st.session_state.search_results = results
            st.session_state.last_query = query.strip()

    # Display results if available
    if "search_results" in st.session_state:
        results = st.session_state.search_results

        st.markdown("---")

        # Show search summary
        if results.get("success", False):
            st.success(
                f"Zoekresultaten voor: **{st.session_state.get('last_query', '')}**"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Gevonden Documenten", results.get("total_documents", 0))
            with col2:
                st.metric("Relevante Fragmenten", results.get("total_chunks", 0))

            # Toggle between documents and chunks view
            view_option = st.radio(
                "Weergave:",
                ["📚 Documenten", "🔍 Tekstfragmenten", "📋 Beide"],
                horizontal=True,
                help="Kies welke resultaten je wilt bekijken",
            )

            st.markdown("---")

            # Display based on selected view
            if view_option == "📚 Documenten":
                display_documents(results.get("documents", []))

            elif view_option == "🔍 Tekstfragmenten":
                display_chunks(results.get("chunks", []))

            elif view_option == "📋 Beide":
                # Display both in tabs
                tab1, tab2 = st.tabs(["📚 Documenten", "🔍 Tekstfragmenten"])

                with tab1:
                    display_documents(results.get("documents", []))

                with tab2:
                    display_chunks(results.get("chunks", []))

        else:
            # Show error
            error_msg = results.get("error", "Onbekende fout opgetreden")
            st.error(f"Fout bij zoeken: {error_msg}")


def main() -> None:
    """
    Main function to run the Streamlit application.
    """
    # Page configuration
    st.set_page_config(page_title="W👀verzicht", page_icon="📑", layout="wide")

    # Header
    st.title("🔍 W👀verzicht")

    # Mode selector
    st.markdown("### ⚙️ Interface Mode")
    mode = st.radio(
        "Kies je interface:",
        ["💬 Chat Mode (Q&A)", "🔍 Search Mode (Document Retrieval)"],
        horizontal=True,
        help="Chat Mode: Stel vragen en krijg antwoorden. Search Mode: Zoek documenten en bekijk fragmenten.",
    )

    # Disclaimer
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

    st.markdown("---")

    # Render the appropriate interface based on mode
    if mode == "💬 Chat Mode (Q&A)":
        render_chat_mode()
    else:
        render_search_mode()

    # App footer content
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )


if __name__ == "__main__":
    main()
