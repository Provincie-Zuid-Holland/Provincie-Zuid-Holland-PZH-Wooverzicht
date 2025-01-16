import os

# Paths 
DOWNLOADS_FOLDER = "data/downloads"
EXTRACTED_FOLDER = "data/extracted"
EMBEDDINGS_FOLDER = "data/embeddings"

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ChromaDB persistence directory
CHROMADB_PATH = "data/embeddings/chromadb"

