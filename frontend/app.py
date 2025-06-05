"""
Streamlit Frontend for WOO Document Search System

This application provides a user interface for:
1. Searching through WOO documents
2. Viewing relevant document results and chunks
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
                    label_visibility="collapsed",
                    value=chunk["content"],
                    height=100,
                    disabled=True,
                    key=f"chunk_{idx}",
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


def main() -> None:
    """
    Main function to run the Streamlit application.
    """
    # Page configuration
    st.set_page_config(page_title="W👀verzicht", page_icon="📑", layout="wide")

    # Header
    st.title("🔍 W👀verzicht")
    st.markdown(
        """
    Deze applicatie helpt je bij het zoeken in WOO-documenten.
    Voer een zoekopdracht in om relevante documenten en tekstfragmenten te vinden.
    """
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

    # App footer content
    st.markdown("---")
    st.markdown(
        "Deze applicatie is ontwikkeld om WOO-verzoeken efficiënter te verwerken. "
        "Voor vragen of ondersteuning, neem contact op met de beheerder."
    )


if __name__ == "__main__":
    main()
