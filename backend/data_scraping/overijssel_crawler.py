from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin


class Crawler:
    """
    Deze class is voor het crawlen van webpagina's en het verzamelen van document URLs.
    De crawler gebruikt Selenium voor het navigeren door pagina's en BeautifulSoup voor het parsen van HTML.
    Selenium is een benodigde package omdat de data van Overijssel dynamisch wordt geladen door JavaScript.
    Dit is dezelfde URL en we hebben dus selenium nodig om de JS achter de "next 15" button te laden om zo de HTML te veranderen

    Attributen:
        base_url (str): De basis URL waar het crawlen start
        max_urls (int): Maximum aantal URLs dat verzameld moet worden
        pages_visited (int): Aantal bezochte pagina's
        urls_per_page (dict): Dictionary die URLs per pagina opslaat
        seen_document_urls (set): Set van reeds geziene document URLs
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance voor het wachten op elementen

    Methodes:
        clean_url(url: str) -> str:
            Schoont een URL op door dubbele '/list/' entries te verwijderen, anders bugt het en krijg je .nl/list/list en dan 404.

        extract_page_links(html_content: str) -> list:
            Extraheert document links uit HTML content

        get_links() -> list:
            Verzamelt alle document links door de pagina's te crawlen

        print_results(urls: list) -> None:
            Print een overzicht van gevonden URLs per pagina, de return is uiteindelijk een lijst van URLs.
    """

    def __init__(self, base_url, max_urls=15):
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

        # Initialiseer Chrome driver met headless modus
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Draai zonder GUI
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(
            self.driver, 10
        )  # Wacht maximaal 10 seconden op elementen

    def clean_url(self, url):
        """
        Verwijdert dubbele '/list/' entries uit URLs.

        Parameters:
            url (str): De URL die opgeschoond moet worden

        Returns:
            str: De opgeschoonde URL
        """
        return url.replace("/list/list/", "/list/")

    def extract_page_links(self, html_content):
        """
        Extraheert document links uit de HTML content met BeautifulSoup.

        Parameters:
            html_content (str): De HTML content waarin gezocht moet worden

        Returns:
            list: Lijst met gevonden document URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/list/document/" in href.lower():
                full_link = urljoin(self.base_url, href)
                clean_link = self.clean_url(full_link)
                links.append(clean_link)

        return links

    def get_links(self):
        """
        Hoofdfunctie voor het verzamelen van document links door pagina's te crawlen.
        Navigeert door pagina's totdat het maximum aantal URLs is bereikt of er geen
        nieuwe pagina's meer zijn.

        Returns:
            list: Lijst met alle verzamelde document URLs
        """
        all_links = []
        current_page = 1

        try:
            # Laad initiële pagina
            self.driver.get(self.base_url)
            time.sleep(2)  # Wacht tot JavaScript is geladen

            while len(all_links) < self.max_urls:
                print(f"\nVerwerken van pagina {current_page}...")

                # Wacht tot document links aanwezig zijn
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "document-hoofd"))
                )

                # Verkrijg huidige pagina content en extraheer links
                current_links = self.extract_page_links(self.driver.page_source)
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

                # Probeer volgende pagina knop te vinden en te klikken
                try:
                    next_buttons = self.driver.find_elements(
                        By.CLASS_NAME, "js-nav-button"
                    )
                    next_button = next(
                        button
                        for button in next_buttons
                        if "Volgende pagina" in button.text
                    )

                    print("Volgende pagina knop gevonden, klikken...")
                    next_button.click()

                    # Wacht tot pagina is bijgewerkt
                    time.sleep(2)

                    # Controleer of er nieuwe content is
                    new_links = self.extract_page_links(self.driver.page_source)
                    if set(new_links) == set(current_links):
                        print("Geen nieuwe content gevonden na navigatie")
                        break

                    current_page += 1

                except StopIteration:
                    print("Geen volgende pagina knop gevonden")
                    break
                except Exception as e:
                    print(f"Fout tijdens navigatie: {e}")
                    break

            return all_links

        except Exception as e:
            print(f"Er is een fout opgetreden tijdens het crawlen: {e}")
            return all_links
        finally:
            self.driver.quit()

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
        Destructor om ervoor te zorgen dat de browser wordt afgesloten.
        """
        try:
            self.driver.quit()
        except:
            pass


if __name__ == "__main__":
    # Configuratie voor het crawlen
    base_url = "https://woo.dataportaaloverijssel.nl/list"
    max_urls = 45

    try:
        crawler = Crawler(base_url, max_urls)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawlen onderbroken door gebruiker")
        if "crawler" in locals():
            crawler.print_results(urls)
    except Exception as e:
        print(f"\nEr is een fout opgetreden: {e}")
