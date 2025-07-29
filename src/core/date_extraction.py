"""
Date Extraction Service
Handles extracting date/time information from media files and filenames
"""

import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dateutil import parser as date_parser


class DateExtractionService:
    """Service for extracting dates from media files and metadata"""
    
    # Common filename date patterns
    FILENAME_PATTERNS = [
        # Google Photos patterns
        (r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', '%Y%m%d_%H%M%S'),  # 20210315_143022
        (r'IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', 'IMG_%Y%m%d_%H%M%S'),  # IMG_20210315_143022
        (r'VID_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', 'VID_%Y%m%d_%H%M%S'),  # VID_20210315_143022
        
        # General patterns
        (r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})', '%Y-%m-%d_%H-%M-%S'),  # 2021-03-15_14-30-22
        (r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})', '%Y-%m-%d %H:%M:%S'),  # 2021-03-15 14:30:22
        (r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})', '%Y%m%d_%H%M'),  # 20210315_1430
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # 2021-03-15
        (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),  # 20210315
        
        # Phone patterns
        (r'Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', 'Screenshot_%Y-%m-%d-%H-%M-%S'),
        (r'WhatsApp Image (\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})', 'WhatsApp Image %Y-%m-%d at %H.%M.%S'),
        
        # Camera patterns
        (r'DSC(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', 'DSC%Y%m%d%H%M%S'),
        (r'P(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', 'P%Y%m%d_%H%M%S'),
    ]
    
    def __init__(self, logger):
        self.logger = logger
    
    def extract_date_from_file(self, file_path: Path, guess_from_name: bool = True) -> Optional[datetime]:
        """
        Extract date from file using multiple methods
        
        Priority order:
        1. JSON metadata file (if exists)
        2. EXIF data (for images)
        3. Filename pattern matching (if enabled)
        4. File modification time (fallback)
        
        Args:
            file_path: Path to the media file
            guess_from_name: Whether to try extracting date from filename
            
        Returns:
            datetime object or None if no date found
        """
        # Method 1: Try JSON metadata file
        json_date = self._extract_from_json_metadata(file_path)
        if json_date:
            self.logger.debug(f"Found date from JSON metadata for {file_path.name}: {json_date}")
            return json_date
        
        # Method 2: Try EXIF data for images
        exif_date = self._extract_from_exif(file_path)
        if exif_date:
            self.logger.debug(f"Found date from EXIF for {file_path.name}: {exif_date}")
            return exif_date
        
        # Method 3: Try filename pattern matching
        if guess_from_name:
            filename_date = self._extract_from_filename(file_path)
            if filename_date:
                self.logger.debug(f"Found date from filename for {file_path.name}: {filename_date}")
                return filename_date
        
        # Method 4: Fallback to file modification time
        try:
            mtime = file_path.stat().st_mtime
            fallback_date = datetime.fromtimestamp(mtime, tz=timezone.utc)
            self.logger.debug(f"Using file mtime for {file_path.name}: {fallback_date}")
            return fallback_date
        except Exception as e:
            self.logger.warning(f"Could not get file mtime for {file_path}: {e}")
            return None
    
    def _extract_from_json_metadata(self, file_path: Path) -> Optional[datetime]:
        """Extract date from accompanying JSON metadata file"""
        # Look for .json file with same name
        json_path = file_path.with_suffix(file_path.suffix + '.json')
        if not json_path.exists():
            # Try without original extension
            json_path = file_path.with_suffix('.json')
            if not json_path.exists():
                return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Try different timestamp fields
            timestamp_fields = [
                'photoTakenTime.timestamp',
                'creationTime.timestamp', 
                'modificationTime.timestamp',
                'timestamp'
            ]
            
            for field in timestamp_fields:
                timestamp = self._get_nested_field(metadata, field)
                if timestamp:
                    try:
                        # Handle different timestamp formats
                        if isinstance(timestamp, str):
                            # ISO format
                            return date_parser.parse(timestamp)
                        elif isinstance(timestamp, (int, float)):
                            # Unix timestamp
                            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    except Exception as e:
                        self.logger.debug(f"Could not parse timestamp {timestamp} from {field}: {e}")
                        continue
            
            # Try photoTakenTime object
            photo_taken = metadata.get('photoTakenTime', {})
            if isinstance(photo_taken, dict):
                timestamp = photo_taken.get('timestamp')
                if timestamp:
                    try:
                        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    except Exception:
                        pass
            
        except Exception as e:
            self.logger.debug(f"Could not read JSON metadata from {json_path}: {e}")
        
        return None
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field from dictionary using dot notation"""
        fields = field_path.split('.')
        current = data
        
        for field in fields:
            if isinstance(current, dict) and field in current:
                current = current[field]
            else:
                return None
        
        return current
    
    def _extract_from_exif(self, file_path: Path) -> Optional[datetime]:
        """Extract date from EXIF data"""
        try:
            from PIL import Image, ExifTags
            
            # Only process image files
            if not self._is_image_file(file_path):
                return None
            
            with Image.open(file_path) as img:
                exif_dict = img.getexif()
                if not exif_dict:
                    return None
                
                # Look for datetime fields in priority order
                datetime_tags = [
                    'DateTimeOriginal',
                    'DateTimeDigitized', 
                    'DateTime'
                ]
                
                for tag_name in datetime_tags:
                    tag_id = None
                    for tag, name in ExifTags.TAGS.items():
                        if name == tag_name:
                            tag_id = tag
                            break
                    
                    if tag_id and tag_id in exif_dict:
                        date_str = exif_dict[tag_id]
                        try:
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except Exception as e:
                            self.logger.debug(f"Could not parse EXIF date {date_str}: {e}")
                            continue
            
        except ImportError:
            self.logger.debug("PIL not available for EXIF extraction")
        except Exception as e:
            self.logger.debug(f"Could not read EXIF from {file_path}: {e}")
        
        return None
    
    def _extract_from_filename(self, file_path: Path) -> Optional[datetime]:
        """Extract date from filename using pattern matching"""
        filename = file_path.name
        
        for pattern, format_str in self.FILENAME_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    # Extract matched groups and format them
                    groups = match.groups()
                    
                    # Handle different pattern types
                    if len(groups) >= 6:  # Full datetime
                        year, month, day, hour, minute, second = groups[:6]
                        date_str = f"{year}{month}{day}_{hour}{minute}{second}"
                        return datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    elif len(groups) >= 5:  # No seconds
                        year, month, day, hour, minute = groups[:5]
                        date_str = f"{year}{month}{day}_{hour}{minute}"
                        return datetime.strptime(date_str, '%Y%m%d_%H%M')
                    elif len(groups) >= 3:  # Date only
                        year, month, day = groups[:3]
                        date_str = f"{year}{month}{day}"
                        return datetime.strptime(date_str, '%Y%m%d')
                
                except Exception as e:
                    self.logger.debug(f"Could not parse filename date from {filename} with pattern {pattern}: {e}")
                    continue
        
        return None
    
    def _is_image_file(self, file_path: Path) -> bool:
        """Check if file is an image"""
        image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            '.webp', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw'
        }
        return file_path.suffix.lower() in image_extensions
    
    def extract_creation_time_from_json(self, file_path: Path) -> Optional[Tuple[datetime, datetime]]:
        """
        Extract both photo taken time and creation time from JSON
        
        Returns:
            Tuple of (photo_taken_time, creation_time) or None
        """
        json_path = file_path.with_suffix(file_path.suffix + '.json')
        if not json_path.exists():
            json_path = file_path.with_suffix('.json')
            if not json_path.exists():
                return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            photo_taken = None
            creation_time = None
            
            # Extract photo taken time
            photo_taken_data = metadata.get('photoTakenTime', {})
            if isinstance(photo_taken_data, dict):
                timestamp = photo_taken_data.get('timestamp')
                if timestamp:
                    try:
                        photo_taken = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    except Exception:
                        pass
            
            # Extract creation time
            creation_data = metadata.get('creationTime', {})
            if isinstance(creation_data, dict):
                timestamp = creation_data.get('timestamp')
                if timestamp:
                    try:
                        creation_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    except Exception:
                        pass
            
            if photo_taken and creation_time:
                return (photo_taken, creation_time)
        
        except Exception as e:
            self.logger.debug(f"Could not extract times from JSON {json_path}: {e}")
        
        return None