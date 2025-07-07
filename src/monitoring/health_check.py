#!/usr/bin/env python3
"""Production health check monitoring system"""

import os
import time
import logging
import subprocess
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any

import psutil

logger = logging.getLogger(__name__)

# Critical paths to check for permissions
CRITICAL_PATHS = ('blog_posts', 'logs', 'config.py')
SECONDS_PER_HOUR = 3600


@dataclass
class HealthStatus:
    """System health status container"""
    status: str
    timestamp: str
    checks: Dict[str, Any]
    response_time_ms: float


class HealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check core system resources"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'status': 'healthy'
        }
    
    def check_ai_service(self) -> Dict[str, Any]:
        """Verify AI service availability"""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                timeout=5,
                text=True,
                check=True
            )
            model_count = len(result.stdout.splitlines()) - 1
            return {
                'ollama_available': True,
                'models': model_count,
                'status': 'healthy'
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                'ollama_available': False,
                'error': str(e),
                'status': 'unhealthy'
            }
        except Exception as e:
            logger.exception("Unexpected error checking AI service")
            return {
                'ollama_available': False,
                'error': str(e),
                'status': 'unhealthy'
            }
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Validate critical file access permissions"""
        path_checks = {}
        
        for path in CRITICAL_PATHS:
            path_status = {'exists': os.path.exists(path)}
            if path_status['exists']:
                path_status.update({
                    'readable': os.access(path, os.R_OK),
                    'writable': os.access(path, os.W_OK)
                })
            path_checks[path] = path_status
        
        all_healthy = all(
            status['exists'] and status['readable']
            for status in path_checks.values()
            if status['exists']
        )
        
        return {
            'paths': path_checks,
            'status': 'healthy' if all_healthy else 'degraded'
        }
    
    def get_uptime(self) -> Dict[str, Any]:
        """Calculate system uptime metrics"""
        uptime_seconds = time.time() - self.start_time
        return {
            'uptime_seconds': uptime_seconds,
            'uptime_hours': round(uptime_seconds / SECONDS_PER_HOUR, 2),
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'status': 'healthy'
        }
    
    def perform_health_check(self) -> HealthStatus:
        """Execute comprehensive health assessment"""
        start_time = time.perf_counter()
        
        checks = {
            'system_resources': self.check_system_resources(),
            'ai_service': self.check_ai_service(),
            'file_permissions': self.check_file_permissions(),
            'uptime': self.get_uptime()
        }
        
        # Determine overall system status
        status_priority = {'unhealthy': 3, 'degraded': 2, 'healthy': 1}
        overall_status = max(
            (check['status'] for check in checks.values()),
            key=status_priority.get,
            default='unknown'
        )
        
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            checks=checks,
            response_time_ms=round(response_time_ms, 2)
        )


# Global health monitor instance
health_monitor = HealthMonitor()