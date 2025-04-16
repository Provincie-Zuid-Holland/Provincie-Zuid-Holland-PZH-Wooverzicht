###########################################################################
# HOW TO USE THIS SCRIPT:
# This scripts has been created so you are able to manually add woo verzoeken to the DB.
# There are two ways to do this:
# 1. You can paste the URL(s) in the "urls" parameter in the script itself (in the main) and run the script.
# 2. You can run the script and paste one (not more) URL in the terminal when prompted.
#############################################################################

import sys
import os
import importlib
import argparse
from typing import Tuple
import tempfile
from extract import extract_data
from createdb import db_pipeline


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


def execute_manual_pipeline(urls: list) -> None:
    """
    Function that executues the pipeline for adding documents to the database. But now you have to manually input the URLs.
    This function is used for testing purposes.

    Args:
        urls (list): A list of urls that you want to add to the database. If left empty the script will ask for a URL to be input in the terminal

    Returns:
        nothing

    Raises:
        ValueError: If either length or width is negative.

    Example:
        area = calculate_area(5.0, 3.0)
        print(area)  # Output: 15.0
    """
    # Ensure current directory and parent are in Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, current_dir)
    sys.path.insert(0, parent_dir)

    while len(urls) == 0:
        print("#" * 100)
        print("GEEN URL MEEGEGEVEN!\nPlak hier de URL die je in de DB wilt toevoegen:")
        inp = input()
        if len(inp) >= 4:
            urls.append(inp)

    # Import the appropriate modules based on source
    province = ""
    for url in urls:
        if "gelderland" in url.lower():
            province = "gelderland"
        elif "zuid-holland" in url.lower():
            province = "zuid_holland"
        elif "overijssel" in url.lower():
            province = "overijssel"
        elif "brabant" in url.lower():
            province = "noord_brabant"
        elif "flevoland" in url.lower():
            province = "flevoland"
        else:
            print(f"INVALID URL: [{url}]")
            continue
        try:
            Crawler, Scraper, base_url = import_crawler_and_scraper(province)
        except ImportError as e:
            print(f"Error importing required modules for province {province}: {e}")
        if not urls:
            print("No URLs found to process.")
            continue

        print(f"Processing {url}")

        try:
            # Initialize scraper
            scraper = Scraper()
        except Exception as e:
            print(f"Error initializing scraper: {e}")
            continue

        # Process each URL the crawler found
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                scraper.scrape_document(temp_dir, url, 1)  # SCRAPE
                combined_data_list = extract_data(temp_dir)  # EXTRACT
                for combined_data in combined_data_list:
                    db_pipeline(combined_data)  # CHUNK AND PUT IN DATABASE
                print("")
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            continue

        print("\nProcessing complete!")


if __name__ == "__main__":
    ######################################
    # Paste manual urls in here
    urls = []
    #######################################
    execute_manual_pipeline(urls)
