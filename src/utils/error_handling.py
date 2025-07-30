"""
Comprehensive Error Handling with Recovery Mechanisms

This module provides robust error handling capabilities with automatic recovery,
user guidance, and graceful degradation for the Google Photos Takeout Helper.

Features:
- Hierarchical error classification
- Automatic recovery mechanisms
- User-friendly error messages
- Logging and monitoring integration
- Graceful degradation strategies
- Error context preservation

Based on Dart reference: dart-version/lib/utils/error_handling.dart
"""

import logging
import traceback
import time
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Type, Union, TypeVar, Generic,
    Protocol, runtime_checkable
)
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    FATAL = "fatal"           # Process cannot continue
    ERROR = "error"           # Major issue but recoverable
    WARNING = "warning"       # Minor issue with workaround
    INFO = "info"            # Informational message
    DEBUG = "debug"          # Debug information


class ErrorCategory(Enum):
    """Error categories for targeted recovery strategies."""
    FILESYSTEM = "filesystem"        # File/directory access issues
    NETWORK = "network"             # Network connectivity issues
    VALIDATION = "validation"       # Input validation failures
    RESOURCE = "resource"           # Memory/disk/CPU constraints
    PERMISSION = "permission"       # Access permission issues
    CORRUPTION = "corruption"       # Data corruption or integrity
    CONFIGURATION = "configuration" # Configuration errors
    EXTERNAL = "external"           # External tool/dependency issues
    UNKNOWN = "unknown"             # Unclassified errors


class RecoveryStrategy(Enum):
    """Available recovery strategies for errors."""
    RETRY = "retry"                 # Retry the operation
    FALLBACK = "fallback"           # Use alternative method
    SKIP = "skip"                   # Skip and continue
    USER_INPUT = "user_input"       # Request user intervention
    GRACEFUL_DEGRADE = "graceful_degrade"  # Reduce functionality
    ABORT = "abort"                 # Stop processing
    IGNORE = "ignore"               # Log but continue


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    user_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        if not self.stack_trace:
            self.stack_trace = traceback.format_stack()[-3]  # Skip this frame


@dataclass
class RecoveryAction:
    """Defines a recovery action for an error."""
    strategy: RecoveryStrategy
    description: str
    action: Optional[Callable] = None
    max_attempts: int = 1
    delay_seconds: float = 0.0
    fallback_action: Optional['RecoveryAction'] = None
    user_prompt: Optional[str] = None
    
    def execute(self, context: ErrorContext, *args, **kwargs) -> bool:
        """
        Execute the recovery action.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            if self.action:
                result = self.action(context, *args, **kwargs)
                return result if isinstance(result, bool) else True
            return True
        except Exception as e:
            logger.error(f"Recovery action failed: {e}")
            return False


@dataclass
class ErrorHandlingResult:
    """Result of error handling process."""
    recovered: bool
    strategy_used: Optional[RecoveryStrategy] = None
    attempts_made: int = 0
    final_error: Optional[Exception] = None
    messages: List[str] = field(default_factory=list)
    context: Optional[ErrorContext] = None


class ProcessingError(Exception):
    """
    Base exception class with enhanced error handling capabilities.
    """
    
    def __init__(self, 
                 message: str,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 context: Optional[ErrorContext] = None,
                 recoverable: bool = True,
                 original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext(operation="unknown")
        self.recoverable = recoverable
        self.original_exception = original_exception
        self.timestamp = time.time()
        
    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}|{self.category.value}] {self.message}"


class FilesystemError(ProcessingError):
    """File system related errors."""
    
    def __init__(self, message: str, path: Optional[Path] = None, **kwargs):
        super().__init__(message, ErrorCategory.FILESYSTEM, **kwargs)
        if path and self.context:
            self.context.file_path = path


class ValidationError(ProcessingError):
    """Input validation errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.VALIDATION, **kwargs)


class ResourceError(ProcessingError):
    """Resource constraint errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.RESOURCE, **kwargs)


class ConfigurationError(ProcessingError):
    """Configuration related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.CONFIGURATION, **kwargs)


@runtime_checkable
class ErrorReporter(Protocol):
    """Protocol for error reporting implementations."""
    
    def report_error(self, error: ProcessingError, context: ErrorContext) -> None:
        """Report an error occurrence."""
        ...
    
    def report_recovery(self, error: ProcessingError, result: ErrorHandlingResult) -> None:
        """Report a recovery attempt result."""
        ...


class ConsoleErrorReporter:
    """Console-based error reporter."""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and self._supports_colors()
        self.colors = {
            ErrorSeverity.FATAL: '\033[91m',    # Red
            ErrorSeverity.ERROR: '\033[91m',    # Red 
            ErrorSeverity.WARNING: '\033[93m',  # Yellow
            ErrorSeverity.INFO: '\033[94m',     # Blue
            ErrorSeverity.DEBUG: '\033[90m',    # Gray
            'reset': '\033[0m'                  # Reset
        }
    
    def _supports_colors(self) -> bool:
        """Check if terminal supports colors."""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and 
                os.name != 'nt') or os.getenv('FORCE_COLOR', '').lower() in ('1', 'true', 'yes')
    
    def report_error(self, error: ProcessingError, context: ErrorContext) -> None:
        """Report an error to console."""
        color = self.colors.get(error.severity, '') if self.use_colors else ''
        reset = self.colors['reset'] if self.use_colors else ''
        
        icon = {
            ErrorSeverity.FATAL: '💥',
            ErrorSeverity.ERROR: '❌',
            ErrorSeverity.WARNING: '⚠️',
            ErrorSeverity.INFO: 'ℹ️',
            ErrorSeverity.DEBUG: '🔍'
        }.get(error.severity, '❓')
        
        print(f"{color}{icon} {error}{reset}")
        
        if context.file_path:
            print(f"   📁 File: {context.file_path}")
        if context.function_name:
            print(f"   🔧 Function: {context.function_name}")
    
    def report_recovery(self, error: ProcessingError, result: ErrorHandlingResult) -> None:
        """Report recovery attempt result."""
        if result.recovered:
            print(f"✅ Recovered using {result.strategy_used.value if result.strategy_used else 'unknown'} strategy")
        else:
            print(f"❌ Recovery failed after {result.attempts_made} attempts")


class ErrorRecoveryManager:
    """
    Manages error recovery strategies and execution.
    """
    
    def __init__(self, reporter: Optional[ErrorReporter] = None):
        self.reporter = reporter or ConsoleErrorReporter()
        self.recovery_strategies: Dict[ErrorCategory, List[RecoveryAction]] = {}
        self._setup_default_strategies()
    
    def _setup_default_strategies(self) -> None:
        """Setup default recovery strategies for different error categories."""
        
        # Filesystem errors
        self.recovery_strategies[ErrorCategory.FILESYSTEM] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry file operation after brief delay",
                max_attempts=3,
                delay_seconds=1.0
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.USER_INPUT,
                description="Request user intervention for file access",
                user_prompt="File access failed. Please check permissions and try again."
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.SKIP,
                description="Skip problematic file and continue"
            )
        ]
        
        # Network errors  
        self.recovery_strategies[ErrorCategory.NETWORK] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry network operation with exponential backoff",
                max_attempts=5,
                delay_seconds=2.0
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                description="Use offline mode or cached data"
            )
        ]
        
        # Resource errors
        self.recovery_strategies[ErrorCategory.RESOURCE] = [
            RecoveryAction(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADE,
                description="Reduce resource usage and retry"
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.USER_INPUT,
                description="Request user to free up resources",
                user_prompt="Insufficient resources. Please free up disk space/memory and try again."
            )
        ]
        
        # Validation errors
        self.recovery_strategies[ErrorCategory.VALIDATION] = [
            RecoveryAction(
                strategy=RecoveryStrategy.USER_INPUT,
                description="Request corrected input from user"
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                description="Use default values or sensible fallbacks"
            )
        ]
        
        # Permission errors
        self.recovery_strategies[ErrorCategory.PERMISSION] = [
            RecoveryAction(
                strategy=RecoveryStrategy.USER_INPUT,
                description="Request elevated permissions or alternative path",
                user_prompt="Permission denied. Please run as administrator or choose different location."
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                description="Use alternative location with proper permissions"
            )
        ]
    
    def handle_error(self, error: ProcessingError, *args, **kwargs) -> ErrorHandlingResult:
        """
        Handle an error using appropriate recovery strategies.
        
        Args:
            error: The error to handle
            *args, **kwargs: Arguments to pass to recovery actions
            
        Returns:
            ErrorHandlingResult with recovery outcome
        """
        result = ErrorHandlingResult(
            recovered=False,
            context=error.context,
            final_error=error
        )
        
        # Report the error
        self.reporter.report_error(error, error.context)
        
        # Try recovery strategies if error is recoverable
        if not error.recoverable:
            result.messages.append("Error marked as non-recoverable")
            return result
        
        strategies = self.recovery_strategies.get(error.category, [])
        if not strategies:
            result.messages.append(f"No recovery strategies for category: {error.category}")
            return result
        
        for strategy in strategies:
            try:
                result.attempts_made += 1
                result.strategy_used = strategy.strategy
                
                # Execute recovery with retry logic
                recovered = self._execute_with_retry(strategy, error.context, *args, **kwargs)
                
                if recovered:
                    result.recovered = True
                    result.messages.append(f"Recovered using {strategy.strategy.value}")
                    break
                else:
                    result.messages.append(f"Strategy {strategy.strategy.value} failed")
                    
            except Exception as recovery_error:
                result.messages.append(f"Recovery strategy failed: {recovery_error}")
                result.final_error = recovery_error
        
        # Report recovery result
        self.reporter.report_recovery(error, result)
        return result
    
    def _execute_with_retry(self, action: RecoveryAction, context: ErrorContext, 
                          *args, **kwargs) -> bool:
        """Execute recovery action with retry logic."""
        for attempt in range(action.max_attempts):
            try:
                if attempt > 0 and action.delay_seconds > 0:
                    time.sleep(action.delay_seconds * (attempt + 1))
                
                success = action.execute(context, *args, **kwargs)
                if success:
                    return True
                    
            except Exception as e:
                logger.debug(f"Recovery attempt {attempt + 1} failed: {e}")
                if attempt == action.max_attempts - 1:
                    raise
        
        return False
    
    def register_strategy(self, category: ErrorCategory, strategy: RecoveryAction) -> None:
        """Register a custom recovery strategy."""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)


def with_error_handling(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    recovery_manager: Optional[ErrorRecoveryManager] = None,
    reraise: bool = True
):
    """
    Decorator for automatic error handling with recovery.
    
    Args:
        category: Error category for classification
        severity: Error severity level
        recovery_manager: Custom recovery manager
        reraise: Whether to reraise after failed recovery
    """
    def decorator(func: Callable[..., R]) -> Callable[..., Optional[R]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[R]:
            manager = recovery_manager or ErrorRecoveryManager()
            
            try:
                return func(*args, **kwargs)
            except ProcessingError as e:
                # Handle known processing errors
                result = manager.handle_error(e, *args, **kwargs)
                if not result.recovered and reraise:
                    raise
                return None
            except Exception as e:
                # Convert unknown exceptions to ProcessingError
                context = ErrorContext(
                    operation=func.__name__,
                    function_name=func.__name__
                )
                
                processing_error = ProcessingError(
                    message=str(e),
                    category=category,
                    severity=severity,
                    context=context,
                    original_exception=e
                )
                
                result = manager.handle_error(processing_error, *args, **kwargs)
                if not result.recovered and reraise:
                    raise processing_error
                return None
                
        return wrapper
    return decorator


@contextmanager
def error_context(operation: str, **context_kwargs):
    """
    Context manager for error handling with automatic context capture.
    
    Args:
        operation: Description of the operation being performed
        **context_kwargs: Additional context information
    """
    context = ErrorContext(operation=operation, **context_kwargs)
    
    try:
        yield context
    except Exception as e:
        if isinstance(e, ProcessingError):
            if not e.context:
                e.context = context
        else:
            # Convert to ProcessingError with context
            raise ProcessingError(
                message=str(e),
                context=context,
                original_exception=e
            )


def create_default_recovery_manager() -> ErrorRecoveryManager:
    """Create a default recovery manager with console reporting."""
    return ErrorRecoveryManager(ConsoleErrorReporter())


# Convenience functions for common error types
def filesystem_error(message: str, path: Optional[Path] = None, **kwargs) -> FilesystemError:
    """Create a filesystem error with proper context."""
    return FilesystemError(message, path=path, **kwargs)


def validation_error(message: str, **kwargs) -> ValidationError:
    """Create a validation error."""
    return ValidationError(message, **kwargs)


def resource_error(message: str, **kwargs) -> ResourceError:
    """Create a resource error."""
    return ResourceError(message, **kwargs)


def config_error(message: str, **kwargs) -> ConfigurationError:
    """Create a configuration error."""
    return ConfigurationError(message, **kwargs)