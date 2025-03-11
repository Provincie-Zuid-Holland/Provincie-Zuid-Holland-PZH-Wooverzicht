import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlunparse
import time
import re
import sys


class Crawler:
    """
    A class for crawling web pages and collecting WOO document URLs from Zuid-Holland.
    Uses requests and BeautifulSoup for HTML parsing.

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
            crawler = Crawler("https://www.zuid-holland.nl/path/to/documents", max_urls=100)
        """
        # Fix the base URL - remove fragment and keep query parameters
        # This is crucial for Zuid-Holland's site
        parsed_url = urlparse(base_url)
        query_params = dict(parse_qsl(parsed_url.fragment.lstrip("&")))
        # Reconstruct URL without fragment
        self.base_url = urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                "&".join(f"{k}={v}" for k, v in query_params.items()),
                "",
            )
        )

        self.max_urls = int(max_urls)  # Ensure it's an integer
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()
        self.debug = debug

        self.log(f"Initializing crawler with max_urls={self.max_urls}")
        self.log(f"Fixed base URL: {self.base_url}")

        # Initialize requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
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
            if crawler.is_woo_document_url("https://www.zuid-holland.nl/besluiten/besluit/123"):
                print("This is a WOO document URL")
        """
        if not url or not isinstance(url, str):
            return False

        parsed_url = urlparse(url)
        base_domain = "www.zuid-holland.nl"

        # Check if it's a WOO document URL based on the path pattern
        result = (
            parsed_url.netloc == base_domain
            and "/besluiten/besluit/" in parsed_url.path
        )
        if result and self.debug:
            self.log(f"Valid WOO URL found: {url}")
        return result

    def get_next_page_url(self, current_url: str) -> str:
        """
        Determines the URL of the next page by increasing the page number.

        Args:
            current_url (str): The URL of the current page

        Returns:
            str: The URL of the next page

        Example:
            next_url = crawler.get_next_page_url("https://example.com/page?pager_page=1")
            # Returns "https://example.com/page?pager_page=2"
        """
        # Parse the URL properly
        parsed_url = urlparse(current_url)
        query_params = dict(parse_qsl(parsed_url.query))

        # Find current page number
        if "pager_page" in query_params:
            current_page = int(query_params["pager_page"])
        else:
            current_page = 0

        next_page = current_page + 1

        # Update page number
        query_params["pager_page"] = str(next_page)

        # Reconstruct URL
        next_url = urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                "&".join(f"{k}={v}" for k, v in query_params.items()),
                "",
            )
        )

        self.log(f"Next page URL: {next_url} (current was page {current_page})")
        return next_url

    def extract_page_links(self, html_content: str, page_url: str) -> list:
        """
        Extracts document links from HTML content.

        Args:
            html_content (str): The HTML content to parse
            page_url (str): The URL of the page (for resolving relative URLs)

        Returns:
            list: A list of absolute URLs to WOO documents

        Example:
            html = requests.get("https://www.zuid-holland.nl/page").text
            links = crawler.extract_page_links(html, "https://www.zuid-holland.nl/page")
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

    def test_page_content(self, html_content: str) -> bool:
        """
        Tests page content to verify if we're getting the expected data structure.

        Args:
            html_content (str): The HTML content to test

        Returns:
            bool: True if the page contains expected structure, False otherwise

        Example:
            html = requests.get("https://www.zuid-holland.nl/page").text
            if crawler.test_page_content(html):
                print("Page structure is as expected")
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Check if the page has expected structure
        title = soup.find("title")
        self.log(f"Page title: {title.text if title else 'No title found'}")

        # Check for common elements
        h1s = soup.find_all("h1")
        self.log(f"Found {len(h1s)} h1 elements: {[h.text for h in h1s]}")

        # Look for links with besluit in path
        besluit_links = []
        for a in soup.find_all("a", href=True):
            if "/besluiten/besluit/" in a["href"]:
                besluit_links.append(a["href"])

        self.log(
            f"Found {len(besluit_links)} raw links containing '/besluiten/besluit/': {besluit_links[:5]}..."
        )

        return len(besluit_links) > 0

    def get_links(self) -> list:
        """
        Main function for collecting document links by crawling pages.

        Returns:
            list: A list of collected document URLs

        Raises:
            Exception: If an error occurs during crawling

        Example:
            urls = crawler.get_links()
            print(f"Collected {len(urls)} document URLs")
        """
        self.log(f"Starting URL collection with limit: {self.max_urls}")
        all_links = []
        current_page = 0
        current_url = self.base_url

        try:
            while current_url and len(all_links) < self.max_urls:
                self.log(f"=== Processing page {current_page} ===")
                self.log(f"Current URL count: {len(all_links)}/{self.max_urls}")
                self.log(f"Current URL: {current_url}")

                # Fetch the page
                try:
                    self.log(f"Fetching page content...")
                    response = self.session.get(
                        current_url, headers=self.headers, timeout=20
                    )
                    response.raise_for_status()
                    html_content = response.text
                    self.log(f"Response size: {len(html_content)} bytes")

                    # Test if we're getting valid content
                    content_valid = self.test_page_content(html_content)
                    if not content_valid:
                        self.log(
                            "WARNING: Page content may not be valid or as expected"
                        )

                except Exception as e:
                    self.log(f"Error fetching page: {e}")
                    break

                # Extract links from this page
                current_links = self.extract_page_links(html_content, current_url)
                print(
                    f"Found {len(current_links)} document links on page {current_page}"
                )

                if not current_links:
                    self.log("No document links found on this page, breaking loop")
                    break

                # Calculate how many more URLs we need
                urls_needed = self.max_urls - len(all_links)
                self.log(
                    f"Need {urls_needed} more URLs to reach limit of {self.max_urls}"
                )

                if urls_needed <= 0:
                    self.log("Already reached URL limit before processing this page")
                    break

                # Add unique URLs up to our limit
                page_urls = []
                added_from_this_page = 0

                for link in current_links:
                    if link in self.seen_document_urls:
                        self.log(f"Skipping already seen URL: {link}")
                        continue

                    all_links.append(link)
                    page_urls.append(link)
                    self.seen_document_urls.add(link)
                    added_from_this_page += 1

                    self.log(f"Added URL #{len(all_links)}: {link}")

                    if len(all_links) >= self.max_urls:
                        self.log(f"Reached maximum URLs limit ({self.max_urls})")
                        break

                self.log(f"Added {added_from_this_page} URLs from page {current_page}")
                self.urls_per_page[current_page] = page_urls
                self.pages_visited += 1

                # Enforce the limit
                if len(all_links) >= self.max_urls:
                    self.log("Breaking loop: URL limit reached")
                    break

                # Get next page URL
                next_url = self.get_next_page_url(current_url)
                if not next_url or next_url == current_url:
                    self.log("No next page found or reached last page")
                    break

                current_url = next_url
                current_page += 1
                time.sleep(1)  # Be nice to the server

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

    def get_new_links(self, urls_txt_file_loc: str = "URLs.txt") -> list:
        all_links = self.get_links()

        # Filter links that already exist in the URLs.txt file
        new_links = []
        with open(urls_txt_file_loc, "a+") as f:
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



    def print_results(self, urls: list) -> None:
        """
        Prints an overview of all collected URLs per page.

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

        pages_text = "page" if self.pages_visited == 1 else "pages"
        print(
            f"\n{self.pages_visited} {pages_text} visited and {len(urls)} URLs extracted:"
        )

        for page_num in sorted(self.urls_per_page.keys()):
            page_urls = self.urls_per_page.get(page_num, [])
            print(f"\nPage {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def _is_url_scraped(self, url: str, urls_txt_file_loc: str = "URLs.txt") -> bool:
        """
        Checks if a URL has already been scraped.

        Args:
            url (str): The URL to check

        Returns:
            bool: True if the URL has been scraped, False otherwise

        Example:
            if scraper._is_url_scraped("https://example.com/page"):
                print("This URL has already been scraped")
        """
        with open(urls_txt_file_loc, "r") as f:
            return url in f.read()

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
    # Command line arguments
    max_urls = 10
    if len(sys.argv) > 1:
        try:
            max_urls = int(sys.argv[1])
        except ValueError:
            print(f"Invalid max_urls value: {sys.argv[1]}, using default of 10")

    # Configuration for crawling - CORRECTED URL FORMAT
    base_url = "https://www.zuid-holland.nl/politiek-bestuur/bestuur-zh/gedeputeerde-staten/besluiten/?facet_wob=10&pager_page=0&zoeken_term=&date_from=&date_to="

    try:
        crawler = Crawler(base_url, max_urls=max_urls, debug=True)
        urls = crawler.get_new_links()
        crawler.print_results(urls)
        print(f"\nFinal count: {len(urls)} URLs collected")
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
