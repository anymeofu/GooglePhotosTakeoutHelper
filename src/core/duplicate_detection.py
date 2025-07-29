"""
Duplicate Detection Service
Handles content-based duplicate file detection with size pre-filtering
"""

import time
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional, Any
from collections import defaultdict
import logging

from .media_hash import MediaHashService


class DuplicateDetectionService:
    """
    Service for detecting and managing duplicate files
    
    Features:
    - Size-based pre-filtering for performance
    - Content-based grouping using hash comparison
    - Memory-efficient batch processing
    - Detailed duplicate group analysis
    - Performance metrics and statistics
    """
    
    def __init__(self, logger: logging.Logger, hash_service: MediaHashService):
        self.logger = logger
        self.hash_service = hash_service
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'size_groups_created': 0,
            'hash_comparisons': 0,
            'duplicates_found': 0,
            'unique_files': 0,
            'size_filtering_saved_hashes': 0,
            'processing_time': 0.0
        }
    
    def find_duplicates(self, file_paths: List[Path]) -> Tuple[List[Path], List[Path]]:
        """
        Find duplicate files in a list, returning unique files and duplicates
        
        Args:
            file_paths: List of file paths to check for duplicates
            
        Returns:
            Tuple of (unique_files, duplicate_files)
        """
        start_time = time.time()
        self.logger.info(f"Starting duplicate detection for {len(file_paths)} files")
        
        # Reset statistics
        self.stats['files_processed'] = len(file_paths)
        
        # Step 1: Group files by size (fast pre-filtering)
        size_groups = self._group_by_size(file_paths)
        
        # Step 2: Process each size group for content duplicates
        unique_files = []
        duplicate_files = []
        
        for size, files_with_size in size_groups.items():
            if len(files_with_size) == 1:
                # No duplicates possible for this size
                unique_files.extend(files_with_size)
                self.stats['unique_files'] += 1
            else:
                # Check content hashes for files with same size
                group_unique, group_duplicates = self._find_duplicates_in_size_group(files_with_size)
                unique_files.extend(group_unique)
                duplicate_files.extend(group_duplicates)
                
                self.stats['unique_files'] += len(group_unique)
                self.stats['duplicates_found'] += len(group_duplicates)
        
        self.stats['processing_time'] = time.time() - start_time
        
        # Log results
        self.logger.info(f"Duplicate detection complete in {self.stats['processing_time']:.2f}s")
        self.logger.info(f"Found {len(duplicate_files)} duplicates, {len(unique_files)} unique files")
        self.logger.info(f"Size filtering saved {self.stats['size_filtering_saved_hashes']} hash calculations")
        
        return unique_files, duplicate_files
    
    def _group_by_size(self, file_paths: List[Path]) -> Dict[int, List[Path]]:
        """
        Group files by their size for efficient pre-filtering
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary mapping file size to list of files with that size
        """
        size_groups = defaultdict(list)
        
        for file_path in file_paths:
            try:
                if file_path.exists() and file_path.is_file():
                    file_size = file_path.stat().st_size
                    size_groups[file_size].append(file_path)
                else:
                    self.logger.warning(f"File not found or not accessible: {file_path}")
            except OSError as e:
                self.logger.warning(f"Could not get size for {file_path}: {e}")
        
        self.stats['size_groups_created'] = len(size_groups)
        
        # Calculate how many hash calculations we saved
        single_file_groups = sum(1 for files in size_groups.values() if len(files) == 1)
        self.stats['size_filtering_saved_hashes'] = single_file_groups
        
        self.logger.debug(f"Created {len(size_groups)} size groups, saved {single_file_groups} hash calculations")
        
        return size_groups
    
    def _find_duplicates_in_size_group(self, files_with_same_size: List[Path]) -> Tuple[List[Path], List[Path]]:
        """
        Find duplicates within a group of files that have the same size
        
        Args:
            files_with_same_size: List of files with identical file size
            
        Returns:
            Tuple of (unique_files, duplicate_files) within this size group
        """
        if len(files_with_same_size) <= 1:
            return files_with_same_size, []
        
        hash_groups = defaultdict(list)
        unique_files = []
        duplicate_files = []
        
        # Calculate hashes for all files in this size group
        for file_path in files_with_same_size:
            file_hash = self.hash_service.calculate_file_hash(file_path)
            
            if file_hash:
                hash_groups[file_hash].append(file_path)
                self.stats['hash_comparisons'] += 1
            else:
                # Could not hash file, treat as unique to be safe
                unique_files.append(file_path)
                self.logger.warning(f"Could not hash {file_path}, treating as unique")
        
        # Process hash groups to separate unique files from duplicates
        for file_hash, files_with_hash in hash_groups.items():
            if len(files_with_hash) == 1:
                # Unique file
                unique_files.extend(files_with_hash)
            else:
                # Duplicate group - keep the first file, mark others as duplicates
                unique_files.append(files_with_hash[0])  # Keep first occurrence
                duplicate_files.extend(files_with_hash[1:])  # Mark rest as duplicates
                
                self.logger.debug(f"Found duplicate group with {len(files_with_hash)} files (hash: {file_hash[:8]}...)")
        
        return unique_files, duplicate_files
    
    def group_identical_files(self, file_paths: List[Path]) -> List[List[Path]]:
        """
        Group files by identical content, returning groups of identical files
        
        Args:
            file_paths: List of file paths to group
            
        Returns:
            List of groups, where each group contains identical files
        """
        start_time = time.time()
        self.logger.info(f"Grouping {len(file_paths)} files by content")
        
        # Step 1: Group by size
        size_groups = self._group_by_size(file_paths)
        
        # Step 2: Group by content hash within each size group
        all_groups = []
        
        for size, files_with_size in size_groups.items():
            if len(files_with_size) == 1:
                # Single file group
                all_groups.append(files_with_size)
            else:
                # Multiple files with same size, group by hash
                hash_groups = defaultdict(list)
                
                for file_path in files_with_size:
                    file_hash = self.hash_service.calculate_file_hash(file_path)
                    if file_hash:
                        hash_groups[file_hash].append(file_path)
                    else:
                        # Could not hash, put in its own group
                        all_groups.append([file_path])
                
                # Add hash-based groups
                all_groups.extend(list(hash_groups.values()))
        
        processing_time = time.time() - start_time
        
        # Statistics
        total_groups = len(all_groups)
        duplicate_groups = len([g for g in all_groups if len(g) > 1])
        
        self.logger.info(f"Content grouping complete in {processing_time:.2f}s")
        self.logger.info(f"Created {total_groups} groups, {duplicate_groups} have duplicates")
        
        return all_groups
    
    def analyze_duplicates(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Perform comprehensive duplicate analysis
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with detailed analysis results
        """
        start_time = time.time()
        
        unique_files, duplicate_files = self.find_duplicates(file_paths)
        duplicate_groups = self.group_identical_files(file_paths)
        
        # Calculate space savings
        total_size = 0
        duplicate_size = 0
        
        for file_path in file_paths:
            try:
                if file_path.exists():
                    size = file_path.stat().st_size
                    total_size += size
                    if file_path in duplicate_files:
                        duplicate_size += size
            except OSError:
                continue
        
        # Group statistics
        groups_with_duplicates = [g for g in duplicate_groups if len(g) > 1]
        largest_duplicate_group = max(groups_with_duplicates, key=len, default=[])
        
        analysis_time = time.time() - start_time
        
        return {
            'total_files': len(file_paths),
            'unique_files': len(unique_files),
            'duplicate_files': len(duplicate_files),
            'duplicate_groups': len(groups_with_duplicates),
            'largest_group_size': len(largest_duplicate_group),
            'total_size_bytes': total_size,
            'duplicate_size_bytes': duplicate_size,
            'space_savings_bytes': duplicate_size,
            'space_savings_mb': duplicate_size / (1024 * 1024),
            'space_savings_percent': (duplicate_size / total_size * 100) if total_size > 0 else 0,
            'analysis_time_seconds': analysis_time,
            'performance_stats': self.stats
        }
    
    def find_similar_files(self, file_paths: List[Path], similarity_threshold: float = 0.95) -> List[List[Path]]:
        """
        Find files that are potentially similar (for future enhancement)
        
        Currently returns exact duplicates only. Could be extended with
        perceptual hashing or other similarity algorithms.
        
        Args:
            file_paths: List of file paths to check
            similarity_threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of groups of similar files
        """
        self.logger.info("Finding similar files (currently exact duplicates only)")
        
        # For now, just return exact duplicate groups
        # This could be enhanced with perceptual hashing for images/videos
        return self.group_identical_files(file_paths)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get duplicate detection statistics"""
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters"""
        for key in self.stats:
            if isinstance(self.stats[key], (int, float)):
                self.stats[key] = 0