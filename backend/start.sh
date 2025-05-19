#!/bin/bash

# Make scripts executable
chmod +x /app/cron/run_pipeline.sh

# Set up cron job if ENABLE_CRON is set to true
if [ "$ENABLE_CRON" = "true" ]; then
    echo "Setting up cron job for pipeline..."
    # Install cron if not already installed
    apt-get update && apt-get -y install cron
    
    # Copy crontab file to system location
    cp /app/cron/crontab /etc/cron.d/pipeline-cron
    chmod 0644 /etc/cron.d/pipeline-cron
    
    # Apply crontab
    crontab /etc/cron.d/pipeline-cron
    
    # Start cron service
    service cron start
    echo "Cron job set up successfully"
fi

# Run the API server
echo "Starting API server..."
uvicorn api:app --host 0.0.0.0 --port 8000