"""Unit tests for metrics collection."""

import unittest
import time

from src.utils.metrics import MetricsCollector, TimingContext


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector(window_size=10)
    
    def test_increment_counter(self):
        """Test incrementing a counter."""
        self.collector.increment("test.counter")
        self.assertEqual(self.collector.get_counter("test.counter"), 1)
        
        self.collector.increment("test.counter", value=5)
        self.assertEqual(self.collector.get_counter("test.counter"), 6)
    
    def test_increment_counter_with_tags(self):
        """Test incrementing counter with tags."""
        self.collector.increment("test.counter", tags={"env": "test"})
        self.assertEqual(self.collector.get_counter("test.counter[env=test]"), 1)
    
    def test_set_gauge(self):
        """Test setting a gauge."""
        self.collector.set_gauge("test.gauge", 42.5)
        self.assertEqual(self.collector.get_gauge("test.gauge"), 42.5)
    
    def test_record_timing(self):
        """Test recording timing metrics."""
        self.collector.record_timing("test.timing", 100.5)
        stats = self.collector.get_timing_stats("test.timing")
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['min'], 100.5)
        self.assertEqual(stats['max'], 100.5)
        self.assertEqual(stats['avg'], 100.5)
    
    def test_get_timing_stats_multiple(self):
        """Test timing stats with multiple values."""
        for value in [10, 20, 30, 40, 50]:
            self.collector.record_timing("test.timing", value)
        
        stats = self.collector.get_timing_stats("test.timing")
        self.assertEqual(stats['count'], 5)
        self.assertEqual(stats['min'], 10)
        self.assertEqual(stats['max'], 50)
        self.assertEqual(stats['avg'], 30)
        self.assertEqual(stats['p50'], 30)
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.collector.increment("counter1")
        self.collector.set_gauge("gauge1", 10.0)
        self.collector.record_timing("timing1", 100.0)
        
        all_metrics = self.collector.get_all_metrics()
        self.assertIn("counters", all_metrics)
        self.assertIn("gauges", all_metrics)
        self.assertIn("timings", all_metrics)
        self.assertEqual(all_metrics["counters"]["counter1"], 1)
        self.assertEqual(all_metrics["gauges"]["gauge1"], 10.0)
    
    def test_reset(self):
        """Test resetting metrics."""
        self.collector.increment("test.counter")
        self.collector.set_gauge("test.gauge", 10.0)
        
        self.collector.reset()
        
        self.assertEqual(self.collector.get_counter("test.counter"), 0)
        self.assertIsNone(self.collector.get_gauge("test.gauge"))


class TestTimingContext(unittest.TestCase):
    """Test TimingContext context manager."""
    
    def test_timing_context(self):
        """Test timing context manager."""
        from src.utils.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        
        with TimingContext("test.timing", tags={"test": "true"}):
            time.sleep(0.01)  # Sleep for 10ms
        
        stats = collector.get_timing_stats("test.timing", tags={"test": "true"})
        self.assertGreater(stats.get('count', 0), 0)
        if stats.get('count', 0) > 0:
            self.assertGreater(stats['avg'], 0)


if __name__ == "__main__":
    unittest.main()

