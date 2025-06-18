import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import sys
import logging


class Crawler:
    """
    A class for crawling web pages and collecting WOO document URLs from Flevoland.
    Uses requests and BeautifulSoup for HTML parsing.
    Handles both current WOO requests and archived requests (2022 and earlier).

    Attributes:
        base_url (str): The starting URL for crawling
        max_urls (int): Maximum number of URLs to collect
        pages_visited (int): Counter for visited pages
        urls_per_page (dict): Dictionary mapping page numbers to collected URLs
        seen_document_urls (set): Set of already seen document URLs
        debug (bool): Whether to show debug information
        session (requests.Session): Session for HTTP requests
        headers (dict): HTTP headers for requests
    """

    def __init__(self, base_url: str, max_urls: int = 10, debug: bool = True):
        """
        Initializes the Crawler with a base URL and maximum number of URLs to collect.

        Args:
            base_url (str): Starting URL for crawling
            max_urls (int): Maximum number of URLs to collect
            debug (bool): Whether to show debug information

        Example:
            crawler = Crawler("https://www.flevoland.nl/woo-verzoeken", max_urls=100)
        """
        self.base_url = base_url.rstrip("/")
        self.max_urls = int(max_urls)
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()
        self.debug = debug

        # URL for archived WOO requests (2020 and earlier)
        self.archive_base_url = "https://www.flevoland.nl/Content/Pages/loket/openbare-documenten/Woo-verzoeken-archief-2"

        self.log(f"Initializing crawler with max_urls={self.max_urls}")

        # Initialize requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def log(self, message: str) -> None:
        """
        Helper function for consistent logging.

        Args:
            message (str): The message to log

        Returns:
            None

        Example:
            self.log("Processing page 1")
        """
        if self.debug:
            print(f"[DEBUG] {message}")

    def is_woo_document_url(self, url: str) -> bool:
        """
        Checks if a URL is a WOO document page.

        Args:
            url (str): The URL to check

        Returns:
            bool: True if the URL is a WOO document page, False otherwise

        Example:
            if crawler.is_woo_document_url("https://www.flevoland.nl/woo-verzoeken/123"):
                print("This is a WOO document URL")
        """
        if not url or not isinstance(url, str):
            return False

        parsed_url = urlparse(url)

        # Check for current WOO requests on flevoland.nl
        if parsed_url.netloc == "www.flevoland.nl":
            return (
                "/loket/openbare-documenten/overzicht-openbare-documenten/woo-verzoek-"
                in url.lower()
                or "/loket/openbare-documenten/woo-verzoeken-actueel/" in url.lower()
                or "/loket/openbare-documenten/woo-verzoeken-archief/" in url.lower()
            )

        if parsed_url.netloc == "deeplink.archiefweb.eu":
            # Assumption: All links from this domain are valid WOO documents
            return True

        return False

    def extract_page_links(self, html_content: str, page_url: str) -> list:
        """
        Extracts document links from HTML content.

        Args:
            html_content (str): The HTML content to parse
            page_url (str): The URL of the page (for resolving relative URLs)

        Returns:
            list: A list of absolute URLs to WOO documents

        Example:
            html = requests.get("https://www.flevoland.nl/page").text
            links = crawler.extract_page_links(html, "https://www.flevoland.nl/page")
            print(f"Found {len(links)} document links")
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        # Find all links in the document list
        all_links_count = 0
        for a_tag in soup.find_all("a", href=True):
            all_links_count += 1
            href = a_tag["href"]
            if not href:
                continue

            absolute_url = urljoin(page_url, href)
            if self.is_woo_document_url(absolute_url):
                links.append(absolute_url)

        self.log(
            f"Found {len(links)} WOO document links out of {all_links_count} total links on page"
        )
        return links

    def get_archive_links(self) -> list:
        """
        Gets WOO document URLs from the archive (2022 and earlier).

        Returns:
            list: A list of URLs to archived WOO documents

        Example:
            archive_urls = crawler.get_archive_links()
            print(f"Found {len(archive_urls)} archived WOO documents")
        """
        archive_urls = []
        try:
            response = self.session.get(
                self.archive_base_url, headers=self.headers, timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all archive links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if self.is_woo_document_url(href):
                    archive_urls.append(href)

            self.log(f"Found {len(archive_urls)} archived WOO document URLs")

        except Exception as e:
            self.log(f"Error fetching archive links: {e}")

        return archive_urls

    def get_links(self) -> list:
        """
        Main function for collecting document links by crawling pages.
        Collects both current and archived WOO documents.

        Returns:
            list: A list of collected document URLs

        Example:
            urls = crawler.get_links()
            print(f"Collected {len(urls)} document URLs")
        """
        self.log(f"Starting URL collection with limit: {self.max_urls}")
        all_links = []

        try:
            # First, get current WOO documents
            self.log("Fetching current WOO documents...")
            response = self.session.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            current_links = self.extract_page_links(response.text, self.base_url)
            for link in current_links:
                if len(all_links) >= self.max_urls:
                    break
                if link not in self.seen_document_urls:
                    all_links.append(link)
                    self.seen_document_urls.add(link)
                    self.log(f"Added current WOO document URL: {link}")

            # If we still need more URLs, get archived documents
            if len(all_links) < self.max_urls:
                self.log("Fetching archived WOO documents...")
                archive_links = self.get_archive_links()

                for link in archive_links:
                    if len(all_links) >= self.max_urls:
                        break
                    if link not in self.seen_document_urls:
                        all_links.append(link)
                        self.seen_document_urls.add(link)
                        self.log(f"Added archived WOO document URL: {link}")

            # Final check and trim if needed
            if len(all_links) > self.max_urls:
                self.log(
                    f"Found more URLs ({len(all_links)}) than requested ({self.max_urls}), trimming..."
                )
                all_links = all_links[: self.max_urls]

            self.log(f"Final URL count: {len(all_links)}")
            return all_links

        except Exception as e:
            self.log(f"Error during crawling: {e}")
            import traceback

            self.log(traceback.format_exc())
            return all_links
        finally:
            self.session.close()

    def get_new_links(self, urls_txt_file_path: str = "URLs.txt") -> list:
        """
        Gets new document links that are not already in the URLs.txt file.

        Args:
            urls_txt_file_path (str): The relative path to the URLs.txt file (from the root directory)

        Returns:
            list: A list of new document links

        Example:
            new_urls = crawler.get_new_links()
            print(f"Found {len(new_urls)} new URLs")
        """
        all_links = self.get_links()

        # Filter links that already exist in the URLs.txt file
        new_links = []
        with open(urls_txt_file_path, "a+") as f:
            # Only keep links that are not already in the file
            new_links = []  # [link for link in all_links if link not in f.read()]
            f.seek(0)
            all_seen_links = f.read()
            seen_links = all_seen_links.split("\n")
            for link in all_links:
                if link not in seen_links:
                    new_links.append(link)
            self.log(f"Found {len(new_links)} *NEW* URLs")

            # Update the URLs.txt file with the new links
            for link in new_links:
                f.write(f"{link}\n")

        return new_links

    def print_results(self, urls: list) -> None:
        """
        Prints an overview of all collected URLs.

        Args:
            urls (list): The list of collected URLs

        Returns:
            None

        Example:
            urls = crawler.get_links()
            crawler.print_results(urls)
        """
        if not urls:
            print("No URLs found.")
            return

        print(f"\nFound {len(urls)} WOO document URLs:")

        for i, url in enumerate(urls, 1):
            if "archiefweb.eu" in url:
                print(f"{i}. [ARCHIVE] {url}")
            else:
                print(f"{i}. [CURRENT] {url}")

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
    # Command line arguments
    max_urls = 1000
    if len(sys.argv) > 1:
        try:
            max_urls = int(sys.argv[1])
        except ValueError:
            print(f"Invalid max_urls value: {sys.argv[1]}, using default of 10")

    # Configuration for crawling
    base_url = "https://www.flevoland.nl/Content/Pages/loket/openbare-documenten/Woo-verzoeken-archief"

    try:
        crawler = Crawler(base_url, max_urls=max_urls, debug=True)
        urls = crawler.get_new_links()
        crawler.print_results(urls)
        print(f"\nFinal count: {len(urls)} (new) URLs collected")
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
