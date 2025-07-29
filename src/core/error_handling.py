"""
Comprehensive error handling and recovery system for Google Photos Takeout Helper

This module provides enhanced error handling, recovery mechanisms, and detailed
error reporting for the GPTH processing pipeline.
"""

import os
import sys
import logging
import traceback
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Minor issues, processing can continue
    MEDIUM = "medium"     # Significant issues, may affect results
    HIGH = "high"         # Critical issues, step may fail
    CRITICAL = "critical" # Fatal errors, processing should stop


class ErrorCategory(Enum):
    """Error categories for better classification"""
    FILESYSTEM = "filesystem"       # File/directory access issues
    PERMISSION = "permission"       # Access permission issues
    CORRUPTION = "corruption"       # File corruption or format issues
    DEPENDENCY = "dependency"       # Missing dependencies or external tools
    CONFIGURATION = "configuration" # Configuration or parameter issues
    NETWORK = "network"             # Network connectivity issues
    MEMORY = "memory"               # Memory or resource issues
    UNKNOWN = "unknown"             # Unclassified errors


@dataclass
class ErrorReport:
    """Detailed error report structure"""
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    step_name: str
    file_path: Optional[Path] = None
    error_code: Optional[str] = None
    error_message: str = ""
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_action: Optional[str] = None


@dataclass
class ProcessingStats:
    """Enhanced processing statistics"""
    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=lambda: {
        ErrorSeverity.LOW: 0,
        ErrorSeverity.MEDIUM: 0,
        ErrorSeverity.HIGH: 0,
        ErrorSeverity.CRITICAL: 0
    })
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=lambda: {
        ErrorCategory.FILESYSTEM: 0,
        ErrorCategory.PERMISSION: 0,
        ErrorCategory.CORRUPTION: 0,
        ErrorCategory.DEPENDENCY: 0,
        ErrorCategory.CONFIGURATION: 0,
        ErrorCategory.NETWORK: 0,
        ErrorCategory.MEMORY: 0,
        ErrorCategory.UNKNOWN: 0
    })
    processing_time: float = 0.0
    memory_usage_peak: float = 0.0
    warnings_count: int = 0


class ErrorClassifier:
    """Classify errors by type and severity"""
    
    @staticmethod
    def classify_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> tuple[ErrorSeverity, ErrorCategory]:
        """
        Classify an exception by severity and category
        
        Args:
            exception: The exception to classify
            context: Additional context information
            
        Returns:
            Tuple of (severity, category)
        """
        context = context or {}
        
        # File system related errors
        if isinstance(exception, (FileNotFoundError, IsADirectoryError, NotADirectoryError)):
            return ErrorSeverity.MEDIUM, ErrorCategory.FILESYSTEM
        elif isinstance(exception, PermissionError):
            return ErrorSeverity.HIGH, ErrorCategory.PERMISSION
        elif isinstance(exception, OSError):
            if "disk" in str(exception).lower() or "space" in str(exception).lower():
                return ErrorSeverity.CRITICAL, ErrorCategory.FILESYSTEM
            return ErrorSeverity.MEDIUM, ErrorCategory.FILESYSTEM
        
        # Memory related errors
        elif isinstance(exception, MemoryError):
            return ErrorSeverity.CRITICAL, ErrorCategory.MEMORY
        
        # Import/dependency errors
        elif isinstance(exception, ImportError):
            return ErrorSeverity.HIGH, ErrorCategory.DEPENDENCY
        
        # Configuration errors
        elif isinstance(exception, (ValueError, TypeError)) and "config" in str(exception).lower():
            return ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION
        
        # Corruption/format errors
        elif "corrupt" in str(exception).lower() or "invalid format" in str(exception).lower():
            return ErrorSeverity.MEDIUM, ErrorCategory.CORRUPTION
        
        # Default classification
        else:
            return ErrorSeverity.MEDIUM, ErrorCategory.UNKNOWN


class ErrorRecovery:
    """Error recovery mechanisms"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.recovery_attempts = {}
    
    def attempt_recovery(self, error_report: ErrorReport, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Attempt to recover from an error
        
        Args:
            error_report: The error to recover from
            context: Additional context for recovery
            
        Returns:
            True if recovery was successful, False otherwise
        """
        context = context or {}
        recovery_key = f"{error_report.category}_{error_report.file_path}"
        
        # Limit recovery attempts per file/error type
        if self.recovery_attempts.get(recovery_key, 0) >= 3:
            self.logger.warning(f"Too many recovery attempts for {recovery_key}")
            return False
        
        self.recovery_attempts[recovery_key] = self.recovery_attempts.get(recovery_key, 0) + 1
        
        try:
            # File system recovery
            if error_report.category == ErrorCategory.FILESYSTEM:
                return self._recover_filesystem_error(error_report, context)
            
            # Permission recovery
            elif error_report.category == ErrorCategory.PERMISSION:
                return self._recover_permission_error(error_report, context)
            
            # Corruption recovery
            elif error_report.category == ErrorCategory.CORRUPTION:
                return self._recover_corruption_error(error_report, context)
            
            # Memory recovery
            elif error_report.category == ErrorCategory.MEMORY:
                return self._recover_memory_error(error_report, context)
            
        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
        
        return False
    
    def _recover_filesystem_error(self, error_report: ErrorReport, context: Dict[str, Any]) -> bool:
        """Recover from filesystem errors"""
        if not error_report.file_path or not error_report.file_path.exists():
            self.logger.debug(f"Cannot recover from missing file: {error_report.file_path}")
            return False
        
        # Try to fix file permissions
        try:
            if error_report.file_path.is_file():
                os.chmod(error_report.file_path, 0o644)
                error_report.recovery_action = "Fixed file permissions"
                return True
        except Exception:
            pass
        
        return False
    
    def _recover_permission_error(self, error_report: ErrorReport, context: Dict[str, Any]) -> bool:
        """Recover from permission errors"""
        if not error_report.file_path:
            return False
        
        try:
            # Try to change permissions
            if error_report.file_path.is_file():
                os.chmod(error_report.file_path, 0o644)
            elif error_report.file_path.is_dir():
                os.chmod(error_report.file_path, 0o755)
            
            error_report.recovery_action = "Updated file permissions"
            return True
        except Exception:
            pass
        
        return False
    
    def _recover_corruption_error(self, error_report: ErrorReport, context: Dict[str, Any]) -> bool:
        """Recover from corruption errors"""
        # For corruption, we usually can't recover the file itself
        # but we can mark it for skipping and continue processing
        if error_report.file_path:
            self.logger.warning(f"Marking corrupted file for skipping: {error_report.file_path}")
            error_report.recovery_action = "Marked file as corrupted, will skip"
            return True
        return False
    
    def _recover_memory_error(self, error_report: ErrorReport, context: Dict[str, Any]) -> bool:
        """Recover from memory errors"""
        # Try garbage collection
        import gc
        gc.collect()
        
        # Suggest reducing batch size or concurrent operations
        error_report.recovery_action = "Triggered garbage collection"
        self.logger.warning("Memory error detected - consider reducing batch size")
        return True


class EnhancedErrorHandler:
    """Enhanced error handling with comprehensive reporting and recovery"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.classifier = ErrorClassifier()
        self.recovery = ErrorRecovery(logger)
        self.error_reports: List[ErrorReport] = []
        self.stats = ProcessingStats()
    
    def handle_error(self, 
                    exception: Exception, 
                    step_name: str,
                    file_path: Optional[Path] = None,
                    context: Optional[Dict[str, Any]] = None,
                    attempt_recovery: bool = True) -> ErrorReport:
        """
        Handle an error with classification, logging, and optional recovery
        
        Args:
            exception: The exception that occurred
            step_name: Name of the processing step
            file_path: File being processed when error occurred
            context: Additional context information
            attempt_recovery: Whether to attempt automatic recovery
            
        Returns:
            ErrorReport with details about the error and recovery
        """
        context = context or {}
        
        # Classify the error
        severity, category = self.classifier.classify_exception(exception, context)
        
        # Create error report
        error_report = ErrorReport(
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            step_name=step_name,
            file_path=file_path,
            error_message=str(exception),
            exception_type=type(exception).__name__,
            stack_trace=traceback.format_exc(),
            context=context.copy()
        )
        
        # Update statistics
        self.stats.errors_by_severity[severity] += 1
        self.stats.errors_by_category[category] += 1
        
        # Log the error
        self._log_error(error_report)
        
        # Attempt recovery if requested and severity allows
        if attempt_recovery and severity != ErrorSeverity.CRITICAL:
            error_report.recovery_attempted = True
            error_report.recovery_successful = self.recovery.attempt_recovery(error_report, context)
            
            if error_report.recovery_successful:
                self.logger.info(f"Recovery successful: {error_report.recovery_action}")
        
        # Store the error report
        self.error_reports.append(error_report)
        
        return error_report
    
    def _log_error(self, error_report: ErrorReport):
        """Log an error with appropriate level based on severity"""
        msg = f"[{error_report.step_name}] {error_report.category.value}: {error_report.error_message}"
        
        if error_report.file_path:
            msg += f" (File: {error_report.file_path})"
        
        if error_report.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(msg)
        elif error_report.severity == ErrorSeverity.HIGH:
            self.logger.error(msg)
        elif error_report.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)
        
        # Log stack trace for high/critical errors
        if error_report.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.debug(f"Stack trace: {error_report.stack_trace}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors encountered"""
        return {
            'total_errors': len(self.error_reports),
            'errors_by_severity': {k.value: v for k, v in self.stats.errors_by_severity.items() if v > 0},
            'errors_by_category': {k.value: v for k, v in self.stats.errors_by_category.items() if v > 0},
            'critical_errors': sum(1 for r in self.error_reports if r.severity == ErrorSeverity.CRITICAL),
            'recovered_errors': sum(1 for r in self.error_reports if r.recovery_successful),
            'recent_errors': [
                {
                    'timestamp': r.timestamp.isoformat(),
                    'severity': r.severity.value,
                    'step': r.step_name,
                    'message': r.error_message,
                    'file': str(r.file_path) if r.file_path else None,
                    'recovered': r.recovery_successful
                }
                for r in self.error_reports[-10:]  # Last 10 errors
            ]
        }
    
    def should_stop_processing(self) -> bool:
        """Determine if processing should stop based on error severity"""
        critical_errors = sum(1 for r in self.error_reports if r.severity == ErrorSeverity.CRITICAL)
        return critical_errors > 0
    
    def export_error_report(self, output_path: Path) -> bool:
        """Export detailed error report to file"""
        try:
            import json
            
            report_data = {
                'generation_time': datetime.now().isoformat(),
                'summary': self.get_error_summary(),
                'detailed_errors': [
                    {
                        'timestamp': r.timestamp.isoformat(),
                        'severity': r.severity.value,
                        'category': r.category.value,
                        'step_name': r.step_name,
                        'file_path': str(r.file_path) if r.file_path else None,
                        'error_code': r.error_code,
                        'error_message': r.error_message,
                        'exception_type': r.exception_type,
                        'context': r.context,
                        'recovery_attempted': r.recovery_attempted,
                        'recovery_successful': r.recovery_successful,
                        'recovery_action': r.recovery_action,
                        'stack_trace': r.stack_trace if r.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
                    }
                    for r in self.error_reports
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Error report exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export error report: {e}")
            return False