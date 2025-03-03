import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote
import zipfile
import tempfile
import hashlib
import re
import json


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

    def extract_document_ids(self, html_content: str) -> dict:
        """
        Extracts document IDs from checkbox values in the HTML and returns them in a structured format.

        Args:
            html_content (str): HTML content containing the document checkboxes

        Returns:
            dict: A dictionary with "nodeIds" key containing the list of document IDs
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all checkbox input elements
        checkboxes = soup.find_all("input", {"type": "checkbox"})

        # Extract the value attribute from each checkbox
        document_ids = [
            checkbox.get("value") for checkbox in checkboxes if checkbox.get("value")
        ]

        # Format as requested
        payload = {"nodeIds": document_ids}

        print(f"Found {len(document_ids)} document IDs")
        return payload

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

    def download_files(self, url, payload, temp_dir):
        """
        Downloads files using the API and extracts them to the temporary directory.

        Args:
            url (str): The API URL to download files
            payload (dict): The payload containing nodeIds
            temp_dir (str): Temporary directory to save downloaded files

        Returns:
            bool: True if successful, False otherwise
        """
        # Make the POST request with the required headers and payload
        response = requests.post(url, headers=self.headers, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            zip_id = data.get("zipId")
            if zip_id:
                print(f"zipId: {zip_id}")
                # Construct the URL to download the file using the zipId
                file_url = f"https://api-brabant.iprox-open.nl/api/v1/public/download-zip/{zip_id}"
                print(f"Constructed file URL: {file_url}")

                file_response = requests.get(file_url)
                if file_response.status_code == 200:
                    # Save the downloaded zip file to the temp directory
                    temp_zip_path = os.path.join(temp_dir, "downloaded_files.zip")
                    with open(temp_zip_path, "wb") as file:
                        file.write(file_response.content)

                    # Create a directory to extract the files
                    extract_dir = os.path.join(temp_dir, "extracted_files")
                    os.makedirs(extract_dir, exist_ok=True)

                    # Extract the downloaded zip file
                    try:
                        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                            zip_ref.extractall(extract_dir)
                        print(f"Files extracted to {extract_dir}")
                        return True
                    except zipfile.BadZipFile:
                        print("Downloaded file is not a valid zip file")
                        # Save the raw file anyway in case it's a direct file download
                        with open(
                            os.path.join(extract_dir, "downloaded_file"), "wb"
                        ) as f:
                            f.write(file_response.content)
                        print("Saved raw downloaded file")
                        return True
                else:
                    print(f"Error downloading file: {file_response.status_code}")
                    print(file_response.text)
                    return False
            else:
                print("zipId not found in the response")
                return False
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False

    def scrape_document(self, url: str, index: int) -> None:
        """
        Scrapes a document URL and saves all found files in a zip file.
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")
        download_id = url[
            url.rindex("/") + 1 :
        ]  # Get unique ID after last slash in url "e.g. https://open.brabant.nl/woo-verzoeken/e661cfe8-5f7a-49d5-8cf3-c8bcb65309d8"
        zip_path = os.path.join(self.base_download_dir, f"woo-{download_id}.zip")
        if os.path.exists(zip_path):
            print(f"Zip file woo-{download_id}.zip already exists")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            html_content = self.fetch_html(url)
            if not html_content:
                print(f"Could not retrieve content for {url}")
                return

            metadata = self.generate_metadata(html_content, url)
            metadata_path = self.create_metadata_file(metadata, temp_dir)

            # Extract document IDs and download files
            payload = self.extract_document_ids(html_content)

            download_url = f"https://api-brabant.iprox-open.nl/api/v1/public/download/{download_id}"

            # Download files to temp directory
            download_success = self.download_files(download_url, payload, temp_dir)

            # Create zip file with metadata and downloaded files
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add metadata file
                zipf.write(metadata_path, arcname="metadata.txt")

                # Add downloaded files from the extracted directory
                extract_dir = os.path.join(temp_dir, "extracted_files")
                if download_success and os.path.exists(extract_dir):
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calculate relative path for the archive
                            arcname = os.path.relpath(file_path, extract_dir)
                            # Add file to the zip
                            zipf.write(
                                file_path, arcname=os.path.join("files", arcname)
                            )
                            print(f"Added to zip: {arcname}")

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
        "https://open.brabant.nl/woo-verzoeken/e661cfe8-5f7a-49d5-8cf3-c8bcb65309d8"
    )
    scraper = Scraper()
    scraper.scrape_document(EXAMPLE_DOC_URL, 1)
