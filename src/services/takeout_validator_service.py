"""
Takeout Validator Service

This service validates Google Takeout directory structures and provides
helpful guidance for users when their input doesn't match expected patterns.

Features:
- Smart Takeout folder detection
- Year folder validation ("Photos from YYYY" pattern)
- Album folder recognition
- Content analysis and recommendations
- Detailed validation reports with user guidance

Based on Dart reference: dart-version/lib/core/api/gpth_core_api.dart
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class FolderAnalysis:
    """Analysis result for a directory structure."""
    path: Path
    folder_type: str  # 'takeout', 'year', 'album', 'unknown', 'media'
    year: Optional[int] = None
    contains_media: bool = False
    media_count: int = 0
    subfolder_count: int = 0
    confidence_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result for input structure."""
    is_valid_takeout: bool
    recommended_input_path: Optional[Path]
    structure_type: str  # 'full_takeout', 'photos_only', 'partial', 'invalid'
    year_folders: List[FolderAnalysis]
    album_folders: List[FolderAnalysis]
    total_media_files: int
    estimated_size_mb: float
    validation_score: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    user_guidance: str = ""


@dataclass
class ContentAnalysis:
    """Analysis of content types and sizes."""
    image_files: int = 0
    video_files: int = 0
    json_metadata_files: int = 0
    other_files: int = 0
    total_size_bytes: int = 0
    largest_files: List[Tuple[Path, int]] = field(default_factory=list)
    file_extensions: Set[str] = field(default_factory=set)


class TakeoutValidationService:
    """
    Service for validating and analyzing Google Takeout directory structures.
    
    Provides intelligent validation with specific guidance for common issues
    and recommendations for optimal processing paths.
    """
    
    # Common Google Photos year folder patterns
    YEAR_FOLDER_PATTERNS = [
        r'^Photos from (\d{4})$',
        r'^(\d{4})$',
        r'^Photos (\d{4})$',
        r'^Google Photos (\d{4})$'
    ]
    
    # Media file extensions
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.webp', '.heic', '.heif', '.raw', '.cr2', '.nef', '.dng'
    }
    
    VIDEO_EXTENSIONS = {
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp',
        '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts', '.mts'
    }
    
    # Google-specific extensions
    GOOGLE_EXTENSIONS = {
        '.mp', '.mv'  # Pixel motion photos
    }
    
    # Takeout folder indicators
    TAKEOUT_INDICATORS = {
        'Google Photos',
        'Takeout',
        'Photos from',
        'archive_browser.html'
    }
    
    ALBUM_KEYWORDS = {
        'album', 'Album', 'ALBUM',
        'favorites', 'Favorites', 'FAVORITES',
        'shared', 'Shared', 'SHARED',
        'library', 'Library', 'LIBRARY'
    }
    
    def __init__(self, scan_depth_limit: int = 5, max_files_to_scan: int = 10000):
        """
        Initialize validation service.
        
        Args:
            scan_depth_limit: Maximum directory depth to scan
            max_files_to_scan: Maximum number of files to analyze for performance
        """
        self.scan_depth_limit = scan_depth_limit
        self.max_files_to_scan = max_files_to_scan
        self.media_extensions = self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS | self.GOOGLE_EXTENSIONS
    
    def validate_takeout_structure(self, input_path: Path) -> ValidationResult:
        """
        Perform comprehensive validation of a potential Takeout directory.
        
        Args:
            input_path: Path to validate
            
        Returns:
            ValidationResult with detailed analysis and recommendations
        """
        logger.info(f"Validating Takeout structure at: {input_path}")
        
        if not input_path.exists():
            return ValidationResult(
                is_valid_takeout=False,
                recommended_input_path=None,
                structure_type='invalid',
                year_folders=[],
                album_folders=[],
                total_media_files=0,
                estimated_size_mb=0.0,
                validation_score=0.0,
                issues=[f"Path does not exist: {input_path}"],
                user_guidance="Please check the path and ensure it exists and is accessible."
            )
        
        if not input_path.is_dir():
            return ValidationResult(
                is_valid_takeout=False,
                recommended_input_path=None,
                structure_type='invalid',
                year_folders=[],
                album_folders=[],
                total_media_files=0,
                estimated_size_mb=0.0,
                validation_score=0.0,
                issues=[f"Path is not a directory: {input_path}"],
                user_guidance="Please select a directory containing extracted Google Takeout files."
            )
        
        # Analyze the directory structure
        folder_analysis = self._analyze_folder_structure(input_path)
        content_analysis = self._analyze_content(input_path)
        
        # Determine the best structure type and recommendations
        structure_type, recommended_path = self._determine_structure_type(input_path, folder_analysis)
        
        # Calculate validation score
        validation_score = self._calculate_validation_score(folder_analysis, content_analysis, structure_type)
        
        # Generate user guidance
        guidance = self._generate_user_guidance(structure_type, folder_analysis, content_analysis)
        
        # Extract year and album folders
        year_folders = [f for f in folder_analysis if f.folder_type == 'year']
        album_folders = [f for f in folder_analysis if f.folder_type == 'album']
        
        # Determine if this is a valid takeout based on score and content
        is_valid = validation_score >= 0.5 and content_analysis.image_files + content_analysis.video_files > 0
        
        # Collect issues and recommendations
        issues = []
        warnings = []
        recommendations = []
        
        for folder in folder_analysis:
            issues.extend(folder.issues)
            recommendations.extend(folder.suggestions)
        
        if content_analysis.image_files + content_analysis.video_files == 0:
            issues.append("No media files found in the directory structure")
        
        if validation_score < 0.3:
            warnings.append("Directory structure doesn't match typical Google Takeout format")
        
        return ValidationResult(
            is_valid_takeout=is_valid,
            recommended_input_path=recommended_path,
            structure_type=structure_type,
            year_folders=year_folders,
            album_folders=album_folders,
            total_media_files=content_analysis.image_files + content_analysis.video_files,
            estimated_size_mb=content_analysis.total_size_bytes / (1024 * 1024),
            validation_score=validation_score,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            user_guidance=guidance
        )
    
    def quick_validate(self, input_path: Path) -> bool:
        """
        Quick validation check for basic Takeout structure.
        
        Args:
            input_path: Path to check
            
        Returns:
            True if appears to be a valid Takeout structure
        """
        try:
            if not input_path.exists() or not input_path.is_dir():
                return False
            
            # Check for obvious Takeout indicators
            folder_name = input_path.name.lower()
            if 'takeout' in folder_name or 'google' in folder_name:
                return True
            
            # Look for typical Takeout subfolders
            for item in input_path.iterdir():
                if item.is_dir():
                    item_name = item.name
                    if any(indicator in item_name for indicator in self.TAKEOUT_INDICATORS):
                        return True
                    
                    # Check for year folders
                    for pattern in self.YEAR_FOLDER_PATTERNS:
                        if re.match(pattern, item_name):
                            return True
            
            # Check for media files in immediate subdirectories
            media_count = 0
            for item in input_path.rglob('*'):
                if item.suffix.lower() in self.media_extensions:
                    media_count += 1
                    if media_count >= 5:  # Found enough media files
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Quick validation failed for {input_path}: {e}")
            return False
    
    def find_takeout_root(self, search_path: Path) -> Optional[Path]:
        """
        Search for the actual Takeout root directory within a given path.
        
        Args:
            search_path: Path to search within
            
        Returns:
            Path to detected Takeout root, or None if not found
        """
        candidates = []
        
        # Check current directory first
        if self.quick_validate(search_path):
            candidates.append((search_path, 1.0))
        
        # Look in subdirectories
        try:
            for item in search_path.iterdir():
                if item.is_dir():
                    # Check for typical Takeout folder names
                    score = 0.0
                    name_lower = item.name.lower()
                    
                    if 'takeout' in name_lower:
                        score += 0.8
                    if 'google' in name_lower:
                        score += 0.6
                    if 'photos' in name_lower:
                        score += 0.4
                    
                    # Check if it contains typical structure
                    if self.quick_validate(item):
                        score += 0.5
                    
                    if score > 0.5:
                        candidates.append((item, score))
        
        except PermissionError:
            logger.warning(f"Permission denied scanning {search_path}")
            return None
        
        # Return the highest-scoring candidate
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _analyze_folder_structure(self, root_path: Path, depth: int = 0) -> List[FolderAnalysis]:
        """
        Recursively analyze folder structure to identify patterns.
        
        Args:
            root_path: Root directory to analyze
            depth: Current recursion depth
            
        Returns:
            List of FolderAnalysis objects
        """
        results = []
        
        if depth > self.scan_depth_limit:
            return results
        
        try:
            for item in root_path.iterdir():
                if item.is_dir():
                    analysis = self._analyze_single_folder(item, depth)
                    results.append(analysis)
                    
                    # Recurse into subdirectories
                    if depth < self.scan_depth_limit:
                        sub_results = self._analyze_folder_structure(item, depth + 1)
                        results.extend(sub_results)
        
        except PermissionError:
            logger.warning(f"Permission denied accessing {root_path}")
        
        return results
    
    def _analyze_single_folder(self, folder_path: Path, depth: int) -> FolderAnalysis:
        """
        Analyze a single folder to determine its type and characteristics.
        
        Args:
            folder_path: Folder to analyze
            depth: Directory depth
            
        Returns:
            FolderAnalysis object
        """
        folder_name = folder_path.name
        analysis = FolderAnalysis(path=folder_path, folder_type='unknown')
        
        # Check for year folder patterns
        for pattern in self.YEAR_FOLDER_PATTERNS:
            match = re.match(pattern, folder_name)
            if match:
                analysis.folder_type = 'year'
                analysis.year = int(match.group(1))
                analysis.confidence_score = 0.9
                break
        
        # Check for Takeout indicators
        if analysis.folder_type == 'unknown':
            for indicator in self.TAKEOUT_INDICATORS:
                if indicator in folder_name:
                    analysis.folder_type = 'takeout'
                    analysis.confidence_score = 0.8
                    break
        
        # Check for album indicators
        if analysis.folder_type == 'unknown':
            for keyword in self.ALBUM_KEYWORDS:
                if keyword in folder_name:
                    analysis.folder_type = 'album'
                    analysis.confidence_score = 0.7
                    break
        
        # Analyze contents
        try:
            media_count = 0
            subfolder_count = 0
            
            for item in folder_path.iterdir():
                if item.is_dir():
                    subfolder_count += 1
                elif item.suffix.lower() in self.media_extensions:
                    media_count += 1
            
            analysis.contains_media = media_count > 0
            analysis.media_count = media_count
            analysis.subfolder_count = subfolder_count
            
            # Adjust confidence based on content
            if media_count > 0:
                analysis.confidence_score += 0.2
            if subfolder_count > 0 and analysis.folder_type in ['takeout', 'year']:
                analysis.confidence_score += 0.1
            
            # If it contains media but no specific type detected, classify as media folder
            if analysis.folder_type == 'unknown' and media_count > 0:
                analysis.folder_type = 'media'
                analysis.confidence_score = 0.5
        
        except PermissionError:
            analysis.issues.append("Permission denied - cannot access folder contents")
            analysis.confidence_score = 0.0
        
        # Add suggestions based on analysis
        self._add_folder_suggestions(analysis)
        
        return analysis
    
    def _analyze_content(self, root_path: Path) -> ContentAnalysis:
        """
        Analyze file content within the directory structure.
        
        Args:
            root_path: Root directory to analyze
            
        Returns:
            ContentAnalysis with file type counts and sizes
        """
        analysis = ContentAnalysis()
        files_scanned = 0
        
        try:
            for file_path in root_path.rglob('*'):
                if files_scanned >= self.max_files_to_scan:
                    break
                
                if file_path.is_file():
                    files_scanned += 1
                    ext = file_path.suffix.lower()
                    analysis.file_extensions.add(ext)
                    
                    try:
                        file_size = file_path.stat().st_size
                        analysis.total_size_bytes += file_size
                        
                        # Track largest files
                        if len(analysis.largest_files) < 10:
                            analysis.largest_files.append((file_path, file_size))
                        else:
                            # Keep only the largest files
                            smallest_large = min(analysis.largest_files, key=lambda x: x[1])
                            if file_size > smallest_large[1]:
                                analysis.largest_files.remove(smallest_large)
                                analysis.largest_files.append((file_path, file_size))
                        
                        # Categorize file types
                        if ext in self.IMAGE_EXTENSIONS or ext in self.GOOGLE_EXTENSIONS:
                            analysis.image_files += 1
                        elif ext in self.VIDEO_EXTENSIONS:
                            analysis.video_files += 1
                        elif ext == '.json':
                            analysis.json_metadata_files += 1
                        else:
                            analysis.other_files += 1
                    
                    except (OSError, PermissionError):
                        analysis.other_files += 1
        
        except Exception as e:
            logger.warning(f"Content analysis failed: {e}")
        
        # Sort largest files by size
        analysis.largest_files.sort(key=lambda x: x[1], reverse=True)
        
        return analysis
    
    def _determine_structure_type(self, input_path: Path, 
                                 folder_analysis: List[FolderAnalysis]) -> Tuple[str, Optional[Path]]:
        """
        Determine the type of structure and recommend the best input path.
        
        Args:
            input_path: Original input path
            folder_analysis: Analysis of folder structure
            
        Returns:
            Tuple of (structure_type, recommended_path)
        """
        # Count different folder types
        takeout_folders = [f for f in folder_analysis if f.folder_type == 'takeout']
        year_folders = [f for f in folder_analysis if f.folder_type == 'year']
        album_folders = [f for f in folder_analysis if f.folder_type == 'album']
        media_folders = [f for f in folder_analysis if f.folder_type == 'media']
        
        # Determine structure type
        if takeout_folders and year_folders:
            structure_type = 'full_takeout'
            # Recommend the deepest takeout folder that contains year folders
            recommended_path = takeout_folders[0].path
        elif year_folders:
            structure_type = 'photos_only'
            # Find the parent of year folders
            recommended_path = year_folders[0].path.parent
        elif album_folders or media_folders:
            structure_type = 'partial'
            recommended_path = input_path
        else:
            structure_type = 'invalid'
            recommended_path = None
        
        return structure_type, recommended_path
    
    def _calculate_validation_score(self, folder_analysis: List[FolderAnalysis],
                                  content_analysis: ContentAnalysis, structure_type: str) -> float:
        """Calculate overall validation score from 0.0 to 1.0."""
        score = 0.0
        
        # Base score from structure type
        structure_scores = {
            'full_takeout': 1.0,
            'photos_only': 0.8,
            'partial': 0.6,
            'invalid': 0.0
        }
        score += structure_scores.get(structure_type, 0.0) * 0.4
        
        # Score from folder analysis
        if folder_analysis:
            avg_confidence = sum(f.confidence_score for f in folder_analysis) / len(folder_analysis)
            score += avg_confidence * 0.3
        
        # Score from content analysis
        total_media = content_analysis.image_files + content_analysis.video_files
        if total_media > 0:
            score += 0.2
            if total_media > 100:
                score += 0.1  # Bonus for significant content
        
        return min(score, 1.0)
    
    def _generate_user_guidance(self, structure_type: str, folder_analysis: List[FolderAnalysis],
                               content_analysis: ContentAnalysis) -> str:
        """Generate helpful guidance text for the user."""
        if structure_type == 'full_takeout':
            return (
                "✅ Valid Google Takeout structure detected. "
                f"Found {len([f for f in folder_analysis if f.folder_type == 'year'])} year folders "
                f"with {content_analysis.image_files + content_analysis.video_files} media files. "
                "Ready for processing."
            )
        elif structure_type == 'photos_only':
            return (
                "📁 Google Photos folder structure detected. "
                f"Found {len([f for f in folder_analysis if f.folder_type == 'year'])} year folders. "
                "This appears to be the Photos section of a Google Takeout."
            )
        elif structure_type == 'partial':
            return (
                "⚠️ Partial or unusual folder structure detected. "
                f"Found {content_analysis.image_files + content_analysis.video_files} media files. "
                "Processing may work but results could be incomplete."
            )
        else:
            return (
                "❌ This doesn't appear to be a Google Takeout structure. "
                "Please ensure you've extracted the ZIP files and selected the correct folder. "
                "Look for folders named 'Takeout', 'Google Photos', or 'Photos from YYYY'."
            )
    
    def _add_folder_suggestions(self, analysis: FolderAnalysis) -> None:
        """Add specific suggestions based on folder analysis."""
        if analysis.folder_type == 'year' and analysis.media_count == 0:
            analysis.suggestions.append(
                f"Year folder '{analysis.path.name}' contains no media files. "
                "Check if this is the correct folder or if extraction was incomplete."
            )
        
        if analysis.folder_type == 'unknown' and analysis.media_count > 0:
            analysis.suggestions.append(
                f"Folder '{analysis.path.name}' contains {analysis.media_count} media files "
                "but doesn't match typical Takeout patterns. It may still be processable."
            )
        
        if analysis.confidence_score < 0.5:
            analysis.suggestions.append(
                "Consider checking if this folder is part of a larger Takeout structure."
            )


def create_takeout_validator() -> TakeoutValidationService:
    """Factory function to create a configured TakeoutValidationService."""
    return TakeoutValidationService()