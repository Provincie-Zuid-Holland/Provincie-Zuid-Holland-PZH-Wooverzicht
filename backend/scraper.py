import requests
from bs4 import BeautifulSoup

class Scraper:
    """
    Deze class is voor het scrapen van web content, het vinden van PDF's, downloaden van PDF's en het genereren van metadata.

    Methodes:   
        fetch_html(url: str) -> str:
            deze functie fetched de html content van een URL.

        find_pdfs(html_content: str) -> list:
            deze identified en extract PDF file links van de html content.

        download_files(url: str, save_path: str) -> None:
            Download een file van de specifieke URL naar en path

        generate_metadata(file_path: str) -> dict:
            generate metadata van een given file.

        generate_zip_name(contect: str) -> str:
            genereer een contextuele naam van een zip file

    """
    def __init__(self):
        pass

    def fetch_html(self, url: str) -> str:
            """
            Fetches HTML content van een specifieke webpagina.

            Parameters:
            url (str): De URL van de webpagina waarvan HTML opgehaald moet worden.

            Returns:
            str: HTML content van de webpagina als string.
            """
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                print(f"Error fetching HTML from {url}: {e}")
                return ""

    def find_pdfs(self, html_content: str) -> list:
        # Identificeert en extract pdf file links van de html content. 
        # Returned een lijst van PDF file links in de html.
        pass

    def download_file(self, file_url: str, save_path: str) -> None:
        # Download een file van een URL pad, parameter file_url en directory path waar het gestored moet worden
        pass

    def create_unique_zip(file_paths: list, zip_name: str) -> None:
        # Makt een zip file containing de files die gespecificeerd zijn.
        # Parameters: file_paths is een lijst of file paths in de ZIP
        # parameter zip_name: naam of de zip file (contextually)
        pass

    def generate_metadata(self, file_path:str) -> dict:
        # Genereert metadata voor een file
        # parameter: file_path de path voor generatie van metadata
        # return: dictionairy containing the metadata
        pass

    def generate_zip_name(self, context: str) -> str:
        # Creates a contextual name for zip filel
        # parameter context: contextual information for naming
        # return: A string representing the zip file name
        pass

Scraper = Scraper()
sc = Scraper.fetch_html(url=f'https://woo.dataportaaloverijssel.nl/list/document/759bdb1b-9add-4ab0-bd8c-72502a0ed4f5')

print(sc)