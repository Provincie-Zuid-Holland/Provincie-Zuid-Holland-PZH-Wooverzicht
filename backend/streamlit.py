import streamlit as st
import base64
import os
# from rag import process_query  # Importeer de RAG-functie vanuit rag.py

class StreamlitApp:
    """
    Deze class bevat de logica voor de Streamlit-applicatie.
    Het doel is om een gebruiksvriendelijke interface te bieden waar gebruikers vragen kunnen stellen over Woo-verzoeken.
    De applicatie bevat ook functionaliteit om afbeeldingen en stijlen te verwerken.

    Attributen:
        background_image_path (str): Pad naar de achtergrondafbeelding
        encoded_image (str): Base64-gecodeerde afbeelding
    """

    def __init__(self):
        """
        Initialiseert de StreamlitApp class en configureert de basisinstellingen voor de applicatie.
        """
        st.set_page_config(page_title="Wooverzicht Overijssel", layout="centered")

        # Stel het pad in naar de achtergrondafbeelding
        self.background_image_path = os.path.join(
            os.path.dirname(__file__),  # Huidige map
            "..",                       # Ga naar de hoofdmap
            "frontend", 
            "images", 
            "background.png"
        )

        # Controleer of de afbeelding bestaat
        if not os.path.exists(self.background_image_path):
            raise FileNotFoundError(f"Achtergrondafbeelding niet gevonden op {self.background_image_path}")

        # Codeer de afbeelding in Base64
        self.encoded_image = self._get_base64_encoded_image(self.background_image_path)

    def _get_base64_encoded_image(self, image_path: str) -> str:
        """
        Encodeert een afbeelding in Base64-formaat.

        Parameters:
            image_path (str): Het pad naar de afbeelding

        Returns:
            str: Base64-gecodeerde string van de afbeelding
        """
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    def _set_styles(self):
        """
        Stelt de CSS-stijl in voor de Streamlit-applicatie, inclusief de achtergrondafbeelding en kleuren.
        """
        header_img_style = f"""
        <style>
        .stApp {{
            background-color: white; /* Zet de achtergrondkleur naar wit */
            padding-top: 0;
        }}

        img.header {{
            display: block;
            margin: 0 auto;  /* Centreer de afbeelding horizontaal */
            max-width: 100%; /* Zorg ervoor dat het schaalt binnen de container */
            height: auto;    /* Behoud de aspect ratio */
        }}
        </style>
        """
        st.markdown(header_img_style, unsafe_allow_html=True)

    def _render_header(self):
        """
        Render de afbeelding bovenaan de pagina.
        """
        st.markdown(
            f'<img class="header" src="data:image/png;base64,{self.encoded_image}" alt="Header Image">',
            unsafe_allow_html=True
        )

    def _process_query(self, query: str) -> str:
        """
        Roept de RAG-applicatie aan om een antwoord op de vraag te genereren.

        Parameters:
            query (str): De door de gebruiker ingevoerde vraag

        Returns:
            str: Het antwoord gegenereerd door de RAG-applicatie
        """
        return process_query(query)

    def run(self):
        """
        Hoofdfunctie voor het uitvoeren van de Streamlit-app.
        Render de interface en verwerk gebruikersinteracties.
        """
        # Stel de stijlen in
        self._set_styles()

        # Render de header-afbeelding
        self._render_header()

        # Zet de titel en beschrijving
        st.title("Wooverzicht Overijssel")
        st.write(
            """
            Typ je vraag over een Woo-verzoek en klik op "Verzend" om informatie op te zoeken of de status te controleren.
            """
        )

        # Vraag de gebruiker om een query
        user_query = st.text_input("Stel hier je vraag:")

        if st.button("Verzenden"):
            # Verwerk de query en geef een antwoord
            response = self._process_query(user_query)
            st.write(f"**Response:** {response}")


if __name__ == "__main__":
    # Maak een instantie van de StreamlitApp en voer deze uit
    app = StreamlitApp()
    app.run()