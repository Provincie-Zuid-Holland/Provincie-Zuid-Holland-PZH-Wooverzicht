import sys
import os
from pathlib import Path
import argparse
from typing import List, Optional, Tuple


# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)


def import_crawler_and_scraper(source: str) -> Tuple[type, type, str]:
    """
    Imports the appropriate Crawler and Scraper classes based on the source.

    Args:
        source (str): The source province to scrape ('overijssel', 'gelderland', or 'zuid_holland')

    Returns:
        tuple: A tuple containing (Crawler class, Scraper class, base_url)

    Raises:
        ImportError: If the required modules cannot be imported

    Example:
        Crawler, Scraper, base_url = import_crawler_and_scraper('overijssel')
        crawler = Crawler(base_url, 10)
    """
    if source == "overijssel":
        from backend.data_scraping.overijssel_crawler import Crawler
        from backend.data_scraping.overijssel_scraper import Scraper

        base_url = "https://woo.dataportaaloverijssel.nl/list"
    elif source == "gelderland":
        from backend.data_scraping.gelderland_crawler import Crawler
        from backend.data_scraping.gelderland_scraper import Scraper

        base_url = "https://open.gelderland.nl/woo-documenten"
    else:  # zuid_holland
        from backend.data_scraping.zuidholland_crawler import Crawler
        from backend.data_scraping.zuidholland_scraper import Scraper

        base_url = "https://www.zuid-holland.nl/politiek-bestuur/bestuur-zh/gedeputeerde-staten/besluiten/?facet_wob=10&pager_page=0&zoeken_term=&date_from=&date_to="

    return Crawler, Scraper, base_url


def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments

    Example:
        args = parse_arguments()
        print(f"Source: {args.source}, Max URLs: {args.max_urls}")
    """
    parser = argparse.ArgumentParser(
        description="Scrape WOO documents from various provinces."
    )
    parser.add_argument(
        "--source",
        "-s",
        choices=["overijssel", "gelderland", "zuid_holland"],
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
    return parser.parse_args()


def main() -> None:
    """
    Main program that integrates Crawler and Scraper for either Overijssel, Gelderland, or Zuid-Holland.

    The function performs the following steps:
    1. Parse command line arguments to determine source and max URLs
    2. Import appropriate Crawler and Scraper classes
    3. Use Crawler to collect document URLs
    4. Use Scraper to download documents and organize them in folders

    Returns:
        None

    Raises:
        KeyboardInterrupt: If the user interrupts the program
        Exception: For any other errors during execution

    Example:
        # Run from command line
        $ python script.py --source overijssel --max-urls 20
    """
    # Parse command line arguments
    args = parse_arguments()

    # Import the appropriate modules based on source
    try:
        Crawler, Scraper, base_url = import_crawler_and_scraper(args.source)
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        sys.exit(1)

    # Configuration
    max_urls = args.max_urls

    try:
        print(
            f"Starting {args.source.replace('_', '-').capitalize()} crawler to collect URLs..."
        )
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
