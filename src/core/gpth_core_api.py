"""
Google Photos Takeout Helper - Core API
Python implementation of the main processing functionality
"""

import os
import json
import logging
import hashlib
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from dateutil import parser as date_parser
from tqdm import tqdm

class AlbumMode(Enum):
    """Album handling modes"""
    SHORTCUT = "shortcut"
    DUPLICATE_COPY = "duplicate-copy"
    REVERSE_SHORTCUT = "reverse-shortcut"
    JSON = "json"
    NOTHING = "nothing"

class ExtensionFixMode(Enum):
    """Extension fixing modes"""
    NONE = "none"
    STANDARD = "standard"
    CONSERVATIVE = "conservative"
    SOLO = "solo"

class ProcessingStep(Enum):
    FIX_EXTENSIONS = 1
    DISCOVER_MEDIA = 2
    REMOVE_DUPLICATES = 3
    EXTRACT_DATES = 4
    WRITE_EXIF = 5
    FIND_ALBUMS = 6
    MOVE_FILES = 7
    UPDATE_CREATION_TIME = 8

@dataclass
class ProcessingConfig:
    """Configuration for processing operations"""
    input_path: str
    output_path: str
    album_mode: AlbumMode = AlbumMode.SHORTCUT
    date_division: int = 0  # 0=single folder, 1=year, 2=year/month, 3=year/month/day
    divide_partner_shared: bool = False
    skip_extras: bool = True
    write_exif: bool = True
    transform_pixel_mp: bool = False
    guess_from_name: bool = True
    update_creation_time: bool = False
    limit_filesize: bool = False
    extension_fix_mode: ExtensionFixMode = ExtensionFixMode.STANDARD
    verbose: bool = False
    fix_mode: bool = False
    dry_run: bool = False
    max_threads: int = 4

@dataclass
class ProcessingResult:
    """Results from processing operations"""
    success: bool
    total_files: int = 0
    processed_files: int = 0
    duplicates_removed: int = 0
    albums_found: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0

class GooglePhotosTakeoutHelper:
    """
    Main API class for Google Photos Takeout Helper functionality
    Provides clean interface for both CLI and GUI implementations
    """
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = self._setup_logging()
        self._progress_callback: Optional[Callable[[int, str, float], None]] = None
        self._cancel_requested = False
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('gpth')
        logger.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def set_progress_callback(self, callback: Callable[[int, str, float], None]) -> None:
        """Set progress callback for GUI updates"""
        self._progress_callback = callback
    
    def cancel_processing(self) -> None:
        """Request cancellation of current processing"""
        self._cancel_requested = True
    
    def _update_progress(self, step: int, message: str, progress: float = 0.0) -> None:
        """Update progress if callback is set"""
        if self._progress_callback:
            self._progress_callback(step, message, progress)
    
    def validate_paths(self) -> Tuple[bool, List[str]]:
        """Validate input and output paths"""
        errors = []
        
        input_path = Path(self.config.input_path)
        if not input_path.exists():
            errors.append(f"Input path does not exist: {input_path}")
        elif not input_path.is_dir():
            errors.append(f"Input path is not a directory: {input_path}")
            
        output_path = Path(self.config.output_path)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create output directory: {e}")
            
        return len(errors) == 0, errors
    
    def discover_takeout_structure(self) -> Dict[str, Any]:
        """Analyze the takeout structure and provide information"""
        input_path = Path(self.config.input_path)
        structure = {
            'total_files': 0,
            'media_files': 0,
            'json_files': 0,
            'folders': [],
            'has_photos': False,
            'has_albums': False,
            'estimated_processing_time': 0
        }
        
        self.logger.info("Discovering takeout structure...")
        
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw', '.mp4', '.mov', '.avi'}
        
        for root, dirs, files in os.walk(input_path):
            root_path = Path(root)
            try:
                rel_path = root_path.relative_to(input_path)
                
                if 'Photos from' in str(rel_path) or 'Google Photos' in str(rel_path):
                    structure['has_photos'] = True
                
                if 'album' in str(rel_path).lower():
                    structure['has_albums'] = True
                
                for file in files:
                    structure['total_files'] += 1
                    file_path = root_path / file
                    
                    if file_path.suffix.lower() in media_extensions:
                        structure['media_files'] += 1
                    elif file_path.suffix.lower() == '.json':
                        structure['json_files'] += 1
            except ValueError:
                # Handle cases where root_path is not relative to input_path
                continue
        
        # Estimate processing time (rough calculation)
        structure['estimated_processing_time'] = structure['media_files'] * 0.1  # 100ms per file
        
        self.logger.info(f"Found {structure['media_files']} media files and {structure['json_files']} metadata files")
        
        return structure
    
    def process_takeout(self) -> ProcessingResult:
        """Main processing function - orchestrates all steps using the new pipeline"""
        try:
            # Validate paths first
            valid, errors = self.validate_paths()
            if not valid:
                result = ProcessingResult(success=False)
                result.errors.extend(errors)
                return result
            
            # Create new pipeline and execute
            from .processing_pipeline import ProcessingPipeline
            pipeline = ProcessingPipeline(self.logger, self.config)
            
            # Set up progress callback if available
            if self._progress_callback:
                pipeline.set_progress_callback(self._progress_callback)
            
            # Execute pipeline
            pipeline_result = pipeline.execute(
                Path(self.config.input_path),
                Path(self.config.output_path)
            )
            
            # Convert pipeline result to legacy format
            return pipeline.convert_to_processing_result(pipeline_result)
            
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            result = ProcessingResult(success=False)
            result.errors.append(f"Processing failed: {str(e)}")
            return result
    
    def _fix_extensions(self) -> None:
        """Fix incorrect file extensions based on content"""
        self.logger.info("Fixing file extensions...")
        if not HAS_PIL:
            self.logger.warning("PIL not available, skipping extension fixing")
            return
            
        input_path = Path(self.config.input_path)
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and not file_path.suffix:
                try:
                    with Image.open(file_path) as img:
                        if img.format:
                            format_ext = {
                                'JPEG': '.jpg',
                                'PNG': '.png',
                                'GIF': '.gif',
                                'BMP': '.bmp',
                                'TIFF': '.tiff'
                            }.get(img.format, '.jpg')
                            
                            new_path = file_path.with_suffix(format_ext)
                            if not new_path.exists():
                                file_path.rename(new_path)
                                self.logger.debug(f"Renamed {file_path} to {new_path}")
                            
                except Exception:
                    # Not an image file or can't process, skip
                    continue
    
    def _discover_media_files(self) -> List[Path]:
        """Discover all media files in the input directory"""
        self.logger.info("Discovering media files...")
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw', '.mp4', '.mov', '.avi'}
        
        input_path = Path(self.config.input_path)
        media_files = []
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                media_files.append(file_path)
        
        self.logger.info(f"Found {len(media_files)} media files")
        return media_files
    
    def _remove_duplicates(self, media_files: List[Path]) -> Tuple[List[Path], List[Path]]:
        """Remove duplicate files based on content hash"""
        self.logger.info("Removing duplicates...")
        
        seen_hashes = {}
        unique_files = []
        duplicates = []
        
        for file_path in tqdm(media_files, desc="Checking duplicates", disable=not self.config.verbose):
            try:
                # Calculate file hash
                hasher = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                
                if file_hash in seen_hashes:
                    duplicates.append(file_path)
                    self.logger.debug(f"Duplicate found: {file_path}")
                else:
                    seen_hashes[file_hash] = file_path
                    unique_files.append(file_path)
                    
            except Exception as e:
                self.logger.warning(f"Could not process {file_path}: {e}")
                unique_files.append(file_path)  # Keep file if we can't check it
        
        self.logger.info(f"Removed {len(duplicates)} duplicates")
        return unique_files, duplicates
    
    def _extract_dates(self, media_files: List[Path]) -> Dict[Path, Optional[datetime]]:
        """Extract dates from EXIF, JSON metadata, or filename"""
        self.logger.info("Extracting dates...")
        file_dates = {}
        
        for file_path in tqdm(media_files, desc="Extracting dates", disable=not self.config.verbose):
            date_taken = None
            
            try:
                # Try EXIF data first
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.tiff']:
                    date_taken = self._extract_date_from_exif(file_path)
                
                # Try JSON metadata
                if not date_taken:
                    date_taken = self._extract_date_from_json(file_path)
                
                # Try filename
                if not date_taken:
                    date_taken = self._extract_date_from_filename(file_path)
                
                file_dates[file_path] = date_taken
                
            except Exception as e:
                self.logger.warning(f"Could not extract date from {file_path}: {e}")
                file_dates[file_path] = None
        
        return file_dates
    
    def _extract_date_from_exif(self, file_path: Path) -> Optional[datetime]:
        """Extract date from EXIF data"""
        if not HAS_PIL:
            return None
            
        try:
            with Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag == 'DateTime':
                            return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass
        return None
    
    def _extract_date_from_json(self, file_path: Path) -> Optional[datetime]:
        """Extract date from accompanying JSON metadata file"""
        # Try multiple JSON file patterns
        json_candidates = [
            file_path.with_suffix(file_path.suffix + '.json'),
            file_path.with_suffix('.json'),
            file_path.parent / f"{file_path.stem}.json"
        ]
        
        for json_path in json_candidates:
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Try different timestamp fields
                    for field in ['photoTakenTime', 'creationTime', 'modificationTime']:
                        if field in metadata:
                            timestamp = metadata[field].get('timestamp', '')
                            if timestamp:
                                return datetime.fromtimestamp(int(timestamp))
                    
                except Exception as e:
                    self.logger.debug(f"Could not parse JSON metadata for {file_path}: {e}")
        
        return None
    
    def _extract_date_from_filename(self, file_path: Path) -> Optional[datetime]:
        """Extract date from filename patterns"""
        filename = file_path.stem
        
        # Common patterns
        patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{4})(\d{2})(\d{2})',    # YYYYMMDD
            r'IMG_(\d{4})(\d{2})(\d{2})', # IMG_YYYYMMDD
            r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})', # YYYY-MM-DD_HH-MM-SS
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 3:
                        year, month, day = groups[:3]
                        hour = int(groups[3]) if len(groups) > 3 else 0
                        minute = int(groups[4]) if len(groups) > 4 else 0
                        second = int(groups[5]) if len(groups) > 5 else 0
                        return datetime(int(year), int(month), int(day), hour, minute, second)
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _write_exif_data(self, media_files: List[Path], file_dates: Dict[Path, Optional[datetime]]) -> None:
        """Write EXIF data to files"""
        self.logger.info("Writing EXIF data...")
        
        for file_path in tqdm(media_files, desc="Writing EXIF", disable=not self.config.verbose):
            if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                try:
                    # This would implement EXIF writing logic
                    # For now, just log the action
                    date_taken = file_dates.get(file_path)
                    if date_taken:
                        self.logger.debug(f"Would write EXIF date {date_taken} for {file_path}")
                except Exception as e:
                    self.logger.warning(f"Could not write EXIF for {file_path}: {e}")
    
    def _find_albums(self) -> List[Dict[str, Any]]:
        """Find album information from JSON metadata"""
        self.logger.info("Finding albums...")
        albums = []
        
        input_path = Path(self.config.input_path)
        for json_file in input_path.rglob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'albumData' in data:
                    albums.append({
                        'name': data['albumData'].get('title', 'Unknown'),
                        'path': str(json_file.parent),
                        'files': data.get('mediaItems', [])
                    })
                    
            except Exception as e:
                self.logger.debug(f"Could not parse album data from {json_file}: {e}")
        
        self.logger.info(f"Found {len(albums)} albums")
        return albums
    
    def _move_files(self, media_files: List[Path], file_dates: Dict[Path, Optional[datetime]]) -> None:
        """Move files to organized directory structure using album mode strategies"""
        self.logger.info("Moving files...")
        # Find album information first
        albums_info = self._find_albums()
        # Store album info for JSON mode
        self._albums_for_json = {}
        
        # Process each file according to album mode
        for file_path in tqdm(media_files, desc="Moving files", disable=not self.config.verbose):
            try:
                date_taken = file_dates.get(file_path) or datetime.now()
                # Determine if this file is partner shared
                is_partner_shared = self._is_partner_shared_file(file_path)
                # Find which albums this file belongs to
                file_albums = self._get_file_albums(file_path, albums_info)
                
                # Process according to album mode
                if self.config.album_mode == AlbumMode.SHORTCUT:
                    self._process_shortcut_mode(file_path, date_taken, file_albums, is_partner_shared)
                elif self.config.album_mode == AlbumMode.DUPLICATE_COPY:
                    self._process_duplicate_copy_mode(file_path, date_taken, file_albums, is_partner_shared)
                elif self.config.album_mode == AlbumMode.REVERSE_SHORTCUT:
                    self._process_reverse_shortcut_mode(file_path, date_taken, file_albums, is_partner_shared)
                elif self.config.album_mode == AlbumMode.JSON:
                    self._process_json_mode(file_path, date_taken, file_albums, is_partner_shared)
                else:  # AlbumMode.NOTHING
                    self._process_nothing_mode(file_path, date_taken, is_partner_shared)
                    
            except Exception as e:
                self.logger.error(f"Could not move {file_path}: {e}")
        
        # Finalize any mode-specific operations
        if self.config.album_mode == AlbumMode.JSON:
            self._finalize_json_mode()
    
    def _update_creation_times(self, media_files: List[Path], file_dates: Dict[Path, Optional[datetime]]) -> None:
        """Update file creation times to match extracted dates"""
        self.logger.info("Updating file creation times...")
        
        for file_path in tqdm(media_files, desc="Updating timestamps", disable=not self.config.verbose):
            try:
                date_taken = file_dates.get(file_path)
                if date_taken:
                    timestamp = date_taken.timestamp()
                    os.utime(file_path, (timestamp, timestamp))
                    self.logger.debug(f"Updated timestamp for {file_path}")
            except Exception as e:
                self.logger.warning(f"Could not update timestamp for {file_path}: {e}")

    def validate_takeout_structure(self, input_path: str) -> Dict[str, Any]:
        """Validate Google Photos takeout structure"""
        input_dir = Path(input_path)
        
        if not input_dir.exists():
            return {
                'is_valid': False,
                'message': 'Directory does not exist',
                'details': []
            }
        
        details = []
        is_valid = True
        
        # Check for basic Google Photos structure
        directories = [p for p in input_dir.iterdir() if p.is_dir()]
        
        # Look for year folders (Photos from YYYY)
        year_folders = [d for d in directories
                       if 'photos from' in d.name.lower() and
                       re.search(r'20\d{2}', d.name)]
        
        if year_folders:
            details.append(f'Found {len(year_folders)} year folder(s)')
        else:
            details.append('No year folders found (Photos from YYYY)')
        
        # Look for album folders
        album_folders = [d for d in directories
                        if 'photos from' not in d.name.lower() and
                        not d.name.startswith('.') and
                        d.name.lower() not in ['archive', 'trash']]
        
        if album_folders:
            details.append(f'Found {len(album_folders)} potential album folder(s)')
        
        # Basic validation - need at least some folders
        if not year_folders and not album_folders:
            is_valid = False
            details.append('No recognizable Google Photos structure found')
        
        return {
            'is_valid': is_valid,
            'message': 'Valid Google Photos Takeout structure' if is_valid else 'Invalid structure',
            'details': details
        }
    
    def estimate_space_requirements(self, input_path: str) -> Dict[str, Any]:
        """Estimate disk space requirements for processing"""
        input_dir = Path(input_path)
        
        if not input_dir.exists():
            raise Exception('Input directory does not exist')
        
        total_size = 0
        file_count = 0
        
        for file_path in input_dir.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                    file_count += 1
                except OSError:
                    continue
        
        # Estimate additional space needed (conservative estimate)
        multiplier = 2.0 if self.config.album_mode != AlbumMode.NOTHING else 1.1
        estimated_space = int(total_size * multiplier)
        
        return {
            'current_size': total_size,
            'estimated_required_space': estimated_space,
            'file_count': file_count,
            'additional_space_needed': estimated_space - total_size,
            'space_multiplier': multiplier
        }
    
    def get_available_space(self, path: str) -> Optional[int]:
        """Get available storage space for a given path"""
        try:
            import shutil
            return shutil.disk_usage(path).free
        except Exception:
            return None
    
    def check_exiftool_status(self) -> Dict[str, Any]:
        """Check if ExifTool is available and working"""
        import subprocess
        
        try:
            result = subprocess.run(['exiftool', '-ver'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    'is_available': True,
                    'version': result.stdout.strip(),
                    'message': 'ExifTool is available and ready'
                }
            else:
                return {
                    'is_available': False,
                    'version': None,
                    'message': 'ExifTool found but not working properly'
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {
                'available': False,
                'version': None,
                'path': None,
                'message': 'ExifTool not found. Some features may be limited.'
            }
    
    def validate_takeout_structure(self) -> bool:
        """Validate that the input path contains a valid Google Photos Takeout structure"""
        result = self.check_takeout_structure(self.config.input_path)
        return result['is_valid']
    
    def estimate_space_requirements(self) -> Dict[str, Any]:
        """Estimate disk space requirements using the configured input path"""
        # Use the existing method with parameters
        input_path = Path(self.config.input_path)
        
        if not input_path.exists():
            raise Exception('Input directory does not exist')
        
        total_size = 0
        file_count = 0
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                    file_count += 1
                except OSError:
                    continue
        
        # Estimate additional space needed (conservative estimate)
        multiplier = 2.0 if self.config.album_mode != AlbumMode.NOTHING else 1.1
        estimated_space = int(total_size * multiplier)
        
        # Get available space
        available_space = self.get_available_space(str(input_path))
        
        return {
            'input_size_gb': total_size / (1024**3),
            'output_size_gb': estimated_space / (1024**3),
            'available_space_gb': available_space / (1024**3) if available_space else 0,
            'space_multiplier': multiplier,
            'warning': 'Insufficient space!' if available_space and estimated_space > available_space else None
        }
    
    def fix_dates_in_folder(self) -> ProcessingResult:
        """Fix dates in any folder (not just Takeout) - special mode"""
        start_time = datetime.now()
        result = ProcessingResult(success=False)
        
        try:
            self.logger.info(f"Fix mode: Processing folder {self.config.input_path}")
            
            # Discover media files
            self._update_progress(2, "Discovering media files...")
            media_files = self._discover_media_files()
            result.total_files = len(media_files)
            
            # Extract dates
            self._update_progress(4, "Extracting dates from metadata...")
            file_dates = self._extract_dates(media_files)
            
            # Write EXIF data
            if self.config.write_exif:
                self._update_progress(5, "Writing EXIF metadata...")
                self._write_exif_data(media_files, file_dates)
            
            # Update file timestamps
            if self.config.update_creation_time:
                self._update_progress(8, "Updating file timestamps...")
                self._update_file_timestamps(media_files, file_dates)
            
            result.success = True
            result.processed_files = len(media_files)
            
        except Exception as e:
            self.logger.error(f"Fix dates failed: {e}")
            result.errors.append(str(e))
        
        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def cancel(self):
        """Cancel the current processing operation"""
        self.cancel_processing()
    
    def _update_file_timestamps(self, media_files: List[Path], file_dates: Dict[Path, Optional[datetime]]):
        """Update file creation times based on extracted dates"""
        self.logger.info("Updating creation times...")
        
        for file_path in tqdm(media_files, desc="Updating timestamps", disable=not self.config.verbose):
            try:
                date_taken = file_dates.get(file_path)
                if date_taken and file_path.exists():
                    # Set file modification time
                    timestamp = date_taken.timestamp()
                    os.utime(file_path, (timestamp, timestamp))
                    self.logger.debug(f"Updated timestamp for {file_path}")
                        
            except Exception as e:
                self.logger.warning(f"Could not update timestamp for {file_path}: {e}")