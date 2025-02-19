import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlunparse
import time
import re
import sys


class Crawler:
    """
    Deze class is voor het crawlen van webpagina's en het verzamelen van WOO document URLs van Zuid-Holland.
    De crawler gebruikt requests en BeautifulSoup voor het parsen van HTML.
    """

    def __init__(self, base_url, max_urls=10, debug=True):
        """
        Initialiseert de Crawler met een basis URL en maximum aantal te verzamelen URLs.

        Parameters:
            base_url (str): Start URL voor het crawlen
            max_urls (int): Maximum aantal URLs dat verzameld moet worden
            debug (bool): Of debug informatie getoond moet worden
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

        self.log(f"Initialiseren crawler met max_urls={self.max_urls}")
        self.log(f"Fixed base URL: {self.base_url}")

        # Initialiseer requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def log(self, message):
        """Helper function for consistent logging"""
        if self.debug:
            print(f"[DEBUG] {message}")

    def is_woo_document_url(self, url):
        """
        Controleert of een URL een WOO document pagina is.
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

    def get_next_page_url(self, current_url):
        """
        Bepaalt de URL van de volgende pagina door het paginanummer te verhogen.
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

    def extract_page_links(self, html_content, page_url):
        """
        Extraheert document links uit HTML content.
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

    def test_page_content(self, html_content):
        """
        Tests page content to verify if we're getting the expected data structure
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

    def get_links(self):
        """
        Hoofdfunctie voor het verzamelen van document links door pagina's te crawlen.
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
                    f"Gevonden {len(current_links)} document links op pagina {current_page}"
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

    def print_results(self, urls):
        """
        Print een overzicht van alle verzamelde URLs per pagina.
        """
        if not urls:
            print("Geen URLs gevonden.")
            return

        pages_text = "pagina" if self.pages_visited == 1 else "pagina's"
        print(
            f"\n{self.pages_visited} {pages_text} bezocht en {len(urls)} URLs geëxtraheerd:"
        )

        for page_num in sorted(self.urls_per_page.keys()):
            page_urls = self.urls_per_page.get(page_num, [])
            print(f"\nPagina {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def __del__(self):
        """
        Destructor om ervoor te zorgen dat de session wordt afgesloten.
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

    # Configuratie voor het crawlen - CORRECTED URL FORMAT
    base_url = "https://www.zuid-holland.nl/politiek-bestuur/bestuur-zh/gedeputeerde-staten/besluiten/?facet_wob=10&pager_page=0&zoeken_term=&date_from=&date_to="

    try:
        crawler = Crawler(base_url, max_urls=max_urls, debug=True)
        urls = crawler.get_links()
        crawler.print_results(urls)
        print(f"\nFinal count: {len(urls)} URLs collected")
    except KeyboardInterrupt:
        print("\nCrawlen onderbroken door gebruiker")
    except Exception as e:
        print(f"\nEr is een fout opgetreden: {e}")
