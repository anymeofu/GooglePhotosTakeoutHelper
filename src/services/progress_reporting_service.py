"""
Progress Reporting Service

Comprehensive progress reporting for all processing steps:
- File-based progress tracking
- Real-time progress updates
- Detailed operation statistics
- Time estimation and ETA
- User-friendly progress display

Features:
- Multi-step progress coordination
- Nested progress for sub-operations
- Progress persistence for resumable operations
- Console and file-based progress updates
"""

import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

logger = logging.getLogger(__name__)


class ProgressType(Enum):
    """Types of progress operations."""
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    DISCOVERY = "discovery"
    PROCESSING = "processing"
    MOVING = "moving"
    CLEANUP = "cleanup"


@dataclass
class ProgressStep:
    """Information about a progress step."""
    name: str
    description: str
    weight: float = 1.0  # Relative weight in overall progress
    current: int = 0
    total: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    substeps: List['ProgressStep'] = field(default_factory=list)
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage for this step."""
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100.0)
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time for this step."""
        if not self.start_time:
            return timedelta(0)
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[timedelta]:
        """Estimate remaining time based on current progress."""
        if self.progress_percent == 0 or not self.start_time:
            return None
        
        elapsed = self.elapsed_time
        if elapsed.total_seconds() < 1:  # Too early to estimate
            return None
        
        remaining_percent = 100.0 - self.progress_percent
        if remaining_percent <= 0:
            return timedelta(0)
        
        time_per_percent = elapsed.total_seconds() / self.progress_percent
        estimated_remaining_seconds = time_per_percent * remaining_percent
        return timedelta(seconds=estimated_remaining_seconds)


@dataclass
class ProgressUpdate:
    """Progress update message."""
    step_name: str
    operation_type: ProgressType
    current: int
    total: int
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ProgressReporter:
    """
    Centralized progress reporting system with multiple output formats.
    """
    
    def __init__(self, show_progress: bool = True, verbose: bool = False):
        """
        Initialize progress reporter.
        
        Args:
            show_progress: Show progress bars and updates
            verbose: Show detailed progress information
        """
        self.show_progress = show_progress
        self.verbose = verbose
        self.steps: Dict[str, ProgressStep] = {}
        self.active_step: Optional[str] = None
        self.overall_start_time = datetime.now()
        self.callbacks: List[Callable[[ProgressUpdate], None]] = []
        self.progress_bars: Dict[str, Any] = {}  # tqdm progress bars
        self._lock = threading.Lock()
        
        # Overall progress tracking
        self.total_steps = 0
        self.completed_steps = 0
    
    def add_progress_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Add a callback function for progress updates."""
        with self._lock:
            self.callbacks.append(callback)
    
    def define_steps(self, steps: List[Dict[str, Any]]) -> None:
        """
        Define the processing steps and their weights.
        
        Args:
            steps: List of step definitions with name, description, weight
        """
        with self._lock:
            self.steps.clear()
            self.total_steps = len(steps)
            
            for step_def in steps:
                step = ProgressStep(
                    name=step_def['name'],
                    description=step_def.get('description', step_def['name']),
                    weight=step_def.get('weight', 1.0)
                )
                self.steps[step.name] = step
        
        if self.show_progress and self.verbose:
            print(f"📋 Defined {len(steps)} processing steps")
    
    def start_step(self, step_name: str, total_items: int = 0, message: str = "") -> None:
        """
        Start a processing step.
        
        Args:
            step_name: Name of the step to start
            total_items: Total number of items to process in this step
            message: Initial message for the step
        """
        with self._lock:
            if step_name not in self.steps:
                # Create step if it doesn't exist
                self.steps[step_name] = ProgressStep(
                    name=step_name,
                    description=step_name,
                    weight=1.0
                )
            
            step = self.steps[step_name]
            step.status = "running"
            step.start_time = datetime.now()
            step.total = total_items
            step.current = 0
            self.active_step = step_name
        
        # Create progress bar if tqdm is available and progress is enabled
        if self.show_progress and HAS_TQDM and total_items > 0:
            self.progress_bars[step_name] = tqdm(
                total=total_items,
                desc=step.description,
                unit="items",
                ncols=80,
                leave=False
            )
        
        # Console output
        if self.show_progress:
            if message:
                print(f"🔄 {step.description}: {message}")
            else:
                print(f"🔄 {step.description}")
        
        # Send update to callbacks
        self._send_update(step_name, ProgressType.PROCESSING, 0, total_items, message)
    
    def update_step(self, step_name: str, current: int, message: str = "", 
                   details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update progress for a step.
        
        Args:
            step_name: Name of the step to update
            current: Current progress value
            message: Progress message
            details: Additional details
        """
        with self._lock:
            if step_name not in self.steps:
                return
            
            step = self.steps[step_name]
            step.current = current
        
        # Update progress bar
        if step_name in self.progress_bars:
            bar = self.progress_bars[step_name]
            bar.n = current
            if message:
                bar.set_description(f"{step.description}: {message}")
            bar.refresh()
        
        # Verbose output
        if self.verbose and message:
            percent = (current / step.total * 100) if step.total > 0 else 0
            print(f"  📊 {percent:.1f}% - {message}")
        
        # Send update to callbacks
        self._send_update(step_name, ProgressType.PROCESSING, current, step.total, 
                         message, details or {})
    
    def complete_step(self, step_name: str, message: str = "") -> None:
        """
        Mark a step as completed.
        
        Args:
            step_name: Name of the step to complete
            message: Completion message
        """
        with self._lock:
            if step_name not in self.steps:
                return
            
            step = self.steps[step_name]
            step.status = "completed"
            step.end_time = datetime.now()
            step.current = step.total
            self.completed_steps += 1
        
        # Close progress bar
        if step_name in self.progress_bars:
            self.progress_bars[step_name].close()
            del self.progress_bars[step_name]
        
        # Console output
        if self.show_progress:
            elapsed = step.elapsed_time
            if message:
                print(f"✅ {step.description}: {message} ({elapsed})")
            else:
                print(f"✅ {step.description} completed ({elapsed})")
        
        # Send completion update
        self._send_update(step_name, ProgressType.PROCESSING, step.total, step.total, 
                         message or "Completed")
    
    def fail_step(self, step_name: str, error_message: str) -> None:
        """
        Mark a step as failed.
        
        Args:
            step_name: Name of the failed step
            error_message: Error description
        """
        with self._lock:
            if step_name not in self.steps:
                return
            
            step = self.steps[step_name]
            step.status = "failed"
            step.end_time = datetime.now()
        
        # Close progress bar
        if step_name in self.progress_bars:
            self.progress_bars[step_name].close()
            del self.progress_bars[step_name]
        
        # Console output
        if self.show_progress:
            print(f"❌ {step.description} failed: {error_message}")
        
        # Send failure update
        self._send_update(step_name, ProgressType.PROCESSING, step.current, step.total, 
                         f"Failed: {error_message}")
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall progress summary."""
        with self._lock:
            completed_weight = sum(step.weight for step in self.steps.values() 
                                 if step.status == "completed")
            total_weight = sum(step.weight for step in self.steps.values())
            
            overall_percent = (completed_weight / total_weight * 100) if total_weight > 0 else 0
            
            elapsed = datetime.now() - self.overall_start_time
            
            # Estimate remaining time
            if overall_percent > 0 and overall_percent < 100:
                time_per_percent = elapsed.total_seconds() / overall_percent
                remaining_percent = 100 - overall_percent
                estimated_remaining = timedelta(seconds=time_per_percent * remaining_percent)
            else:
                estimated_remaining = timedelta(0)
            
            return {
                'percent_complete': overall_percent,
                'completed_steps': self.completed_steps,
                'total_steps': self.total_steps,
                'elapsed_time': elapsed,
                'estimated_remaining': estimated_remaining,
                'current_step': self.active_step,
                'step_details': {name: {
                    'status': step.status,
                    'progress': step.progress_percent,
                    'elapsed': step.elapsed_time
                } for name, step in self.steps.items()}
            }
    
    def show_summary(self) -> None:
        """Display a final progress summary."""
        if not self.show_progress:
            return
            
        progress = self.get_overall_progress()
        elapsed = progress['elapsed_time']
        
        print("\n" + "=" * 50)
        print("📊 PROCESSING SUMMARY")
        print("=" * 50)
        print(f"✅ Completed: {progress['completed_steps']}/{progress['total_steps']} steps")
        print(f"⏱️  Total time: {elapsed}")
        
        if self.verbose:
            print("\n📋 Step details:")
            for name, details in progress['step_details'].items():
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏸️'
                }.get(details['status'], '❓')
                print(f"  {status_emoji} {name}: {details['progress']:.1f}% ({details['elapsed']})")
    
    def create_zip_progress_callback(self, step_name: str = "extract_zips") -> Callable:
        """Create a progress callback for ZIP extraction."""
        def zip_callback(zip_progress):
            message = f"Extracting {zip_progress.current_archive} ({zip_progress.current_file})"
            self.update_step(
                step_name, 
                zip_progress.files_extracted, 
                message,
                {
                    'current_file': zip_progress.current_file,
                    'current_archive': zip_progress.current_archive,
                    'bytes_extracted': zip_progress.bytes_extracted,
                    'total_bytes': zip_progress.total_bytes
                }
            )
        
        return zip_callback
    
    def _send_update(self, step_name: str, operation_type: ProgressType, 
                    current: int, total: int, message: str = "",
                    details: Optional[Dict[str, Any]] = None) -> None:
        """Send progress update to all registered callbacks."""
        update = ProgressUpdate(
            step_name=step_name,
            operation_type=operation_type,
            current=current,
            total=total,
            message=message,
            details=details or {}
        )
        
        for callback in self.callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def close(self) -> None:
        """Close all progress bars and clean up resources."""
        with self._lock:
            for bar in self.progress_bars.values():
                bar.close()
            self.progress_bars.clear()


class FileOperationProgress:
    """Specialized progress tracker for file operations."""
    
    def __init__(self, reporter: ProgressReporter, operation_name: str):
        self.reporter = reporter
        self.operation_name = operation_name
        self.files_processed = 0
        self.bytes_processed = 0
        self.total_files = 0
        self.total_bytes = 0
        self.current_file = ""
        
    def start(self, total_files: int, total_bytes: int = 0) -> None:
        """Start file operation tracking."""
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.reporter.start_step(
            self.operation_name,
            total_files,
            f"Processing {total_files:,} files"
        )
    
    def update_file(self, file_path: Path, file_size: int = 0) -> None:
        """Update progress for a single file."""
        self.files_processed += 1
        self.bytes_processed += file_size
        self.current_file = file_path.name
        
        if self.total_bytes > 0:
            # Show both file and byte progress
            bytes_mb = self.bytes_processed / (1024 * 1024)
            total_mb = self.total_bytes / (1024 * 1024)
            message = f"{self.current_file} ({bytes_mb:.1f}/{total_mb:.1f} MB)"
        else:
            # Show just file progress
            message = f"{self.current_file}"
        
        self.reporter.update_step(
            self.operation_name,
            self.files_processed,
            message,
            {
                'current_file': str(file_path),
                'file_size': file_size,
                'bytes_processed': self.bytes_processed,
                'total_bytes': self.total_bytes
            }
        )
    
    def complete(self, message: str = "") -> None:
        """Complete the file operation."""
        if not message:
            if self.total_bytes > 0:
                total_mb = self.bytes_processed / (1024 * 1024)
                message = f"Processed {self.files_processed:,} files ({total_mb:.1f} MB)"
            else:
                message = f"Processed {self.files_processed:,} files"
        
        self.reporter.complete_step(self.operation_name, message)


def create_progress_reporter(show_progress: bool = True, verbose: bool = False) -> ProgressReporter:
    """
    Factory function to create a configured progress reporter.
    
    Args:
        show_progress: Whether to show progress output
        verbose: Whether to show detailed progress
        
    Returns:
        Configured ProgressReporter instance
    """
    return ProgressReporter(show_progress=show_progress, verbose=verbose)


# Standard step definitions for common operations
STANDARD_PROCESSING_STEPS = [
    {'name': 'validate_input', 'description': 'Validating input structure', 'weight': 1.0},
    {'name': 'extract_zips', 'description': 'Extracting ZIP files', 'weight': 2.0},
    {'name': 'discover_media', 'description': 'Discovering media files', 'weight': 2.0},
    {'name': 'remove_duplicates', 'description': 'Removing duplicates', 'weight': 3.0},
    {'name': 'extract_dates', 'description': 'Extracting date information', 'weight': 4.0},
    {'name': 'fix_extensions', 'description': 'Fixing file extensions', 'weight': 1.0},
    {'name': 'write_exif', 'description': 'Writing EXIF metadata', 'weight': 3.0},
    {'name': 'find_albums', 'description': 'Processing albums', 'weight': 2.0},
    {'name': 'organize_files', 'description': 'Organizing files', 'weight': 5.0},
    {'name': 'finalize', 'description': 'Finalizing processing', 'weight': 1.0}
]