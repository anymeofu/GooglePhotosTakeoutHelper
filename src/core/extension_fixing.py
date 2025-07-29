"""
Extension Fixing Service
Handles file extension correction based on MIME type detection
"""

import mimetypes
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum


class ExtensionFixMode(Enum):
    """Extension fixing modes"""
    NONE = "none"
    STANDARD = "standard"
    CONSERVATIVE = "conservative"
    SOLO = "solo"


class ExtensionFixingService:
    """Service for fixing file extensions based on actual content"""
    
    def __init__(self, logger, mode: ExtensionFixMode = ExtensionFixMode.STANDARD):
        self.logger = logger
        self.mode = mode
        
        # Initialize MIME type mappings
        self._init_mime_mappings()
        
        # Track statistics
        self.stats = {
            'files_checked': 0,
            'extensions_fixed': 0,
            'extensions_changed': {},
            'problematic_files': []
        }
    
    def _init_mime_mappings(self):
        """Initialize MIME type to extension mappings"""
        # Common MIME types and their preferred extensions
        self.mime_to_ext = {
            # Images
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/webp': '.webp',
            'image/heic': '.heic',
            'image/heif': '.heif',
            
            # Videos
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'video/x-ms-wmv': '.wmv',
            'video/webm': '.webm',
            'video/3gpp': '.3gp',
            'video/x-matroska': '.mkv',
            
            # Audio
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/aac': '.aac',
            'audio/ogg': '.ogg',
            'audio/mp4': '.m4a',
        }
        
        # Extensions that should never be changed (conservative mode)
        self.protected_extensions = {
            '.json', '.txt', '.xml', '.html', '.htm', '.css', '.js',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.7z', '.tar', '.gz'
        }
        
        # Known problematic extensions that often need fixing
        self.problematic_extensions = {
            '.tmp', '.download', '.part', '.crdownload', ''
        }
    
    def fix_extensions_in_directory(self, directory: Path, dry_run: bool = False) -> Dict[str, int]:
        """
        Fix extensions for all files in a directory
        
        Args:
            directory: Directory to process
            dry_run: If True, only log what would be done
            
        Returns:
            Dictionary with statistics
        """
        if self.mode == ExtensionFixMode.NONE:
            self.logger.info("Extension fixing disabled")
            return self.stats
        
        self.logger.info(f"Starting extension fixing in {directory} (mode: {self.mode.value})")
        
        # Get all files to process
        files_to_check = []
        for file_path in directory.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                files_to_check.append(file_path)
        
        self.logger.info(f"Found {len(files_to_check)} files to check")
        
        # Process files based on mode
        for file_path in files_to_check:
            try:
                self._fix_single_file_extension(file_path, dry_run)
            except Exception as e:
                self.logger.warning(f"Error fixing extension for {file_path}: {e}")
                self.stats['problematic_files'].append(str(file_path))
        
        self._log_statistics()
        return self.stats
    
    def _fix_single_file_extension(self, file_path: Path, dry_run: bool = False) -> Optional[Path]:
        """
        Fix extension for a single file
        
        Args:
            file_path: Path to the file
            dry_run: If True, only log what would be done
            
        Returns:
            New file path if renamed, None if no change
        """
        self.stats['files_checked'] += 1
        
        # Skip files based on mode
        if self._should_skip_file(file_path):
            return None
        
        # Detect file type
        detected_mime = self._detect_mime_type(file_path)
        if not detected_mime:
            self.logger.debug(f"Could not detect MIME type for {file_path}")
            return None
        
        # Get correct extension
        correct_ext = self.mime_to_ext.get(detected_mime)
        if not correct_ext:
            self.logger.debug(f"No mapping for MIME type {detected_mime} for file {file_path}")
            return None
        
        current_ext = file_path.suffix.lower()
        
        # Check if extension needs fixing
        if current_ext == correct_ext.lower():
            self.logger.debug(f"Extension already correct for {file_path}")
            return None
        
        # Conservative mode: only fix obviously wrong extensions
        if self.mode == ExtensionFixMode.CONSERVATIVE:
            if current_ext not in self.problematic_extensions:
                self.logger.debug(f"Conservative mode: skipping {file_path} with extension {current_ext}")
                return None
        
        # Generate new file path
        new_path = file_path.with_suffix(correct_ext)
        
        # Handle conflicts
        counter = 1
        original_new_path = new_path
        while new_path.exists():
            stem = original_new_path.stem
            new_path = original_new_path.parent / f"{stem}_{counter}{correct_ext}"
            counter += 1
        
        # Perform the rename
        if not dry_run:
            try:
                file_path.rename(new_path)
                self.logger.info(f"Renamed {file_path.name} -> {new_path.name}")
                
                # Update statistics
                self.stats['extensions_fixed'] += 1
                old_ext = current_ext if current_ext else '(no extension)'
                if old_ext not in self.stats['extensions_changed']:
                    self.stats['extensions_changed'][old_ext] = 0
                self.stats['extensions_changed'][old_ext] += 1
                
                return new_path
                
            except Exception as e:
                self.logger.error(f"Failed to rename {file_path} to {new_path}: {e}")
                self.stats['problematic_files'].append(str(file_path))
                return None
        else:
            self.logger.info(f"DRY RUN: Would rename {file_path.name} -> {new_path.name}")
            self.stats['extensions_fixed'] += 1
            return new_path
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on mode and extension"""
        current_ext = file_path.suffix.lower()
        
        # Always skip JSON metadata files
        if current_ext == '.json':
            return True
        
        # Solo mode: only process files without extensions or with problematic ones
        if self.mode == ExtensionFixMode.SOLO:
            if current_ext and current_ext not in self.problematic_extensions:
                return True
        
        # Conservative mode: skip protected extensions
        elif self.mode == ExtensionFixMode.CONSERVATIVE:
            if current_ext in self.protected_extensions:
                return True
        
        return False
    
    def _detect_mime_type(self, file_path: Path) -> Optional[str]:
        """
        Detect MIME type using multiple methods
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string or None if detection failed
        """
        # Method 1: Try python-magic if available
        mime_type = self._detect_with_magic(file_path)
        if mime_type:
            return mime_type
        
        # Method 2: Try file command (Unix/Linux)
        mime_type = self._detect_with_file_command(file_path)
        if mime_type:
            return mime_type
        
        # Method 3: Try built-in mimetypes module (based on extension)
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            self.logger.debug(f"Detected MIME type via mimetypes: {mime_type} for {file_path}")
            return mime_type
        
        # Method 4: Basic file signature detection
        mime_type = self._detect_by_signature(file_path)
        if mime_type:
            return mime_type
        
        return None
    
    def _detect_with_magic(self, file_path: Path) -> Optional[str]:
        """Try to detect MIME type using python-magic"""
        try:
            import magic
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(str(file_path))
            self.logger.debug(f"Detected MIME type via magic: {mime_type} for {file_path}")
            return mime_type
        except ImportError:
            self.logger.debug("python-magic not available")
            return None
        except Exception as e:
            self.logger.debug(f"Magic detection failed for {file_path}: {e}")
            return None
    
    def _detect_with_file_command(self, file_path: Path) -> Optional[str]:
        """Try to detect MIME type using file command"""
        try:
            result = subprocess.run(
                ['file', '--mime-type', '-b', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                mime_type = result.stdout.strip()
                self.logger.debug(f"Detected MIME type via file command: {mime_type} for {file_path}")
                return mime_type
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            self.logger.debug(f"File command detection failed for {file_path}: {e}")
        
        return None
    
    def _detect_by_signature(self, file_path: Path) -> Optional[str]:
        """Detect MIME type by reading file signature (magic bytes)"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            
            # Common file signatures
            signatures = [
                # Images
                (b'\xff\xd8\xff', 'image/jpeg'),
                (b'\x89PNG\r\n\x1a\n', 'image/png'),
                (b'GIF87a', 'image/gif'),
                (b'GIF89a', 'image/gif'),
                (b'BM', 'image/bmp'),
                (b'RIFF', 'image/webp'),  # Need to check further for WebP
                
                # Videos
                (b'\x00\x00\x00\x20ftypmp4', 'video/mp4'),
                (b'\x00\x00\x00\x18ftypmp4', 'video/mp4'),
                (b'ftypMSNV', 'video/mp4'),
                (b'ftypisom', 'video/mp4'),
                (b'RIFF', 'video/avi'),  # Need to check further for AVI
            ]
            
            for signature, mime_type in signatures:
                if header.startswith(signature):
                    # Special handling for RIFF files
                    if mime_type in ['image/webp', 'video/avi'] and len(header) >= 12:
                        riff_type = header[8:12]
                        if riff_type == b'WEBP':
                            mime_type = 'image/webp'
                        elif riff_type == b'AVI ':
                            mime_type = 'video/avi'
                        else:
                            continue
                    
                    self.logger.debug(f"Detected MIME type via signature: {mime_type} for {file_path}")
                    return mime_type
            
        except Exception as e:
            self.logger.debug(f"Signature detection failed for {file_path}: {e}")
        
        return None
    
    def _log_statistics(self):
        """Log processing statistics"""
        stats = self.stats
        
        self.logger.info(f"Extension fixing completed:")
        self.logger.info(f"  Files checked: {stats['files_checked']}")
        self.logger.info(f"  Extensions fixed: {stats['extensions_fixed']}")
        
        if stats['extensions_changed']:
            self.logger.info("  Extension changes:")
            for old_ext, count in stats['extensions_changed'].items():
                self.logger.info(f"    {old_ext}: {count} files")
        
        if stats['problematic_files']:
            self.logger.warning(f"  Problematic files: {len(stats['problematic_files'])}")
            for file_path in stats['problematic_files'][:5]:  # Show first 5
                self.logger.warning(f"    {file_path}")
            if len(stats['problematic_files']) > 5:
                self.logger.warning(f"    ... and {len(stats['problematic_files']) - 5} more")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()