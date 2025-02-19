import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time


class Crawler:
    """
    Deze class is voor het crawlen van webpagina's en het verzamelen van WOO document URLs van Gelderland.
    De crawler gebruikt requests en BeautifulSoup voor het parsen van HTML.
    In tegenstelling tot Overijssel heeft Gelderland geen JavaScript-gerenderde content, dus Selenium is niet nodig.

    Attributen:
        base_url (str): De basis URL waar het crawlen start
        max_urls (int): Maximum aantal URLs dat verzameld moet worden
        pages_visited (int): Aantal bezochte pagina's
        urls_per_page (dict): Dictionary die URLs per pagina opslaat
        seen_document_urls (set): Set van reeds geziene document URLs
        session: Requests session voor het hergebruiken van verbindingen

    Methodes:
        is_woo_document_url(url: str) -> bool:
            Controleert of een URL een WOO document pagina is

        get_next_page_url(current_url: str, soup: BeautifulSoup) -> str:
            Bepaalt de URL van de volgende pagina

        extract_page_links(html_content: str, page_url: str) -> list:
            Extraheert document links uit HTML content

        get_links() -> list:
            Verzamelt alle document links door de pagina's te crawlen

        print_results(urls: list) -> None:
            Print een overzicht van gevonden URLs per pagina
    """

    def __init__(self, base_url, max_urls=10):
        """
        Initialiseert de Crawler met een basis URL en maximum aantal te verzamelen URLs.

        Parameters:
            base_url (str): Start URL voor het crawlen
            max_urls (int): Maximum aantal URLs dat verzameld moet worden
        """
        self.base_url = base_url.rstrip("/")
        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()

        # Initialiseer requests session
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def is_woo_document_url(self, url):
        """
        Controleert of een URL een WOO document pagina is.

        Parameters:
            url (str): De te controleren URL

        Returns:
            bool: True als het een WOO document URL is
        """
        if not url or not isinstance(url, str):
            return False

        parsed_url = urlparse(url)
        base_domain = urlparse(self.base_url).netloc

        return (
            parsed_url.netloc == base_domain
            and parsed_url.path.startswith("/woo-documenten/")
            and len(parsed_url.path) > 16
        )  # '/woo-documenten/' is 16 chars

    def get_next_page_url(self, current_url, soup):
        """
        Bepaalt de URL van de volgende pagina.

        Parameters:
            current_url (str): Huidige pagina URL
            soup (BeautifulSoup): Geparseerde HTML content

        Returns:
            str: URL van de volgende pagina of None
        """
        # Probeer eerst een 'Volgende' knop te vinden
        next_button = soup.select_one('a.next, a[rel="next"], a:contains("Volgende")')
        if next_button and "href" in next_button.attrs:
            return urljoin(current_url, next_button["href"])

        # Als alternatief, kijk naar de pagina parameter
        parsed_url = urlparse(current_url)
        query_params = {}

        # Parse bestaande query parameters
        if parsed_url.query:
            for param in parsed_url.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value

        # Bepaal huidige pagina
        current_page = (
            int(query_params.get("pagina", 1))
            if query_params.get("pagina", "").isdigit()
            else 1
        )
        next_page = current_page + 1

        # Check of er nog resultaten zijn
        results = soup.select(".document-item, article, .woo-item")
        if not results:
            return None

        # Bouw de volgende pagina URL
        if "pagina" in query_params:
            query_params["pagina"] = str(next_page)
            new_query = "&".join(f"{k}={v}" for k, v in query_params.items())
        else:
            if parsed_url.query:
                new_query = f"{parsed_url.query}&pagina={next_page}"
            else:
                new_query = f"pagina={next_page}"

        # Construct de nieuwe URL
        url_parts = list(parsed_url)
        url_parts[4] = new_query  # index 4 is query
        return urlparse("").geturl().join(url_parts)

    def extract_page_links(self, html_content, page_url):
        """
        Extraheert document links uit HTML content.

        Parameters:
            html_content (str): HTML content om te parsen
            page_url (str): URL van de huidige pagina

        Returns:
            list: Lijst met document URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href:
                continue

            absolute_url = urljoin(page_url, href)
            if self.is_woo_document_url(absolute_url):
                links.append(absolute_url)

        return links

    def get_links(self):
        """
        Hoofdfunctie voor het verzamelen van document links door pagina's te crawlen.

        Returns:
            list: Lijst met alle verzamelde document URLs
        """
        all_links = []
        current_page = 1
        current_url = self.base_url

        try:
            while len(all_links) < self.max_urls and current_url:
                print(f"\nVerwerken van pagina {current_page}...")

                # Haal de pagina op
                try:
                    response = self.session.get(
                        current_url, headers=self.headers, timeout=20
                    )
                    response.raise_for_status()
                    html_content = response.text
                except Exception as e:
                    print(f"Fout bij ophalen pagina {current_url}: {e}")
                    break

                # Extraheer links en update tellers
                soup = BeautifulSoup(html_content, "html.parser")
                current_links = self.extract_page_links(html_content, current_url)
                print(
                    f"Gevonden {len(current_links)} document links op pagina {current_page}"
                )

                # Sla unieke URLs voor deze pagina op
                page_urls = []
                for link in current_links:
                    if len(all_links) >= self.max_urls:
                        break
                    if link not in self.seen_document_urls:
                        all_links.append(link)
                        page_urls.append(link)
                        self.seen_document_urls.add(link)

                self.urls_per_page[current_page] = page_urls
                self.pages_visited = current_page

                if len(all_links) >= self.max_urls:
                    print(f"Maximum aantal URLs bereikt ({self.max_urls})")
                    break

                # Bepaal volgende pagina URL
                next_url = self.get_next_page_url(current_url, soup)
                if not next_url or next_url == current_url:
                    print("Geen volgende pagina gevonden")
                    break

                current_url = next_url
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
    base_url = "https://open.gelderland.nl/woo-documenten"
    max_urls = 10

    try:
        crawler = Crawler(base_url, max_urls)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawlen onderbroken door gebruiker")
    except Exception as e:
        print(f"\nEr is een fout opgetreden: {e}")
