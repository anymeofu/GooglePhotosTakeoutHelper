"""
Disk Space Service with Cross-Platform Support

This service handles disk space checking and validation across different platforms:
- Windows: PowerShell, WMI, and dir command fallbacks
- macOS/Linux: df command with proper parsing
- Container/minimal systems: Python fallbacks
- Space requirement calculations based on album behavior

Features:
- Cross-platform disk space checking
- Album behavior multiplier calculations
- Safety margin enforcement
- Multi-path space validation
- Performance optimizations

Based on Dart reference: dart-version/lib/infrastructure/consolidated_disk_space_service.dart
"""

import os
import sys
import shutil
import subprocess
import platform
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Union
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class AlbumBehavior(Enum):
    """Album behavior types with their space multipliers."""
    SHORTCUT = "shortcut"
    REVERSE_SHORTCUT = "reverse-shortcut"
    DUPLICATE_COPY = "duplicate-copy"
    JSON = "json"
    NOTHING = "nothing"


@dataclass
class SpaceRequirement:
    """Space requirement calculation result."""
    input_size_bytes: int
    estimated_output_bytes: int
    safety_margin_bytes: int
    total_required_bytes: int
    album_multiplier: float
    behavior: str
    breakdown: Dict[str, int]


@dataclass
class DiskSpaceInfo:
    """Disk space information for a path."""
    path: Path
    total_bytes: int
    used_bytes: int
    free_bytes: int
    filesystem: Optional[str] = None
    mount_point: Optional[str] = None


@dataclass
class SpaceValidationResult:
    """Result of space validation check."""
    is_sufficient: bool
    available_space: int
    required_space: int
    deficit_bytes: int
    recommendations: List[str]
    warnings: List[str]
    disk_info: Optional[DiskSpaceInfo] = None


class DiskSpaceService:
    """
    Cross-platform service for disk space checking and validation.
    
    Provides intelligent space calculations based on album behavior
    and safe margins for different operating systems.
    """
    
    # Album behavior multipliers
    ALBUM_MULTIPLIERS = {
        AlbumBehavior.SHORTCUT.value: 1.1,           # Small symlink overhead
        AlbumBehavior.REVERSE_SHORTCUT.value: 1.1,   # Small symlink overhead
        AlbumBehavior.DUPLICATE_COPY.value: 2.0,     # Full file duplication
        AlbumBehavior.JSON.value: 1.05,              # Small JSON metadata
        AlbumBehavior.NOTHING.value: 1.0             # Move operation only
    }
    
    # Default safety margins (in bytes)
    DEFAULT_SAFETY_MARGIN = 100 * 1024 * 1024  # 100MB
    LARGE_DATASET_MARGIN = 1024 * 1024 * 1024  # 1GB for >10GB datasets
    
    # Platform detection
    IS_WINDOWS = platform.system() == 'Windows'
    IS_MACOS = platform.system() == 'Darwin'
    IS_LINUX = platform.system() == 'Linux'
    
    def __init__(self, safety_margin_mb: int = 100):
        """
        Initialize disk space service.
        
        Args:
            safety_margin_mb: Default safety margin in MB
        """
        self.safety_margin_bytes = safety_margin_mb * 1024 * 1024
    
    def get_disk_space(self, path: Union[str, Path]) -> Optional[DiskSpaceInfo]:
        """
        Get disk space information for a given path.
        
        Args:
            path: Path to check (file or directory)
            
        Returns:
            DiskSpaceInfo object or None if checking fails
        """
        path = Path(path)
        
        # Ensure we check an existing directory
        if path.is_file():
            path = path.parent
        
        if not path.exists():
            # Try to create parent directories to get the target disk
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.warning(f"Cannot access path for space checking: {path}")
                return None
        
        try:
            # Try platform-specific methods first
            if self.IS_WINDOWS:
                return self._get_windows_disk_space(path)
            elif self.IS_MACOS or self.IS_LINUX:
                return self._get_unix_disk_space(path)
            else:
                # Fallback for unknown platforms
                return self._get_python_disk_space(path)
        
        except Exception as e:
            logger.warning(f"Platform-specific space check failed for {path}: {e}")
            # Try Python fallback
            return self._get_python_disk_space(path)
    
    def calculate_space_requirements(self, input_paths: List[Path], 
                                   album_behavior: str,
                                   additional_margin_mb: int = 0) -> SpaceRequirement:
        """
        Calculate space requirements for processing.
        
        Args:
            input_paths: List of input paths to analyze
            album_behavior: Album behavior mode
            additional_margin_mb: Additional safety margin in MB
            
        Returns:
            SpaceRequirement with detailed breakdown
        """
        logger.info(f"Calculating space requirements for {len(input_paths)} paths with behavior: {album_behavior}")
        
        # Calculate total input size
        total_input_size = 0
        for path in input_paths:
            try:
                if path.is_file():
                    total_input_size += path.stat().st_size
                elif path.is_dir():
                    total_input_size += self._calculate_directory_size(path)
            except Exception as e:
                logger.warning(f"Could not calculate size for {path}: {e}")
        
        # Get album behavior multiplier
        multiplier = self.ALBUM_MULTIPLIERS.get(album_behavior, 1.1)
        
        # Calculate estimated output size
        estimated_output = int(total_input_size * multiplier)
        
        # Calculate safety margin
        base_margin = self.safety_margin_bytes
        if total_input_size > 10 * 1024 * 1024 * 1024:  # > 10GB
            base_margin = self.LARGE_DATASET_MARGIN
        
        additional_margin = additional_margin_mb * 1024 * 1024
        total_margin = base_margin + additional_margin
        
        # Total requirement
        total_required = estimated_output + total_margin
        
        # Detailed breakdown
        breakdown = {
            'input_size': total_input_size,
            'processing_overhead': estimated_output - total_input_size,
            'safety_margin': total_margin,
            'total': total_required
        }
        
        return SpaceRequirement(
            input_size_bytes=total_input_size,
            estimated_output_bytes=estimated_output,
            safety_margin_bytes=total_margin,
            total_required_bytes=total_required,
            album_multiplier=multiplier,
            behavior=album_behavior,
            breakdown=breakdown
        )
    
    def validate_space_for_processing(self, input_paths: List[Path], 
                                    output_path: Path,
                                    album_behavior: str,
                                    additional_margin_mb: int = 0) -> SpaceValidationResult:
        """
        Validate that sufficient space is available for processing.
        
        Args:
            input_paths: Input paths to process
            output_path: Output directory
            album_behavior: Album behavior mode
            additional_margin_mb: Additional safety margin
            
        Returns:
            SpaceValidationResult with validation status and recommendations
        """
        # Calculate requirements
        requirements = self.calculate_space_requirements(
            input_paths, album_behavior, additional_margin_mb
        )
        
        # Get available space at output location
        disk_info = self.get_disk_space(output_path)
        
        if not disk_info:
            return SpaceValidationResult(
                is_sufficient=False,
                available_space=0,
                required_space=requirements.total_required_bytes,
                deficit_bytes=requirements.total_required_bytes,
                recommendations=["Could not detect disk space. Proceed with caution."],
                warnings=["Disk space validation failed"]
            )
        
        # Check if space is sufficient
        is_sufficient = disk_info.free_bytes >= requirements.total_required_bytes
        deficit = max(0, requirements.total_required_bytes - disk_info.free_bytes)
        
        # Generate recommendations and warnings
        recommendations = []
        warnings = []
        
        if not is_sufficient:
            deficit_gb = deficit / (1024 ** 3)
            recommendations.extend([
                f"Free up at least {deficit_gb:.1f}GB of disk space",
                "Consider using 'shortcut' album behavior to reduce space requirements",
                "Use 'json' or 'nothing' album behavior for minimal space usage"
            ])
            warnings.append(f"Insufficient disk space: need {deficit_gb:.1f}GB more")
        
        # Add platform-specific recommendations
        if disk_info.free_bytes < requirements.total_required_bytes * 1.2:  # Less than 20% buffer
            if self.IS_WINDOWS:
                recommendations.extend([
                    "Check Windows Disk Cleanup utility",
                    "Consider moving to a drive with more space"
                ])
            elif self.IS_MACOS:
                recommendations.extend([
                    "Check macOS Storage Management",
                    "Consider using external storage"
                ])
            else:
                recommendations.append("Consider using external storage or cleaning temporary files")
        
        # Album-specific suggestions
        if album_behavior == AlbumBehavior.DUPLICATE_COPY.value and not is_sufficient:
            recommendations.append(
                "Switch to 'shortcut' album behavior to reduce space usage by ~50%"
            )
        
        return SpaceValidationResult(
            is_sufficient=is_sufficient,
            available_space=disk_info.free_bytes,
            required_space=requirements.total_required_bytes,
            deficit_bytes=deficit,
            recommendations=recommendations,
            warnings=warnings,
            disk_info=disk_info
        )
    
    def _get_windows_disk_space(self, path: Path) -> Optional[DiskSpaceInfo]:
        """Get disk space using Windows-specific methods."""
        try:
            # Method 1: Try PowerShell (most reliable)
            result = self._get_windows_powershell_space(path)
            if result:
                return result
            
            # Method 2: Try WMI via PowerShell
            result = self._get_windows_wmi_space(path)
            if result:
                return result
            
            # Method 3: Fallback to Python shutil
            return self._get_python_disk_space(path)
            
        except Exception as e:
            logger.warning(f"Windows disk space check failed: {e}")
            return self._get_python_disk_space(path)
    
    def _get_windows_powershell_space(self, path: Path) -> Optional[DiskSpaceInfo]:
        """Get disk space using PowerShell Get-Volume command."""
        try:
            # Get the drive letter
            drive_letter = str(path.resolve()).split(':')[0]
            
            # PowerShell command to get volume info
            cmd = [
                'powershell', '-Command',
                f"Get-Volume -DriveLetter '{drive_letter}' | Select-Object Size, SizeRemaining | ConvertTo-Json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                import json
                data = json.loads(result.stdout)
                total = int(data['Size'])
                free = int(data['SizeRemaining'])
                used = total - free
                
                return DiskSpaceInfo(
                    path=path,
                    total_bytes=total,
                    used_bytes=used,
                    free_bytes=free,
                    filesystem='NTFS',  # Assume NTFS on Windows
                    mount_point=f"{drive_letter}:\\"
                )
        
        except Exception as e:
            logger.debug(f"PowerShell space check failed: {e}")
        
        return None
    
    def _get_windows_wmi_space(self, path: Path) -> Optional[DiskSpaceInfo]:
        """Get disk space using WMI via PowerShell."""
        try:
            drive_letter = str(path.resolve()).split(':')[0]
            
            cmd = [
                'powershell', '-Command',
                f"Get-WmiObject -Class Win32_LogicalDisk -Filter \"DeviceID='{drive_letter}:'\" | "
                "Select-Object Size, FreeSpace | ConvertTo-Json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                import json
                data = json.loads(result.stdout)
                total = int(data['Size'])
                free = int(data['FreeSpace'])
                used = total - free
                
                return DiskSpaceInfo(
                    path=path,
                    total_bytes=total,
                    used_bytes=used,
                    free_bytes=free,
                    filesystem='NTFS',
                    mount_point=f"{drive_letter}:\\"
                )
        
        except Exception as e:
            logger.debug(f"WMI space check failed: {e}")
        
        return None
    
    def _get_unix_disk_space(self, path: Path) -> Optional[DiskSpaceInfo]:
        """Get disk space using Unix df command."""
        try:
            # Use df command to get filesystem info
            cmd = ['df', '-B1', str(path)]  # -B1 for byte units
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    # Parse df output (format: Filesystem 1B-blocks Used Available Use% Mounted)
                    data_line = lines[1].split()
                    if len(data_line) >= 6:
                        total = int(data_line[1])
                        used = int(data_line[2])
                        available = int(data_line[3])
                        mount_point = data_line[5] if len(data_line) > 5 else str(path)
                        filesystem = lines[1].split()[0]
                        
                        return DiskSpaceInfo(
                            path=path,
                            total_bytes=total,
                            used_bytes=used,
                            free_bytes=available,
                            filesystem=filesystem,
                            mount_point=mount_point
                        )
        
        except Exception as e:
            logger.debug(f"Unix df command failed: {e}")
        
        return self._get_python_disk_space(path)
    
    def _get_python_disk_space(self, path: Path) -> Optional[DiskSpaceInfo]:
        """Fallback disk space check using Python's shutil."""
        try:
            usage = shutil.disk_usage(path)
            return DiskSpaceInfo(
                path=path,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                filesystem='unknown',
                mount_point=str(path)
            )
        
        except Exception as e:
            logger.error(f"Python disk space check failed for {path}: {e}")
            return None
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of a directory tree."""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except Exception as e:
            logger.warning(f"Error calculating directory size for {directory}: {e}")
        
        return total_size
    
    def get_space_recommendations(self, available_gb: float, required_gb: float, 
                                album_behavior: str) -> List[str]:
        """
        Generate specific recommendations based on space situation.
        
        Args:
            available_gb: Available space in GB
            required_gb: Required space in GB
            album_behavior: Current album behavior
            
        Returns:
            List of specific recommendations
        """
        recommendations = []
        
        deficit_gb = required_gb - available_gb
        
        if deficit_gb > 0:
            # Space deficit recommendations
            recommendations.append(f"Need {deficit_gb:.1f}GB more disk space")
            
            # Album behavior suggestions
            if album_behavior == AlbumBehavior.DUPLICATE_COPY.value:
                savings = required_gb * 0.5  # Roughly 50% savings
                recommendations.append(
                    f"Use 'shortcut' album behavior to save ~{savings:.1f}GB"
                )
            
            if album_behavior in [AlbumBehavior.SHORTCUT.value, AlbumBehavior.DUPLICATE_COPY.value]:
                minimal_savings = required_gb * 0.9  # Roughly 90% savings
                recommendations.append(
                    f"Use 'nothing' album behavior to save ~{minimal_savings:.1f}GB"
                )
        
        elif deficit_gb > -1.0:  # Less than 1GB buffer
            recommendations.append("Very tight space - consider adding safety margin")
        
        # Platform-specific cleanup suggestions
        if self.IS_WINDOWS:
            recommendations.extend([
                "Run Disk Cleanup (cleanmgr.exe)",
                "Check Downloads and Temp folders",
                "Consider moving to external drive"
            ])
        elif self.IS_MACOS:
            recommendations.extend([
                "Check Storage Management in About This Mac",
                "Empty Trash and Downloads",
                "Consider using external storage"
            ])
        else:
            recommendations.extend([
                "Clean temporary files (/tmp, ~/.cache)",
                "Check for large log files",
                "Consider external storage or cloud sync"
            ])
        
        return recommendations
    
    def format_space_info(self, space_info: DiskSpaceInfo) -> str:
        """Format disk space information for display."""
        total_gb = space_info.total_bytes / (1024 ** 3)
        used_gb = space_info.used_bytes / (1024 ** 3)
        free_gb = space_info.free_bytes / (1024 ** 3)
        used_percent = (space_info.used_bytes / space_info.total_bytes) * 100
        
        return (
            f"Disk: {space_info.filesystem} ({space_info.mount_point})\n"
            f"Total: {total_gb:.1f}GB, Used: {used_gb:.1f}GB ({used_percent:.1f}%), "
            f"Free: {free_gb:.1f}GB"
        )


def create_disk_space_service(safety_margin_mb: int = 100) -> DiskSpaceService:
    """
    Factory function to create a configured DiskSpaceService.
    
    Args:
        safety_margin_mb: Safety margin in MB
        
    Returns:
        Configured DiskSpaceService instance
    """
    return DiskSpaceService(safety_margin_mb=safety_margin_mb)