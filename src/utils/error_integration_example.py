"""
Error Handling Integration Example

This module demonstrates how to integrate the comprehensive error handling
system into existing services and CLI components.

Features demonstrated:
- Decorator-based error handling
- Context manager usage
- Custom recovery strategies
- Service integration patterns
"""

import logging
from pathlib import Path
from typing import List, Optional

from .error_handling import (
    ErrorSeverity, ErrorCategory, RecoveryStrategy,
    ErrorContext, RecoveryAction, ErrorHandlingResult,
    ProcessingError, FilesystemError, ValidationError, ResourceError,
    ErrorRecoveryManager, ConsoleErrorReporter,
    with_error_handling, error_context,
    create_default_recovery_manager,
    filesystem_error, validation_error, resource_error
)

logger = logging.getLogger(__name__)


class ExampleFileProcessor:
    """
    Example service demonstrating error handling integration.
    """
    
    def __init__(self):
        self.recovery_manager = create_default_recovery_manager()
        self._setup_custom_strategies()
    
    def _setup_custom_strategies(self):
        """Setup custom recovery strategies for this service."""
        
        # Custom strategy for file corruption
        corruption_recovery = RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use backup file or skip corrupted file",
            action=self._handle_corrupted_file
        )
        
        self.recovery_manager.register_strategy(
            ErrorCategory.CORRUPTION, 
            corruption_recovery
        )
    
    def _handle_corrupted_file(self, context: ErrorContext, *args, **kwargs) -> bool:
        """Custom recovery action for corrupted files."""
        if context.file_path:
            backup_path = context.file_path.with_suffix(context.file_path.suffix + '.backup')
            if backup_path.exists():
                logger.info(f"Using backup file: {backup_path}")
                # Logic to use backup file would go here
                return True
        return False
    
    @with_error_handling(
        category=ErrorCategory.FILESYSTEM,
        severity=ErrorSeverity.ERROR
    )
    def process_single_file(self, file_path: Path) -> bool:
        """
        Process a single file with automatic error handling.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            True if processing succeeded, False otherwise
        """
        if not file_path.exists():
            raise filesystem_error(f"File not found: {file_path}", path=file_path)
        
        if not file_path.is_file():
            raise filesystem_error(f"Path is not a file: {file_path}", path=file_path)
        
        # Simulate file processing
        try:
            with file_path.open('rb') as f:
                data = f.read()
                if len(data) == 0:
                    raise filesystem_error(f"File is empty: {file_path}", path=file_path)
                
                # Process the file data
                logger.info(f"Processed file: {file_path} ({len(data)} bytes)")
                return True
                
        except PermissionError:
            raise filesystem_error(
                f"Permission denied accessing file: {file_path}",
                path=file_path,
                category=ErrorCategory.PERMISSION
            )
    
    def process_files_with_context(self, file_paths: List[Path]) -> dict:
        """
        Process multiple files using error context managers.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'processed': [],
            'failed': [],
            'skipped': []
        }
        
        for file_path in file_paths:
            try:
                with error_context("process_file_batch", file_path=file_path) as ctx:
                    # Add custom context information
                    ctx.user_data['batch_size'] = len(file_paths)
                    ctx.user_data['file_index'] = file_paths.index(file_path)
                    
                    # Process the file
                    success = self.process_single_file(file_path)
                    if success:
                        results['processed'].append(file_path)
                    else:
                        results['failed'].append(file_path)
                        
            except ProcessingError as e:
                # Handle the error with recovery
                recovery_result = self.recovery_manager.handle_error(e)
                
                if recovery_result.recovered:
                    results['processed'].append(file_path)
                elif recovery_result.strategy_used == RecoveryStrategy.SKIP:
                    results['skipped'].append(file_path)
                else:
                    results['failed'].append(file_path)
        
        return results
    
    def validate_input_with_recovery(self, input_path: Path) -> bool:
        """
        Validate input with built-in error recovery.
        
        Args:
            input_path: Path to validate
            
        Returns:
            True if validation passed or was recovered
        """
        try:
            with error_context("input_validation", file_path=input_path):
                if not input_path.exists():
                    raise validation_error(f"Input path does not exist: {input_path}")
                
                if not input_path.is_dir():
                    raise validation_error(f"Input path is not a directory: {input_path}")
                
                # Check if directory is empty
                if not any(input_path.iterdir()):
                    raise validation_error(f"Input directory is empty: {input_path}")
                
                return True
                
        except ProcessingError as e:
            recovery_result = self.recovery_manager.handle_error(e)
            return recovery_result.recovered
    
    def check_disk_space_with_recovery(self, required_space_mb: int) -> bool:
        """
        Check disk space with recovery mechanisms.
        
        Args:
            required_space_mb: Required space in megabytes
            
        Returns:
            True if sufficient space or recovered
        """
        try:
            with error_context("disk_space_check"):
                import shutil
                
                # Get available space
                total, used, free = shutil.disk_usage(Path.cwd())
                free_mb = free // (1024 * 1024)
                
                if free_mb < required_space_mb:
                    raise resource_error(
                        f"Insufficient disk space: {free_mb}MB available, {required_space_mb}MB required"
                    )
                
                return True
                
        except ProcessingError as e:
            recovery_result = self.recovery_manager.handle_error(e)
            return recovery_result.recovered


# Example CLI integration
class ExampleCLIWithErrorHandling:
    """Example CLI component with integrated error handling."""
    
    def __init__(self):
        self.processor = ExampleFileProcessor()
        self.recovery_manager = create_default_recovery_manager()
    
    def run_processing_workflow(self, input_dir: Path, output_dir: Path) -> bool:
        """
        Run complete processing workflow with error handling.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            
        Returns:
            True if workflow completed successfully
        """
        try:
            # Step 1: Validate inputs
            with error_context("workflow_validation"):
                if not self.processor.validate_input_with_recovery(input_dir):
                    logger.error("Input validation failed and could not be recovered")
                    return False
                
                # Check disk space (assume we need 1GB)
                if not self.processor.check_disk_space_with_recovery(1024):
                    logger.error("Disk space check failed and could not be recovered")
                    return False
            
            # Step 2: Gather files to process
            with error_context("file_discovery", file_path=input_dir):
                file_paths = list(input_dir.rglob('*'))
                file_paths = [p for p in file_paths if p.is_file()]
                
                if not file_paths:
                    raise validation_error(f"No files found in input directory: {input_dir}")
            
            # Step 3: Process files
            with error_context("bulk_processing"):
                results = self.processor.process_files_with_context(file_paths)
                
                # Report results
                logger.info(f"Processing complete:")
                logger.info(f"  Processed: {len(results['processed'])} files")
                logger.info(f"  Failed: {len(results['failed'])} files")
                logger.info(f"  Skipped: {len(results['skipped'])} files")
                
                # Consider workflow successful if majority of files processed
                success_rate = len(results['processed']) / len(file_paths)
                return success_rate >= 0.8  # 80% success threshold
                
        except ProcessingError as e:
            recovery_result = self.recovery_manager.handle_error(e)
            return recovery_result.recovered
        
        except Exception as e:
            # Handle unexpected errors
            context = ErrorContext(operation="processing_workflow")
            processing_error = ProcessingError(
                message=f"Unexpected error in workflow: {e}",
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.FATAL,
                context=context,
                original_exception=e
            )
            
            recovery_result = self.recovery_manager.handle_error(processing_error)
            return recovery_result.recovered


def demonstrate_error_handling():
    """Demonstrate the error handling system in action."""
    
    print("🔧 Error Handling System Demonstration")
    print("=" * 50)
    
    # Create example processor
    processor = ExampleFileProcessor()
    
    # Test 1: File not found (should retry then skip)
    print("\n📁 Test 1: File not found scenario")
    try:
        result = processor.process_single_file(Path("nonexistent_file.txt"))
        print(f"Result: {result}")
    except Exception as e:
        print(f"Final exception: {e}")
    
    # Test 2: Validation with recovery
    print("\n✅ Test 2: Validation with recovery")
    result = processor.validate_input_with_recovery(Path("nonexistent_directory"))
    print(f"Validation result: {result}")
    
    # Test 3: Batch processing with mixed results
    print("\n📦 Test 3: Batch processing")
    test_files = [
        Path("file1.txt"),  # Won't exist
        Path("file2.txt"),  # Won't exist
        Path(__file__),     # This file exists
    ]
    
    results = processor.process_files_with_context(test_files)
    print(f"Batch results: {results}")
    
    print(f"\n🎉 Error handling demonstration complete!")


if __name__ == "__main__":
    # Setup logging for demonstration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    demonstrate_error_handling()