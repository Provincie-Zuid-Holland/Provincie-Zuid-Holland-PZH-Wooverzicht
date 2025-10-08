import os
import requests
from bs4 import BeautifulSoup
import dateparser
from datetime import timezone
import time
from urllib.parse import urlparse, unquote, urljoin
import zipfile
import tempfile
import hashlib
import re
import logging


class Scraper:
    """
    A class for scraping and downloading documents from the WOO portal Zuid-Holland.
    Uses requests and BeautifulSoup for HTML parsing.
    Documents are downloaded and stored in zip files along with their metadata.
    The scraper keeps track of which files have already been downloaded to avoid duplicates.

    Attributes:
        supported_extensions (tuple): List of supported file extensions (.pdf, .docx, etc.)
        base_download_dir (str): Base directory where zip files are stored
        downloaded_files_cache (dict): Cache of already downloaded files and their locations
        session (requests.Session): Requests session for connection reuse
        headers (dict): HTTP headers for requests
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
        # Fix the path to be relative to the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_base = os.path.join(script_dir, "downloads")
        self.base_download_dir = os.path.join(downloads_base, "zuid_holland")
        os.makedirs(self.base_download_dir, exist_ok=True)

        print(f"Files will be saved to: {self.base_download_dir}")

        # Cache to keep track of downloaded files
        self.downloaded_files_cache = self._build_existing_files_cache()

        # Requests session for connection reuse
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def _build_existing_files_cache(self) -> dict:
        """
        Builds a cache of existing files in zip files.

        Returns:
            dict: A dictionary mapping filenames to their containing zip paths

        Example:
            cache = scraper._build_existing_files_cache()
            print(len(cache))  # Output: Number of files found
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

    def fetch_html(self, url: str) -> str | None:
        """
        Retrieves HTML content using requests.

        Args:
            url (str): The URL to fetch HTML content from

        Returns:
            str: The HTML content as a string, or None if the fetch failed

        Raises:
            requests.exceptions.RequestException: If there's an issue with the request

        Example:
            html_content = scraper.fetch_html("https://example.com/page")
            if html_content:
                print(f"Successfully retrieved {len(html_content)} bytes")
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

    def _extract_publiekssamenvatting(self, soup: BeautifulSoup) -> str:
        """
        Extracts the publiekssamenvatting from the <div class="summary"> section.
        The summary may be directly in the div or in nested paragraphs.

        Args:
            soup (BeautifulSoup): Parsed HTML content

        Returns:
            str: The publiekssamenvatting text, or empty string if not found
        """
        try:
            # Look for the summary div
            summary_div = soup.find("div", class_="summary")
            if summary_div:
                # First try to get all paragraphs within the summary div
                paragraphs = summary_div.find_all("p")
                if paragraphs:
                    # Get text from all paragraphs and join them
                    # Filter out paragraphs that are mainly links (likely document references)
                    summary_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # Check if paragraph is mostly links (more than 80% of content is in links)
                        links = p.find_all("a")
                        if links:
                            link_text_length = sum(
                                len(link.get_text(strip=True)) for link in links
                            )
                            total_text_length = len(text)
                            if (
                                total_text_length > 0
                                and (link_text_length / total_text_length) > 0.8
                            ):
                                # This paragraph is mostly links, likely document references
                                continue

                        if (
                            text and len(text) > 20
                        ):  # Only include substantial paragraphs
                            summary_parts.append(text)

                    if summary_parts:
                        return " ".join(summary_parts)

                # If no good paragraphs found, try to get direct text from the div
                # but exclude text from nested links
                summary_text = summary_div.get_text(strip=True)
                if summary_text and len(summary_text) > 20:
                    return summary_text

        except Exception as e:
            print(f"Error extracting publiekssamenvatting: {e}")

        return ""

    def generate_metadata(self, html_content: str, url: str) -> dict:
        """
        Generates metadata from HTML content.

        Args:
            html_content (str): The HTML content to extract metadata from
            url (str): The URL of the page

        Returns:
            dict: A dictionary containing extracted metadata with keys:
                - url: Original URL
                - title: Document title
                - summary: Document summary/description
                - date: Document publication date
                - woo_themes: List of WOO themes/categories

        Example:
            html = scraper.fetch_html("https://example.com/page")
            metadata = scraper.generate_metadata(html, "https://example.com/page")
            print(f"Title: {metadata['title']}")
        """
        metadata = {
            "url": url,
            "provincie": "Zuid-Holland",
            "titel": "",
            "datum": "",
            "type": "woo-verzoek",
            "publiekssamenvatting": "",
        }
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Try to find title (h1 is most likely)
            title_tag = soup.find("h1")
            if title_tag:
                metadata["titel"] = title_tag.get_text(strip=True)

            # Extract publiekssamenvatting
            metadata["publiekssamenvatting"] = self._extract_publiekssamenvatting(soup)

            # Find the div with class "datetime"
            date_tag = soup.find("div", class_="datetime")
            if date_tag:
                date_str = date_tag.get_text(strip=True)
                # Remove "Datum Besluit: " from string
                date_str = date_str.replace("Datum besluit: ", "")
                d = dateparser.parse(date_str).replace(tzinfo=timezone.utc)
                metadata["datum"] = int(d.timestamp())
                print(f"Datum in metadata: {metadata["datum"]}")

            return metadata

        except Exception as e:
            print(f"Error generating metadata: {e}")
            return metadata

    def get_filename_from_url(self, url: str) -> str:
        """
        Extracts the original filename from the URL and adds a hash for uniqueness (if no filename is found).

        Args:
            url (str): The URL of the file

        Returns:
            str: A unique filename based on the URL

        Example:
            filename = scraper.get_filename_from_url("https://example.com/documents/report.pdf")
            print(filename)  # Output: report.pdf
        """
        parsed_url = urlparse(url)
        original_filename = os.path.basename(unquote(parsed_url.path))

        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            original_filename = original_filename.replace(char, "_")

        # If filename is empty or invalid, try from Content-Disposition header
        if (
            not original_filename
            or original_filename == "_"
            or "." not in original_filename
        ):
            try:
                head_response = self.session.head(url, headers=self.headers, timeout=10)
                content_disposition = head_response.headers.get("content-disposition")
                if content_disposition:
                    filename_match = re.search(
                        r'filename="?([^";]+)', content_disposition
                    )
                    if filename_match:
                        original_filename = filename_match.group(1)
                        for char in invalid_chars:
                            original_filename = original_filename.replace(char, "_")
            except Exception as e:
                print(f"Could not retrieve Content-Disposition: {e}")

        # If we still don't have a good filename, use generic name with extension
        if (
            not original_filename
            or original_filename == "_"
            or "." not in original_filename
        ):
            # Try to determine extension from URL
            extension = ".pdf"  # Default extension
            for ext in self.supported_extensions:
                if url.lower().endswith(ext):
                    extension = ext
                    break
            # Add hash to filename for uniqueness (in case of generic name)
            hash = self._get_file_hash(url)
            original_filename = f"{hash}_document{extension}"

        return f"{original_filename}"

    def find_documents(self, html_content: str, url: str) -> list:
        """
        Searches for all supported document types in the HTML content.

        Args:
            html_content (str): The HTML content to search in
            url (str): The base URL for converting relative links to absolute

        Returns:
            list: A list of tuples containing (document_url, filename)

        Example:
            html = scraper.fetch_html("https://example.com/page")
            documents = scraper.find_documents(html, "https://example.com/page")
            print(f"Found {len(documents)} downloadable documents")
        """
        doc_links = []
        if not html_content:
            return doc_links

        soup = BeautifulSoup(html_content, "html.parser")
        print("Searching for document links...")
        found_any = False  # Flag to track if we found any documents

        # First look in specific attachment/download sections
        # Zuid-Holland site likely uses specific classes for attachments
        attachment_sections = [
            soup.select(
                ".bijlagen, .downloads, .attachments, .field--name-field-bijlagen"
            ),
            soup.select(".document-list, .documents-list"),
            soup.select(".field--type-file, .field--type-document"),
            soup.select(".documentlisting, .downloads-list, .documents"),
        ]

        for section_list in attachment_sections:
            if section_list:
                for section in section_list:
                    links = section.find_all("a", href=True)
                    for link in links:
                        href = link["href"]
                        absolute_url = urljoin(url, href)
                        if self._is_supported_file(absolute_url):
                            filename = self.get_filename_from_url(absolute_url)
                            extension = os.path.splitext(absolute_url.lower())[1]
                            print(
                                f"{extension.upper()[1:]} file found in attachments: {filename}"
                            )
                            doc_links.append((absolute_url, filename))
                            found_any = True

        # As backup, also search the entire document
        if not doc_links:
            print("Searching entire document for downloadable files...")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)
                if self._is_supported_file(absolute_url):
                    # Look for context suggesting it's a download
                    download_indicators = [
                        "download",
                        "bijlage",
                        "document",
                        "bestand",
                        "pdf",
                        "doc",
                        "xls",
                        "bekijk",
                    ]

                    link_text = link.get_text(strip=True).lower()
                    link_classes = (
                        " ".join(link.get("class", [])).lower()
                        if link.get("class")
                        else ""
                    )
                    parent_classes = (
                        " ".join(link.parent.get("class", [])).lower()
                        if link.parent.get("class")
                        else ""
                    )

                    is_download_link = any(
                        indicator in link_text
                        or indicator in link_classes
                        or indicator in parent_classes
                        or indicator in href.lower()
                        for indicator in download_indicators
                    )

                    if is_download_link:
                        filename = self.get_filename_from_url(absolute_url)
                        extension = os.path.splitext(absolute_url.lower())[1]
                        print(
                            f"{extension.upper()[1:]} file found: {filename} - {absolute_url}"
                        )
                        doc_links.append((absolute_url, filename))
                        found_any = True

        if not found_any:
            print("DEBUG: No documents found. Dumping HTML structure for analysis:")
            print(f"Page URL: {url}")
            print(f"All links: {len(soup.find_all('a', href=True))}")
            print("Sample links:")
            for link in soup.find_all("a", href=True)[:10]:
                print(f"- {link.get_text()[:50]} -> {link['href']}")

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

    def check_file_size_not_too_large(self, url):
        """
        Checkt de grootte van het zip bestand.
        """
        try:
            response = self.session.head(url, headers=self.headers, timeout=30)
            file_size = int(response.headers.get("content-length", 0))
            # Load max size from .env
            max_size = int(os.getenv("MAX_ZIP_SIZE", 1024 * 1024 * 1024))  # 1gb
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
            raise RuntimeError(f"Could not retrieve content for {url}")

        # Generate and save metadata
        metadata = self.generate_metadata(html_content, url)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Find all document links
        doc_links = self.find_documents(html_content, url)
        if not doc_links:
            print("No documents found")
            return

        print(f"{len(doc_links)} document(s) found to download")

        # Download only new files
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
    BASE_URL = "https://www.zuid-holland.nl/politiek-bestuur/bestuur-zh/gedeputeerde-staten/besluiten/"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = "https://www.zuid-holland.nl/politiek-bestuur/gedeputeerde-staten/besluiten/besluit/beantwoording-woo-verzoek-deelbesluit-2"
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
