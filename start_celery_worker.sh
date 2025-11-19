#!/bin/bash

# Load environment variables from .env file
set -a
source .env
set +a

# Start Celery worker using Python script
python run_celery_worker.py \
  --loglevel=INFO \
  --concurrency=4 \
  --pool=solo
