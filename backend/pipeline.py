import sys
import os
import importlib
from typing import Tuple
import tempfile
from extract import extract_data
from createdb import db_pipeline
from config import SUPPORTED_PROVINCES, MAX_URLS, URLS_WRITE_LOCATION
import logging

# Set up logging

handler = logging.StreamHandler(sys.stdout)
handler.flush = sys.stdout.flush  # Ensures flushing
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[handler]
)
logger = logging.getLogger(__name__)

def import_crawler_and_scraper(source: str) -> Tuple[type, type, str]:
    """
    Dynamically imports the appropriate Crawler and Scraper classes based on the source.

    Args:
        source (str): The source province to scrape

    Returns:
        tuple: A tuple containing (Crawler class, Scraper class, base_url)

    Raises:
        ImportError: If the required modules cannot be imported
    """
    province_config = {
        "overijssel": {
            "crawler_module": "overijssel_crawler",
            "scraper_module": "overijssel_scraper",
            "base_url": "https://woo.dataportaaloverijssel.nl/list",
        },
        "gelderland": {
            "crawler_module": "gelderland_crawler",
            "scraper_module": "gelderland_scraper",
            "base_url": "https://open.gelderland.nl",
        },
        "noord_brabant": {
            "crawler_module": "noordbrabant_crawler",
            "scraper_module": "noordbrabant_scraper",
            "base_url": "https://open.brabant.nl/woo-verzoeken",
        },
        "zuid_holland": {
            "crawler_module": "zuidholland_crawler",
            "scraper_module": "zuidholland_scraper",
            "base_url": "https://www.zuid-holland.nl/politiek-bestuur/bestuur-zh/gedeputeerde-staten/besluiten/?facet_wob=10&pager_page=0&zoeken_term=&date_from=&date_to=",
        },
        "flevoland": {
            "crawler_module": "flevoland_crawler",
            "scraper_module": "flevoland_scraper",
            "base_url": "https://www.flevoland.nl/Content/Pages/loket/openbare-documenten/Woo-verzoeken-archief",
        },
    }

    if source not in province_config:
        raise ValueError(f"Unsupported source: {source}")

    config = province_config[source]

    try:
        # Attempt to import modules with multiple potential paths
        import_paths = [
            f"backend.data_scraping.{config['crawler_module']}",
            f"data_scraping.{config['crawler_module']}",
            config["crawler_module"],
        ]

        for path in import_paths:
            try:
                crawler_module = importlib.import_module(path)
                Crawler = getattr(crawler_module, "Crawler")
                break
            except (ImportError, AttributeError):
                continue
        else:
            raise ImportError(f"Could not import Crawler for {source}")

        # Repeat for Scraper
        import_paths = [
            f"backend.data_scraping.{config['scraper_module']}",
            f"data_scraping.{config['scraper_module']}",
            config["scraper_module"],
        ]

        for path in import_paths:
            try:
                scraper_module = importlib.import_module(path)
                Scraper = getattr(scraper_module, "Scraper")
                break
            except (ImportError, AttributeError):
                continue
        else:
            raise ImportError(f"Could not import Scraper for {source}")

        return Crawler, Scraper, config["base_url"]

    except Exception as e:
        print(f"Import error for {source}: {e}")
        raise


def log_failed_download(url: str, error: Exception) -> None:
    """
    Logs failed download attempts to a file.

    Args:
        url (str): The URL that failed to download.
        error (Exception): The exception that was raised during the download attempt.
    """
    with open("failed_downloads.txt", "a+") as f:
        f.write(f"Failed to download: {url}: {error}\n")


def execute_pipeline() -> None:
    """
    Main program that integrates Crawler and Scraper for all supported provinces.
    """
    # Ensure current directory and parent are in Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, current_dir)
    sys.path.insert(0, parent_dir)

    provinces = SUPPORTED_PROVINCES

    # Import the appropriate modules based on source
    for province in provinces:
        try:
            Crawler, Scraper, base_url = import_crawler_and_scraper(province)
        except ImportError as e:
            logger.info(f"Error importing required modules: {e}")
            sys.exit(1)

        try:
            logger.info("<>" * 40)
            logger.info(f"Starting {province.upper()} crawler to collect URLs...")
            logger.info("<>" * 40)
            crawler = Crawler(base_url, max_urls=MAX_URLS)
            urls = crawler.get_new_links(URLS_WRITE_LOCATION)

            if not urls:
                logger.info("No URLs found to process.")
                continue

            logger.info(f"\nFound {len(urls)} URLs")

            # Initialize scraper
            scraper = Scraper()

            # Process each URL the crawler found
            with open(URLS_WRITE_LOCATION, "a+") as f:
                for i, url in enumerate(urls, 1):
                    logger.info(f"\n===\nProcessing URL {i}/{len(urls)}\n===")
                    try:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            logger.info(f"Start scraping URL: {url}")
                            scraper.scrape_document(temp_dir, url, i)  # SCRAPE
                            logger.info(f"Start extracting data")
                            combined_data_list = extract_data(temp_dir)  # EXTRACT
                            logger.info(f"Start chunking and loading into DB")
                            for combined_data in combined_data_list:
                                db_pipeline(combined_data, False)  # CHUNK AND PUT IN DATABASE
                            f.write(f"{url}\n")  # Log successfully processed URL
                            f.flush()
                            logger.info("")
                    except RuntimeError as fe:
                        logger.info(f"Fetch error for URL {url}: {fe}")
                        log_failed_download(url, fe)
                        continue
                    except Exception as e:
                        logger.info(f"Error processing URL {url}: {e}")
                        log_failed_download(url, e)
                        continue

            print("\nProcessing complete!")

        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    execute_pipeline()
