import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlunparse
import time
import re
import logging
from typing import List, Dict


class Crawler:
    """
    Crawler for collecting WOO document URLs from Noord-Brabant's document portal.

    This crawler is designed to handle the unique structure of Noord-Brabant's
    WOO document listing, which uses UUIDs and requires careful parsing.

    Attributes:
        base_url (str): Starting URL for crawling WOO documents
        max_urls (int): Maximum number of URLs to collect
        pages_visited (int): Counter for visited pages
        urls_per_page (dict): Dictionary mapping page numbers to collected URLs
        seen_document_urls (set): Set of already seen document URLs
    """

    def __init__(self, base_url: str, max_urls: int = 10, debug: bool = True):
        """
        Initialize the Noord-Brabant crawler.

        Args:
            base_url (str): Starting URL for crawling
            max_urls (int): Maximum number of URLs to collect
            debug (bool): Enable detailed logging
        """
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s - %(levelname)s: %(message)s",
        )
        self.logger = logging.getLogger("NoordBrabantCrawler")

        # Normalize base URL
        parsed_url = urlparse(base_url)
        self.base_url = urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                "",
                parsed_url.query,
                "",
            )
        )

        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()
        self.debug = debug

        # Create requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
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
        Check if a URL is a valid WOO document URL for Noord-Brabant.

        Args:
            url (str): URL to validate

        Returns:
            bool: True if valid WOO document URL, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        parsed_url = urlparse(url)
        base_domain = "open.brabant.nl"

        # UUID pattern for Noord-Brabant
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

        return (
            parsed_url.netloc == base_domain
            and "/woo-verzoeken/" in parsed_url.path
            and re.search(uuid_pattern, parsed_url.path) is not None
            and not parsed_url.path.endswith("/woo-verzoeken/")
        )

    def get_next_page_url(self, current_url: str) -> str:
        """
        Determine the URL for the next page of results.

        Args:
            current_url (str): Current page URL

        Returns:
            str: URL for the next page, or None if no next page
        """
        parsed_url = urlparse(current_url)
        query_params = dict(parse_qsl(parsed_url.query))

        # Increment page number
        current_page = int(query_params.get("page", 1))
        next_page = current_page + 1
        query_params["page"] = str(next_page)

        # Reconstruct URL with new page parameter
        new_query = "&".join(f"{k}={v}" for k, v in query_params.items())
        url_parts = list(parsed_url)
        url_parts[4] = new_query
        return urlunparse(url_parts)

    def extract_page_links(self, html_content: str, page_url: str) -> List[str]:
        """
        Extract document links from page HTML.

        Args:
            html_content (str): HTML content to parse
            page_url (str): URL of the current page

        Returns:
            List[str]: List of absolute document URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        # Find all links that potentially point to WOO documents
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(page_url, href)

            if self.is_woo_document_url(absolute_url):
                links.append(absolute_url)

        self.logger.info(f"Found {len(links)} document links on this page")
        return links

    def get_links(self) -> List[str]:
        """
        Main method to collect WOO document URLs.

        Returns:
            List[str]: Collected document URLs
        """
        all_links = []
        current_page = 1
        current_url = self.base_url

        # Ensure page parameter is present
        if "page=" not in current_url:
            current_url += "?page=1" if "?" not in current_url else "&page=1"

        try:
            while len(all_links) < self.max_urls:
                self.logger.info(f"Processing page {current_page}")

                try:
                    response = self.session.get(
                        current_url, headers=self.headers, timeout=20
                    )
                    response.raise_for_status()
                except requests.RequestException as e:
                    self.logger.error(f"Error fetching page: {e}")
                    break

                # Extract links from this page
                current_links = self.extract_page_links(response.text, current_url)

                # Add unique links
                page_urls = []
                for link in current_links:
                    if (
                        link not in self.seen_document_urls
                        and len(all_links) < self.max_urls
                    ):
                        all_links.append(link)
                        page_urls.append(link)
                        self.seen_document_urls.add(link)

                # Record page results
                self.urls_per_page[current_page] = page_urls
                self.pages_visited = current_page

                # Stop if no links found
                if not current_links:
                    self.logger.info("No more links found")
                    break

                # Determine next page
                next_url = self.get_next_page_url(current_url)
                if next_url == current_url:
                    self.logger.info("No more pages to process")
                    break

                current_url = next_url
                current_page += 1

                # Be nice to the server
                time.sleep(1)

            return all_links

        except Exception as e:
            self.logger.error(f"Unexpected error during crawling: {e}")
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
            new_links = [] #[link for link in all_links if link not in f.read()]
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

    def print_results(self, urls: List[str]) -> None:
        """
        Print a summary of collected URLs.

        Args:
            urls (List[str]): List of collected URLs
        """
        if not urls:
            print("No (new) URLs found.")
            return

        print(f"\n{self.pages_visited} pages visited and {len(urls)} URLs extracted:")

        for page_num, page_urls in self.urls_per_page.items():
            print(f"\nPage {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def __del__(self):
        """
        Ensure session is closed when object is deleted.
        """
        try:
            self.session.close()
        except:
            pass


if __name__ == "__main__":
    BASE_URL = "https://open.brabant.nl/woo-verzoeken"
    MAX_URLS = 10

    crawler = Crawler(BASE_URL, MAX_URLS)
    urls = crawler.get_new_links()
    crawler.print_results(urls)
