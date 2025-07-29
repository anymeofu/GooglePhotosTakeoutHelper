"""
Platform-specific services for Google Photos Takeout Helper

This module provides abstractions for platform-specific operations like
timestamp management, file attributes, and system-specific optimizations.
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PlatformService(ABC):
    """Abstract base class for platform-specific services"""
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name"""
        pass
    
    @abstractmethod
    def is_supported(self) -> bool:
        """Check if this platform service is supported on current system"""
        pass


class TimestampService(PlatformService):
    """Abstract service for managing file timestamps"""
    
    @abstractmethod
    def update_creation_time(self, file_path: Path, timestamp: datetime) -> bool:
        """
        Update file creation time
        
        Args:
            file_path: Path to the file
            timestamp: New creation time
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_creation_time(self, file_path: Path) -> Optional[datetime]:
        """
        Get file creation time
        
        Args:
            file_path: Path to the file
            
        Returns:
            Creation time as datetime or None if unavailable
        """
        pass
    
    @abstractmethod
    def update_access_and_modification_time(self, file_path: Path, timestamp: datetime) -> bool:
        """
        Update file access and modification times
        
        Args:
            file_path: Path to the file
            timestamp: New timestamp
            
        Returns:
            True if successful, False otherwise
        """
        pass


class WindowsTimestampService(TimestampService):
    """Windows-specific timestamp management"""
    
    def __init__(self):
        self._advanced_available = False
        
        # Check if advanced Windows timestamp support is available
        try:
            import subprocess
            # Test if we can use PowerShell for advanced timestamp operations
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Command Set-ItemProperty'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._advanced_available = True
                logger.debug("PowerShell available for advanced timestamp operations")
        except Exception:
            logger.debug("PowerShell not available for timestamp operations")
    
    def get_platform_name(self) -> str:
        return "windows"
    
    def is_supported(self) -> bool:
        return sys.platform.startswith('win')
    
    def update_creation_time(self, file_path: Path, timestamp: datetime) -> bool:
        """Update Windows file creation time"""
        if not self.is_supported():
            return False
            
        # First try PowerShell method for true creation time
        if self._advanced_available:
            try:
                return self._update_creation_time_powershell(file_path, timestamp)
            except Exception as e:
                logger.debug(f"PowerShell creation time update failed: {e}")
        
        # Fallback to standard method (updates access/modification time)
        return self.update_access_and_modification_time(file_path, timestamp)
    
    def _update_creation_time_powershell(self, file_path: Path, timestamp: datetime) -> bool:
        """Update creation time using PowerShell"""
        try:
            import subprocess
            
            # Format timestamp for PowerShell
            ps_timestamp = timestamp.strftime('%m/%d/%Y %H:%M:%S')
            
            # PowerShell command to update creation time
            ps_command = f"""
            $file = Get-Item '{file_path}'
            $file.CreationTime = [datetime]'{ps_timestamp}'
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.debug(f"PowerShell creation time update failed: {e}")
            return False
    
    def get_creation_time(self, file_path: Path) -> Optional[datetime]:
        """Get Windows file creation time"""
        if not self.is_supported():
            return None
            
        try:
            stat = file_path.stat()
            # On Windows, st_ctime is the creation time
            return datetime.fromtimestamp(stat.st_ctime)
        except Exception as e:
            logger.debug(f"Failed to get creation time for {file_path}: {e}")
            return None
    
    def update_access_and_modification_time(self, file_path: Path, timestamp: datetime) -> bool:
        """Update access and modification times using standard os.utime"""
        try:
            unix_timestamp = timestamp.timestamp()
            os.utime(file_path, (unix_timestamp, unix_timestamp))
            return True
        except Exception as e:
            logger.warning(f"Failed to update access/modification time for {file_path}: {e}")
            return False


class UnixTimestampService(TimestampService):
    """Unix/Linux timestamp management"""
    
    def get_platform_name(self) -> str:
        return "unix"
    
    def is_supported(self) -> bool:
        return not sys.platform.startswith('win') and sys.platform != 'darwin'
    
    def update_creation_time(self, file_path: Path, timestamp: datetime) -> bool:
        """
        On Unix systems, there's no separate creation time
        This updates modification time instead
        """
        return self.update_access_and_modification_time(file_path, timestamp)
    
    def get_creation_time(self, file_path: Path) -> Optional[datetime]:
        """
        On Unix systems, return modification time as closest equivalent
        """
        try:
            stat = file_path.stat()
            return datetime.fromtimestamp(stat.st_mtime)
        except Exception as e:
            logger.debug(f"Failed to get modification time for {file_path}: {e}")
            return None
    
    def update_access_and_modification_time(self, file_path: Path, timestamp: datetime) -> bool:
        """Update access and modification times"""
        try:
            unix_timestamp = timestamp.timestamp()
            os.utime(file_path, (unix_timestamp, unix_timestamp))
            return True
        except Exception as e:
            logger.warning(f"Failed to update timestamps for {file_path}: {e}")
            return False


class MacOSTimestampService(UnixTimestampService):
    """macOS-specific timestamp management"""
    
    def get_platform_name(self) -> str:
        return "macos"
    
    def is_supported(self) -> bool:
        return sys.platform == 'darwin'
    
    def update_creation_time(self, file_path: Path, timestamp: datetime) -> bool:
        """
        macOS has creation time (birthtime) support
        Try to use SetFile command if available, then touch with birthtime
        """
        # Try touch command with birthtime support
        try:
            import subprocess
            timestamp_str = timestamp.strftime('%Y%m%d%H%M.%S')
            result = subprocess.run(
                ['touch', '-t', timestamp_str, str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception as e:
            logger.debug(f"macOS touch command failed: {e}")
        
        # Try using SetFile if available (Xcode command line tools)
        try:
            import subprocess
            # Format: MM/DD/YYYY HH:MM:SS
            setfile_timestamp = timestamp.strftime('%m/%d/%Y %H:%M:%S')
            result = subprocess.run(
                ['SetFile', '-d', setfile_timestamp, str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception as e:
            logger.debug(f"macOS SetFile command failed: {e}")
        
        # Fallback to standard method
        return super().update_creation_time(file_path, timestamp)


class PlatformServiceManager:
    """Manager for platform-specific services"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._timestamp_service: Optional[TimestampService] = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize platform-specific services"""
        # Detect platform and initialize appropriate services
        services = [
            WindowsTimestampService(),
            MacOSTimestampService(),
            UnixTimestampService()
        ]
        
        for service in services:
            if service.is_supported():
                self._timestamp_service = service
                self.logger.info(f"Initialized {service.get_platform_name()} platform services")
                break
        
        if not self._timestamp_service:
            self.logger.warning("No platform-specific services available")
    
    @property
    def timestamp_service(self) -> Optional[TimestampService]:
        """Get the timestamp service for current platform"""
        return self._timestamp_service
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get information about current platform and available services"""
        info = {
            'system': sys.platform,
            'python_version': sys.version,
            'services': {}
        }
        
        if self._timestamp_service:
            info['services']['timestamp'] = {
                'platform': self._timestamp_service.get_platform_name(),
                'supported': self._timestamp_service.is_supported()
            }
            
            # Add Windows-specific info
            if isinstance(self._timestamp_service, WindowsTimestampService):
                info['services']['timestamp']['powershell_available'] = self._timestamp_service._advanced_available
        
        return info


# Global platform service manager instance
platform_manager = PlatformServiceManager()


def get_timestamp_service() -> Optional[TimestampService]:
    """Convenience function to get timestamp service"""
    return platform_manager.timestamp_service


def get_platform_info() -> Dict[str, Any]:
    """Convenience function to get platform information"""
    return platform_manager.get_platform_info()