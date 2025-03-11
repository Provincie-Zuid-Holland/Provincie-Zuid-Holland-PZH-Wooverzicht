import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
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
        _build_existing_files_cache: Builds a cache of all files already downloaded in zip files
        _get_file_hash: Generates a unique hash for a file URL to identify duplicates
        _is_file_downloaded: Checks if a file has already been downloaded
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
        )

        # Create the base download directory for zip files with province subfolder
        downloads_base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data_scraping", "downloads"
        )
        self.base_download_dir = os.path.join(downloads_base, "overijssel")
        os.makedirs(self.base_download_dir, exist_ok=True)

        # Cache to keep track of downloaded files
        self.downloaded_files_cache = self._build_existing_files_cache()

        # Selenium configuration
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def _build_existing_files_cache(self) -> dict:
        """
        Builds a cache of existing files in zip files.

        Returns:
            dict: A dictionary mapping filenames to their containing zip paths

        Raises:
            Exception: If there's an error accessing the zip files or directory

        Example:
            cache = scraper._build_existing_files_cache()
            print(f"Found {len(cache)} previously downloaded files")
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
            url (str): The URL of the file

        Returns:
            str: MD5 hash of the URL as a hexadecimal string

        Example:
            hash_value = scraper._get_file_hash("https://example.com/document.pdf")
            print(hash_value)  # Output: a1b2c3d4...
        """
        return hashlib.md5(url.encode()).hexdigest()

    def _is_file_downloaded(self, filename: str, url: str) -> tuple:
        """
        Checks if a file has already been downloaded.

        Args:
            filename (str): The filename to check
            url (str): The URL of the file

        Returns:
            tuple: (bool, str) - Whether the file is downloaded and its zip path if applicable

        Example:
            is_downloaded, zip_path = scraper._is_file_downloaded("document.pdf", "https://example.com/document.pdf")
            if is_downloaded:
                print(f"File already exists in {zip_path}")
        """
        if filename in self.downloaded_files_cache:
            return True, self.downloaded_files_cache[filename]

        file_hash = self._get_file_hash(url)
        for existing_file, zip_path in self.downloaded_files_cache.items():
            if existing_file.startswith(file_hash):
                return True, zip_path

        return False, None

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

    def fetch_html(self, url: str) -> str:
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

    def generate_metadata(self, html_content: str) -> dict:
        """
        Generates metadata from the HTML content.

        Args:
            html_content (str): The HTML content to extract metadata from

        Returns:
            dict: A dictionary containing extracted metadata with keys:
                - title: Document title
                - summary: Document summary/description
                - creation_year: Document creation year
                - woo_themes: List of WOO themes/categories

        Example:
            html = scraper.fetch_html("https://example.com/page")
            metadata = scraper.generate_metadata(html)
            print(f"Document title: {metadata['title']}")
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Get the title
            title_div = soup.find("div", class_="print-document")
            title = (
                title_div.find("div", class_="document-hoofd")
                .find("a")
                .get_text(strip=True)
            )

            # Get the summary
            summary_td = soup.find("td", class_="zoekoverzicht", colspan="2")
            summary = (
                summary_td.find_all("p")[1].get_text(strip=True)
                if len(summary_td.find_all("p")) > 1
                else ""
            )

            # Get the creation year
            creation_year_tag = soup.find("td", string="Creatie jaar")
            creation_year = (
                creation_year_tag.find_next_sibling("td").get_text(strip=True)
                if creation_year_tag
                else None
            )

            # Get the WOO themes
            woo_themes_tag = soup.find("td", string="WOO thema's")
            woo_themes_list = (
                woo_themes_tag.find_next_sibling("td").find_all("li")
                if woo_themes_tag
                else []
            )
            woo_themes = [theme.get_text(strip=True) for theme in woo_themes_list]

            # Combine results in a dictionary
            return {
                "title": title,
                "summary": summary,
                "creation_year": creation_year,
                "woo_themes": woo_themes,
            }

        except Exception as e:
            print(f"Error generating metadata: {e}")
            return {
                "title": "Unknown",
                "summary": "Not available",
                "creation_year": "Unknown",
                "woo_themes": [],
            }

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
            metadata (dict): The metadata to write to the file
            temp_dir (str): The directory where the metadata file should be created

        Returns:
            str: The path to the created metadata file

        Example:
            metadata = {
                "title": "Example Document",
                "summary": "An example document",
                "creation_year": "2023",
                "woo_themes": ["Example Theme"]
            }
            metadata_path = scraper.create_metadata_file(metadata, "/tmp/downloads")
            print(f"Metadata saved to {metadata_path}")
        """
        metadata_path = os.path.join(temp_dir, "metadata.txt")
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {metadata['title']}\n")
            f.write(f"Summary: {metadata['summary']}\n")
            f.write(f"Creation year: {metadata['creation_year']}\n")
            f.write(f"WOO themes: {', '.join(metadata['woo_themes'])}\n")
        return metadata_path

    def scrape_document(self, temp_dir: tempfile.TemporaryDirectory, url: str, index: int) -> None:
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

        # # Check if zip file already exists
        # zip_path = os.path.join(self.base_download_dir, f"woo-{index}.zip")
        # if os.path.exists(zip_path):
        #     print(f"Zip file woo-{index}.zip already exists")
        #     return

        html_content = self.fetch_html(url)
        if not html_content:
            print(f"Could not retrieve content for {url}")
            return

        # Generate and save metadata
        metadata = self.generate_metadata(html_content)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Find all document links
        doc_links = self.find_documents(html_content)
        if not doc_links:
            print("No documents found")
            return

        print(f"{len(doc_links)} document(s) found to download")

        # Download only new files
        downloaded_files = []
        skipped_files = []
        for doc_url, filename in doc_links:
            # is_downloaded, existing_zip = self._is_file_downloaded(
            #     filename, doc_url
            # )
            # if is_downloaded:
            #     print(
            #         f"File {filename} has already been downloaded in {existing_zip}"
            #     )
            #     skipped_files.append((filename, existing_zip))
            #     continue

            save_path = os.path.join(temp_dir, filename)
            if self.download_document(doc_url, save_path):
                downloaded_files.append(save_path)
                # # Update cache with new file
                # self.downloaded_files_cache[filename] = zip_path

        # # Only create a zip file if there are new files
        # if downloaded_files:
        #     with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        #         # Add metadata
        #         zipf.write(metadata_path, os.path.basename(metadata_path))

        #         # Add new files
        #         for file_path in downloaded_files:
        #             zipf.write(file_path, os.path.basename(file_path))

        #     print(f"Zip file created: woo-{index}.zip")
        #     print(f"Number of new files: {len(downloaded_files)}")
        #     print(f"Number of skipped files: {len(skipped_files)}")
        # else:
        #     print("No new files to download")

    def __del__(self):
        """
        Cleanup Selenium driver when closing.

        Ensures the Selenium driver is properly closed to prevent resource leaks.
        """
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    BASE_URL = "https://woo.dataportaaloverijssel.nl/list"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = (
        "https://woo.dataportaaloverijssel.nl/list/document/cd16950c-e62e-4b63-b275-60d29481c343"
    )
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