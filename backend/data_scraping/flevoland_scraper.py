import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote, urljoin
import zipfile
import tempfile
import hashlib
import re
import locale
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests


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

    def _get_file_hash(self, url: str) -> str:
        """
        Generates a unique hash for a file URL.

        Args:
            url (str): The URL to hash

        Returns:
            str: MD5 hash of the URL

        Example:
            hash = scraper._get_file_hash("https://example.com/document.pdf")
        """
        return hashlib.md5(url.encode()).hexdigest()

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

    def fetch_html(self, url: str) -> str:
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

    def fetch_html_with_selenium(self, url: str) -> str:

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

            # 3. Waits for the iframe to appear (up to 10 seconds)
            iframe_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "site-iframe"))
            )

            # 4. Gets the actual source URL of the iframe
            iframe_src = iframe_element.get_attribute("src")
            iframe_base_url = iframe_src or url

            # 5. Switches browser context to inside the iframe
            driver.switch_to.frame(iframe_element)
            # 6. Gets the fully rendered HTML content inside the iframe
            iframe_html = driver.page_source
            return iframe_html, iframe_base_url

        finally:
            # Clean up Selenium if it was used
            if driver:
                driver.quit()

    def generate_metadata(self, html_content: str, url: str, selenium_url: str) -> dict:
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
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            metadata = {
                "url": url,
                "provincie": "Flevoland",
                "titel": "",
                "datum": "",
                "type": "woo-verzoek",
            }

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

            # If using selenium/archive links the date is hidden in the link itself instead of on the HTML page
            if selenium_url:
                print(selenium_url)
                # Find timestamp in selenium_url
                pattern = r"/archiefweb/(\d+)/"
                # Search for the pattern in the URL/string
                match = re.search(pattern, selenium_url)
                print(match.group(1))
                date_paragraph = match.group(1)
                if date_paragraph:
                    date_part = date_paragraph[:8]  # (YYYYMMDD format)
                    # Convert to datetime object
                    d = datetime.strptime(date_part, "%Y%m%d")
                    # Format as dd-mm-yyyy
                    date_str = d.strftime("%d-%m-%Y")
                    metadata["datum"] = date_str
            else:
                datum_heading = soup.find("h2", string="Datum besluit") or soup.find(
                    "h2", string="Datum"
                )
                date_paragraph = datum_heading.find_next("p")

                if date_paragraph:
                    locale.setlocale(locale.LC_ALL, "nl_NL")
                    d = datetime.strptime(date_paragraph.text, "%d %B %Y")
                    # Convert dd-month-yyyy to dd-mm-yyyy format
                    date_str = d.strftime("%d-%m-%Y")
                    metadata["datum"] = date_str

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

        ####################################################
        # First check if we can find the doc_links in the HTML content (without selenium)
        # This for newer html pages (e.g. not the archive)
        soup = BeautifulSoup(html_content, "html.parser")
        # Find all buttons (a elements with class="button")
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
        return doc_links

    def get_filename_from_url(self, url: str) -> str:
        """
        Extracts original filename from URL and adds hash for uniqueness.

        Args:
            url (str): The URL of the file

        Returns:
            str: A unique filename based on the URL

        Example:
            filename = scraper.get_filename_from_url("https://example.com/doc.pdf")
        """
        parsed_url = urlparse(url)
        original_filename = os.path.basename(unquote(parsed_url.path))

        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            original_filename = original_filename.replace(char, "_")

        # Add hash to filename for uniqueness
        file_hash = self._get_file_hash(url)
        filename_parts = os.path.splitext(original_filename)
        return f"{file_hash}_{filename_parts[0]}{filename_parts[1]}"

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
            print("*" * 50)
            print(selenium_url)
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
            if self.download_document(doc_url, save_path):
                downloaded_files.append(save_path)

    def __del__(self):
        """
        Destructor to ensure the session is closed.

        Ensures proper cleanup of resources when the object is destroyed.
        """
        try:
            self.session.close()
        except:
            pass


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
