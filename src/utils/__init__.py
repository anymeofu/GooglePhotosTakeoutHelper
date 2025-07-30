"""
Utilities Package

Common utility modules for the Google Photos Takeout Helper.

Available modules:
- error_handling: Comprehensive error handling with recovery mechanisms
- system_optimization: System resource monitoring and optimization hints
"""

from .error_handling import (
    ErrorSeverity, ErrorCategory, RecoveryStrategy,
    ErrorContext, RecoveryAction, ErrorHandlingResult,
    ProcessingError, FilesystemError, ValidationError, ResourceError, ConfigurationError,
    ErrorRecoveryManager, ConsoleErrorReporter,
    with_error_handling, error_context,
    create_default_recovery_manager,
    filesystem_error, validation_error, resource_error, config_error
)

from .system_optimization import (
    ResourceType, PerformanceLevel, OptimizationPriority,
    ResourceMetrics, OptimizationRecommendation, SystemAnalysisResult,
    SystemResourceMonitor, SystemOptimizationAnalyzer,
    create_system_monitor, create_optimization_analyzer, print_system_analysis
)

__all__ = [
    # Error handling - Enums
    'ErrorSeverity', 'ErrorCategory', 'RecoveryStrategy',
    
    # Error handling - Data classes
    'ErrorContext', 'RecoveryAction', 'ErrorHandlingResult',
    
    # Error handling - Exceptions
    'ProcessingError', 'FilesystemError', 'ValidationError', 'ResourceError', 'ConfigurationError',
    
    # Error handling - Classes
    'ErrorRecoveryManager', 'ConsoleErrorReporter',
    
    # Error handling - Decorators and context managers
    'with_error_handling', 'error_context',
    
    # Error handling - Factory functions
    'create_default_recovery_manager',
    'filesystem_error', 'validation_error', 'resource_error', 'config_error',
    
    # System optimization - Enums
    'ResourceType', 'PerformanceLevel', 'OptimizationPriority',
    
    # System optimization - Data classes
    'ResourceMetrics', 'OptimizationRecommendation', 'SystemAnalysisResult',
    
    # System optimization - Classes
    'SystemResourceMonitor', 'SystemOptimizationAnalyzer',
    
    # System optimization - Factory functions
    'create_system_monitor', 'create_optimization_analyzer', 'print_system_analysis'
]