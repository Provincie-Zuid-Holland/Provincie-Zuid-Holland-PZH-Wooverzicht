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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class Scraper:
    """
    A class for scraping and downloading documents from the Noord-Brabant WOO portal.
    Documents are downloaded and stored in zip files along with their metadata.
    """

    def __init__(self, download_dir=None):
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

        # Set the download directory for Selenium
        self.selenium_download_dir = download_dir or self.base_download_dir

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

        # Setup Selenium webdriver
        self.driver = None

    def setup_selenium_driver(self):
        """
        Sets up the Selenium webdriver with appropriate options.
        """
        chrome_options = Options()

        # Set download directory
        prefs = {
            "download.default_directory": self.selenium_download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Add additional options for headless mode if needed
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)

        # Set implicit wait
        self.driver.implicitly_wait(10)

        return self.driver

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

    def select_all_and_download_with_selenium(self, url):
        """
        Uses Selenium to select all documents and download them.
        """
        if not self.driver:
            self.setup_selenium_driver()

        print(f"Opening page: {url}")
        self.driver.get(url)

        # Wait for page to load completely
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )

        print("Page loaded, looking for 'Selecteer alles' checkbox")

        try:
            # Find and click the "Selecteer alles" checkbox
            select_all_checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(., 'Selecteer alles')]/input")
                )
            )
            print("Found 'Selecteer alles' checkbox, clicking it")
            select_all_checkbox.click()

            # Wait for the download button to become enabled (no longer having opacity-50 class)
            download_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(., 'Downloaden') and not(contains(@class, 'opacity-50'))]",
                    )
                )
            )

            print("Download button is now enabled, clicking it")
            download_button.click()

            # Wait for download to start and complete
            # This depends on the file size - adjust timeout as needed
            print("Waiting for download to complete...")
            time.sleep(10)  # Simple wait for download to start

            # We could add more sophisticated download completion detection here

            # Try to find the filename from browser downloads
            return True

        except Exception as e:
            print(f"Error during Selenium automation: {e}")
            return False

    def wait_for_download_complete(self, timeout=60):
        """
        Waits for downloads to complete by checking for .crdownload or .tmp files.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            downloading_files = [
                f
                for f in os.listdir(self.selenium_download_dir)
                if f.endswith(".crdownload") or f.endswith(".tmp")
            ]
            if not downloading_files:
                return True
            time.sleep(1)
        return False

    def find_latest_download(self):
        """
        Finds the most recently downloaded file in the download directory.
        """
        files = [
            os.path.join(self.selenium_download_dir, f)
            for f in os.listdir(self.selenium_download_dir)
            if os.path.isfile(os.path.join(self.selenium_download_dir, f))
        ]

        if not files:
            return None

        # Get the most recently modified file
        latest_file = max(files, key=os.path.getmtime)
        return latest_file

    def scrape_document(self, url: str, index: int) -> None:
        """
        Scrapes a document URL, selects all documents, downloads them and saves metadata.
        """
        print(f"\n{'='*80}\nProcessing document {index}: {url}\n{'='*80}")

        zip_path = os.path.join(self.base_download_dir, f"woo-{index}.zip")
        if os.path.exists(zip_path):
            print(f"Zip file woo-{index}.zip already exists")
            return

        # Get HTML content and extract metadata
        html_content = self.fetch_html(url)
        if not html_content:
            print(f"Could not retrieve content for {url}")
            return

        metadata = self.generate_metadata(html_content, url)

        # Use Selenium to select all and download
        download_success = self.select_all_and_download_with_selenium(url)

        if download_success:
            # Wait for download to complete
            self.wait_for_download_complete()

            # Find the most recently downloaded file
            latest_file = self.find_latest_download()

            if latest_file:
                print(f"Download completed: {latest_file}")

                # Move or rename the file to our target zip path if needed
                if latest_file != zip_path:
                    # Check if it's already a zip file
                    if latest_file.endswith(".zip"):
                        # Move/rename the file
                        os.rename(latest_file, zip_path)
                        print(f"Renamed downloaded file to: {zip_path}")
                    else:
                        # If it's not a zip, create a new zip and add the file
                        with zipfile.ZipFile(
                            zip_path, "w", zipfile.ZIP_DEFLATED
                        ) as zipf:
                            zipf.write(
                                latest_file, arcname=os.path.basename(latest_file)
                            )
                        print(f"Added downloaded file to new zip: {zip_path}")

                # Add metadata to the zip file
                with tempfile.TemporaryDirectory() as temp_dir:
                    metadata_path = self.create_metadata_file(metadata, temp_dir)
                    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(metadata_path, arcname="metadata.txt")

                print(f"Added metadata to: {zip_path}")
            else:
                print("No downloaded file found")
        else:
            print("Download via Selenium failed, saving metadata only")
            # Save metadata only
            with tempfile.TemporaryDirectory() as temp_dir:
                metadata_path = self.create_metadata_file(metadata, temp_dir)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(metadata_path, arcname="metadata.txt")

    def __del__(self):
        """
        Cleanup when closing.
        """
        try:
            if self.driver:
                self.driver.quit()
            self.session.close()
        except:
            pass


def find_api_endpoints(url):
    """
    Helper function to identify API endpoints by monitoring network traffic.
    This can help understand the API structure for future improvements.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

    # Setup Chrome to log network activity
    capabilities = DesiredCapabilities.CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

    chrome_options = Options()
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)

    try:
        driver.get(url)
        time.sleep(5)  # Allow page to load

        # Find and click the "Selecteer alles" checkbox if present
        try:
            select_all = driver.find_element(
                By.XPATH, "//label[contains(., 'Selecteer alles')]/input"
            )
            select_all.click()
            time.sleep(2)

            # Click download button if enabled
            download_btn = driver.find_element(
                By.XPATH, "//button[contains(., 'Downloaden')]"
            )
            if "opacity-50" not in download_btn.get_attribute("class"):
                download_btn.click()
                time.sleep(5)
        except:
            pass

        # Extract network logs
        logs = driver.get_log("performance")

        # Filter for API calls
        api_endpoints = []
        for log in logs:
            try:
                network_log = json.loads(log["message"])["message"]
                if "Network.requestWillBeSent" in network_log["method"]:
                    url = network_log["params"]["request"]["url"]
                    if "/api/" in url and url not in api_endpoints:
                        api_endpoints.append(url)
            except:
                pass

        return api_endpoints

    finally:
        driver.quit()


if __name__ == "__main__":
    BASE_URL = "https://open.brabant.nl/woo-verzoeken"

    # Example document URL (replace with actual URL)
    EXAMPLE_DOC_URL = (
        "https://open.brabant.nl/woo-verzoeken/e661cfe8-5f7a-49d5-8cf3-c8bcb65309d8"
    )

    # Uncomment to discover API endpoints
    # print("Discovering API endpoints...")
    # endpoints = find_api_endpoints(EXAMPLE_DOC_URL)
    # print("Found the following potential API endpoints:")
    # for endpoint in endpoints:
    #     print(f"  - {endpoint}")
    # print("You can use these endpoints to improve the scraper in the future.")

    scraper = Scraper()
    scraper.scrape_document(EXAMPLE_DOC_URL, 1)
