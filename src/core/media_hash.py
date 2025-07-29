"""
Media Hash Service
Handles content-based hashing for duplicate detection with LRU cache
"""

import hashlib
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
import logging


class MediaHashService:
    """
    Service for calculating and caching file content hashes
    
    Features:
    - Stream-based SHA256 hashing for large files
    - LRU cache with file modification time validation
    - Thread-safe operations
    - Performance adaptive chunk sizes
    """
    
    def __init__(self, logger: logging.Logger, cache_size: int = 10000):
        self.logger = logger
        self.cache_size = cache_size
        self.cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()  # file_path -> (hash, mtime)
        self.cache_lock = threading.Lock()
        
        # Performance settings
        self.large_file_threshold = 50 * 1024 * 1024  # 50MB
        self.chunk_size_small = 64 * 1024  # 64KB for smaller files
        self.chunk_size_large = 1024 * 1024  # 1MB for larger files
        
        # Statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'files_hashed': 0,
            'total_bytes_processed': 0,
            'large_files_processed': 0
        }
    
    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """
        Calculate SHA256 hash of a file with caching
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            SHA256 hash string or None if error
        """
        if not file_path.exists() or not file_path.is_file():
            return None
        
        file_path_str = str(file_path)
        
        try:
            # Get file modification time
            stat = file_path.stat()
            current_mtime = stat.st_mtime
            file_size = stat.st_size
            
            # Check cache first
            with self.cache_lock:
                if file_path_str in self.cache:
                    cached_hash, cached_mtime = self.cache[file_path_str]
                    
                    # Validate cache entry with modification time
                    if abs(cached_mtime - current_mtime) < 1.0:  # Allow 1 second tolerance
                        # Move to end (most recently used)
                        del self.cache[file_path_str]
                        self.cache[file_path_str] = (cached_hash, cached_mtime)
                        self.stats['cache_hits'] += 1
                        return cached_hash
                    else:
                        # Cache entry is stale, remove it
                        del self.cache[file_path_str]
            
            # Cache miss, calculate hash
            self.stats['cache_misses'] += 1
            file_hash = self._calculate_hash_streaming(file_path, file_size)
            
            if file_hash:
                # Add to cache
                with self.cache_lock:
                    # Remove oldest entries if cache is full
                    while len(self.cache) >= self.cache_size:
                        self.cache.popitem(last=False)  # Remove oldest (FIFO)
                    
                    self.cache[file_path_str] = (file_hash, current_mtime)
                
                self.stats['files_hashed'] += 1
                self.stats['total_bytes_processed'] += file_size
                
                if file_size > self.large_file_threshold:
                    self.stats['large_files_processed'] += 1
            
            return file_hash
            
        except Exception as e:
            self.logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return None
    
    def _calculate_hash_streaming(self, file_path: Path, file_size: int) -> Optional[str]:
        """
        Calculate hash using streaming to handle large files efficiently
        
        Args:
            file_path: Path to file
            file_size: Size of file in bytes
            
        Returns:
            SHA256 hash string or None if error
        """
        try:
            hasher = hashlib.sha256()
            
            # Choose chunk size based on file size
            chunk_size = (self.chunk_size_large if file_size > self.large_file_threshold 
                         else self.chunk_size_small)
            
            start_time = time.time()
            bytes_read = 0
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    hasher.update(chunk)
                    bytes_read += len(chunk)
                    
                    # Log progress for very large files
                    if file_size > self.large_file_threshold and bytes_read % (10 * 1024 * 1024) == 0:
                        progress = (bytes_read / file_size) * 100
                        elapsed = time.time() - start_time
                        speed = bytes_read / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        self.logger.debug(f"Hashing {file_path.name}: {progress:.1f}% ({speed:.1f} MB/s)")
            
            hash_str = hasher.hexdigest()
            
            # Log timing for large files
            elapsed = time.time() - start_time
            if file_size > self.large_file_threshold and elapsed > 1.0:
                speed = file_size / (1024 * 1024 * elapsed)
                self.logger.debug(f"Hashed {file_path.name} ({file_size/(1024*1024):.1f}MB) in {elapsed:.2f}s ({speed:.1f} MB/s)")
            
            return hash_str
            
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the hash cache"""
        with self.cache_lock:
            self.cache.clear()
        self.logger.info("Hash cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache and performance statistics"""
        with self.cache_lock:
            cache_size = len(self.cache)
        
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        hit_rate = (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_entries': cache_size,
            'cache_hit_rate_percent': hit_rate,
            'total_requests': total_requests,
            'files_hashed': self.stats['files_hashed'],
            'total_bytes_processed': self.stats['total_bytes_processed'],
            'large_files_processed': self.stats['large_files_processed'],
            'total_gb_processed': self.stats['total_bytes_processed'] / (1024**3)
        }
    
    def validate_cache_entry(self, file_path: Path) -> bool:
        """
        Validate if a cache entry is still valid for a file
        
        Args:
            file_path: Path to check
            
        Returns:
            True if cache entry is valid, False otherwise
        """
        file_path_str = str(file_path)
        
        try:
            with self.cache_lock:
                if file_path_str not in self.cache:
                    return False
                
                cached_hash, cached_mtime = self.cache[file_path_str]
                current_mtime = file_path.stat().st_mtime
                
                return abs(cached_mtime - current_mtime) < 1.0
                
        except Exception:
            return False
    
    def precompute_hashes(self, file_paths: list[Path], progress_callback=None) -> Dict[Path, Optional[str]]:
        """
        Precompute hashes for a list of files with optional progress callback
        
        Args:
            file_paths: List of file paths to hash
            progress_callback: Optional callback function(current, total, file_path)
            
        Returns:
            Dictionary mapping file paths to their hashes
        """
        results = {}
        total_files = len(file_paths)
        
        self.logger.info(f"Precomputing hashes for {total_files} files...")
        
        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress_callback(i + 1, total_files, file_path)
            
            hash_result = self.calculate_file_hash(file_path)
            results[file_path] = hash_result
            
            if (i + 1) % 100 == 0 or i == total_files - 1:
                self.logger.info(f"Precomputed hashes: {i + 1}/{total_files} files")
        
        return results