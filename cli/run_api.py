#!/usr/bin/env python3
"""
Script to run the FastAPI application.
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import init_config

# Initialize configuration
try:
    config = init_config()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.monitoring.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Configuration initialized successfully")
    
except Exception as e:
    print(f"Failed to initialize configuration: {e}")
    print("\nPlease ensure the following environment variables are set:")
    print("  - DATABASE_URL")
    print("  - JWT_SECRET_KEY")
    print("  - API_KEY_SALT")
    print("\nOr create a .env file with these values.")
    sys.exit(1)

# Import app after config is initialized
from src.api.main import app

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting API server on {config.api.host}:{config.api.port}")
    
    uvicorn.run(
        "src.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=1 if config.api.reload else config.api.workers,
        log_level=config.monitoring.log_level.lower()
    )
