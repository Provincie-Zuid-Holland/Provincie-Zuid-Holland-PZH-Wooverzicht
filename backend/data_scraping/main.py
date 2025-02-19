import sys
import os
from pathlib import Path
import argparse

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)


def main():
    """
    Main program that integrates Crawler and Scraper for either Overijssel or Gelderland.
    - Uses Crawler to collect URLs
    - Uses Scraper to download PDFs and organize them in folders
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Scrape WOO documents from Overijssel or Gelderland."
    )
    parser.add_argument(
        "--source",
        "-s",
        choices=["overijssel", "gelderland"],
        default="overijssel",
        help="Data source to scrape (default: overijssel)",
    )
    parser.add_argument(
        "--max-urls",
        "-m",
        type=int,
        default=10,
        help="Maximum number of URLs to process (default: 10)",
    )
    args = parser.parse_args()

    # Import the appropriate modules based on source
    if args.source == "overijssel":
        from backend.data_scraping.overijssel_crawler import Crawler
        from backend.data_scraping.overijssel_scraper import Scraper

        base_url = "https://woo.dataportaaloverijssel.nl/list"
    else:  # gelderland
        from backend.data_scraping.gelderland_crawler import Crawler
        from backend.data_scraping.gelderland_scraper import Scraper

        base_url = "https://open.gelderland.nl/woo-documenten"

    # Configuration
    max_urls = args.max_urls

    try:
        print(f"Starting {args.source.capitalize()} crawler to collect URLs...")
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
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
