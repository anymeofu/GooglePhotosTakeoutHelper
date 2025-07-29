"""
EXIF Writer Service for Google Photos Takeout Helper

This module provides functionality to write EXIF metadata (timestamps, GPS coordinates)
back to image and video files using ExifTool or fallback methods.
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ExifWriterService:
    """Service for writing EXIF metadata to media files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._exiftool_available = None
        self._exiftool_path = None
        self._exiftool_version = None
        self._check_exiftool_availability()
    
    def _check_exiftool_availability(self):
        """Check if ExifTool is available on the system"""
        try:
            # Try common ExifTool names and paths
            exiftool_commands = ['exiftool', 'exiftool.exe']
            
            for cmd in exiftool_commands:
                try:
                    result = subprocess.run(
                        [cmd, '-ver'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        self._exiftool_available = True
                        self._exiftool_path = cmd
                        self._exiftool_version = result.stdout.strip()
                        self.logger.info(f"ExifTool {self._exiftool_version} found at {cmd}")
                        return
                        
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    continue
            
            self._exiftool_available = False
            self.logger.warning("ExifTool not found - EXIF writing will be limited")
            
        except Exception as e:
            self._exiftool_available = False
            self.logger.warning(f"Error checking ExifTool availability: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get EXIF writer status information"""
        return {
            'exiftool_available': self._exiftool_available,
            'exiftool_path': self._exiftool_path,
            'exiftool_version': self._exiftool_version,
            'fallback_methods': ['PIL (read-only)', 'File timestamps']
        }
    
    def is_supported_file(self, file_path: Path) -> bool:
        """Check if file type supports EXIF writing"""
        if not file_path.exists():
            return False
            
        # Supported image formats
        image_extensions = {'.jpg', '.jpeg', '.tiff', '.tif'}
        
        # Supported video formats (with ExifTool)
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v'}
        
        extension = file_path.suffix.lower()
        
        if extension in image_extensions:
            return True
        elif extension in video_extensions and self._exiftool_available:
            return True
        
        return False
    
    def write_datetime(self, file_path: Path, date_taken: datetime, dry_run: bool = False) -> bool:
        """
        Write datetime to EXIF metadata
        
        Args:
            file_path: Path to the file
            date_taken: Datetime to write
            dry_run: If True, don't actually write, just log what would happen
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_supported_file(file_path):
            self.logger.debug(f"File type not supported for EXIF writing: {file_path}")
            return False
        
        if dry_run:
            self.logger.debug(f"Would write EXIF datetime {date_taken} to {file_path}")
            return True
        
        if self._exiftool_available:
            return self._write_datetime_exiftool(file_path, date_taken)
        else:
            return self._write_datetime_fallback(file_path, date_taken)
    
    def write_gps_coordinates(self, file_path: Path, latitude: float, longitude: float, 
                            altitude: Optional[float] = None, dry_run: bool = False) -> bool:
        """
        Write GPS coordinates to EXIF metadata
        
        Args:
            file_path: Path to the file
            latitude: GPS latitude
            longitude: GPS longitude
            altitude: GPS altitude (optional)
            dry_run: If True, don't actually write, just log what would happen
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_supported_file(file_path):
            return False
        
        if dry_run:
            coords_str = f"{latitude}, {longitude}"
            if altitude is not None:
                coords_str += f", {altitude}m"
            self.logger.debug(f"Would write GPS coordinates {coords_str} to {file_path}")
            return True
        
        if self._exiftool_available:
            return self._write_gps_exiftool(file_path, latitude, longitude, altitude)
        else:
            self.logger.warning(f"GPS writing requires ExifTool for {file_path}")
            return False
    
    def _write_datetime_exiftool(self, file_path: Path, date_taken: datetime) -> bool:
        """Write datetime using ExifTool"""
        try:
            # Format datetime for ExifTool
            exif_datetime = date_taken.strftime('%Y:%m:%d %H:%M:%S')
            
            # Build ExifTool command
            cmd = [
                self._exiftool_path,
                f'-DateTimeOriginal={exif_datetime}',
                f'-CreateDate={exif_datetime}',
                f'-ModifyDate={exif_datetime}',
                '-overwrite_original',
                str(file_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully wrote EXIF datetime to {file_path}")
                return True
            else:
                self.logger.warning(f"ExifTool failed for {file_path}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Error writing EXIF datetime to {file_path}: {e}")
            return False
    
    def _write_gps_exiftool(self, file_path: Path, latitude: float, longitude: float, 
                          altitude: Optional[float] = None) -> bool:
        """Write GPS coordinates using ExifTool"""
        try:
            # Build ExifTool command for GPS
            cmd = [
                self._exiftool_path,
                f'-GPSLatitude={latitude}',
                f'-GPSLongitude={longitude}',
                '-overwrite_original'
            ]
            
            if altitude is not None:
                cmd.append(f'-GPSAltitude={altitude}')
            
            cmd.append(str(file_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully wrote GPS coordinates to {file_path}")
                return True
            else:
                self.logger.warning(f"ExifTool GPS write failed for {file_path}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Error writing GPS to {file_path}: {e}")
            return False
    
    def _write_datetime_fallback(self, file_path: Path, date_taken: datetime) -> bool:
        """Fallback method for writing datetime without ExifTool"""
        try:
            # For JPEG files, try using Pillow if available
            if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                return self._write_datetime_pillow(file_path, date_taken)
            else:
                self.logger.debug(f"No fallback method for {file_path.suffix} files")
                return False
                
        except Exception as e:
            self.logger.warning(f"Fallback EXIF write failed for {file_path}: {e}")
            return False
    
    def _write_datetime_pillow(self, file_path: Path, date_taken: datetime) -> bool:
        """Write datetime using Pillow (limited support)"""
        try:
            from PIL import Image, ExifTags
            from PIL.ExifTags import TAGS
            
            # Note: Pillow has limited EXIF writing support
            # Most modern use cases should use ExifTool
            self.logger.debug(f"Attempting Pillow EXIF write for {file_path}")
            
            with Image.open(file_path) as img:
                exif_dict = img.getexif()
                
                # Add datetime to EXIF
                datetime_str = date_taken.strftime('%Y:%m:%d %H:%M:%S')
                
                # Find EXIF datetime tags
                for tag_name in ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']:
                    tag_id = None
                    for tid, name in TAGS.items():
                        if name == tag_name:
                            tag_id = tid
                            break
                    
                    if tag_id:
                        exif_dict[tag_id] = datetime_str
                
                # Save with updated EXIF (this may not work for all PIL versions)
                img.save(file_path, exif=exif_dict)
                self.logger.debug(f"Pillow EXIF write completed for {file_path}")
                return True
                
        except ImportError:
            self.logger.debug("PIL not available for EXIF writing")
        except Exception as e:
            self.logger.debug(f"Pillow EXIF write failed: {e}")
        
        return False
    
    def bulk_write_metadata(self, files_metadata: List[Tuple[Path, datetime, Optional[Tuple[float, float, Optional[float]]]]],
                          dry_run: bool = False) -> Dict[str, int]:
        """
        Write metadata to multiple files efficiently
        
        Args:
            files_metadata: List of (file_path, datetime, gps_coords) tuples
            dry_run: If True, don't actually write, just simulate
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'datetime_written': 0,
            'gps_written': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for file_path, date_taken, gps_coords in files_metadata:
            if not self.is_supported_file(file_path):
                stats['skipped'] += 1
                continue
            
            success = True
            
            # Write datetime
            if date_taken:
                if self.write_datetime(file_path, date_taken, dry_run):
                    stats['datetime_written'] += 1
                else:
                    success = False
            
            # Write GPS coordinates
            if gps_coords and len(gps_coords) >= 2:
                lat, lon = gps_coords[0], gps_coords[1]
                alt = gps_coords[2] if len(gps_coords) > 2 else None
                
                if self.write_gps_coordinates(file_path, lat, lon, alt, dry_run):
                    stats['gps_written'] += 1
                else:
                    success = False
            
            if not success:
                stats['failed'] += 1
        
        return stats


# Global EXIF writer service instance
exif_writer = ExifWriterService()


def get_exif_writer() -> ExifWriterService:
    """Get the global EXIF writer service instance"""
    return exif_writer


def check_exiftool_status() -> Dict[str, Any]:
    """Check ExifTool status - convenience function"""
    return exif_writer.get_status()