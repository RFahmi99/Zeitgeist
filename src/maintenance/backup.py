#!/usr/bin/env python3
"""Automated backup system for blog data."""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List

import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BACKUP_DIR = Path('backups')
BACKUP_ITEMS = [
    'blog_posts',
    'config.py',
    'main.py',
    'requirements.txt',
    '.env',
    'analytics.json'
]
RETENTION_COUNT = 10  # Number of backups to retain


def create_backup() -> Path:
    """
    Create a timestamped backup of all specified blog data.
    
    Returns:
        Path to the created backup directory
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'blog_backup_{timestamp}'
    backup_path.mkdir(exist_ok=True)
    
    logger.info(f"Creating backup at: {backup_path}")
    
    for item in BACKUP_ITEMS:
        item_path = Path(item)
        if not item_path.exists():
            logger.warning(f"Skipping missing item: {item}")
            continue
            
        try:
            if item_path.is_dir():
                shutil.copytree(item_path, backup_path / item_path.name)
            else:
                shutil.copy2(item_path, backup_path / item_path.name)
            logger.debug(f"Backed up: {item}")
        except Exception as error:
            logger.error(f"Failed to backup {item}: {error}")
    
    logger.info(f"Backup completed: {backup_path}")
    return backup_path


def clean_old_backups():
    """Remove old backups beyond the retention limit."""
    backups = sorted(
        BACKUP_DIR.glob('blog_backup_*'), 
        key=os.path.getmtime
    )
    
    if len(backups) <= RETENTION_COUNT:
        return
        
    for old_backup in backups[:-RETENTION_COUNT]:
        try:
            if old_backup.is_dir():
                shutil.rmtree(old_backup)
            else:
                old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup}")
        except Exception as error:
            logger.error(f"Failed to remove {old_backup}: {error}")


def perform_backup():
    """Execute backup creation and cleanup."""
    create_backup()
    clean_old_backups()


def schedule_backups():
    """Schedule periodic backups based on environment configuration."""
    try:
        interval = int(os.getenv('DB_BACKUP_INTERVAL', '24'))
        schedule.every(interval).hours.do(perform_backup)
        logger.info(f"Backups scheduled every {interval} hours")
    except ValueError:
        logger.error("Invalid DB_BACKUP_INTERVAL value, using default 24 hours")
        schedule.every(24).hours.do(perform_backup)
    
    logger.info("Backup scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    perform_backup()
    schedule_backups()