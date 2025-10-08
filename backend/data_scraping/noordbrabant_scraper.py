from datetime import timezone
import dateparser
import os
import requests
from bs4 import BeautifulSoup
import zipfile
import tempfile
import logging


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

    def fetch_html(self, url: str) -> str | None:
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

    def _extract_publiekssamenvatting(self, soup: BeautifulSoup) -> str:
        """
        Extracts the publiekssamenvatting which appears as a paragraph after the h1 title.
        The text is typically wrapped in a span inside the paragraph.

        Args:
            soup (BeautifulSoup): Parsed HTML content

        Returns:
            str: The publiekssamenvatting text, or empty string if not found
        """
        try:
            # Find the h1 title
            h1_tag = soup.find("h1")
            if h1_tag:
                # Look for the next paragraph after the h1
                next_paragraph = h1_tag.find_next("p")
                if next_paragraph:
                    # Check if there's a span inside the paragraph
                    span_tag = next_paragraph.find("span")
                    if span_tag:
                        return span_tag.get_text(strip=True)
                    else:
                        # Fallback to the paragraph text if no span
                        return next_paragraph.get_text(strip=True)

        except Exception as e:
            print(f"Error extracting publiekssamenvatting: {e}")

        return ""

    def generate_metadata(self, html_content: str, url: str) -> dict:
        """
        Extracts metadata from HTML content.
        """
        metadata = {
            "url": url,
            "provincie": "Noord-Brabant",
            "titel": "",
            "datum": "",
            "type": "woo-verzoek",
            "publiekssamenvatting": "",
        }
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title
            title_tag = soup.find("h1")
            if title_tag:
                metadata["titel"] = title_tag.get_text(strip=True)

            # Extract publiekssamenvatting
            metadata["publiekssamenvatting"] = self._extract_publiekssamenvatting(soup)

            # Find the heading that says "Datum besluit"
            # datum_heading = soup.find("div", text="Rapportdatum")
            # date_paragraph = datum_heading.find_next("p")
            # if date_paragraph:
            #     metadata["datum"] = date_paragraph.text

            # find date in dt class with Rapportdatum as text

            date_title = soup.find("dt", string="Rapportdatum:")
            date = date_title.find_next("dd") if date_title else None
            metadata["datum"] = (
                int(
                    dateparser.parse(date.text).replace(tzinfo=timezone.utc).timestamp()
                )
                if date
                else 0
            )

            return metadata
        except Exception as e:
            print(f"Error generating metadata: {e}")
            return metadata

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
                "provincie": "Noord-Brabant",
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

    def scrape_document(
        self, temp_dir: tempfile.TemporaryDirectory, url: str, index: int
    ) -> None:
        """
        Scrapes a document URL and saves all found files in a zip file.
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")
        download_id = url[
            url.rindex("/") + 1 :
        ]  # Get unique ID after last slash in url "e.g. https://open.brabant.nl/woo-verzoeken/e661cfe8-5f7a-49d5-8cf3-c8bcb65309d8"

        html_content = self.fetch_html(url)
        if not html_content:
            raise RuntimeError(f"Could not retrieve content for {url}")

        metadata = self.generate_metadata(html_content, url)
        _ = self.create_metadata_file(metadata, temp_dir)

        # Extract document IDs and download files
        payload = self.extract_document_ids(html_content)

        download_url = (
            f"https://api-brabant.iprox-open.nl/api/v1/public/download/{download_id}"
        )

        # Download files to temp directory
        _ = self.download_files(download_url, payload, temp_dir)

        # Move all downloaded files (where in subdirectory `extracted_files`) to the temp directory
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path != os.path.join(temp_dir, file):
                    os.rename(file_path, os.path.join(temp_dir, file))

        # Remove the empty extracted_files directory (if it is empty), and remove the downloaded_files.zip
        try:
            os.rmdir(os.path.join(temp_dir, "extracted_files"))
            os.remove(os.path.join(temp_dir, "downloaded_files.zip"))

        except Exception as e:
            print(f"Error removing files: {e}")

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
    BASE_URL = "https://open.brabant.nl/woo-verzoeken"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = (
        "https://open.brabant.nl/woo-verzoeken/457b0102-8db1-433c-a958-10c5491c6945"
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
