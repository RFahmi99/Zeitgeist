#!/usr/bin/env python3
"""Advanced performance monitoring and metrics collection system"""

import time
import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Callable, Any, Optional

logger = logging.getLogger(__name__)

# Constants
SECONDS_PER_HOUR = 3600
DEFAULT_RETENTION_HOURS = 24
CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


@dataclass
class MetricDataPoint:
    """Single metric data point with timestamp and tags"""
    timestamp: float
    value: float
    tags: Dict[str, str]


class MetricsAggregator:
    """Metrics collection and aggregation system"""
    
    def __init__(self, retention_hours: int = DEFAULT_RETENTION_HOURS):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.retention_hours = retention_hours
        self.lock = threading.RLock()  # Reentrant lock for nested operations
        self._cleanup_thread = None
        self._start_cleanup_thread()
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric with timestamp and optional tags"""
        with self.lock:
            data_point = MetricDataPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            self.metrics[name].append(data_point)
    
    def record_timer(
        self, 
        name: str, 
        start_time: float, 
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record execution time duration in milliseconds"""
        duration_ms = (time.time() - start_time) * 1000
        self.record_metric(f"{name}.duration_ms", duration_ms, tags)
    
    def record_counter(
        self, 
        name: str, 
        increment: int = 1, 
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record counter increment"""
        self.record_metric(f"{name}.count", increment, tags)
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Dict[str, float]]:
        """Generate aggregated metrics summary for the last N hours"""
        cutoff_time = time.time() - (hours * SECONDS_PER_HOUR)
        summary = {}
        
        with self.lock:
            for metric_name, data_points in self.metrics.items():
                # Filter recent data points efficiently
                recent_points = [
                    dp for dp in data_points 
                    if dp.timestamp >= cutoff_time
                ]
                
                if not recent_points:
                    continue
                
                values = [dp.value for dp in recent_points]
                summary[metric_name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[-1],
                    'first_timestamp': recent_points[0].timestamp,
                    'last_timestamp': recent_points[-1].timestamp
                }
        
        return summary
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period"""
        cutoff_time = time.time() - (self.retention_hours * SECONDS_PER_HOUR)
        
        with self.lock:
            for metric_name, data_points in list(self.metrics.items()):
                # Remove old points from the left (oldest)
                while data_points and data_points[0].timestamp < cutoff_time:
                    data_points.popleft()
                
                # Remove metric if no data points remain
                if not data_points:
                    del self.metrics[metric_name]
    
    def _cleanup_worker(self) -> None:
        """Background worker for periodic metrics cleanup"""
        while True:
            time.sleep(CLEANUP_INTERVAL_SECONDS)
            try:
                self._cleanup_old_metrics()
            except Exception as e:
                logger.exception("Metrics cleanup error: %s", e)
    
    def _start_cleanup_thread(self) -> None:
        """Initialize and start background cleanup thread"""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="MetricsCleanupThread",
            daemon=True
        )
        self._cleanup_thread.start()


# Global metrics collector instance
metrics = MetricsAggregator()


def timed_operation(
    metric_name: str, 
    tags: Optional[Dict[str, str]] = None
) -> Callable:
    """Decorator factory for timing function execution
    
    Records:
        - Execution duration in milliseconds
        - Success/error counters
    
    Args:
        metric_name: Base name for generated metrics
        tags: Optional tags to attach to metrics
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.record_timer(metric_name, start_time, tags)
                metrics.record_counter(f"{metric_name}.success", tags=tags)
                return result
            except Exception as e:
                metrics.record_counter(f"{metric_name}.error", tags=tags)
                raise e
        return wrapper
    return decorator