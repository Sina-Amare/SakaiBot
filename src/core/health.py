"""Health check utilities for monitoring system status."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..utils.logging import get_logger
from ..utils.metrics import get_metrics_collector
from ..utils.task_manager import get_task_manager

logger = get_logger(__name__)


class HealthChecker:
    """Checks system health and status."""
    
    def __init__(self):
        """Initialize health checker."""
        self._start_time = datetime.utcnow()
        self._logger = get_logger(self.__class__.__name__)
    
    def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': (datetime.utcnow() - self._start_time).total_seconds(),
            'components': {}
        }
        
        # Check task manager
        try:
            task_manager = get_task_manager()
            active_tasks = len(task_manager._tasks) if hasattr(task_manager, '_tasks') else 0
            health_status['components']['task_manager'] = {
                'status': 'healthy',
                'active_tasks': active_tasks
            }
        except Exception as e:
            health_status['components']['task_manager'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check metrics collector
        try:
            metrics = get_metrics_collector()
            all_metrics = metrics.get_all_metrics()
            health_status['components']['metrics'] = {
                'status': 'healthy',
                'metric_count': len(all_metrics.get('counters', {})) + len(all_metrics.get('gauges', {}))
            }
        except Exception as e:
            health_status['components']['metrics'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        return health_status
    
    def get_status_summary(self) -> str:
        """
        Get human-readable health status summary.
        
        Returns:
            Status summary string
        """
        health = self.check_health()
        status = health['status']
        uptime = health['uptime_seconds']
        
        summary = f"Status: {status.upper()}\n"
        summary += f"Uptime: {uptime:.0f} seconds\n"
        summary += "Components:\n"
        
        for component, info in health['components'].items():
            comp_status = info.get('status', 'unknown')
            summary += f"  - {component}: {comp_status}\n"
        
        return summary


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

