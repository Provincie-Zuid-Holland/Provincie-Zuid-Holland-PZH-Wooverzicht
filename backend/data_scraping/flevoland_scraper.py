import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote
import zipfile
import tempfile
import re
from datetime import timezone
import dateparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    InvalidArgumentException,
)
from typing import Tuple
import logging


class Scraper:
    """
    A class for scraping and downloading documents from Flevoland's WOO portal.
    Uses requests and BeautifulSoup for HTML parsing.
    Downloads are saved in zip files along with their metadata.
    Keeps track of downloaded files to prevent duplicates.

    Attributes:
        supported_extensions (tuple): List of supported file extensions (.pdf, .docx, etc.)
        base_download_dir (str): Base directory where zip files are stored
        downloaded_files_cache (dict): Cache of previously downloaded files and their locations
        session (requests.Session): Session for reusing connections
        headers (dict): HTTP headers for requests
    """

    def __init__(self):
        """
        Initializes the Scraper with the base directory structure and maintains a cache of downloaded files.

        Example:
            scraper = Scraper()
        """
        # List of supported file formats
        self.supported_extensions = ".pdf"

        # Create the base download directory with province subfolder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_base = os.path.join(script_dir, "downloads")
        self.base_download_dir = os.path.join(downloads_base, "flevoland")
        os.makedirs(self.base_download_dir, exist_ok=True)

        print(f"Files will be saved to: {self.base_download_dir}")

        # Cache for tracking downloaded files
        self.downloaded_files_cache = self._build_existing_files_cache()

        # Requests session for connection reuse
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def _build_existing_files_cache(self) -> dict:
        """
        Builds a cache of existing files in zip archives.

        Returns:
            dict: Cache mapping filenames to their zip locations

        Example:
            cache = scraper._build_existing_files_cache()
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

    def _is_supported_file(self, url: str) -> bool:
        """
        Checks if a file type is supported for download.

        Args:
            url (str): The URL to check

        Returns:
            bool: True if the file type is supported

        Example:
            if scraper._is_supported_file("document.pdf"):
                print("This is a supported file type")
        """
        return url.lower().endswith(self.supported_extensions)

    def fetch_html(self, url: str) -> str | None:
        """
        Fetches HTML content using requests.

        Args:
            url (str): The URL to fetch

        Returns:
            str: The HTML content of the page, or None if failed

        Example:
            html = scraper.fetch_html("https://example.com")
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Fetching HTML (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.text

            except Exception as e:
                print(f"Error fetching HTML (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    def fetch_html_with_selenium(self, url: str) -> Tuple[str, str] | Tuple[None, None]:
        """
        Fetches HTML content using selenium. This is necessary for pages that load content dynamically. (e.g. with javascript)
        This function is used for archived woo verzoeken of Flevoland

        Args:
            url (str): The URL to fetch

        Returns:
            str: The HTML content of the page
            str: Url of the iframe

        Example:
            html = scraper.fetch_html_with_selenium("https://deeplink.archiefweb.eu/FbBW/")
        """
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = None

        try:
            # Selenium is needed because BeautifulSoup can only parse static HTML,
            # but can't access content inside iframes or execute JavaScript.
            # This code:
            # 1. Launches a real Chrome browser (headless)
            driver = webdriver.Chrome(options=options)
            # 2. Actually visits the webpage, executing all JavaScript and loading all resources
            driver.get(url)

            # 3. Waits for the iframe to appear (up to 5 seconds)
            iframe_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "site-iframe"))
            )

            # 4. Gets the actual source URL of the iframe, this is used to retrieve the date published of archived woo verzoeken. (the date is hidden in the url and can not be found on the site itself)
            iframe_base_url = iframe_element.get_attribute("src")
            # 5. Switches browser context to inside the iframe
            driver.switch_to.frame(iframe_element)
            # 6. Gets the fully rendered HTML content inside the iframe
            iframe_html = driver.page_source
            return iframe_html, iframe_base_url
        except TimeoutException as e:
            print(f"Fetching HTML with Selenium Timed out: {e}")
            return None, None
        except InvalidArgumentException as e:
            print(f"Invalid URL: {e}")
            return None, None

        finally:
            # Clean up Selenium if it was used
            if driver:
                driver.quit()

    def _extract_publiekssamenvatting(self, soup: BeautifulSoup, url: str) -> str:
        """
        Extracts the publiekssamenvatting from the HTML content.
        Handles both newer sites (with 'Samenvatting' header) and older sites (positioned above 'Documenten' header).

        Args:
            soup (BeautifulSoup): Parsed HTML content
            url (str): The URL of the page (for determining site type)

        Returns:
            str: The publiekssamenvatting text, or empty string if not found
        """
        try:
            # Check if this is a newer site (flevoland.nl domain)
            if "flevoland.nl" in url and "archiefweb.eu" not in url:
                # Assumption: Site always has a 'Samenvatting' header, and the next paragraph contains the summary
                samenvatting_header = soup.find("h2", string="Samenvatting")
                if samenvatting_header:
                    next_paragraph = samenvatting_header.find_next("p")
                    if next_paragraph:
                        return next_paragraph.get_text(strip=True)

            # Older site: Look for content positioned before the "Documenten" header
            documenten_header = soup.find("h2", string="Documenten")
            if documenten_header:
                preceding_elements = []
                current = documenten_header.find_previous_sibling()

                # Walk backwards through siblings until we find substantial content
                while current:
                    if current.name == "p":
                        text = current.get_text(strip=True)
                        if len(text) > 50:  # Filter out short paragraphs
                            preceding_elements.append(text)
                    elif current.name in ["h1", "h2", "h3"]:
                        # Stop if we hit another header (we've gone too far back)
                        break
                    current = current.find_previous_sibling()

                if preceding_elements:
                    return max(preceding_elements, key=len)

            # fallback: Look for text starting with common patterns
            patterns = [
                r"^Er is een verzoek gedaan in het kader van de Wet openbaarheid van bestuur",
                r"^Naar aanleiding van een verzoek op grond van de Wet open overheid",
                r"^Er is een verzoek gedaan.*Wet.*openbaarheid",
                r"^Naar aanleiding van een.*verzoek.*Woo",
            ]

            paragraphs = soup.find_all("p")
            for paragraph in paragraphs:
                text = paragraph.get_text(strip=True)
                for pattern in patterns:
                    if re.match(pattern, text, re.IGNORECASE):
                        return text

        except Exception as e:
            print(f"Error extracting publiekssamenvatting: {e}")

        return ""

    def generate_metadata(self, html_content: str, url: str, selenium_url=None) -> dict:
        """
        Extracts metadata from the HTML content.

        Args:
            html_content (str): The HTML content to parse
            url (str): The URL of the page

        Returns:
            dict: Dictionary containing metadata fields

        Example:
            metadata = scraper.generate_metadata(html, "https://example.com")
        """
        metadata = {
            "url": url,
            "provincie": "Flevoland",
            "titel": "",
            "datum": "",
            "type": "woo-verzoek",
            "publiekssamenvatting": "",
        }
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Try to find title
            title_candidates = [
                soup.find("h1"),
                soup.find("meta", property="og:title"),
                soup.find("title"),
            ]

            for candidate in title_candidates:
                if candidate:
                    if candidate.name == "meta":
                        metadata["titel"] = candidate.get("content", "").strip()
                    else:
                        metadata["titel"] = candidate.get_text(strip=True)
                    break

            # Extract publiekssamenvatting
            metadata["publiekssamenvatting"] = self._extract_publiekssamenvatting(
                soup, url
            )

            # If using selenium/archive links the date is hidden in the link itself instead of on the HTML page
            if selenium_url:
                # Find timestamp in selenium_url in between /archiefweb/ and /
                # Example: https://deeplink.archiefweb.eu/FbBW/archiefweb/20230901/archiefweb.eu/FbBW
                pattern = r"/archiefweb/(\d+)/"
                # Search for the pattern in the URL/string using regex
                match = re.search(pattern, selenium_url)
                date_paragraph = match.group(1) if match else None
                # Convert YYYYMMDD to dd-mm-yyyy format
                if date_paragraph:
                    date_part = date_paragraph[:8]  # (YYYYMMDD format)
                    # Convert to datetime object
                    d = dateparser.parse(date_part).replace(tzinfo=timezone.utc)
                    metadata["datum"] = int(d.timestamp())
            else:
                datum_heading = soup.find("h2", string="Datum besluit") or soup.find(
                    "h2", string="Datum"
                )
                date_paragraph = datum_heading.find_next("p") if datum_heading else None

                if date_paragraph:
                    d = dateparser.parse(date_paragraph.text).replace(
                        tzinfo=timezone.utc
                    )
                    metadata["datum"] = int(d.timestamp())

            return metadata

        except Exception as e:
            print(f"Error generating metadata: {e}")
            return metadata

    def find_documents(self, html_content: str, url: str) -> list:
        """
        Searches for all supported document types in the HTML content.

        Args:
            html_content (str): The HTML content to parse
            url (str): The URL of the page

        Returns:
            list: List of tuples containing (document_url, filename)

        Example:
            documents = scraper.find_documents(html, "https://example.com")
        """
        doc_links = []
        if not html_content:
            return doc_links

        soup = BeautifulSoup(html_content, "html.parser")

        # All woo verzoeken (except for very old ones) have a button with the text "Open de PDF". Therefore we can use this to find the document links.
        buttons = soup.find_all("a", class_="button")

        for button in buttons:
            # Check if button text contains 'Open de PDF' (case insensitive)
            if "open de pdf" in button.text.lower():
                # Extract the href attribute
                if button.has_attr("href"):
                    base_url = "https://www.flevoland.nl/"
                    # if url contains "archiefweb.eu" use other base url
                    if "archiefweb.eu" in url:
                        base_url = ""
                    link = base_url + button["href"]
                    filename = self.get_filename_from_url(button["href"])
                    doc_links.append((link, filename))

        # If no doc_links default to finding all links ending in pdf. This is used for older woo verzoeken.
        if not doc_links:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if self._is_supported_file(href):
                    filename = self.get_filename_from_url(href)
                    extension = os.path.splitext(href.lower())[1]
                    print(f"{extension.upper()[1:]} file found: {filename}")
                    doc_links.append((href, filename))

        return doc_links

    def get_filename_from_url(self, url: str) -> str:
        """
        Extracts original filename from URL.
        Args:
            url (str): The URL of the file

        Returns:
            str: A filename based on the URL, sanitized for invalid characters.

        Example:
            filename = scraper.get_filename_from_url("https://example.com/doc.pdf")
        """
        parsed_url = urlparse(url)
        original_filename = os.path.basename(unquote(parsed_url.path))

        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            original_filename = original_filename.replace(char, "_")

        return f"{original_filename}"

    def download_document(self, url: str, save_path: str) -> bool:
        """
        Downloads a document with error handling and retries.

        Args:
            url (str): The URL of the document to download
            save_path (str): Where to save the downloaded file

        Returns:
            bool: True if download was successful

        Example:
            success = scraper.download_document("https://example.com/doc.pdf", "doc.pdf")
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(
                    f"Downloading document (attempt {attempt + 1}/{max_retries}): {os.path.basename(save_path)}"
                )
                response = self.session.get(
                    url, stream=True, headers=self.headers, timeout=30
                )
                response.raise_for_status()

                with open(save_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

                if os.path.getsize(save_path) > 0:
                    extension = os.path.splitext(save_path)[1].upper()[1:]
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

    def create_metadata_file(self, metadata: dict, temp_dir: str) -> str:
        """
        Creates a metadata text file.

        Args:
            metadata (dict): The metadata to write
            temp_dir (str): Directory to save the file in

        Returns:
            str: Path to the created metadata file

        Example:
            metadata_path = scraper.create_metadata_file(metadata, "/tmp")
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
        Main function that scrapes a document URL and downloads all found files.

        Args:
            url (str): The URL to scrape
            index (int): Index number for the zip file

        Example:
            scraper.scrape_document("https://example.com/woo/123", 1)
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")

        selenium_url = None
        # if url contains "archiefweb.eu" fetch html with selenium
        if "archiefweb.eu" in url:
            html_content, selenium_url = self.fetch_html_with_selenium(url)
        else:
            html_content = self.fetch_html(url)
        if not html_content:
            print(f"Could not fetch content for {url}")
            return

        # Generate and save metadata
        metadata = self.generate_metadata(html_content, url, selenium_url)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Find document links
        doc_links = self.find_documents(html_content, url)
        if not doc_links:
            print("No documents found")
            return

        print(f"Found {len(doc_links)} document(s) to download")

        # Download files
        downloaded_files = []
        # skipped_files = []

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

    def __del__(self):
        """
        Destructor to ensure the session is closed.
        """
        try:
            self.session.close()
        except AttributeError as e:
            logging.warning("Session attribute not found in destructor: %s", e)
        except Exception as e:
            logging.error("Failed to close session in destructor: %s", e)


if __name__ == "__main__":
    BASE_URL = (
        "https://www.flevoland.nl/loket/openbare-documenten/woo-verzoeken-archief"
    )

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = "https://deeplink.archiefweb.eu/FbBW/"
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
