#!/usr/bin/env python3
"""System monitoring and health check script."""

import logging
import os
from datetime import datetime

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health thresholds
DISK_WARNING_THRESHOLD = 90  # Percentage
MEMORY_WARNING_THRESHOLD = 85  # Percentage
LOG_SIZE_WARNING = 100  # MB


def check_system_health() -> dict:
    """
    Check system health and return status report.
    
    Returns:
        Dictionary containing system health status
    """
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Perform all health checks
    health_report['checks']['disk_space'] = _check_disk_health()
    health_report['checks']['memory'] = _check_memory_health()
    health_report['checks']['log_file'] = _check_log_file_health()
    
    # Determine overall status
    if any(check['status'] == 'warning' for check in health_report['checks'].values()):
        health_report['status'] = 'warning'
    
    return health_report


def _check_disk_health() -> dict:
    """Check disk usage health."""
    disk_usage = psutil.disk_usage('/')
    status = 'healthy' if disk_usage.percent < DISK_WARNING_THRESHOLD else 'warning'
    
    return {
        'usage_percent': disk_usage.percent,
        'free_gb': round(disk_usage.free / (1024 ** 3), 1),
        'total_gb': round(disk_usage.total / (1024 ** 3), 1),
        'status': status,
        'threshold': DISK_WARNING_THRESHOLD
    }


def _check_memory_health() -> dict:
    """Check memory usage health."""
    memory = psutil.virtual_memory()
    status = 'healthy' if memory.percent < MEMORY_WARNING_THRESHOLD else 'warning'
    
    return {
        'usage_percent': memory.percent,
        'available_gb': round(memory.available / (1024 ** 3), 1),
        'total_gb': round(memory.total / (1024 ** 3), 1),
        'status': status,
        'threshold': MEMORY_WARNING_THRESHOLD
    }


def _check_log_file_health() -> dict:
    """Check log file health."""
    log_file = 'blog_system.log'
    if not os.path.exists(log_file):
        return {
            'status': 'error',
            'message': 'Log file not found'
        }
    
    log_size_mb = os.path.getsize(log_file) / (1024 ** 2)
    status = 'healthy' if log_size_mb < LOG_SIZE_WARNING else 'warning'
    
    return {
        'size_mb': round(log_size_mb, 2),
        'status': status,
        'threshold': LOG_SIZE_WARNING
    }


def print_health_report(health_report: dict):
    """Print formatted health report to console."""
    print("\nSystem Health Check")
    print("=" * 50)
    print(f"Overall Status: {health_report['status'].upper()}")
    print(f"Timestamp: {health_report['timestamp']}\n")
    
    for check_name, check_data in health_report['checks'].items():
        print(f"{check_name.replace('_', ' ').title()}: {check_data['status'].upper()}")
        
        for key, value in check_data.items():
            if key not in ['status', 'message']:
                unit = ''
                if 'percent' in key:
                    unit = '%'
                elif 'gb' in key:
                    unit = 'GB'
                elif 'mb' in key:
                    unit = 'MB'
                
                print(f"  {key.replace('_', ' ').title()}: {value}{unit}")
        
        if 'message' in check_data:
            print(f"  Message: {check_data['message']}")
        
        print()


def main():
    """Main monitoring function."""
    logger.info("Starting system health check")
    health = check_system_health()
    print_health_report(health)
    logger.info("Health check completed")


if __name__ == "__main__":
    main()