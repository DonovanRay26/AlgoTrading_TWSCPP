"""
Performance tracker for basic system status monitoring.
Tracks system health and basic metrics for the pairs trading system.
"""

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psutil

from monitoring.logging_config import get_logger


class PerformanceTracker:
    """
    Basic performance tracker for system monitoring.
    Tracks system health, uptime, and basic metrics.
    """
    
    def __init__(self):
        """Initialize the performance tracker."""
        self.logger = get_logger("PerformanceTracker")
        
        # System metrics
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        
        # Performance data
        self.system_metrics: Dict[str, Any] = {}
        self.update_count = 0
        
        # Threading
        self.lock = threading.Lock()
        
        # Update frequency
        self.update_interval = 60  # seconds
        
    def update(self):
        """Update performance metrics."""
        try:
            with self.lock:
                # Calculate uptime
                uptime = datetime.now() - self.start_time
                
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Update metrics
                self.system_metrics = {
                    'uptime_seconds': uptime.total_seconds(),
                    'uptime_formatted': str(uptime).split('.')[0],  # Remove microseconds
                    'cpu_usage_percent': cpu_percent,
                    'memory_usage_mb': memory.used / (1024 * 1024),
                    'memory_usage_percent': memory.percent,
                    'disk_usage_percent': (disk.used / disk.total) * 100,
                    'last_update': datetime.now(),
                    'update_count': self.update_count
                }
                
                self.update_count += 1
                self.last_update = datetime.now()
                
                # Log metrics periodically
                if self.update_count % 10 == 0:  # Every 10 updates
                    self.logger.info(
                        f"System Status - Uptime: {self.system_metrics['uptime_formatted']}, "
                        f"CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%"
                    )
                
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def get_performance_data(self) -> Optional[Dict[str, Any]]:
        """Get current performance data."""
        with self.lock:
            if not self.system_metrics:
                return None
            
            # Create a copy of current metrics
            return self.system_metrics.copy()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health assessment."""
        with self.lock:
            health = {
                'status': 'HEALTHY',
                'warnings': [],
                'critical_issues': []
            }
            
            if not self.system_metrics:
                health['status'] = 'UNKNOWN'
                health['warnings'].append('No performance data available')
                return health
            
            # Check CPU usage
            cpu_usage = self.system_metrics.get('cpu_usage_percent', 0)
            if cpu_usage > 90:
                health['status'] = 'CRITICAL'
                health['critical_issues'].append(f'High CPU usage: {cpu_usage:.1f}%')
            elif cpu_usage > 80:
                health['status'] = 'WARNING'
                health['warnings'].append(f'High CPU usage: {cpu_usage:.1f}%')
            
            # Check memory usage
            memory_usage = self.system_metrics.get('memory_usage_percent', 0)
            if memory_usage > 95:
                health['status'] = 'CRITICAL'
                health['critical_issues'].append(f'High memory usage: {memory_usage:.1f}%')
            elif memory_usage > 85:
                health['status'] = 'WARNING'
                health['warnings'].append(f'High memory usage: {memory_usage:.1f}%')
            
            # Check disk usage
            disk_usage = self.system_metrics.get('disk_usage_percent', 0)
            if disk_usage > 95:
                health['status'] = 'CRITICAL'
                health['critical_issues'].append(f'High disk usage: {disk_usage:.1f}%')
            elif disk_usage > 85:
                health['status'] = 'WARNING'
                health['warnings'].append(f'High disk usage: {disk_usage:.1f}%')
            
            # Check if system is responsive
            time_since_update = (datetime.now() - self.last_update).total_seconds()
            if time_since_update > 300:  # 5 minutes
                health['status'] = 'CRITICAL'
                health['critical_issues'].append(f'System not responding: {time_since_update:.0f}s since last update')
            
            return health
    
    def get_uptime(self) -> str:
        """Get formatted uptime string."""
        with self.lock:
            if not self.system_metrics:
                return "Unknown"
            return self.system_metrics.get('uptime_formatted', 'Unknown')
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        with self.lock:
            return self.system_metrics.get('cpu_usage_percent', 0.0)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        with self.lock:
            return self.system_metrics.get('memory_usage_percent', 0.0)
    
    def reset(self):
        """Reset performance tracker."""
        with self.lock:
            self.start_time = datetime.now()
            self.last_update = datetime.now()
            self.system_metrics.clear()
            self.update_count = 0
            self.logger.info("Performance tracker reset")
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        health = self.get_system_health()
        return health['status'] in ['HEALTHY', 'WARNING']  # WARNING is still considered healthy
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        with self.lock:
            health = self.get_system_health()
            
            return {
                'system_health': health,
                'uptime': self.get_uptime(),
                'cpu_usage': self.get_cpu_usage(),
                'memory_usage': self.get_memory_usage(),
                'update_count': self.update_count,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }


# Global performance tracker instance
_performance_tracker = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the global performance tracker instance."""
    global _performance_tracker
    
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    
    return _performance_tracker
