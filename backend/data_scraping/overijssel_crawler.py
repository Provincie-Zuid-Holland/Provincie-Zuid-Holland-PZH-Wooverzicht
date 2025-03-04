import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import json


class Crawler:
    """
    Deze class is voor het crawlen van webpagina's en het verzamelen van WOO document URLs van Overijssel.
    De crawler gebruikt requests om API-aanroepen te doen om de JSON-data te verkrijgen.
    Overijssel gebruikt een API voor paginering in plaats van directe HTML-navigatie.

    Attributen:
        base_url (str): De basis URL voor het weergeven van documenten
        api_url (str): De API URL voor het ophalen van documentgegevens
        max_urls (int): Maximum aantal URLs dat verzameld moet worden
        pages_visited (int): Aantal opgehaalde pagina's
        urls_per_page (dict): Dictionary die URLs per pagina opslaat
        seen_document_urls (set): Set van reeds geziene document URLs
        session: Requests session voor het hergebruiken van verbindingen

    Methodes:
        build_document_url(uuid: str) -> str:
            Bouwt de volledige document URL op basis van de UUID

        fetch_documents(offset: int, limit: int) -> dict:
            Haalt documentgegevens op via de API

        get_links() -> list:
            Verzamelt alle document links door API-aanroepen te doen

        print_results(urls: list) -> None:
            Print een overzicht van gevonden URLs per pagina
    """

    def __init__(self, base_url, api_url, max_urls=10, page_size=15):
        """
        Initialiseert de Crawler met een basis URL, API URL en maximum aantal te verzamelen URLs.

        Parameters:
            base_url (str): Basis URL voor het weergeven van documenten
            api_url (str): API URL voor het ophalen van documentgegevens
            max_urls (int): Maximum aantal URLs dat verzameld moet worden
            page_size (int): Aantal resultaten per pagina
        """
        self.base_url = base_url.rstrip("/")
        self.api_url = api_url
        self.max_urls = max_urls
        self.page_size = page_size
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()

        # Initialiseer requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "nl,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
            "Origin": "https://woo.dataportaaloverijssel.nl",
            "Referer": "https://woo.dataportaaloverijssel.nl/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }

    def build_document_url(self, uuid):
        """
        Bouwt de volledige document URL op basis van de UUID.

        Parameters:
            uuid (str): Document UUID

        Returns:
            str: Volledige document URL
        """
        return f"{self.base_url}/document/{uuid}"

    def fetch_documents(self, offset, limit):
        """
        Haalt documentgegevens op via de API.

        Parameters:
            offset (int): Startpositie voor paginering
            limit (int): Aantal resultaten per pagina

        Returns:
            dict: JSON-response met documentgegevens
        """
        # Volledige URL expliciet definiëren
        url = "https://admin.geoportaaloverijssel.nl/api/document/search/woo"

        # Query parameters toevoegen
        params = {
            "sort": "dateDesc",
            "limit": limit,
            "offset": offset,
            "text": "",
            "typeFilter": "",
            "themeFilter": "",
            "creationYear": 0,
        }

        try:
            response = self.session.get(
                url, params=params, headers=self.headers, timeout=20
            )
            response.raise_for_status()
            print(f"API URL aangeroepen: {response.url}")
            return response.json()
        except Exception as e:
            print(f"Fout bij ophalen data van API: {e}")
            return None

    def get_links(self):
        """
        Hoofdfunctie voor het verzamelen van document links via API-aanroepen.

        Returns:
            list: Lijst met alle verzamelde document URLs
        """
        all_links = []
        current_page = 1
        offset = 0

        try:
            while len(all_links) < self.max_urls:
                print(f"\nVerwerken van pagina {current_page}...")

                # Haal documentgegevens op via de API
                response_data = self.fetch_documents(offset, self.page_size)

                if not response_data or "records" not in response_data:
                    print("Geen resultaten gevonden of ongeldig API-antwoord.")
                    break

                # Verwerk de documentgegevens
                records = response_data.get("records", [])
                total_count = response_data.get("count", 0)

                if not records:
                    print("Geen records gevonden op deze pagina.")
                    break

                print(f"Gevonden {len(records)} records op pagina {current_page}")

                # Verzamel document URLs voor deze pagina
                page_urls = []
                for record in records:
                    uuid = record.get("uuid")
                    if not uuid:
                        continue

                    document_url = self.build_document_url(uuid)

                    if document_url not in self.seen_document_urls:
                        all_links.append(document_url)
                        page_urls.append(document_url)
                        self.seen_document_urls.add(document_url)

                        if len(all_links) >= self.max_urls:
                            break

                self.urls_per_page[current_page] = page_urls
                self.pages_visited = current_page

                if len(all_links) >= self.max_urls:
                    print(f"Maximum aantal URLs bereikt ({self.max_urls})")
                    break

                # Controleer of er meer pagina's zijn
                if (
                    len(records) < self.page_size
                    or offset + self.page_size >= total_count
                ):
                    print("Geen volgende pagina beschikbaar.")
                    break

                # Ga naar de volgende pagina
                offset += self.page_size
                current_page += 1
                time.sleep(1)  # Wees netjes voor de server

            return all_links

        except Exception as e:
            print(f"Er is een fout opgetreden tijdens het crawlen: {e}")
            return all_links
        finally:
            self.session.close()

    def print_results(self, urls):
        """
        Print een overzicht van alle verzamelde URLs per pagina.

        Parameters:
            urls (list): Lijst met alle verzamelde URLs
        """
        if not urls:
            print("Geen URLs gevonden.")
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

    def __del__(self):
        """
        Destructor om ervoor te zorgen dat de session wordt afgesloten.
        """
        try:
            self.session.close()
        except:
            pass


if __name__ == "__main__":
    # Configuratie voor het crawlen
    base_url = "https://woo.dataportaaloverijssel.nl"
    api_url = "https://admin.geoportaaloverijssel.nl/api/document/search/woo"
    max_urls = 10
    page_size = 15

    print(f"Base URL: {base_url}")
    print(f"API URL: {api_url}")

    try:
        crawler = Crawler(base_url, api_url, max_urls, page_size)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawlen onderbroken door gebruiker")
    except Exception as e:
        print(f"\nEr is een fout opgetreden: {e}")
