import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin

class WebCrawler:
    """
    Crawls web pages to collect document URLs using Selenium and BeautifulSoup.
    """

    def __init__(self, base_url: str, max_urls: int = 15):
        """
        Initializes the WebCrawler instance.

        Args:
            base_url (str): The base URL where crawling starts.
            max_urls (int): Maximum number of URLs to collect.
        """
        self.base_url = base_url.rstrip('/')
        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def clean_url(self, url: str) -> str:
        """
        Cleans a URL by removing duplicate '/list/' entries.

        Args:
            url (str): URL to be cleaned.

        Returns:
            str: Cleaned URL.
        """
        return url.replace('/list/list/', '/list/')

    def extract_page_links(self, html_content: str) -> List[str]:
        """
        Extracts document links from HTML content.

        Args:
            html_content (str): HTML content to parse.

        Returns:
            List[str]: List of found document URLs.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = [self.clean_url(urljoin(self.base_url, link['href']))
                 for link in soup.find_all('a', href=True)
                 if '/list/document/' in link['href'].lower()]
        return links

    def get_links(self) -> List[str]:
        """
        Collects document links by crawling pages.

        Returns:
            List[str]: List of all collected document URLs.
        """
        all_links = []
        current_page = 1

        try:
            self.driver.get(self.base_url)
            time.sleep(2)

            while len(all_links) < self.max_urls:
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "document-hoofd")))
                current_links = self.extract_page_links(self.driver.page_source)

                page_urls = [link for link in current_links if link not in self.seen_document_urls]
                all_links.extend(page_urls[:self.max_urls - len(all_links)])
                self.seen_document_urls.update(page_urls)

                self.urls_per_page[current_page] = page_urls
                self.pages_visited = current_page

                if len(all_links) >= self.max_urls:
                    break

                try:
                    next_button = next(button for button in self.driver.find_elements(By.CLASS_NAME, 'js-nav-button')
                                       if 'Volgende pagina' in button.text)
                    next_button.click()
                    time.sleep(2)
                    current_page += 1
                except StopIteration:
                    break

            return all_links

        except Exception as e:
            logging.error(f"Error during crawling: {e}")
            return all_links

        finally:
            self.driver.quit()

    def print_results(self, urls: List[str]) -> None:
        """
        Prints an overview of all collected URLs by page.

        Args:
            urls (List[str]): List of all collected URLs.
        """
        if not urls:
            print("No URLs found.")
            return

        print(f"\nVisited {self.pages_visited} page(s) and extracted {len(urls)} URLs:")
        for page_num, page_urls in self.urls_per_page.items():
            print(f"\nPage {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def __del__(self):
        """Destructor to ensure the browser is closed."""
        try:
            self.driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    BASE_URL = "https://woo.dataportaaloverijssel.nl/list"
    MAX_URLS = 45

    try:
        crawler = WebCrawler(BASE_URL, MAX_URLS)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
        if 'crawler' in locals():
            crawler.print_results(urls)
    except Exception as e:
        logging.error(f"\nAn error occurred: {e}")
