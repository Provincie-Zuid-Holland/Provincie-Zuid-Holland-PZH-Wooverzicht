import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote, urljoin
import zipfile
import tempfile
import hashlib
import re
import zipfile, io
from datetime import datetime

# TODO
# Modify code so it downloads everything using the download all as zip button. Then unzip in tempdir and remove zip file itself


class Scraper:
    """
    Deze class is voor het scrapen en downloaden van documenten van het WOO portaal Gelderland.
    De scraper gebruikt requests en BeautifulSoup voor HTML parsing.
    Documenten worden gedownload en opgeslagen in zip bestanden, samen met hun metadata.
    De scraper houdt bij welke bestanden al gedownload zijn om dubbele downloads te voorkomen.

    Attributen:
        supported_extensions (tuple): Lijst van ondersteunde bestandsextensies (.pdf, .docx, etc.)
        base_download_dir (str): Basis directory waar de zip bestanden worden opgeslagen
        downloaded_files_cache (dict): Cache van reeds gedownloade bestanden en hun locaties
        session: Requests session voor het hergebruiken van verbindingen
        headers (dict): HTTP headers voor requests

    Methodes:
        fetch_html(url: str) -> str:
            Haalt de HTML content op van een pagina.

        generate_metadata(html_content: str, url: str) -> dict:
            Extraheert metadata uit de HTML content.

        create_metadata_file(metadata: dict, temp_dir: str) -> str:
            Maakt een tekstbestand met metadata informatie.

        scrape_document(url: str, index: int) -> None:
            Hoofdfunctie die een document URL scraped en alle gevonden bestanden downloadt.
    """

    def __init__(self):
        """
        Initialiseert de Scraper met de basis mapstructuur en houdt een cache bij van gedownloade bestanden.
        """
        # Lijst met ondersteunde bestandsformaten
        self.supported_extensions = (
            ".pdf",
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".pptx",
            ".ppt",
            ".txt",
            ".csv",
            ".rtf",
        )

        # Maak de basis download directory aan voor de zip files met provincie subfolders
        downloads_base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data_scraping", "downloads"
        )
        self.base_download_dir = os.path.join(downloads_base, "gelderland")
        os.makedirs(self.base_download_dir, exist_ok=True)

        # Requests sessie voor hergebruik van verbindingen
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def fetch_html(self, url):
        """
        Haalt HTML content op met requests.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"HTML ophalen (poging {attempt + 1}/{max_retries})")
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.text

            except Exception as e:
                print(f"Fout bij ophalen HTML (poging {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    def generate_metadata(self, html_content, url):
        """
        Genereert metadata van de HTML content.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            metadata = {
                "url": url,
                "provincie": "Gelderland",
                "titel": "",
                "datum": "",
                "type": "woo-verzoek",
            }

            # Probeer titel te vinden (h1 is meest waarschijnlijk)
            title_tag = soup.find("h1")
            if title_tag:
                metadata["titel"] = title_tag.get_text(strip=True)

            # datum
            date_strong = soup.select_one('strong:contains("Publicatiedatum")')

            if date_strong:
                # Get the parent div
                parent_div = date_strong.parent
                # Find the span within the same div
                date_span = parent_div.find("span")
                if date_span:
                    # Convert d-m-yyyy to dd-mm-yyyy format
                    d = datetime.strptime(date_span.text, "%d-%m-%Y")
                    date_str = d.strftime("%d-%m-%Y")
                    metadata["datum"] = date_str

            categorie_strong = soup.select_one('strong:contains("Categorie")')

            if categorie_strong:
                # Get the parent div
                parent_div = categorie_strong.parent
                # Find the span within the same div
                categorie_span = parent_div.find("span")
                if categorie_span.text == "Woo-verzoeken":
                    metadata["type"] = "woo-verzoek"
                else:
                    metadata["type"] = "categorie_span.text"

            return metadata

        except Exception as e:
            print(f"Fout bij genereren metadata: {e}")
            return metadata

    def find_zip(self, html_content, url):
        """
        Zoekt naar een zip bestand op de pagina. Gelderland heeft namelijk een knop waarmee je alle bestanden in een zip kan downloaden.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")

        # Zoek naar alle links in de pagina
        for link in soup.find_all("a", href=True):
            href = link["href"]
            absolute_url = urljoin(url, href)

            # Check of de URL eindigt op een ondersteunde extensie
            if absolute_url.endswith(".zip") and "media.gelderland.nl" in absolute_url:
                # get filename after last '/' in url
                filename = absolute_url.split("/")[-1]
                return absolute_url, filename
        return []

    def download_zip(self, url, save_path):
        """
        Download een zip bestand van de site en zet deze in save_path.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(
                    f"Document downloaden naar (poging {attempt + 1}/{max_retries}): {os.path.basename(save_path)}"
                )
                response = self.session.get(
                    url, stream=True, headers=self.headers, timeout=30
                )
                response.raise_for_status()
                if response.status_code == 200:
                    z = zipfile.ZipFile(io.BytesIO(response.content))
                    z.extractall(save_path)
                    print(
                        f"Zip bestand succesvol gedownload naar: {os.path.basename(save_path)}"
                    )
                    return True
            except Exception as e:
                print(f"Fout bij downloaden (poging {attempt + 1}): {e}")
                return False
        return False

    def create_metadata_file(self, metadata, temp_dir):
        """
        Creates a metadata text file.

        Args:
            metadata (dict): The metadata to write to the file
            temp_dir (str): The directory where the metadata file should be created

        Returns:
            str: The path to the created metadata file

        Example:
            metadata = {
                "url": "https://example.com/page",
                "title": "Example Document",
                "summary": "An example document",
                "date": "2023-01-01",
                "woo_themes": ["Example Theme"]
            }
            metadata_path = scraper.create_metadata_file(metadata, "/tmp/downloads")
            print(f"Metadata saved to {metadata_path}")
        """
        metadata_path = os.path.join(temp_dir, "metadata.txt")
        with open(metadata_path, "w", encoding="utf-8") as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        return metadata_path

    def scrape_document(
        self, temp_dir: tempfile.TemporaryDirectory, url: str, index: int
    ) -> None:
        """
        Scraped een document URL en slaat alle gevonden bestanden op in een zip bestand.
        """
        print(f"\n{'='*80}\nDocument {index} verwerken: {url}\n{'='*80}")

        html_content = self.fetch_html(url)
        if not html_content:
            print(f"Kon geen content ophalen voor {url}")
            return

        # Genereer en sla metadata op
        metadata = self.generate_metadata(html_content, url)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Zoek naar zip bestand
        zip_link = self.find_zip(html_content, url)
        if not zip_link:
            print("Geen zip bestand gevonden")
            return

        # Download zip bestand
        downloaded = self.download_zip(zip_link[0], temp_dir)
        if not downloaded:
            print("Fout bij downloaden zip bestand")
            return
        return

    def __del__(self):
        """
        Cleanup bij afsluiten.
        """
        try:
            self.session.close()
        except:
            pass


if __name__ == "__main__":
    BASE_URL = "https://open.gelderland.nl/woo-documenten"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = "https://open.gelderland.nl/woo-documenten/woo-besluit-over-brief-commissaris-van-de-koning-aan-minister-van-asiel-2025-002957"  # Klein Woo verzoek (3 bestanden)
    # EXAMPLE_DOC_URL = "https://open.gelderland.nl/woo-documenten/woo-besluit-over-projectplan-hagenbeek-2024-2024-014129" # Groot Woo verzoek (140 bestanden)
    # EXAMPLE_DOC_URL = "https://open.gelderland.nl/woo-documenten/woo-besluit-over-het-convenant-nedersaksisch-2024-015084"  # Middel Woo verzoek (25 bestanden)

    scraper = Scraper()
    with tempfile.TemporaryDirectory() as temp_dir:
        scraper.scrape_document(temp_dir, EXAMPLE_DOC_URL, 1)

        print("### VERIFY SCRAPER DOWNLOADS ###")
        # Verify the temp directory is created, and still exists
        print("\nTemp directory:", temp_dir)
        assert os.path.exists(temp_dir)

        # Verify that the downloaded files are in the temp directory
        print(f"\nTemp directory contents: [{len(os.listdir(temp_dir))} files]")
        for iter, filename in enumerate(os.listdir(temp_dir), start=1):
            print(f"{iter}. {filename}")

        # Verify that the metadata file was created
        metadata_file = os.path.join(temp_dir, "metadata.txt")
        if os.path.exists(metadata_file):
            print("\nMetadata file contents:")
            with open(metadata_file, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("\nMetadata file not found")

        # Verify that the downloaded files are not empty
        print("\nDownloaded empty files:")
        for iter, filename in enumerate(os.listdir(temp_dir), start=1):
            file_path = os.path.join(temp_dir, filename)
            if os.path.getsize(file_path) <= 0:
                print(f"{iter}. {filename} - Empty file")
