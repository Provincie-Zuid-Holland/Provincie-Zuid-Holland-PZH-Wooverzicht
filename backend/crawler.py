from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin

class Crawler:
    def __init__(self, base_url, max_urls=15):
        self.base_url = base_url.rstrip('/')
        self.max_urls = max_urls
        self.pages_visited = 0
        self.urls_per_page = {}
        self.seen_document_urls = set()
        
        # Initialize Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode (no GUI)
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)  # Wait up to 10 seconds for elements

    def clean_url(self, url):
        return url.replace('/list/list/', '/list/')

    def extract_page_links(self, html_content):
        """
        Extract document links using BeautifulSoup
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/list/document/' in href.lower():
                full_link = urljoin(self.base_url, href)
                clean_link = self.clean_url(full_link)
                links.append(clean_link)
        
        return links

    def get_links(self):
        all_links = []
        current_page = 1
        
        try:
            # Load initial page
            self.driver.get(self.base_url)
            time.sleep(2)  # Wait for JavaScript to load

            while len(all_links) < self.max_urls:
                print(f"\nProcessing page {current_page}...")
                
                # Wait for document links to be present
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "document-hoofd")))
                
                # Get current page source and extract links
                current_links = self.extract_page_links(self.driver.page_source)
                print(f"Found {len(current_links)} document links on page {current_page}")

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
                    print(f"Reached maximum number of URLs ({self.max_urls})")
                    break

                # Try to find and click next button
                try:
                    next_buttons = self.driver.find_elements(By.CLASS_NAME, 'js-nav-button')
                    next_button = next(button for button in next_buttons if 'Volgende pagina' in button.text)
                    
                    print("Found next button, clicking...")
                    next_button.click()
                    
                    # Wait for page to update
                    time.sleep(2)
                    
                    # Check if we got new content
                    new_links = self.extract_page_links(self.driver.page_source)
                    if set(new_links) == set(current_links):
                        print("No new content found after navigation")
                        break
                    
                    current_page += 1
                    
                except StopIteration:
                    print("No next button found")
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

    def print_results(self, urls):
        if not urls:
            print("No URLs were found.")
            return

        pages_text = "page" if self.pages_visited == 1 else "pages"
        print(f"\nVisited {self.pages_visited} {pages_text} and extracted {len(urls)} URLs:")
        
        for page_num in range(1, self.pages_visited + 1):
            page_urls = self.urls_per_page.get(page_num, [])
            print(f"\nPage {page_num} ({len(page_urls)} URLs):")
            for i, url in enumerate(page_urls, 1):
                print(f"{i}. {url}")

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass


if __name__ == "__main__":
    base_url = "https://woo.dataportaaloverijssel.nl/list"
    max_urls = 45
    
    try:
        crawler = Crawler(base_url, max_urls)
        urls = crawler.get_links()
        crawler.print_results(urls)
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
        if 'crawler' in locals():
            crawler.print_results(urls)
    except Exception as e:
        print(f"\nAn error occurred: {e}")