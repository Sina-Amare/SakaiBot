"""Unit tests for health checker."""

import unittest
from unittest.mock import patch

from src.core.health import HealthChecker, get_health_checker


class TestHealthChecker(unittest.TestCase):
    """Test HealthChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = HealthChecker()
    
    @patch('src.core.health.get_task_manager')
    @patch('src.core.health.get_metrics_collector')
    def test_check_health_healthy(self, mock_metrics, mock_task_manager):
        """Test health check when all components are healthy."""
        mock_task_manager.return_value._tasks = set()
        mock_metrics.return_value.get_all_metrics.return_value = {
            'counters': {'test': 1},
            'gauges': {}
        }
        
        health = self.checker.check_health()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertIn('timestamp', health)
        self.assertIn('uptime_seconds', health)
        self.assertIn('components', health)
    
    @patch('src.core.health.get_task_manager')
    @patch('src.core.health.get_metrics_collector')
    def test_check_health_degraded(self, mock_metrics, mock_task_manager):
        """Test health check when components are degraded."""
        mock_task_manager.side_effect = Exception("Task manager error")
        mock_metrics.return_value.get_all_metrics.return_value = {
            'counters': {},
            'gauges': {}
        }
        
        health = self.checker.check_health()
        
        self.assertEqual(health['status'], 'degraded')
        self.assertIn('components', health)
        self.assertEqual(health['components']['task_manager']['status'], 'unhealthy')
    
    def test_get_status_summary(self):
        """Test getting status summary."""
        summary = self.checker.get_status_summary()
        
        self.assertIn("Status:", summary)
        self.assertIn("Uptime:", summary)
        self.assertIn("Components:", summary)
    
    def test_get_health_checker_singleton(self):
        """Test singleton pattern."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        self.assertIs(checker1, checker2)


if __name__ == "__main__":
    unittest.main()

