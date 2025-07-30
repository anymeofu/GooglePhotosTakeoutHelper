"""
ZIP Extraction Service with Security Validation

This service handles secure extraction of Google Takeout ZIP files with:
- Path traversal attack prevention (Zip Slip protection)
- Memory-efficient streaming for large files
- Cross-platform filename sanitization
- Progress callback support
- Error handling and recovery

Based on Dart reference: dart-version/lib/domain/services/file_operations/archive_extraction_service.dart
"""

import os
import re
import zipfile
import unicodedata
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionProgress:
    """Progress information for ZIP extraction operations."""
    current_file: str
    files_extracted: int
    total_files: int
    bytes_extracted: int
    total_bytes: int
    current_archive: str
    
    @property
    def file_progress_percent(self) -> float:
        """Calculate file-based progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.files_extracted / self.total_files) * 100.0
    
    @property
    def bytes_progress_percent(self) -> float:
        """Calculate byte-based progress percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_extracted / self.total_bytes) * 100.0


@dataclass
class ExtractionResult:
    """Result of ZIP extraction operation."""
    success: bool
    extracted_files: int
    total_size_bytes: int
    extraction_path: Path
    errors: List[str]
    warnings: List[str]


class ZipExtractionError(Exception):
    """Custom exception for ZIP extraction errors."""
    pass


class ZipExtractionService:
    """
    Service for secure ZIP file extraction with comprehensive validation.
    
    Features:
    - Zip Slip attack prevention
    - Cross-platform filename sanitization
    - Memory-efficient extraction for large files
    - Progress reporting
    - Error recovery and detailed logging
    """
    
    # Windows reserved filenames (case-insensitive)
    WINDOWS_RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Characters that need sanitization on various platforms
    INVALID_CHARS = r'[<>:"|?*\x00-\x1f]'
    
    # Maximum path length limits
    MAX_PATH_LENGTH = {
        'windows': 260,
        'unix': 4096
    }
    
    def __init__(self, chunk_size: int = 8192, max_extract_size: int = 50 * 1024 * 1024 * 1024):
        """
        Initialize ZIP extraction service.
        
        Args:
            chunk_size: Size of chunks for streaming extraction (default 8KB)
            max_extract_size: Maximum total extraction size in bytes (default 50GB)
        """
        self.chunk_size = chunk_size
        self.max_extract_size = max_extract_size
        self.progress_callback: Optional[Callable[[ExtractionProgress], None]] = None
    
    def set_progress_callback(self, callback: Callable[[ExtractionProgress], None]) -> None:
        """Set callback function for progress updates."""
        self.progress_callback = callback
    
    def extract_zip_files(self, zip_paths: List[Path], extraction_dir: Path) -> ExtractionResult:
        """
        Extract multiple ZIP files to a target directory.
        
        Args:
            zip_paths: List of ZIP file paths to extract
            extraction_dir: Target directory for extraction
            
        Returns:
            ExtractionResult with extraction statistics and any errors
            
        Raises:
            ZipExtractionError: If extraction fails critically
        """
        extraction_dir = Path(extraction_dir)
        extraction_dir.mkdir(parents=True, exist_ok=True)
        
        total_files = 0
        total_bytes = 0
        extracted_files = 0
        extracted_bytes = 0
        errors = []
        warnings = []
        
        logger.info(f"Starting extraction of {len(zip_paths)} ZIP files to {extraction_dir}")
        
        try:
            # Pre-scan all ZIP files to get totals for progress reporting
            for zip_path in zip_paths:
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        for info in zf.infolist():
                            if not info.is_dir():
                                total_files += 1
                                total_bytes += info.file_size
                except Exception as e:
                    warnings.append(f"Could not scan {zip_path}: {str(e)}")
            
            # Check if total extraction size exceeds limits
            if total_bytes > self.max_extract_size:
                raise ZipExtractionError(
                    f"Total extraction size ({total_bytes / (1024**3):.1f}GB) "
                    f"exceeds maximum allowed ({self.max_extract_size / (1024**3):.1f}GB)"
                )
            
            # Extract each ZIP file
            for zip_path in zip_paths:
                try:
                    result = self._extract_single_zip(
                        zip_path, extraction_dir, extracted_files, total_files, 
                        extracted_bytes, total_bytes
                    )
                    extracted_files += result['files']
                    extracted_bytes += result['bytes']
                    
                except Exception as e:
                    error_msg = f"Failed to extract {zip_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            logger.info(f"Extraction completed: {extracted_files}/{total_files} files, "
                       f"{extracted_bytes / (1024**2):.1f}MB extracted")
            
            return ExtractionResult(
                success=len(errors) == 0,
                extracted_files=extracted_files,
                total_size_bytes=extracted_bytes,
                extraction_path=extraction_dir,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Critical extraction error: {str(e)}")
            raise ZipExtractionError(f"Extraction failed: {str(e)}")
    
    def _extract_single_zip(self, zip_path: Path, extraction_dir: Path, 
                           files_done: int, total_files: int,
                           bytes_done: int, total_bytes: int) -> Dict[str, int]:
        """
        Extract a single ZIP file with security validation.
        
        Args:
            zip_path: Path to ZIP file
            extraction_dir: Target extraction directory
            files_done: Number of files already extracted
            total_files: Total files across all ZIPs
            bytes_done: Bytes already extracted
            total_bytes: Total bytes across all ZIPs
            
        Returns:
            Dictionary with 'files' and 'bytes' extracted from this ZIP
        """
        logger.info(f"Extracting {zip_path}")
        
        extracted_files = 0
        extracted_bytes = 0
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue
                
                try:
                    # Validate and sanitize the extraction path
                    safe_path = self._get_safe_extraction_path(info.filename, extraction_dir)
                    
                    # Create parent directories if needed
                    safe_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract file with streaming to handle large files
                    self._extract_file_safely(zf, info, safe_path)
                    
                    extracted_files += 1
                    extracted_bytes += info.file_size
                    
                    # Report progress
                    if self.progress_callback:
                        progress = ExtractionProgress(
                            current_file=info.filename,
                            files_extracted=files_done + extracted_files,
                            total_files=total_files,
                            bytes_extracted=bytes_done + extracted_bytes,
                            total_bytes=total_bytes,
                            current_archive=zip_path.name
                        )
                        self.progress_callback(progress)
                
                except Exception as e:
                    logger.warning(f"Failed to extract {info.filename}: {str(e)}")
                    continue
        
        return {'files': extracted_files, 'bytes': extracted_bytes}
    
    def _get_safe_extraction_path(self, zip_filename: str, extraction_dir: Path) -> Path:
        """
        Generate a safe extraction path preventing path traversal attacks.
        
        Args:
            zip_filename: Original filename from ZIP
            extraction_dir: Base extraction directory
            
        Returns:
            Safe path for extraction
            
        Raises:
            ZipExtractionError: If path is unsafe
        """
        # Normalize path separators and remove leading separators
        safe_filename = zip_filename.replace('\\', '/').lstrip('/')
        
        # Split into components and validate each
        path_parts = []
        for part in safe_filename.split('/'):
            if not part or part in ('.', '..'):
                continue  # Skip empty, current dir, and parent dir references
            
            # Sanitize the filename component
            sanitized_part = self._sanitize_filename_component(part)
            if sanitized_part:
                path_parts.append(sanitized_part)
        
        if not path_parts:
            raise ZipExtractionError(f"Invalid filename in ZIP: {zip_filename}")
        
        # Construct the safe path
        safe_path = extraction_dir
        for part in path_parts:
            safe_path = safe_path / part
        
        # Verify the final path is within extraction directory
        try:
            safe_path.resolve().relative_to(extraction_dir.resolve())
        except ValueError:
            raise ZipExtractionError(f"Path traversal attempt detected: {zip_filename}")
        
        # Check path length limits
        if len(str(safe_path)) > self.MAX_PATH_LENGTH.get(os.name, 4096):
            raise ZipExtractionError(f"Path too long: {zip_filename}")
        
        return safe_path
    
    def _sanitize_filename_component(self, filename: str) -> str:
        """
        Sanitize a single filename component for cross-platform compatibility.
        
        Args:
            filename: Original filename component
            
        Returns:
            Sanitized filename safe for the current platform
        """
        if not filename:
            return ''
        
        # Unicode normalization
        filename = unicodedata.normalize('NFC', filename)
        
        # Remove/replace invalid characters
        filename = re.sub(self.INVALID_CHARS, '_', filename)
        
        # Handle Windows reserved names
        if os.name == 'nt':
            base_name = filename.split('.')[0].upper()
            if base_name in self.WINDOWS_RESERVED_NAMES:
                filename = f"_{filename}"
        
        # Remove trailing dots and spaces (Windows compatibility)
        filename = filename.rstrip('. ')
        
        # Ensure filename is not empty after sanitization
        if not filename:
            filename = 'unnamed_file'
        
        # Limit length
        max_component_length = 255
        if len(filename.encode('utf-8')) > max_component_length:
            # Truncate while preserving extension
            parts = filename.rsplit('.', 1)
            if len(parts) == 2:
                name, ext = parts
                max_name_length = max_component_length - len(ext.encode('utf-8')) - 1
                name = name.encode('utf-8')[:max_name_length].decode('utf-8', errors='ignore')
                filename = f"{name}.{ext}"
            else:
                filename = filename.encode('utf-8')[:max_component_length].decode('utf-8', errors='ignore')
        
        return filename
    
    def _extract_file_safely(self, zip_file: zipfile.ZipFile, info: zipfile.ZipInfo, dest_path: Path) -> None:
        """
        Extract a single file from ZIP with streaming for large files.
        
        Args:
            zip_file: Open ZipFile object
            info: ZipInfo for the file to extract
            dest_path: Destination path for extraction
        """
        # Use streaming extraction for large files to manage memory
        with zip_file.open(info) as source:
            with open(dest_path, 'wb') as target:
                while True:
                    chunk = source.read(self.chunk_size)
                    if not chunk:
                        break
                    target.write(chunk)
    
    def validate_zip_files(self, zip_paths: List[Path]) -> Dict[str, Any]:
        """
        Validate ZIP files before extraction.
        
        Args:
            zip_paths: List of ZIP file paths to validate
            
        Returns:
            Validation result with file counts, sizes, and any issues
        """
        validation_result = {
            'valid_files': [],
            'invalid_files': [],
            'total_files': 0,
            'total_size_bytes': 0,
            'warnings': [],
            'estimated_extraction_size': 0
        }
        
        for zip_path in zip_paths:
            try:
                if not zip_path.exists():
                    validation_result['invalid_files'].append({
                        'path': zip_path,
                        'error': 'File does not exist'
                    })
                    continue
                
                if not zipfile.is_zipfile(zip_path):
                    validation_result['invalid_files'].append({
                        'path': zip_path,
                        'error': 'Not a valid ZIP file'
                    })
                    continue
                
                # Test ZIP integrity and count contents
                file_count = 0
                uncompressed_size = 0
                
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    # Test ZIP integrity
                    bad_file = zf.testzip()
                    if bad_file:
                        validation_result['warnings'].append(
                            f"Corrupt file detected in {zip_path}: {bad_file}"
                        )
                    
                    # Count files and calculate sizes
                    for info in zf.infolist():
                        if not info.is_dir():
                            file_count += 1
                            uncompressed_size += info.file_size
                
                validation_result['valid_files'].append({
                    'path': zip_path,
                    'file_count': file_count,
                    'compressed_size': zip_path.stat().st_size,
                    'uncompressed_size': uncompressed_size
                })
                
                validation_result['total_files'] += file_count
                validation_result['total_size_bytes'] += zip_path.stat().st_size
                validation_result['estimated_extraction_size'] += uncompressed_size
                
            except Exception as e:
                validation_result['invalid_files'].append({
                    'path': zip_path,
                    'error': str(e)
                })
        
        return validation_result


def create_zip_extraction_service(chunk_size: int = 8192, max_size_gb: int = 50) -> ZipExtractionService:
    """
    Factory function to create a configured ZIP extraction service.
    
    Args:
        chunk_size: Chunk size for streaming extraction
        max_size_gb: Maximum total extraction size in GB
        
    Returns:
        Configured ZipExtractionService instance
    """
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024
    return ZipExtractionService(chunk_size=chunk_size, max_extract_size=max_size_bytes)