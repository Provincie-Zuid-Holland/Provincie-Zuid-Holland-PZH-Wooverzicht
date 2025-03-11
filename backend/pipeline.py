import sys
import os
import importlib
import argparse
from typing import Tuple
import tempfile
from extract import extract_data


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
            "base_url": "https://open.gelderland.nl/woo-documenten",
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


def main() -> None:
    """
    Main program that integrates Crawler and Scraper for all supported provinces.
    """
    # Ensure current directory and parent are in Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, current_dir)
    sys.path.insert(0, parent_dir)

    # provinces = [
    #     "overijssel",
    #     "gelderland",
    #     "zuid_holland",
    #     "noord_brabant",
    #     "flevoland",
    # ]
    provinces = ["flevoland"]
    # Import the appropriate modules based on source
    for province in provinces:
        try:
            Crawler, Scraper, base_url = import_crawler_and_scraper(province)
        except ImportError as e:
            print(f"Error importing required modules: {e}")
            sys.exit(1)

        try:
            print(f"Starting {province} crawler to collect URLs...")
            crawler = Crawler(base_url)
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
                    with tempfile.TemporaryDirectory() as temp_dir:
                        print("&&&&", os.listdir(temp_dir))
                        scraper.scrape_document(temp_dir, url, i)  # SCRAPE
                        test = os.listdir(temp_dir)
                        print("#######################")
                        for i in test:
                            print(i)
                        print(len(test))
                        print("#########")
                        combined_data = extract_data(temp_dir)  # EXTRACT
                        print(combined_data)
                        # EXTRACT.PY / OMZETTEN NAAR JSON
                        # CREATEDB.PY / CHUNKEN EN VECTORISEREN
                        # CLEANUP TEMPDIR

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
