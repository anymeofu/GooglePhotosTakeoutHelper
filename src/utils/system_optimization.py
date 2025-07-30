"""
System Resource Checking and Optimization Hints

This module provides comprehensive system resource monitoring and intelligent
optimization recommendations for the Google Photos Takeout Helper.

Features:
- Real-time system resource monitoring
- Performance bottleneck detection
- Intelligent optimization recommendations
- Cross-platform system information
- Memory usage optimization
- CPU utilization monitoring
- Disk I/O performance analysis
- Network bandwidth considerations

Based on Dart reference: dart-version/lib/utils/system_optimization.dart
"""

import os
import sys
import time
import psutil
import platform
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of system resources to monitor."""
    CPU = auto()
    MEMORY = auto()
    DISK = auto()
    NETWORK = auto()
    GPU = auto()


class PerformanceLevel(Enum):
    """Performance level classifications."""
    OPTIMAL = "optimal"           # Excellent performance
    GOOD = "good"                # Good performance
    MODERATE = "moderate"         # Acceptable performance
    POOR = "poor"                # Poor performance requiring optimization
    CRITICAL = "critical"         # Critical performance issues


class OptimizationPriority(Enum):
    """Priority levels for optimization recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResourceMetrics:
    """System resource metrics snapshot."""
    timestamp: float = field(default_factory=time.time)
    
    # CPU metrics
    cpu_percent: float = 0.0
    cpu_count_logical: int = 0
    cpu_count_physical: int = 0
    cpu_freq_current: float = 0.0
    cpu_freq_max: float = 0.0
    
    # Memory metrics
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_percent: float = 0.0
    
    # Disk metrics
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0
    disk_read_speed_mbps: float = 0.0
    disk_write_speed_mbps: float = 0.0
    
    # Network metrics (if available)
    network_upload_mbps: float = 0.0
    network_download_mbps: float = 0.0
    
    # Process-specific metrics
    process_memory_mb: float = 0.0
    process_cpu_percent: float = 0.0
    process_thread_count: int = 0


@dataclass
class OptimizationRecommendation:
    """System optimization recommendation."""
    priority: OptimizationPriority
    resource_type: ResourceType
    title: str
    description: str
    impact_level: str
    estimated_improvement: str
    implementation_difficulty: str
    specific_actions: List[str] = field(default_factory=list)
    requires_restart: bool = False
    platform_specific: Optional[str] = None  # None, 'windows', 'macos', 'linux'


@dataclass
class SystemAnalysisResult:
    """Complete system analysis result."""
    overall_performance: PerformanceLevel
    metrics: ResourceMetrics
    bottlenecks: List[Tuple[ResourceType, str]]
    recommendations: List[OptimizationRecommendation]
    optimal_settings: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


class SystemResourceMonitor:
    """
    Real-time system resource monitoring with performance analysis.
    """
    
    def __init__(self, monitoring_interval: float = 1.0):
        """
        Initialize the system resource monitor.
        
        Args:
            monitoring_interval: Seconds between monitoring samples
        """
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._metrics_history: List[ResourceMetrics] = []
        self._max_history_size = 100
        
        # Cache system information
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get static system information."""
        try:
            return {
                'platform': platform.system(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'total_memory_gb': psutil.virtual_memory().total / (1024**3),
                'boot_time': psutil.boot_time()
            }
        except Exception as e:
            logger.warning(f"Could not get complete system info: {e}")
            return {'platform': platform.system()}
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        metrics = ResourceMetrics()
        
        try:
            # CPU metrics
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.cpu_count_logical = psutil.cpu_count(logical=True) or 0
            metrics.cpu_count_physical = psutil.cpu_count(logical=False) or 0
            
            # CPU frequency (may not be available on all systems)
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    metrics.cpu_freq_current = cpu_freq.current
                    metrics.cpu_freq_max = cpu_freq.max
            except (AttributeError, OSError):
                pass
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.memory_total_gb = memory.total / (1024**3)
            metrics.memory_used_gb = memory.used / (1024**3)
            metrics.memory_available_gb = memory.available / (1024**3)
            metrics.memory_percent = memory.percent
            
            # Disk metrics for current working directory
            disk = psutil.disk_usage(str(Path.cwd()))
            metrics.disk_total_gb = disk.total / (1024**3)
            metrics.disk_used_gb = disk.used / (1024**3)
            metrics.disk_free_gb = disk.free / (1024**3)
            metrics.disk_percent = (disk.used / disk.total) * 100
            
            # Disk I/O metrics
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io and len(self._metrics_history) > 0:
                    prev_metrics = self._metrics_history[-1]
                    time_diff = metrics.timestamp - prev_metrics.timestamp
                    if time_diff > 0:
                        # Calculate throughput (simplified)
                        read_bytes_diff = disk_io.read_bytes - getattr(self, '_prev_read_bytes', 0)
                        write_bytes_diff = disk_io.write_bytes - getattr(self, '_prev_write_bytes', 0)
                        
                        metrics.disk_read_speed_mbps = (read_bytes_diff / time_diff) / (1024**2)
                        metrics.disk_write_speed_mbps = (write_bytes_diff / time_diff) / (1024**2)
                        
                    self._prev_read_bytes = disk_io.read_bytes
                    self._prev_write_bytes = disk_io.write_bytes
            except (AttributeError, OSError):
                pass
            
            # Process-specific metrics
            try:
                current_process = psutil.Process()
                metrics.process_memory_mb = current_process.memory_info().rss / (1024**2)
                metrics.process_cpu_percent = current_process.cpu_percent()
                metrics.process_thread_count = current_process.num_threads()
            except psutil.Error:
                pass
            
        except Exception as e:
            logger.warning(f"Error collecting metrics: {e}")
        
        return metrics
    
    def start_monitoring(self) -> None:
        """Start continuous monitoring in background thread."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
        logger.info("Started system resource monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join()
        logger.info("Stopped system resource monitoring")
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.is_monitoring:
            try:
                metrics = self.get_current_metrics()
                self._metrics_history.append(metrics)
                
                # Keep history size manageable
                if len(self._metrics_history) > self._max_history_size:
                    self._metrics_history = self._metrics_history[-self._max_history_size:]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval * 2)  # Longer sleep on error
    
    def get_metrics_history(self) -> List[ResourceMetrics]:
        """Get historical metrics data."""
        return self._metrics_history.copy()
    
    def get_average_metrics(self, duration_seconds: Optional[float] = None) -> Optional[ResourceMetrics]:
        """
        Get average metrics over specified duration.
        
        Args:
            duration_seconds: Duration to average over (None for all history)
            
        Returns:
            Average metrics or None if no data
        """
        if not self._metrics_history:
            return None
        
        # Filter metrics by duration
        if duration_seconds:
            cutoff_time = time.time() - duration_seconds
            filtered_metrics = [m for m in self._metrics_history if m.timestamp >= cutoff_time]
        else:
            filtered_metrics = self._metrics_history
        
        if not filtered_metrics:
            return None
        
        # Calculate averages
        avg_metrics = ResourceMetrics()
        count = len(filtered_metrics)
        
        for metrics in filtered_metrics:
            avg_metrics.cpu_percent += metrics.cpu_percent
            avg_metrics.memory_percent += metrics.memory_percent
            avg_metrics.disk_percent += metrics.disk_percent
            avg_metrics.process_memory_mb += metrics.process_memory_mb
            avg_metrics.process_cpu_percent += metrics.process_cpu_percent
            avg_metrics.disk_read_speed_mbps += metrics.disk_read_speed_mbps
            avg_metrics.disk_write_speed_mbps += metrics.disk_write_speed_mbps
        
        # Apply averages
        avg_metrics.cpu_percent /= count
        avg_metrics.memory_percent /= count
        avg_metrics.disk_percent /= count
        avg_metrics.process_memory_mb /= count
        avg_metrics.process_cpu_percent /= count
        avg_metrics.disk_read_speed_mbps /= count
        avg_metrics.disk_write_speed_mbps /= count
        
        # Copy latest values for non-averaged fields
        latest = filtered_metrics[-1]
        avg_metrics.memory_total_gb = latest.memory_total_gb
        avg_metrics.memory_available_gb = latest.memory_available_gb
        avg_metrics.disk_total_gb = latest.disk_total_gb
        avg_metrics.disk_free_gb = latest.disk_free_gb
        avg_metrics.cpu_count_logical = latest.cpu_count_logical
        avg_metrics.cpu_count_physical = latest.cpu_count_physical
        
        return avg_metrics


class SystemOptimizationAnalyzer:
    """
    Analyzes system performance and provides optimization recommendations.
    """
    
    def __init__(self, monitor: SystemResourceMonitor):
        """
        Initialize the optimization analyzer.
        
        Args:
            monitor: System resource monitor instance
        """
        self.monitor = monitor
        self.platform = platform.system().lower()
        
    def analyze_system_performance(self) -> SystemAnalysisResult:
        """
        Perform comprehensive system performance analysis.
        
        Returns:
            Complete analysis with recommendations
        """
        metrics = self.monitor.get_current_metrics()
        bottlenecks = self._detect_bottlenecks(metrics)
        recommendations = self._generate_recommendations(metrics, bottlenecks)
        optimal_settings = self._calculate_optimal_settings(metrics)
        overall_performance = self._assess_overall_performance(metrics)
        warnings = self._generate_warnings(metrics)
        
        return SystemAnalysisResult(
            overall_performance=overall_performance,
            metrics=metrics,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            optimal_settings=optimal_settings,
            warnings=warnings
        )
    
    def _detect_bottlenecks(self, metrics: ResourceMetrics) -> List[Tuple[ResourceType, str]]:
        """Detect system performance bottlenecks."""
        bottlenecks = []
        
        # CPU bottlenecks
        if metrics.cpu_percent > 80:
            bottlenecks.append((ResourceType.CPU, 
                              f"High CPU usage: {metrics.cpu_percent:.1f}%"))
        
        # Memory bottlenecks
        if metrics.memory_percent > 85:
            bottlenecks.append((ResourceType.MEMORY, 
                              f"High memory usage: {metrics.memory_percent:.1f}%"))
        
        # Disk space bottlenecks
        if metrics.disk_percent > 90:
            bottlenecks.append((ResourceType.DISK, 
                              f"Low disk space: {metrics.disk_percent:.1f}% used"))
        
        # Process-specific bottlenecks
        if metrics.process_memory_mb > (metrics.memory_total_gb * 1024 * 0.5):
            bottlenecks.append((ResourceType.MEMORY, 
                              f"Process using {metrics.process_memory_mb:.0f}MB memory"))
        
        return bottlenecks
    
    def _generate_recommendations(self, 
                                 metrics: ResourceMetrics, 
                                 bottlenecks: List[Tuple[ResourceType, str]]) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # CPU optimization recommendations
        if any(bt[0] == ResourceType.CPU for bt in bottlenecks):
            recommendations.extend(self._get_cpu_recommendations(metrics))
        
        # Memory optimization recommendations
        if any(bt[0] == ResourceType.MEMORY for bt in bottlenecks):
            recommendations.extend(self._get_memory_recommendations(metrics))
        
        # Disk optimization recommendations
        if any(bt[0] == ResourceType.DISK for bt in bottlenecks):
            recommendations.extend(self._get_disk_recommendations(metrics))
        
        # General optimization recommendations
        recommendations.extend(self._get_general_recommendations(metrics))
        
        # Sort by priority
        priority_order = {
            OptimizationPriority.CRITICAL: 0,
            OptimizationPriority.HIGH: 1,
            OptimizationPriority.MEDIUM: 2,
            OptimizationPriority.LOW: 3
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    def _get_cpu_recommendations(self, metrics: ResourceMetrics) -> List[OptimizationRecommendation]:
        """Generate CPU-specific recommendations."""
        recommendations = []
        
        if metrics.cpu_percent > 80:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.HIGH,
                resource_type=ResourceType.CPU,
                title="Reduce CPU Thread Count",
                description="High CPU usage detected. Reduce parallel processing threads.",
                impact_level="High",
                estimated_improvement="20-30% CPU reduction",
                implementation_difficulty="Easy",
                specific_actions=[
                    f"Reduce max_threads from current to {max(1, metrics.cpu_count_physical - 1)}",
                    "Use CPU-bound processing with fewer concurrent operations",
                    "Consider processing files in smaller batches"
                ]
            ))
        
        if metrics.cpu_count_logical > 4 and metrics.process_cpu_percent < 25:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.MEDIUM,
                resource_type=ResourceType.CPU,
                title="Increase Parallel Processing",
                description="System has unused CPU capacity. Increase thread count for faster processing.",
                impact_level="Medium",
                estimated_improvement="25-40% speed increase",
                implementation_difficulty="Easy",
                specific_actions=[
                    f"Increase max_threads to {min(metrics.cpu_count_logical, 8)}",
                    "Enable parallel file processing",
                    "Use concurrent I/O operations"
                ]
            ))
        
        return recommendations
    
    def _get_memory_recommendations(self, metrics: ResourceMetrics) -> List[OptimizationRecommendation]:
        """Generate memory-specific recommendations."""
        recommendations = []
        
        if metrics.memory_percent > 85:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.CRITICAL,
                resource_type=ResourceType.MEMORY,
                title="Enable Memory Optimization",
                description="High memory usage detected. Enable streaming and reduce memory footprint.",
                impact_level="High",
                estimated_improvement="40-60% memory reduction",
                implementation_difficulty="Easy",
                specific_actions=[
                    "Enable memory_optimization in system configuration",
                    "Use streaming file processing instead of loading entire files",
                    "Process files in smaller batches",
                    "Clear caches between operations",
                    f"Set memory limit to {metrics.memory_total_gb * 0.7:.1f}GB"
                ]
            ))
        
        if metrics.process_memory_mb > 1024:  # Over 1GB process memory
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.HIGH,
                resource_type=ResourceType.MEMORY,
                title="Reduce Process Memory Usage",
                description="Process is using excessive memory. Implement memory-efficient processing.",
                impact_level="Medium",
                estimated_improvement="30-50% memory reduction",
                implementation_difficulty="Medium",
                specific_actions=[
                    "Use generator patterns instead of loading all data",
                    "Implement lazy loading for large operations",
                    "Free unused objects explicitly",
                    "Use memory mapping for large files"
                ]
            ))
        
        return recommendations
    
    def _get_disk_recommendations(self, metrics: ResourceMetrics) -> List[OptimizationRecommendation]:
        """Generate disk-specific recommendations."""
        recommendations = []
        
        if metrics.disk_percent > 90:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.CRITICAL,
                resource_type=ResourceType.DISK,
                title="Free Disk Space",
                description="Critical: Very low disk space available.",
                impact_level="Critical",
                estimated_improvement="Prevent processing failure",
                implementation_difficulty="Manual",
                specific_actions=[
                    "Clean temporary files and caches",
                    "Remove unnecessary files",
                    "Move files to external storage",
                    "Use a different output directory with more space",
                    f"Free at least {max(5, (95 - metrics.disk_percent) * metrics.disk_total_gb / 100):.1f}GB"
                ]
            ))
        
        if metrics.disk_write_speed_mbps < 50 and metrics.disk_write_speed_mbps > 0:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.MEDIUM,
                resource_type=ResourceType.DISK,
                title="Optimize Disk I/O",
                description="Slow disk write speeds detected. Optimize I/O operations.",
                impact_level="Medium",
                estimated_improvement="20-30% speed increase",
                implementation_difficulty="Easy",
                specific_actions=[
                    "Use SSD for output directory if available",
                    "Increase buffer sizes for file operations",
                    "Reduce concurrent file operations",
                    "Use sequential rather than random access patterns"
                ]
            ))
        
        return recommendations
    
    def _get_general_recommendations(self, metrics: ResourceMetrics) -> List[OptimizationRecommendation]:
        """Generate general optimization recommendations."""
        recommendations = []
        
        # Platform-specific optimizations
        if self.platform == 'windows':
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.LOW,
                resource_type=ResourceType.CPU,
                title="Windows Performance Optimizations",
                description="Apply Windows-specific performance optimizations.",
                impact_level="Low",
                estimated_improvement="5-15% overall improvement",
                implementation_difficulty="Easy",
                platform_specific="windows",
                specific_actions=[
                    "Disable antivirus scanning for processing directories temporarily",
                    "Set process priority to 'High' for better CPU scheduling",
                    "Use Windows-specific file APIs for better performance",
                    "Enable file timestamp updates if needed"
                ]
            ))
        
        elif self.platform == 'darwin':  # macOS
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.LOW,
                resource_type=ResourceType.CPU,
                title="macOS Performance Optimizations",
                description="Apply macOS-specific performance optimizations.",
                impact_level="Low",
                estimated_improvement="5-10% overall improvement",
                implementation_difficulty="Easy",
                platform_specific="macos",
                specific_actions=[
                    "Use macOS native file operations",
                    "Optimize for APFS file system features",
                    "Consider energy impact settings"
                ]
            ))
        
        elif self.platform == 'linux':
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.LOW,
                resource_type=ResourceType.CPU,
                title="Linux Performance Optimizations",
                description="Apply Linux-specific performance optimizations.",
                impact_level="Low",
                estimated_improvement="10-20% overall improvement",
                implementation_difficulty="Medium",
                platform_specific="linux",
                specific_actions=[
                    "Use ionice to set I/O priority",
                    "Adjust vm.swappiness for better memory management",
                    "Use appropriate filesystem mount options",
                    "Consider using preload for frequently accessed files"
                ]
            ))
        
        return recommendations
    
    def _calculate_optimal_settings(self, metrics: ResourceMetrics) -> Dict[str, Any]:
        """Calculate optimal processing settings based on system resources."""
        optimal = {}
        
        # Optimal thread count
        if metrics.cpu_percent > 80:
            optimal['max_threads'] = max(1, metrics.cpu_count_physical - 1)
        elif metrics.cpu_percent < 50 and metrics.memory_percent < 70:
            optimal['max_threads'] = min(metrics.cpu_count_logical, 8)
        else:
            optimal['max_threads'] = metrics.cpu_count_physical
        
        # Memory optimization
        optimal['memory_optimization'] = metrics.memory_percent > 70
        if metrics.memory_total_gb > 8:
            optimal['memory_limit_mb'] = int(metrics.memory_total_gb * 0.7 * 1024)
        else:
            optimal['memory_limit_mb'] = int(metrics.memory_total_gb * 0.5 * 1024)
        
        # Buffer sizes based on available memory
        if metrics.memory_total_gb >= 16:
            optimal['buffer_size'] = 16384  # 16KB
        elif metrics.memory_total_gb >= 8:
            optimal['buffer_size'] = 8192   # 8KB
        else:
            optimal['buffer_size'] = 4096   # 4KB
        
        # Processing batch sizes
        if metrics.memory_total_gb >= 16 and metrics.cpu_count_logical >= 8:
            optimal['batch_size'] = 100
        elif metrics.memory_total_gb >= 8:
            optimal['batch_size'] = 50
        else:
            optimal['batch_size'] = 25
        
        return optimal
    
    def _assess_overall_performance(self, metrics: ResourceMetrics) -> PerformanceLevel:
        """Assess overall system performance level."""
        score = 0
        
        # CPU score (30% weight)
        if metrics.cpu_percent < 50:
            score += 30
        elif metrics.cpu_percent < 70:
            score += 20
        elif metrics.cpu_percent < 85:
            score += 10
        
        # Memory score (30% weight)
        if metrics.memory_percent < 60:
            score += 30
        elif metrics.memory_percent < 80:
            score += 20
        elif metrics.memory_percent < 90:
            score += 10
        
        # Disk score (25% weight)
        if metrics.disk_percent < 70:
            score += 25
        elif metrics.disk_percent < 85:
            score += 15
        elif metrics.disk_percent < 95:
            score += 5
        
        # System capabilities score (15% weight)
        if metrics.cpu_count_logical >= 8 and metrics.memory_total_gb >= 16:
            score += 15
        elif metrics.cpu_count_logical >= 4 and metrics.memory_total_gb >= 8:
            score += 10
        elif metrics.cpu_count_logical >= 2 and metrics.memory_total_gb >= 4:
            score += 5
        # No else clause needed
        
        # Classify performance level
        if score >= 85:
            return PerformanceLevel.OPTIMAL
        elif score >= 70:
            return PerformanceLevel.GOOD
        elif score >= 50:
            return PerformanceLevel.MODERATE
        elif score >= 25:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _generate_warnings(self, metrics: ResourceMetrics) -> List[str]:
        """Generate system warnings based on metrics."""
        warnings = []
        
        if metrics.memory_percent > 95:
            warnings.append("⚠️  Critical memory usage - system may become unstable")
        
        if metrics.disk_percent > 95:
            warnings.append("⚠️  Critical disk space - processing may fail")
        
        if metrics.cpu_count_logical == 1:
            warnings.append("⚠️  Single CPU core detected - processing will be slow")
        
        if metrics.memory_total_gb < 4:
            warnings.append("⚠️  Low system memory - enable memory optimization")
        
        if metrics.disk_free_gb < 1:
            warnings.append("⚠️  Very low disk space - free space immediately")
        
        return warnings


def create_system_monitor() -> SystemResourceMonitor:
    """Create a configured system resource monitor."""
    return SystemResourceMonitor(monitoring_interval=2.0)


def create_optimization_analyzer(monitor: SystemResourceMonitor) -> SystemOptimizationAnalyzer:
    """Create an optimization analyzer with the given monitor."""
    return SystemOptimizationAnalyzer(monitor)


def print_system_analysis(analysis: SystemAnalysisResult) -> None:
    """Print a formatted system analysis report."""
    print(f"\n🖥️  SYSTEM PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    print(f"\n📊 Overall Performance: {analysis.overall_performance.value.upper()}")
    
    # Current metrics
    m = analysis.metrics
    print(f"\n📈 Current System Metrics:")
    print(f"  🔲 CPU: {m.cpu_percent:.1f}% ({m.cpu_count_logical} logical cores)")
    print(f"  💾 Memory: {m.memory_percent:.1f}% ({m.memory_used_gb:.1f}GB/{m.memory_total_gb:.1f}GB)")
    print(f"  💽 Disk: {m.disk_percent:.1f}% ({m.disk_free_gb:.1f}GB free)")
    print(f"  🔄 Process: {m.process_cpu_percent:.1f}% CPU, {m.process_memory_mb:.0f}MB RAM")
    
    # Bottlenecks
    if analysis.bottlenecks:
        print(f"\n⚠️  Detected Bottlenecks:")
        for resource_type, description in analysis.bottlenecks:
            print(f"  • {resource_type.name}: {description}")
    
    # Recommendations
    if analysis.recommendations:
        print(f"\n💡 Optimization Recommendations:")
        for i, rec in enumerate(analysis.recommendations[:5], 1):  # Show top 5
            priority_icon = {
                OptimizationPriority.CRITICAL: "🔴",
                OptimizationPriority.HIGH: "🟡", 
                OptimizationPriority.MEDIUM: "🟠",
                OptimizationPriority.LOW: "🟢"
            }[rec.priority]
            
            print(f"\n  {i}. {priority_icon} {rec.title} [{rec.priority.value.upper()}]")
            print(f"     📝 {rec.description}")
            print(f"     📈 Impact: {rec.impact_level} - {rec.estimated_improvement}")
            if rec.specific_actions:
                print(f"     🔧 Actions: {rec.specific_actions[0]}")
    
    # Optimal settings
    print(f"\n⚙️  Recommended Settings:")
    for key, value in analysis.optimal_settings.items():
        print(f"  • {key}: {value}")
    
    # Warnings
    if analysis.warnings:
        print(f"\n⚠️  System Warnings:")
        for warning in analysis.warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    # Demo the system optimization features
    print("🖥️  System Resource Monitoring Demo")
    print("=" * 50)
    
    # Create monitor and analyzer
    monitor = create_system_monitor()
    analyzer = create_optimization_analyzer(monitor)
    
    # Get current analysis
    analysis = analyzer.analyze_system_performance()
    print_system_analysis(analysis)
    
    # Demo monitoring
    print(f"\n🔄 Starting 5-second monitoring demo...")
    monitor.start_monitoring()
    time.sleep(5)
    
    # Show monitoring results
    history = monitor.get_metrics_history()
    if history:
        print(f"📊 Collected {len(history)} metric samples")
        avg_metrics = monitor.get_average_metrics()
        if avg_metrics:
            print(f"📈 Average CPU: {avg_metrics.cpu_percent:.1f}%")
            print(f"📈 Average Memory: {avg_metrics.memory_percent:.1f}%")
    
    monitor.stop_monitoring()
    print(f"\n✅ System optimization demo complete!")