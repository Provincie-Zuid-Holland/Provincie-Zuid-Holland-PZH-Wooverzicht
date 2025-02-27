import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote
import zipfile
import tempfile
import hashlib
import re


class Scraper:
    """
    A class for scraping and downloading documents from the Noord-Brabant WOO portal.
    Documents are downloaded and stored in zip files along with their metadata.
    """

    def __init__(self):
        """
        Initializes the Scraper with the basic folder structure and maintains a cache of downloaded files.
        """
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

        # Create the base download directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_base = os.path.join(script_dir, "downloads")
        self.base_download_dir = os.path.join(downloads_base, "noord_brabant")
        os.makedirs(self.base_download_dir, exist_ok=True)

        print(f"Files will be saved to: {self.base_download_dir}")

        # Cache to track downloaded files
        self.downloaded_files_cache = self._build_existing_files_cache()

        # Requests session for efficient requests
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://open.brabant.nl",
            "Referer": "https://open.brabant.nl/",
            "Content-Type": "application/json",
        }

        # API base URL
        self.api_base_url = "https://api-brabant.iprox-open.nl/api/v1/public"

    def _build_existing_files_cache(self) -> dict:
        """
        Builds a cache of existing files in zip files.
        """
        cache = {}
        try:
            for filename in os.listdir(self.base_download_dir):
                if filename.endswith(".zip"):
                    zip_path = os.path.join(self.base_download_dir, filename)
                    with zipfile.ZipFile(zip_path, "r") as zipf:
                        for file_info in zipf.filelist:
                            if file_info.filename.lower().endswith(
                                self.supported_extensions
                            ):
                                cache[file_info.filename] = zip_path
        except Exception as e:
            print(f"Warning: Error building cache: {e}")
        return cache

    def fetch_html(self, url: str) -> str:
        """
        Retrieves HTML content using requests.
        """
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching HTML: {e}")
            return None

    def generate_metadata(self, html_content: str, url: str) -> dict:
        """
        Extracts metadata from HTML content.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            metadata = {
                "url": url,
                "title": "Onbekend",
                "document_number": "Onbekend",
                "report_date": "Onbekend",
            }

            # Extract title
            title_tag = soup.find("h1")
            if title_tag:
                metadata["title"] = title_tag.get_text(strip=True)

            # Extract document details
            details = soup.find_all(["dt", "dd"])
            for i in range(0, len(details), 2):
                label = details[i].get_text(strip=True).lower()
                value = (
                    details[i + 1].get_text(strip=True)
                    if i + 1 < len(details)
                    else "Onbekend"
                )

                if "documentnummer" in label:
                    metadata["document_number"] = value
                elif "rapportdatum" in label:
                    metadata["report_date"] = value

            return metadata
        except Exception as e:
            print(f"Error generating metadata: {e}")
            return {
                "url": url,
                "title": "Onbekend",
                "document_number": "Onbekend",
                "report_date": "Onbekend",
            }

    def create_metadata_file(self, metadata: dict, temp_dir: str) -> str:
        """
        Creates a metadata text file.
        """
        metadata_path = os.path.join(temp_dir, "metadata.txt")
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {metadata.get('url', 'Onbekend')}\n")
            f.write(f"Titel: {metadata.get('title', 'Onbekend')}\n")
            f.write(f"Documentnummer: {metadata.get('document_number', 'Onbekend')}\n")
            f.write(f"Rapportdatum: {metadata.get('report_date', 'Onbekend')}\n")
            f.write(f"Verzameld op: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        return metadata_path

    def scrape_document(self, url: str, index: int) -> None:
        """
        Scrapes a document URL and saves all found files in a zip file.
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")

        zip_path = os.path.join(self.base_download_dir, f"woo-{index}.zip")
        if os.path.exists(zip_path):
            print(f"Zip file woo-{index}.zip already exists")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            html_content = self.fetch_html(url)
            if not html_content:
                print(f"Could not retrieve content for {url}")
                return

            metadata = self.generate_metadata(html_content, url)
            metadata_path = self.create_metadata_file(metadata, temp_dir)

            # Create zip file without unnecessary folders
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(metadata_path, arcname="metadata.txt")

            print(f"Zip file created: {zip_path}")

    def __del__(self):
        """
        Cleanup when closing.
        """
        try:
            self.session.close()
        except:
            pass


if __name__ == "__main__":
    BASE_URL = "https://open.brabant.nl/woo-verzoeken"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = (
        "https://open.brabant.nl/woo-verzoeken/a1fb965b-3c28-4abb-957f-29a0fb5a7700"
    )

    scraper = Scraper()
    scraper.scrape_document(EXAMPLE_DOC_URL, 1)
