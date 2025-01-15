from crawler import Crawler
from scraper import Scraper
import os

def main():
    """
    Main program that integrates Crawler and Scraper.
    - Uses Crawler to collect URLs
    - Uses Scraper to download PDFs and organize them in folders
    """
    # Configuration
    base_url = "https://woo.dataportaaloverijssel.nl/list"
    max_urls = 45  # Number of URLs to process
    
    try:
        print("Starting crawler to collect URLs...")
        crawler = Crawler(base_url, max_urls)
        urls = crawler.get_links()
        
        if not urls:
            print("No URLs found to process.")
            return
            
        print(f"\nFound {len(urls)} URLs")
        
        # Initialize scraper
        scraper = Scraper()
        
        # Process each URL the crawler found
        for i, url in enumerate(urls, 1):
            print(f"\nProcessing URL {i}/{len(urls)}")
            try:
                scraper.scrape_document(url, i)
            except Exception as e:
                print(f"Error processing URL {url}: {e}")
                continue
        
        print("\nProcessing complete!")
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()