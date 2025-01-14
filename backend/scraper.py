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
        """
        Identificeert en extract PDF-links van de HTML-content.

        Parameters:
        html_content (str): De HTML-content waarin naar PDF-links wordt gezocht.

        Returns:
        list: Een lijst van gevonden PDF-links.
        """
        pdf_links = []
        try:
            # Parse the HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Check if the href ends with '.pdf'
                if href.lower().endswith('.pdf'):
                    pdf_links.append(href)
            
        except Exception as e:
            print(f"An error occurred while parsing HTML: {e}")
        
        return pdf_links

    def download_file(self, file_url: str, save_path: str) -> None:
        """
        Download een file van de opgegeven URL en sla deze op in het opgegeven pad.

        Parameters:
        file_url (str): De URL van het bestand dat moet worden gedownload.
        save_path (str): Het pad waar het bestand moet worden opgeslagen.

        Returns:
        None
        """
        try:
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
            print(f"Bestand gedownload: {save_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading file {file_url}: {e}")      
    
    def generate_metadata(self, html_content: str) -> dict:
        """
        Parse HTML content and extract metadata such as title, summary, creation year, and WOO themes.

        Args:
            html_content (str): HTML content of the webpage.

        Returns:
            dict: A dictionary containing the extracted metadata.
        """
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the title
        title_div = soup.find('div', class_='print-document')
        title = title_div.find('div', class_='document-hoofd').find('a').get_text(strip=True)

        # Extract the summary 
        summary_td = soup.find('td', class_='zoekoverzicht', colspan="2")
        summary = summary_td.find_all('p')[1].get_text(strip=True)  # Get the second <p> tag

        # Extract the creation year
        creation_year_tag = soup.find('td', string='Creatie jaar')
        creation_year = creation_year_tag.find_next_sibling('td').get_text(strip=True) if creation_year_tag else None

        # Extract the WOO themes
        woo_themes_tag = soup.find('td', string="WOO thema's")
        woo_themes_list = woo_themes_tag.find_next_sibling('td').find_all('li') if woo_themes_tag else []
        woo_themes = [theme.get_text(strip=True) for theme in woo_themes_list]

        # Combine results in a dictionary
        metadata = {
            'title': title,
            'summary': summary,
            'creation_year': creation_year,
            'woo_themes': woo_themes
        }

        return metadata

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


if __name__ == "__main__":
    # Instantiate the Scraper class
    scraper = Scraper()

    # Sample HTML content (replace this with the actual HTML string)
    html_content = """<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,shrink-to-fit=no"><meta name="theme-color" content="#000000"><link rel="manifest" href="/manifest.json"><link rel="shortcut icon" href="/favicon.ico"><title>WOO portaal Provincie Overijssel</title><script defer="defer" src="/static/js/main.972d3c47.js"></script><link href="/static/css/main.b8080ddf.css" rel="stylesheet"></head><body><noscript>You need to enable JavaScript to run this app.</noscript><div id="root"><div class="body-normal "><div id="wrapper"><div id="header"><div class="label">Provincie Overijssel</div><div class="overlay"></div><div class="afbeeldingen"><img src="/clouds.png" alt="WOO portaal Provincie Overijssel" title="WOO portaal Provincie Overijssel"></div><div class="titelbalk">WOO portaal Provincie Overijssel</div><div class="navigatie"><ul><li class=""><a class="hoeken_3_boven" href="/">Home</a></li><li class="active"><a class="hoeken_3_boven" href="/list">Documenten</a></li><li class=""><a class="hoeken_3_boven" href="/contact">Contact</a></li></ul></div></div><div id="content" class="content"><div class="dummy"><div class="content_main"><div class="documents-laatste"><h1>Document Detail</h1><a href="/list">&lt;&lt; Terug naar de zoekresultaten</a><div class="print-document"><div class="document-hoofd hoeken_5"><table width="100%" cellspacing="0" cellpadding="0" border="0"><tbody><tr><td width="20" align="center"><ul><li></li></ul></td><td><a href="/list/document/66294899-f83d-44aa-a102-f367511a73a3">Brief project Daarle</a></td><td class="date" width="100">2024</td></tr></tbody></table></div><div class="document-content"><table width="100%" cellspacing="1" cellpadding="0"><tbody><tr><td class="icoon" width="20" align="center"><ul style="position: absolute; top: 15px;"><li></li></ul></td><td class="zoekoverzicht" colspan="2"><strong>Samenvatting:</strong><p></p><p>In deze brief worden twee vragen beantwoord over windturbines in weidevogelgebied Daarle-Hoge Hexel.</p></td></tr><tr><td class="icoon" width="20" align="center"><ul><li></li></ul></td><td class="zoekoverzicht"><strong>Bijlagen</strong></td><td class="zoekoverzicht"><ul><li><a href="https://www.geoportaaloverijssel.nl/attachment/66294899-f83d-44aa-a102-f367511a73a3/241209_Brief_project_Daarle_Geredigeerd.pdf" target="_blank">241209_Brief_project_Daarle_Geredigeerd.pdf</a></li></ul></td></tr><tr><td class="icoon" width="20" align="center"><ul><li></li></ul></td><td class="zoekoverzicht"><strong>Creatie jaar</strong></td><td class="zoekoverzicht">2024</td></tr><tr><td class="icoon" width="20" align="center"><ul><li></li></ul></td><td class="zoekoverzicht"><strong>Eindverantwoordelijke</strong></td><td class="zoekoverzicht">Provincie Overijssel: eenheid Economie en Cultuur</td></tr><tr><td class="icoon" width="20" align="center"><ul><li></li></ul></td><td class="zoekoverzicht"><strong>WOO thema's</strong></td><td class="zoekoverzicht"><ul><li>overig besluit van algemene strekking</li></ul></td></tr><tr><td class="icoon" width="20" align="center"><ul><li></li></ul></td><td class="zoekoverzicht"><strong>Gebruiksrestricties</strong></td><td class="zoekoverzicht">De bron mag ook voor externe partijen vindbaar zijn</td></tr></tbody></table></div></div></div></div></div></div><div id="footer" class="content_footer"><div class="copyright"><a href="/">WOO portaal Provincie Overijssel</a></div><div class="menu"><ul><li class=""><a class="hoeken_3_boven" href="https://www.overijssel.nl/algemene-onderdelen/proclaimer" target="_blank">Proclaimer</a></li></ul></div></div></div></div></div></body></html>"""
    
    # Extract metadata
    metadata = scraper.generate_metadata(html_content)
    print("Extracted Metadata:")
    print(f"Title: {metadata['title']}")
    print(f"Samenvatting: {metadata['summary']}")
    print(f"Creatie jaar: {metadata['creation_year']}")
    print(f"Woo thema: {metadata['woo_themes']}")