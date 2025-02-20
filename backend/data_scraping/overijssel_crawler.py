from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin


class Crawler:
    """
    A class for crawling web pages and collecting document URLs.
    Uses Selenium for navigating through pages and BeautifulSoup for parsing HTML.
    Selenium is a required package because Overijssel's data is dynamically loaded by JavaScript.
    This is the same URL and we need selenium to handle the JS behind the "next 15" button to change the HTML.

    Attributes:
        base_url (str): The base URL where crawling starts
        max_urls (int): Maximum number of URLs to collect
        pages_visited (int): Number of visited pages
        urls_per_page (dict): Dictionary storing URLs per page
        seen_document_urls (set): Set of already seen document URLs
        driver (webdriver.Chrome): Selenium WebDriver instance
        wait (WebDriverWait): WebDriverWait instance for waiting for elements

    Functions:
        clean_url: Cleans a URL by removing duplicate '/list/' entries to prevent 404 errors
        extract_page_links: Extracts document links from HTML content
        get_links: Collects all document links by crawling pages
        print_results: Prints an overview of found URLs per page, ultimately returning a list of URLs
    """

    def __init__(self, base_url: str, max_urls: int = 15):
        """
        Initializes the Crawler with a base URL and maximum number of URLs to collect.

        Args:
            base_url (str): Starting URL for crawling
            max_urls (int): Maximum number of URLs to collect

        Example:
            crawler = Crawler("https://woo.dataportaaloverijssel.nl/list", 50)
        """
        self.base_url = base_url.rstrip("/")
        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()

        # Initialize Chrome driver in headless mode
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run without GUI
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(
            self.driver, 10
        )  # Wait maximum 10 seconds for elements

    def clean_url(self, url: str) -> str:
        """
        Removes duplicate '/list/' entries from URLs.

        Args:
            url (str): The URL to be cleaned

        Returns:
            str: The cleaned URL

        Example:
            clean_url = crawler.clean_url("https://example.com/list/list/document/123")
            # Returns "https://example.com/list/document/123"
        """
        return url.replace("/list/list/", "/list/")

    def extract_page_links(self, html_content: str) -> list:
        """
        Extracts document links from HTML content using BeautifulSoup.

        Args:
            html_content (str): The HTML content to search in

        Returns:
            list: List of found document URLs

        Example:
            links = crawler.extract_page_links(html_content)
            print(f"Found {len(links)} document links")
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

    def get_links(self) -> list:
        """
        Main function for collecting document links by crawling pages.
        Navigates through pages until the maximum number of URLs is reached or there are no
        more new pages.

        Returns:
            list: List of all collected document URLs

        Raises:
            Exception: If an error occurs during crawling

        Example:
            urls = crawler.get_links()
            print(f"Collected {len(urls)} document URLs")
        """
        all_links = []
        current_page = 1

        try:
            # Load initial page
            self.driver.get(self.base_url)
            time.sleep(2)  # Wait for JavaScript to load

            while len(all_links) < self.max_urls:
                print(f"\nProcessing page {current_page}...")

                # Wait until document links are present
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "document-hoofd"))
                )

                # Get current page content and extract links
                current_links = self.extract_page_links(self.driver.page_source)
                print(
                    f"Found {len(current_links)} document links on page {current_page}"
                )

                # Store unique URLs for this page
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
                    print(f"Maximum number of URLs reached ({self.max_urls})")
                    break

                # Try to find and click the next page button
                try:
                    next_buttons = self.driver.find_elements(
                        By.CLASS_NAME, "js-nav-button"
                    )
                    next_button = next(
                        button
                        for button in next_buttons
                        if "Volgende pagina" in button.text
                    )

                    print("Next page button found, clicking...")
                    next_button.click()

                    # Wait for page to update
                    time.sleep(2)

                    # Check if there's new content
                    new_links = self.extract_page_links(self.driver.page_source)
                    if set(new_links) == set(current_links):
                        print("No new content found after navigation")
                        break

                    current_page += 1

                except StopIteration:
                    print("No next page button found")
                    break
                except Exception as e:
                    print(f"Error during navigation: {e}")
                    break

            return all_links

        except Exception as e:
            print(f"An error occurred during crawling: {e}")
            return all_links
        finally:
            self.driver.quit()

    def print_results(self, urls: list) -> None:
        """
        Prints an overview of all collected URLs per page.

        Args:
            urls (list): List of all collected URLs

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

        for page_num in range(1, self.pages_visited + 1):
            page_urls = self.urls_per_page.get(page_num, [])
            print(f"\nPage {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def __del__(self):
        """
        Destructor to ensure the browser is closed.

        Ensures proper cleanup of resources when the object is destroyed.
        """
        try:
            self.driver.quit()
        except:
            pass


if __name__ == "__main__":
    # Configuration for crawling
    base_url = "https://woo.dataportaaloverijssel.nl/list"
    max_urls = 45

    try:
        crawler = Crawler(base_url, max_urls)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
        if "crawler" in locals():
            crawler.print_results(urls)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
