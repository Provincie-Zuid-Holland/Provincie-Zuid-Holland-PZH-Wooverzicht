#!/bin/bash

# Script to run the pipeline container on demand or on a schedule

function show_help {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --run              Run the pipeline once and exit"
    echo "  --schedule         Schedule the pipeline using cron on the host"
    echo "  --unschedule       Remove any scheduled pipeline jobs"
    echo "  --logs             View the pipeline container logs"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --run           # Run the pipeline container once immediately"
    echo "  $0 --schedule      # Schedule the pipeline to run daily at 2 AM"
    echo "  $0 --logs          # Show logs from the last pipeline run"
}

function run_pipeline {
    echo "Starting pipeline container..."
    docker-compose run --rm pipeline
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "Pipeline completed successfully."
    else
        echo "Pipeline exited with code $exit_code. Check logs for details."
    fi
}

function schedule_pipeline {
    # Check if we're on Linux/Mac (cron available)
    if command -v crontab &> /dev/null; then
        # Create a temporary file with current crontab content
        crontab -l > /tmp/current_crontab 2>/dev/null || echo "" > /tmp/current_crontab
        
        # Check if the job is already scheduled
        if grep -q "run_pipeline.sh --run" /tmp/current_crontab; then
            echo "Pipeline is already scheduled. Use --unschedule first if you want to change the schedule."
            rm /tmp/current_crontab
            return
        fi
        
        # Add the job to run daily at 2 AM
        echo "0 2 * * * $(pwd)/run_pipeline.sh --run > $(pwd)/pipeline.log 2>&1" >> /tmp/current_crontab
        
        # Install the new crontab
        crontab /tmp/current_crontab
        rm /tmp/current_crontab
        
        echo "Pipeline scheduled to run daily at 2 AM."
        echo "Logs will be written to $(pwd)/pipeline.log"
    else
        echo "Cron not available on this system. Please set up a scheduled task manually."
        echo "Command to run: $(pwd)/run_pipeline.sh --run"
    fi
}

function unschedule_pipeline {
    # Check if we're on Linux/Mac (cron available)
    if command -v crontab &> /dev/null; then
        # Create a temporary file with current crontab content
        crontab -l > /tmp/current_crontab 2>/dev/null || echo "" > /tmp/current_crontab
        
        # Remove any lines containing run_pipeline.sh
        sed -i.bak '/run_pipeline\.sh/d' /tmp/current_crontab
        
        # Install the new crontab
        crontab /tmp/current_crontab
        rm /tmp/current_crontab /tmp/current_crontab.bak 2>/dev/null
        
        echo "Pipeline has been unscheduled."
    else
        echo "Cron not available on this system. Please remove the scheduled task manually."
    fi
}

function view_logs {
    if [ -f "pipeline.log" ]; then
        echo "=== Pipeline Logs ==="
        cat pipeline.log
    else
        echo "No pipeline logs found. Run the pipeline first."
    fi
}

# Check arguments
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

case "$1" in
    --run)
        run_pipeline
        ;;
    --schedule)
        schedule_pipeline
        ;;
    --unschedule)
        unschedule_pipeline
        ;;
    --logs)
        view_logs
        ;;
    --help)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac