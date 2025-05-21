# WOOverzicht: Containerized RAG System

This project provides a containerized application for searching through and asking questions about WOO documents. The application is split into a backend API, a frontend UI, and a separate pipeline service for data collection, all running in Docker containers.

## Project Structure

The project is organized with the following structure:

```
project-root/
│
├── backend/                # Backend code and API
│   ├── api.py              # FastAPI backend service
│   ├── conversational_rag.py
│   ├── query_logger.py
│   ├── chromadb_query.py
│   ├── pipeline.py         # Data collection pipeline
│   ├── healthcheck.py      # Database health verification
│   ├── Dockerfile.api      # Dockerfile for API container
│   ├── Dockerfile.pipeline # Dockerfile for pipeline container
│   ├── requirements.api.txt
│   └── requirements.pipeline.txt
│
├── frontend/               # Frontend application
│   ├── app.py              # Streamlit frontend
│   └── Dockerfile
│
├── database/               # ChromaDB database directory
│
├── logging_database.db     # SQLite database for query logging
├── URLs.txt                # Tracked URLs for crawler
│
├── docker-compose.yml      # Docker Compose configuration
├── run_pipeline.sh         # Helper script to run the pipeline
├── .env                    # Environment variables
└── README.md               # Project documentation
```

## Setup Instructions

1. **Prepare the environment file**
   - Copy `.env.example` to `.env`
   - Fill in your OpenAI API key and other configuration

2. **Build and start the main services**
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000/docs

4. **Run the pipeline when needed**
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