import os
import re
import requests
import zipfile
from bs4 import BeautifulSoup
from datetime import datetime

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
        #  Download een file van een URL pad, parameter file_url en directory path waar het gestored moet worden
        pass

    def generate_metadata(self, file_path:str) -> dict:
        # Genereert metadata voor een file
        # parameter: file_path de path voor generatie van metadata
        # return: dictionairy containing the metadata
        pass

    def generate_zip_name(self, url: str) -> str:
        """
        genereer een contextuele naam van een zip file --> Dat is nu cleanurl + datetime
        """
        clean_url = re.sub(r'\W+', '_', url)  
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  
        return f"{clean_url}_{timestamp}.zip"

    def create_unique_zip(self, file_paths: list, zip_name: str) -> None:
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for file_path in file_paths:
                zipf.write(file_path, os.path.basename(file_path))

    def scrape_to_zip(self, url: str) -> None:
        html_content = self.fetch_html(url)
        pdf_links = self.find_pdfs(html_content)
        print(pdf_links)
        
        os.makedirs("downloads", exist_ok=True)  
        downloaded_files = []
        
        for index, pdf_url in enumerate(pdf_links):
            file_name = f"downloads/file_{index+1}.pdf"
            self.download_file(pdf_url, file_name)
            downloaded_files.append(file_name)
        
        metadata_content = ""
        for file_path in downloaded_files:
            metadata = self.generate_metadata(file_path)
            metadata_content += f"Bestandsnaam: {metadata['bestand_naam']}, Grootte: {metadata['bestand_grootte']} bytes, Datum: {metadata['datum_aangemaakt']}\n"
        
        metadata_path = "downloads/metadata.txt"
        with open(metadata_path, 'w') as file:
            file.write(metadata_content)
        
        downloaded_files.append(metadata_path)
        zip_name = self.generate_zip_name(url)
        self.create_unique_zip(downloaded_files, zip_name)

