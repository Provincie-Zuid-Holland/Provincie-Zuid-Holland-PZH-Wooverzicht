import requests
import time
from urllib.parse import urlparse, urljoin


class Crawler:
    """
    Deze class is voor het crawlen van WOO document URLs van Gelderland via de Algolia API.
    De crawler gebruikt direct de Algolia API in plaats van BeautifulSoup parsing.

    Attributen:
        base_url (str): De basis URL voor de WOO documenten pagina
        max_urls (int): Maximum aantal URLs dat verzameld moet worden
        pages_visited (int): Aantal bezochte pagina's
        urls_per_page (dict): Dictionary die URLs per pagina opslaat
        seen_document_urls (set): Set van reeds geziene document URLs
    """

    def __init__(self, base_url="", max_urls: int = 9999, debug: bool = False):
        """
        Initialiseert de Crawler met maximum aantal te verzamelen URLs.

        Parameters:
            max_urls (int): Maximum aantal URLs dat verzameld moet worden
            debug (bool): Schakel gedetailleerde logging in

        Voorbeeld:
            crawler = Crawler(10)
        """
        self.base_url = "https://open.gelderland.nl"
        # Base API URL without query parameters
        self.api_base_url = "https://w247fahdn6-dsn.algolia.net/1/indexes/*/queries"
        # API URL with authentication parameters
        self.api_url = f"{self.api_base_url}?x-algolia-agent=Algolia%20for%20JavaScript%20(4.22.1)%3B%20Browser%20(lite)&x-algolia-api-key=5d7761fa3eeb21d473e7fdea7de0e2bd&x-algolia-application-id=W247FAHDN6"
        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()
        self.debug = debug

        # API headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://open.gelderland.nl",
            "Referer": "https://open.gelderland.nl/woo-documenten",
            "Accept": "*/*",
            "Accept-Language": "nl,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }

    def log(self, message: str) -> None:
        """
        Helper function for consistent logging.

        Args:
            message (str): The message to log
        """
        if self.debug:
            print(f"[DEBUG] {message}")

    def is_valid_document_url(self, url):
        """
        Controleert of een URL een WOO document pagina is.

        Parameters:
            url (str): De te controleren URL

        Returns:
            bool: True als het een geldige WOO document URL is
        """
        if not url or not isinstance(url, str):
            return False

        parsed_url = urlparse(url)
        base_domain = urlparse(self.base_url).netloc

        return (
            parsed_url.netloc == base_domain
            and parsed_url.path.startswith("/woo-documenten/")
            and len(parsed_url.path) > 16  # '/woo-documenten/' is 16 chars
        )

    def get_page_data(self, page_number):
        """
        Haal data op via de Algolia API voor een specifieke pagina.

        Args:
            page_number (int): Het paginanummer om op te halen

        Returns:
            dict: JSON data van de API response
        """
        # Define payload with page number (displayed page is +1)
        payload = {
            "requests": [
                {
                    "indexName": "woo-request_desc",
                    "query": "",
                    "params": f"hitsPerPage=8&page={page_number}&facetFilters=%5B%5D&numericFilters=%5B%5D",
                }
            ]
        }

        # Update referer for the specific page (displayed page is +1)
        display_page = page_number + 1
        self.headers["Referer"] = (
            f"https://open.gelderland.nl/woo-documenten?pagina={display_page}"
        )

        # Send POST request - using json parameter correctly converts to proper content type
        try:
            self.log(f"Sending request to: {self.api_url}")
            self.log(f"Payload: {payload}")
            response = requests.post(self.api_url, headers=self.headers, json=payload)

            if response.status_code != 200:
                self.log(f"Error response code: {response.status_code}")
                self.log(f"Response: {response.text}")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"Error fetching page {page_number}: {e}")
            if "response" in locals():
                self.log(
                    f"Response status: {response.status_code}, Text: {response.text[:200]}"
                )
            return None

    def extract_document_urls(self, api_data):
        """
        Extraheert document URLs uit de Algolia API response.

        Parameters:
            api_data (dict): De API response data

        Returns:
            list: Lijst met document URLs
        """
        document_urls = []

        if not api_data or "results" not in api_data or not api_data["results"]:
            return document_urls

        # Extract hits from the first result
        hits = api_data["results"][0].get("hits", [])

        for hit in hits:
            # Extract slug or other identifiers that form the URL
            if "slug" in hit:
                document_url = f"{self.base_url}/woo-documenten/{hit['slug']}"
                if self.is_valid_document_url(document_url):
                    document_urls.append(document_url)

        return document_urls

    def get_links(self):
        """
        Hoofdfunctie voor het verzamelen van document links via de Algolia API.

        Returns:
            list: Lijst met alle verzamelde document URLs
        """
        all_links = []
        current_page = 0  # Algolia API uses 0-based indexing

        try:
            while len(all_links) < self.max_urls:
                print(f"\nVerwerken van pagina {current_page + 1}...")  # +1 for display

                # Haal de pagina data op via de API
                api_data = self.get_page_data(current_page)

                if not api_data:
                    print(f"Geen data gevonden voor pagina {current_page + 1}")
                    break

                # Extraheer document URLs
                current_links = self.extract_document_urls(api_data)
                print(
                    f"Gevonden {len(current_links)} document links op pagina {current_page + 1}"
                )

                if not current_links:
                    print("Geen document links gevonden op deze pagina")
                    # Check if we've reached the end of results
                    if (
                        api_data["results"][0].get("nbHits", 0)
                        <= (current_page + 1) * 8
                    ):  # hitsPerPage is 8
                        print("Einde van resultaten bereikt")
                        break

                # Sla unieke URLs voor deze pagina op
                page_urls = []
                for link in current_links:
                    if len(all_links) >= self.max_urls:
                        break
                    if link not in self.seen_document_urls:
                        all_links.append(link)
                        page_urls.append(link)
                        self.seen_document_urls.add(link)

                self.urls_per_page[current_page + 1] = page_urls  # +1 for display
                self.pages_visited = current_page + 1

                if len(all_links) >= self.max_urls:
                    print(f"Maximum aantal URLs bereikt ({self.max_urls})")
                    break

                current_page += 1
                time.sleep(1)  # Wees netjes voor de API

            return all_links

        except Exception as e:
            print(f"Er is een fout opgetreden tijdens het ophalen: {e}")
            return all_links

    def get_new_links(self, urls_txt_file_path: str = "URLs.txt") -> list:
        """
        Gets new document links that are not already in the URLs.txt file.

        Args:
            urls_txt_file_path (str): The relative path to the URLs.txt file

        Returns:
            list: A list of new document links
        """
        all_links = self.get_links()

        # Filter links that already exist in the URLs.txt file
        try:
            with open(urls_txt_file_path, "a+") as f:
                f.seek(0)
                all_seen_links = f.read()
                seen_links = all_seen_links.split("\n")

                new_links = []
                for link in all_links:
                    if link not in seen_links:
                        new_links.append(link)
                self.log(f"Found {len(new_links)} *NEW* URLs")

                # Update the URLs.txt file with the new links
                for link in new_links:
                    f.write(f"{link}\n")

            return new_links

        except Exception as e:
            print(f"Error reading or writing to URLs file: {e}")
            return all_links  # Return all links if file operations fail

    def print_results(self, urls):
        """
        Print een overzicht van alle verzamelde URLs per pagina.

        Parameters:
            urls (list): Lijst met alle verzamelde URLs
        """
        if not urls:
            print("Geen (nieuwe) URLs gevonden.")
            return

        pages_text = "pagina" if self.pages_visited == 1 else "pagina's"
        print(
            f"\n{self.pages_visited} {pages_text} bezocht en {len(urls)} URLs geëxtraheerd:"
        )

        for page_num in range(1, self.pages_visited + 1):
            page_urls = self.urls_per_page.get(page_num, [])
            print(f"\nPagina {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")


if __name__ == "__main__":
    # Configuratie voor het crawlen
    max_urls = 7

    try:
        crawler = Crawler(max_urls)
        urls = crawler.get_new_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawlen onderbroken door gebruiker")
    except Exception as e:
        print(f"\nEr is een fout opgetreden: {e}")
