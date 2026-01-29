"""Metrics collection for monitoring and observability."""

import time
from typing import Dict, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Collects and aggregates metrics for monitoring."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of recent values to keep per metric
        """
        self._window_size = window_size
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histories: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._logger = get_logger(self.__class__.__name__)
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to increment by
            tags: Optional tags for the metric
        """
        key = self._build_key(metric_name, tags)
        self._counters[key] += value
        self._logger.debug(f"Metric {key} incremented by {value}")
    
    def set_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric value.
        
        Args:
            metric_name: Name of the metric
            value: Gauge value
            tags: Optional tags for the metric
        """
        key = self._build_key(metric_name, tags)
        self._gauges[key] = value
        self._histories[key].append(MetricValue(value))
        self._logger.debug(f"Metric {key} set to {value}")
    
    def record_timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing metric in milliseconds.
        
        Args:
            metric_name: Name of the metric
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        key = self._build_key(metric_name, tags)
        self._timers[key].append(MetricValue(duration_ms))
        self._logger.debug(f"Timing {key}: {duration_ms}ms")
    
    def get_counter(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Get counter value."""
        key = self._build_key(metric_name, tags)
        return self._counters.get(key, 0)
    
    def get_gauge(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get gauge value."""
        key = self._build_key(metric_name, tags)
        return self._gauges.get(key)
    
    def get_timing_stats(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get timing statistics.
        
        Args:
            metric_name: Name of the metric
            tags: Optional tags
            
        Returns:
            Dictionary with min, max, avg, p50, p95, p99
        """
        key = self._build_key(metric_name, tags)
        values = [v.value for v in self._timers[key]]
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'count': n,
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / n,
            'p50': sorted_values[n // 2] if n > 0 else 0,
            'p95': sorted_values[int(n * 0.95)] if n > 1 else sorted_values[0],
            'p99': sorted_values[int(n * 0.99)] if n > 1 else sorted_values[0]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'timings': {
                key: self.get_timing_stats(key.split('[')[0])
                for key in self._timers.keys()
            }
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histories.clear()
        self._timers.clear()
        self._logger.info("Metrics reset")
    
    def _build_key(self, metric_name: str, tags: Optional[Dict[str, str]]) -> str:
        """Build metric key with tags."""
        if not tags:
            return metric_name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Initialize timing context.
        
        Args:
            metric_name: Name of the metric
            tags: Optional tags
        """
        self._metric_name = metric_name
        self._tags = tags
        self._start_time: Optional[float] = None
    
    def __enter__(self):
        self._start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start_time is not None:
            duration_ms = (time.perf_counter() - self._start_time) * 1000
            get_metrics_collector().record_timing(self._metric_name, duration_ms, self._tags)

