"""
Album Detection Service
Handles detection and parsing of Google Photos album information
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict


class AlbumDetectionService:
    """Service for detecting albums and mapping files to albums"""
    
    def __init__(self, logger):
        self.logger = logger
        self._album_cache: Dict[str, List[str]] = {}
        self._file_to_albums: Dict[str, List[str]] = defaultdict(list)
    
    def discover_albums(self, input_path: Path) -> Dict[str, List[str]]:
        """
        Discover all albums in the takeout directory
        
        Args:
            input_path: Root path of Google Photos takeout
            
        Returns:
            Dictionary mapping album names to lists of file paths
        """
        self.logger.info("Discovering albums...")
        
        albums = {}
        
        # Method 1: Look for album folders with metadata
        album_folders = self._find_album_folders(input_path)
        for folder_path in album_folders:
            album_name = folder_path.name
            files = self._get_media_files_in_folder(folder_path)
            if files:
                albums[album_name] = files
                self.logger.debug(f"Found album folder '{album_name}' with {len(files)} files")
        
        # Method 2: Parse metadata.json files
        metadata_albums = self._parse_metadata_files(input_path)
        for album_name, files in metadata_albums.items():
            if album_name in albums:
                # Merge with existing album
                albums[album_name].extend(files)
                albums[album_name] = list(set(albums[album_name]))  # Remove duplicates
            else:
                albums[album_name] = files
            self.logger.debug(f"Found metadata album '{album_name}' with {len(files)} files")
        
        # Cache the results
        self._album_cache = albums
        
        # Build reverse mapping (file to albums)
        self._build_file_to_albums_mapping()
        
        self.logger.info(f"Discovered {len(albums)} albums with {sum(len(files) for files in albums.values())} file associations")
        
        return albums
    
    def get_albums_for_file(self, file_path: str) -> List[str]:
        """
        Get list of albums that contain the specified file
        
        Args:
            file_path: Path to the media file
            
        Returns:
            List of album names containing this file
        """
        # Normalize path for lookup
        normalized_path = str(Path(file_path).resolve())
        return self._file_to_albums.get(normalized_path, [])
    
    def _find_album_folders(self, input_path: Path) -> List[Path]:
        """Find potential album folders in takeout structure"""
        album_folders = []
        
        # Look for folders that might be albums
        # Google Photos typically has structure like:
        # - Google Photos/
        #   - Album Name/
        #     - photos...
        #   - Photos from 2021/
        #     - photos...
        
        if (input_path / "Google Photos").exists():
            google_photos_dir = input_path / "Google Photos"
            for item in google_photos_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Skip common non-album folders
                    if item.name not in ['Photos from 2019', 'Photos from 2020', 'Photos from 2021', 
                                       'Photos from 2022', 'Photos from 2023', 'Photos from 2024',
                                       'Archive', 'Trash']:
                        album_folders.append(item)
        
        # Also check root level for album folders
        for item in input_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Skip obvious non-album folders
                if item.name not in ['Google Photos', 'Takeout', 'Archive']:
                    has_media = any(self._is_media_file(f) for f in item.rglob('*') if f.is_file())
                    if has_media:
                        album_folders.append(item)
        
        return album_folders
    
    def _get_media_files_in_folder(self, folder_path: Path) -> List[str]:
        """Get list of media files in a folder"""
        media_files = []
        
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and self._is_media_file(file_path):
                media_files.append(str(file_path.resolve()))
        
        return media_files
    
    def _parse_metadata_files(self, input_path: Path) -> Dict[str, List[str]]:
        """Parse metadata.json files to find album information"""
        albums = defaultdict(list)
        
        # Look for metadata.json files
        for json_file in input_path.rglob('metadata.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check if this metadata contains album information
                if 'albums' in metadata:
                    albums_data = metadata['albums']
                    for album_info in albums_data:
                        if isinstance(album_info, dict):
                            album_name = album_info.get('title', 'Unknown Album')
                            
                            # Look for associated media files
                            folder_path = json_file.parent
                            media_files = self._get_media_files_in_folder(folder_path)
                            
                            if media_files:
                                albums[album_name].extend(media_files)
            
            except Exception as e:
                self.logger.debug(f"Could not parse metadata file {json_file}: {e}")
        
        return dict(albums)
    
    def _build_file_to_albums_mapping(self):
        """Build reverse mapping from files to albums"""
        self._file_to_albums.clear()
        
        for album_name, files in self._album_cache.items():
            for file_path in files:
                normalized_path = str(Path(file_path).resolve())
                self._file_to_albums[normalized_path].append(album_name)
    
    def _is_media_file(self, file_path: Path) -> bool:
        """Check if file is a media file"""
        media_extensions = {
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            '.webp', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw',
            '.dng', '.orf', '.pef', '.rw2', '.srw',
            
            # Videos
            '.mp4', '.avi', '.mov', '.m4v', '.mkv', '.wmv', '.flv',
            '.webm', '.3gp', '.mts', '.m2ts', '.ts', '.mxf',
            
            # Google specific
            '.mv', '.mp'  # Pixel Motion Photos
        }
        
        return file_path.suffix.lower() in media_extensions
    
    def detect_partner_shared_files(self, input_path: Path) -> Set[str]:
        """
        Detect files that came from partner sharing
        
        Args:
            input_path: Root path of Google Photos takeout
            
        Returns:
            Set of file paths that are partner shared
        """
        partner_shared = set()
        
        # Method 1: Look for specific folder patterns
        partner_folders = [
            'Photos from [Partner Name]',
            'Partner Photos',
            'Shared Photos'
        ]
        
        for folder_name in partner_folders:
            folder_path = input_path / folder_name
            if folder_path.exists():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file() and self._is_media_file(file_path):
                        partner_shared.add(str(file_path.resolve()))
        
        # Method 2: Look for partner sharing indicators in JSON metadata
        for json_file in input_path.rglob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check for partner sharing indicators
                is_partner_shared = False
                
                if 'sharedAlbum' in metadata:
                    is_partner_shared = True
                elif 'shareTime' in metadata:
                    is_partner_shared = True
                elif metadata.get('isPartnerShared', False):
                    is_partner_shared = True
                
                if is_partner_shared:
                    # Find corresponding media file
                    media_file = json_file.with_suffix('')
                    if media_file.exists() and self._is_media_file(media_file):
                        partner_shared.add(str(media_file.resolve()))
                    else:
                        # Try different extensions
                        for ext in ['.jpg', '.jpeg', '.mp4', '.mov']:
                            potential_file = json_file.with_suffix(ext)
                            if potential_file.exists():
                                partner_shared.add(str(potential_file.resolve()))
                                break
            
            except Exception as e:
                self.logger.debug(f"Could not check partner sharing in {json_file}: {e}")
        
        self.logger.info(f"Detected {len(partner_shared)} partner shared files")
        return partner_shared
    
    def clean_album_name(self, album_name: str) -> str:
        """Clean album name for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(invalid_chars, '_', album_name)
        
        # Remove leading/trailing spaces and dots
        cleaned = cleaned.strip(' .')
        
        # Ensure it's not empty
        if not cleaned:
            cleaned = "Unknown Album"
        
        # Limit length to prevent filesystem issues
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        
        return cleaned
    
    def get_album_statistics(self) -> Dict[str, int]:
        """Get statistics about discovered albums"""
        if not self._album_cache:
            return {}
        
        stats = {}
        for album_name, files in self._album_cache.items():
            stats[album_name] = len(files)
        
        # Sort by file count descending
        stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
        
        return stats