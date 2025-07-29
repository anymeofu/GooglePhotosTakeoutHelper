"""
Path Generator for Google Photos Takeout Helper
Handles date-based folder organization and path generation
"""

from pathlib import Path
from datetime import datetime
from typing import Optional


class PathGenerator:
    """Generates target paths based on date organization settings"""
    
    def __init__(self, output_path: str, date_division: int = 0, divide_partner_shared: bool = False):
        """
        Initialize path generator
        
        Args:
            output_path: Base output directory
            date_division: 0=single folder, 1=year, 2=year/month, 3=year/month/day
            divide_partner_shared: Whether to separate partner shared files
        """
        self.output_path = Path(output_path)
        self.date_division = date_division
        self.divide_partner_shared = divide_partner_shared
    
    def generate_target_directory(self, album_name: Optional[str], date_taken: datetime, 
                                is_partner_shared: bool = False) -> Path:
        """
        Generate target directory path based on configuration
        
        Args:
            album_name: Name of album (None for ALL_PHOTOS)
            date_taken: Date the photo/video was taken
            is_partner_shared: Whether file is from partner sharing
            
        Returns:
            Path object for the target directory
        """
        # Start with base output path
        target_path = self.output_path
        
        # Add partner shared folder if enabled and file is partner shared
        if self.divide_partner_shared and is_partner_shared:
            target_path = target_path / "PARTNER_SHARED"
        
        # Add album folder if specified
        if album_name:
            # Clean album name for filesystem
            clean_album_name = self._clean_folder_name(album_name)
            target_path = target_path / clean_album_name
        else:
            # No album = ALL_PHOTOS
            target_path = target_path / "ALL_PHOTOS"
        
        # Add date-based organization if enabled
        if self.date_division > 0:
            target_path = self._add_date_folders(target_path, date_taken)
        
        return target_path
    
    def _add_date_folders(self, base_path: Path, date_taken: datetime) -> Path:
        """Add date-based folder structure"""
        result_path = base_path
        
        if self.date_division >= 1:  # Year
            result_path = result_path / str(date_taken.year)
        
        if self.date_division >= 2:  # Year/Month
            month_str = f"{date_taken.month:02d}-{date_taken.strftime('%B')}"
            result_path = result_path / month_str
        
        if self.date_division >= 3:  # Year/Month/Day
            day_str = f"{date_taken.day:02d}"
            result_path = result_path / day_str
        
        return result_path
    
    def _clean_folder_name(self, name: str) -> str:
        """Clean folder name for filesystem compatibility"""
        import re
        
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(invalid_chars, '_', name)
        
        # Remove leading/trailing spaces and dots
        cleaned = cleaned.strip(' .')
        
        # Ensure it's not empty
        if not cleaned:
            cleaned = "Unknown"
        
        # Limit length to prevent filesystem issues
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        
        return cleaned
    
    def get_all_photos_path(self, is_partner_shared: bool = False) -> Path:
        """Get the ALL_PHOTOS directory path"""
        return self.generate_target_directory(None, datetime.now(), is_partner_shared)
    
    def get_partner_shared_path(self) -> Path:
        """Get the PARTNER_SHARED directory path"""
        if self.divide_partner_shared:
            return self.output_path / "PARTNER_SHARED"
        else:
            return self.output_path