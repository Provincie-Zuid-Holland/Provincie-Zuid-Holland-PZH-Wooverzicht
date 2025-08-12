# WOOverzicht: Containerized RAG System

This project provides a containerized application for searching through and asking questions about WOO documents. The application is split into a backend API, a frontend UI, and a separate pipeline service for data collection, all running in Docker containers.

## Project Structure

The project is organized with the following structure:

```bash
.
├── Dockerfile.dbcheck                    # Docker container for database health checks
├── README.md                            # Project documentation
├── backend/                             # Backend services and data processing
│   ├── Dockerfile.api                   # Docker container for FastAPI backend
│   ├── Dockerfile.pipeline              # Docker container for data pipeline
│   ├── URLs.txt                         # List of tracked URLs for crawling
│   ├── api.py                          # FastAPI backend service
│   ├── chromadb_query.py               # ChromaDB vector database query interface
│   ├── config.py                       # Configuration settings and environment variables
│   ├── conversational_rag.py           # RAG (Retrieval Augmented Generation) system
│   ├── createdb.py                     # Database initialization script
│   ├── data_scraping/                  # Province-specific web scraping modules
│   │   ├── flevoland_crawler.py        # Flevoland province website crawler
│   │   ├── flevoland_scraper.py        # Flevoland province data scraper
│   │   ├── gelderland_crawler.py       # Gelderland province website crawler
│   │   ├── gelderland_scraper.py       # Gelderland province data scraper
│   │   ├── noordbrabant_crawler.py     # Noord-Brabant province website crawler
│   │   ├── noordbrabant_scraper.py     # Noord-Brabant province data scraper
│   │   ├── overijssel_crawler.py       # Overijssel province website crawler
│   │   ├── overijssel_scraper.py       # Overijssel province data scraper
│   │   ├── zuidholland_crawler.py      # Zuid-Holland province website crawler
│   │   └── zuidholland_scraper.py      # Zuid-Holland province data scraper
│   ├── extract.py                      # Document text extraction and processing
│   ├── failed_downloads.txt            # Log of failed download attempts
│   ├── healthcheck.py                  # System health monitoring
│   ├── manual_pipeline.py              # Manual pipeline execution script to add one specific woo-verzoek
│   ├── pipeline.py                     # Main data collection and processing pipeline to build/add to DB
│   ├── requirements.api.txt            # Python dependencies for API service
│   ├── requirements.pipeline.txt       # Python dependencies for pipeline service
│   ├── requirements.txt                # General Python dependencies
│   └── start.sh                        # Backend startup script
├── bitbucket-pipelines.yml             # CI/CD pipeline configuration
├── check.py                            # System verification script
├── database/                           # ChromaDB vector database storage
├── docker-compose.yml                  # Multi-container Docker orchestration
├── requirements.txt                    # Root level Python dependencies
└── wooverzicht-frontend/               # Next.js frontend application
    ├── Dockerfile                      # Frontend container configuration
    ├── README.md                       # Frontend documentation
    ├── eslint.config.mjs               # ESLint code quality configuration
    ├── next.config.js                  # Next.js framework configuration
    ├── next.config.ts                  # TypeScript Next.js configuration
    ├── package-lock.json               # Locked dependency versions
    ├── package.json                    # Node.js dependencies and scripts
    ├── postcss.config.mjs              # PostCSS styling configuration
    ├── public/                         # Static assets and images like logos
    ├── src/                            # Source code
    │   ├── app/                        # Next.js app directory (routing)
    │   ├── components/                 # Reusable UI components
    │   ├── hooks/                      # Custom React hooks
    │   ├── services/                   # API communication layer
    │   ├── theme/                      # UI theming and design tokens
    │   ├── types/                      # TypeScript type definitions
    │   └── utils/                      # Utility functions and constants
    └── tsconfig.json                   # TypeScript compiler configuration
```

## Setup Instructions

1. **Prepare the environment file**
   - Copy `.env.example` to `.env` in the backend folder
   - Fill in your OpenAI API key and other configuration

2. **Build database if none exists**

   ```bash
   docker-compose up -d --build --backend-pipeline
   ```

3. **Build and start the main services**

   ```bash
   docker-compose up -d --build
   ```

4. **Access the application**
   - Frontend: <http://localhost:3000/>
   - Backend API: <http://localhost:8000/>

5. **Run the pipeline when needed**
   ```bash
   # Run the pipeline once immediately
   ./run_pipeline.sh --run
   
   # Schedule the pipeline to run daily (using host system's cron)
   ./run_pipeline.sh --schedule
   
   # View pipeline logs
   ./run_pipeline.sh --logs
   ```

## Architecture Overview

This application follows a microservices architecture with three main components:

1. **Frontend (Streamlit)**
   - Provides the user interface
   - Communicates with the backend via HTTP/SSE
   - Handles displaying responses and sources

2. **Backend API (FastAPI)**
   - Processes queries and generates responses
   - Manages access to the RAG system
   - Handles document retrieval via ChromaDB
   - Logs interactions automatically

3. **Pipeline Service**
   - Runs as a separate container
   - Collects new documents from provincial websites
   - Processes and indexes documents for search
   - Updates the vector database
   - Only runs when explicitly triggered

### Key Benefits of This Architecture

1. **Complete Separation**: The pipeline container doesn't interfere with the API service
2. **Resource Optimization**: Pipeline resources are only used when needed
3. **Safer Database Updates**: Health checks ensure database integrity
4. **Flexible Scheduling**: Run the pipeline on demand or on a schedule
5. **Shared Codebase**: Both backend services use the same code but with different entry points

## Database Safety Mechanisms

To ensure that the pipeline's updates to the database don't interfere with the API service:

1. **Health Checks**: Both containers run health checks to verify database integrity
2. **Dependency Conditions**: Frontend only starts when backend is healthy
3. **Volume Mounting**: All containers share the same database volumes for consistency

## Running and Managing the Pipeline

The pipeline can be run in different ways:

1. **On-demand execution**:
   ```bash
   ./run_pipeline.sh --run
   ```

2. **Scheduled execution** (using the host's crontab):
   ```bash
   ./run_pipeline.sh --schedule
   ```

3. **Manual execution with custom environment variables**:
   ```bash
   MAX_URLS=50 docker-compose run pipeline
   ```

## Development

To modify the application:

1. Make changes to the code in the respective directories
2. Rebuild the containers: `docker-compose up -d --build`

For local development without Docker:

1. Set up a virtual environment and install dependencies from the appropriate requirements file
2. Run the FastAPI server: `uvicorn backend.api:app --reload`
3. Run the Streamlit app: `streamlit run frontend/app.py`
4. Run the pipeline: `python backend/pipeline.py`