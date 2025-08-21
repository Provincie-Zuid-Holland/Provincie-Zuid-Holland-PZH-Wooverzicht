import os

SUPPORTED_PROVINCES = [
    "overijssel",
    "zuid_holland",
    "noord_brabant",
    "flevoland",
    "gelderland",
]

MAX_URLS = 1000  # Maximum number of URLs to crawl per province.

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the folder containing ZIP files
DOWNLOADS_FOLDER = os.path.join(BASE_DIR, "downloads")

# Path to the folder where extracted files will be stored
EXTRACTED_FOLDER = os.path.join(BASE_DIR, "extracted")

# Path to the folder where Json files will be stored
JSON_FOLDER = os.path.join(BASE_DIR, "json")

# ChromaDB configuration
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chromadb")
CHROMA_COLLECTION_NAME = "pdf_chunks"
