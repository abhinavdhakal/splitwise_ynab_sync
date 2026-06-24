"""Configuration management for Splitwise-YNAB sync tool."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Centralized configuration management."""
    
    # Splitwise API Configuration
    SW_API_KEY: str = os.getenv('SW_API_KEY') or os.getenv('SPLITWISE_API_KEY', '')
    
    # YNAB API Configuration  
    YNAB_TOKEN: str = os.getenv('YNAB_TOKEN', '')
    YNAB_BUDGET: str = os.getenv('YNAB_BUDGET') or os.getenv('YNAB_BUDGET_NAME', 'last-used')
    YNAB_SW_ACCOUNT: str = os.getenv('YNAB_SW_ACCOUNT') or os.getenv('YNAB_ACCOUNT_NAME', 'Splitwise')
    YNAB_SW_CATEGORY: str = os.getenv('YNAB_SW_CATEGORY', 'Splitwise')
    
    # Sync Configuration
    USER_NAME: str = os.getenv('USER_NAME', 'you')
    SYNC_DAYS: int = int(os.getenv('SYNC_DAYS', '15'))  # Default to 15 days for GitHub Actions
    POLL_INTERVAL: int = int(os.getenv('POLL_INTERVAL', '15'))  # minutes
    ALLOW_DUPLICATES: bool = os.getenv('ALLOW_DUPLICATES', 'false').lower() == 'true'
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        required_fields = [
            ('SW_API_KEY', cls.SW_API_KEY),
            ('YNAB_TOKEN', cls.YNAB_TOKEN),
        ]
        
        missing = [name for name, value in required_fields if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    @classmethod
    def setup_logging(cls) -> logging.Logger:
        """Setup and return configured logger."""
        logger = logging.getLogger('splitwise_ynab_sync')
        logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Clear any existing handlers
        logger.handlers = []
        
        # Create console handler with formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger