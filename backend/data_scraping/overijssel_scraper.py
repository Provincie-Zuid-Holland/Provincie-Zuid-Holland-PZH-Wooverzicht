from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from urllib.parse import urlparse, unquote
import zipfile
import tempfile
import hashlib


class Scraper:
    """
    A class for scraping and downloading documents from the WOO portal Overijssel.
    Uses Selenium for loading JavaScript-rendered content and BeautifulSoup for HTML parsing.
    Documents are downloaded and stored in zip files along with their metadata.
    The scraper keeps track of which files have already been downloaded to avoid duplicates.

    Attributes:
        supported_extensions (tuple): List of supported file extensions (.pdf, .docx, etc.)
        base_download_dir (str): Base directory where zip files are stored
        downloaded_files_cache (dict): Cache of already downloaded files and their locations
        driver (webdriver.Chrome): Selenium WebDriver instance for loading JavaScript content
        wait (WebDriverWait): WebDriverWait instance for waiting for elements

    Functions:
        _get_file_hash: Generates a unique hash for a file URL to identify duplicates
        _is_supported_file: Checks if a file type is supported for download
        fetch_html: Retrieves HTML content from a page, including JavaScript-rendered content
        generate_metadata: Extracts metadata from HTML content
        get_filename_from_url: Generates a unique and valid filename from a URL
        find_documents: Finds all downloadable documents in the HTML content
        download_document: Downloads a document with error handling and retries
        create_metadata_file: Creates a text file with metadata information
        scrape_document: Main function that scrapes a document URL and downloads all found files
    """

    def __init__(self):
        """
        Initializes the Scraper with the basic folder structure and maintains a cache of downloaded files.
        """
        # List of supported file formats
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
            ".zip",
        )

        # Set WebDriverManager to use system cache directory
        os.environ["WDM_CACHE_DIR"] = "/.wdm"

        # Selenium configuration
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1920,1080")

        # Use binary location to point to installed Chrome
        options.binary_location = "/usr/bin/google-chrome"

        # Use ChromeDriverManager with the latest version
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def _get_file_hash(self, url: str) -> str:
        """
        Generates a unique hash for a file URL.

        Args:
            url (str): The URL of the file

        Returns:
            str: MD5 hash of the URL as a hexadecimal string

        Example:
            hash_value = scraper._get_file_hash("https://example.com/document.pdf")
            print(hash_value)  # Output: a1b2c3d4...
        """
        return hashlib.md5(url.encode()).hexdigest()

    def _is_supported_file(self, url: str) -> bool:
        """
        Checks if the file type is supported.

        Args:
            url (str): The URL of the file to check

        Returns:
            bool: True if the file extension is supported, False otherwise

        Example:
            if scraper._is_supported_file("https://example.com/document.pdf"):
                print("This file type is supported")
        """
        return url.lower().endswith(self.supported_extensions)

    def fetch_html(self, url: str) -> str | None:
        """
        Retrieves HTML content using Selenium for JavaScript-rendered content.

        Args:
            url (str): The URL to fetch HTML content from

        Returns:
            str: The HTML content as a string, or None if the fetch failed

        Raises:
            Exception: If there's an issue with the Selenium driver or timeout

        Example:
            html_content = scraper.fetch_html("https://example.com/page")
            if html_content:
                print(f"Successfully retrieved {len(html_content)} bytes")
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Fetching HTML (attempt {attempt + 1}/{max_retries})")
                self.driver.get(url)
                time.sleep(2)  # Give JavaScript time to load

                try:
                    self.wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".print-document, .document-hoofd")
                        )
                    )
                except Exception as e:
                    print(f"Warning: Timeout waiting for main content: {e}")

                return self.driver.page_source

            except Exception as e:
                print(f"Error fetching HTML (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    def generate_metadata(self, html_content: str, url: str) -> dict:
        """
        Generates metadata from the HTML content.

        Args:
            html_content (str): The HTML content to extract metadata from

        Returns:
            dict: A dictionary containing extracted metadata with keys:
            metadata = {
                "url": www.url.com,
                "provincie": "Overijssel",
                "titel": "titel",
                "datum": "01-11-1999",
                "type": "woo-verzoek",
            }

        Example:
            html = scraper.fetch_html("https://example.com/page")
            metadata = scraper.generate_metadata(html)
            print(f"Document title: {metadata['title']}")
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            metadata = {
                "url": url,
                "provincie": "Overijssel",
                "titel": "",
                "datum": "",
                "type": "",
            }
            # Get the title
            title_div = soup.find("div", class_="print-document")
            title = (
                (
                    title_div.find("div", class_="document-hoofd")
                    .find("a")
                    .get_text(strip=True)
                )
                if title_div
                else ""
            )
            metadata["titel"] = title
            # Get the creation year
            creation_year_tag = soup.find("td", string="Creatie jaar")
            creation_year = (
                creation_year_tag.find_next_sibling("td").get_text(strip=True)
                if creation_year_tag
                else ""
            )
            metadata["datum"] = (
                int(datetime.strptime(creation_year, "%Y").timestamp())
                if creation_year
                else 0
            )
            # Get the WOO themes
            woo_theme_tag = soup.find("td", string="WOO thema's")
            woo_theme = (
                woo_theme_tag.find_next_sibling("td").find("li")
                if woo_theme_tag
                else ""
            )
            metadata["type"] = woo_theme.text

            # Combine results in a dictionary
            return metadata

        except Exception as e:
            print(f"Error generating metadata: {e}")
            return metadata

    def get_filename_from_url(self, url: str) -> str:
        """
        Extracts the original filename from the URL and adds a hash for uniqueness.

        Args:
            url (str): The URL of the file

        Returns:
            str: A unique filename based on the URL with added hash

        Example:
            filename = scraper.get_filename_from_url("https://example.com/documents/report.pdf")
            print(filename)  # Output: a1b2c3d4_report.pdf
        """
        parsed_url = urlparse(url)
        original_filename = os.path.basename(unquote(parsed_url.path))

        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            original_filename = original_filename.replace(char, "_")

        # Add hash to filename for unique identification
        file_hash = self._get_file_hash(url)
        filename_parts = os.path.splitext(original_filename)
        return f"{file_hash}_{filename_parts[0]}{filename_parts[1]}"

    def find_documents(self, html_content: str) -> list:
        """
        Searches for all supported document types in the HTML content.

        Args:
            html_content (str): The HTML content to search in

        Returns:
            list: A list of tuples containing (document_url, filename)

        Example:
            html = scraper.fetch_html("https://example.com/page")
            documents = scraper.find_documents(html)
            print(f"Found {len(documents)} downloadable documents")
        """
        doc_links = []
        if not html_content:
            return doc_links

        soup = BeautifulSoup(html_content, "html.parser")
        print("Searching for document links...")

        # First look in the attachments section
        bijlagen_cell = soup.find("td", string="Bijlagen")
        if bijlagen_cell:
            bijlagen_content = bijlagen_cell.find_next_sibling("td")
            if bijlagen_content:
                links = bijlagen_content.find_all("a", href=True)
                for link in links:
                    href = link["href"]
                    if self._is_supported_file(href):
                        filename = self.get_filename_from_url(href)
                        extension = os.path.splitext(href.lower())[1]
                        print(
                            f"{extension.upper()[1:]} file found in attachments: {filename}"
                        )
                        doc_links.append((href, filename))

        # As backup, also search the entire document
        if not doc_links:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if self._is_supported_file(href):
                    filename = self.get_filename_from_url(href)
                    extension = os.path.splitext(href.lower())[1]
                    print(f"{extension.upper()[1:]} file found: {filename}")
                    doc_links.append((href, filename))

        return doc_links

    def download_document(self, url: str, save_path: str) -> bool:
        """
        Downloads a document with improved error handling.

        Args:
            url (str): The URL of the document to download
            save_path (str): The path where the document should be saved

        Returns:
            bool: True if download was successful, False otherwise

        Example:
            success = scraper.download_document(
                "https://example.com/document.pdf",
                "/tmp/downloads/document.pdf"
            )
            if success:
                print("Document downloaded successfully")
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(
                    f"Downloading document (attempt {attempt + 1}/{max_retries}): {os.path.basename(save_path)}"
                )
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(save_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

                if os.path.getsize(save_path) > 0:
                    extension = os.path.splitext(save_path)[1].upper()[1:]
                    if extension == "ZIP":
                        with zipfile.ZipFile(save_path, "r") as zip_ref:
                            folder_path = os.path.dirname(
                                save_path
                            )  # Extract folder location from save path by removing last part of path behind / or \\
                            zip_ref.extractall(folder_path)
                        os.remove(save_path)
                        print(
                            f"{extension} file successfully downloaded and extracted: {os.path.basename(save_path)}"
                        )
                    else:
                        print(
                            f"{extension} file successfully downloaded: {os.path.basename(save_path)}"
                        )
                    return True
                else:
                    print("Warning: Downloaded file is empty")
                    os.remove(save_path)

            except Exception as e:
                print(f"Error downloading (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(2)
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
                "url": www.url.nl,
                "provincie": "Overijssel",
                "titel": "titel",
                "datum": "01-11-1999",
                "type": "woo-verzoek",
            }
            metadata_path = scraper.create_metadata_file(metadata, "/tmp/downloads")
            print(f"Metadata saved to {metadata_path}")
        """
        metadata_path = os.path.join(temp_dir, "metadata.txt")
        with open(metadata_path, "w", encoding="utf-8") as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        return metadata_path

    def check_file_size_not_too_large(self, url):
        """
        Checkt de grootte van het zip bestand.
        """
        try:
            response = self.session.head(url, headers=self.headers, timeout=30)
            file_size = int(response.headers.get("content-length", 0))
            # Load max size from .env
            max_size = int(os.getenv("MAX_ZIP_SIZE", 2.5 * 1024 * 1024 * 1024))  # 2.5GB
            if file_size > max_size:
                print(f"Zip bestand is te groot ({file_size / (1024 * 1024):.2f} MB)")
                return False
            return True
        except Exception as e:
            print(f"Fout bij controleren zip bestand grootte: {e}")
            return False

    def scrape_document(
        self, temp_dir: tempfile.TemporaryDirectory, url: str, index: int
    ) -> None:
        """
        Scrapes a document URL and saves all found files in a zip file.

        Args:
            url (str): The URL of the document page to scrape
            index (int): The index number for identifying the zip file

        Returns:
            None

        Example:
            scraper.scrape_document("https://example.com/woo/document123", 42)
            # This will create woo-42.zip if documents are found
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")

        html_content = self.fetch_html(url)
        if not html_content:
            print(f"Could not retrieve content for {url}")
            return

        # Generate and save metadata
        metadata = self.generate_metadata(html_content, url)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Find all document links
        doc_links = self.find_documents(html_content)
        if not doc_links:
            print("No documents found")
            return

        print(f"{len(doc_links)} document(s) found to download")

        # Download only new files
        downloaded_files = []
        for doc_url, filename in doc_links:
            save_path = os.path.join(temp_dir, filename)
            if self.check_file_size_not_too_large(doc_url):
                if self.download_document(doc_url, save_path):
                    downloaded_files.append(save_path)
            else:
                # Log dat het zip bestand te groot is
                print(
                    f"Bestand is te groot ({doc_url}) en is niet gedownload. "
                    f"Maximale grootte is {os.getenv('MAX_ZIP_SIZE', 2.5 * 1024 * 1024 * 1024) / (1024 * 1024 * 1024)} GB"
                )
                # sla link naar zip bestand op in tekst bestand
                with open("failed_downloads.txt", "a+") as f:
                    f.write(f"Bestand te groot: {doc_url}\n")


if __name__ == "__main__":
    BASE_URL = "https://woo.dataportaaloverijssel.nl/list"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = "https://woo.dataportaaloverijssel.nl/list/document/e2808ed7-b8bb-4a50-85d5-2af12e771b62"
    scraper = Scraper()
    with tempfile.TemporaryDirectory() as temp_dir:
        scraper.scrape_document(temp_dir, EXAMPLE_DOC_URL, 1)

        # Verify the temp directory is created, and still exists
        print("\nTemp directory:", temp_dir)
        assert os.path.exists(temp_dir)

        # Verify that the downloaded files are in the temp directory
        print("\nTemp directory contents:")
        for filename in os.listdir(temp_dir):
            print(filename)

        # Verify that the metadata file was created
        metadata_file = os.path.join(temp_dir, "metadata.txt")
        if os.path.exists(metadata_file):
            print("\nMetadata file contents:")
            with open(metadata_file, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("\nMetadata file not found")

        # Verify that the downloaded files are not empty
        print("\nDownloaded files:")
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.getsize(file_path) > 0:
                print(f"{filename} - OK")
            else:
                print(f"{filename} - Empty file")
