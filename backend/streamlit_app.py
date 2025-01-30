from pathlib import Path
import streamlit as st
import base64
from typing import Optional

class StreamlitApp:
    """
    A streamlined Streamlit application for handling Woo-verzoeken (Information Disclosure Requests).
    Provides a user-friendly interface for querying and displaying information about requests.

    The application includes functionality for:
    - Custom styling and background images
    - Query processing
    - Response rendering

    Attributes:
        background_image: Path
            Path object pointing to the background image
        image_cache: Optional[str]
            Cached base64 encoded image string
    """

    def __init__(self, image_name: str = "background.png"):
        """
        Initialize the StreamlitApp with basic configuration and image setup.

        Args:
            image_name: str
                Name of the background image file (default: "background.png")
        """
        # Configure page settings
        st.set_page_config(page_title="Wooverzicht Overijssel", layout="centered")
        
        # Initialize image attributes
        self.background_image = Path(__file__).parent.parent / "frontend" / "images" / image_name
        self.image_cache: Optional[str] = None
        
        # Validate image existence
        if not self.background_image.exists():
            raise FileNotFoundError(f"Background image not found at {self.background_image}")

    @property
    def encoded_image(self) -> str:
        """
        Lazy load and cache the base64 encoded background image.

        Returns:
            str: Base64 encoded image string
        """
        if self.image_cache is None:
            self.image_cache = base64.b64encode(self.background_image.read_bytes()).decode()
        return self.image_cache

    def _apply_styles(self) -> None:
        """Apply custom CSS styles to the Streamlit application."""
        st.markdown(
            """
            <style>
            .stApp {
                background-color: white;
                padding-top: 0;
            }
            img.header {
                display: block;
                margin: 0 auto;
                max-width: 100%;
                height: auto;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    def _render_header(self) -> None:
        """Render the header image using the cached base64 encoded image."""
        st.markdown(
            f'<img class="header" src="data:image/png;base64,{self.encoded_image}" alt="Header Image">',
            unsafe_allow_html=True
        )

    def _process_query(self, query: str) -> str:
        """
        Process a user query through the RAG application.

        Args:
            query: str
                The user's input query

        Returns:
            str: Generated response from the RAG application
        """
        # Import the RAG function here to avoid circular imports
        from rag import process_query
        return process_query(query)

    def run(self) -> None:
        """
        Main execution function for the Streamlit application.
        Handles rendering and user interaction flow.
        """
        # Setup UI components
        self._apply_styles()
        self._render_header()

        # Main content
        st.title("Wooverzicht Overijssel")
        st.write(
            "Typ je vraag over een Woo-verzoek en klik op \"Verzend\" "
            "om informatie op te zoeken of de status te controleren."
        )

        # User interaction
        query = st.text_input("Stel hier je vraag:")
        if st.button("Verzenden") and query:
            response = self._process_query(query)
            st.write(f"**Response:** {response}")


if __name__ == "__main__":
    StreamlitApp().run()