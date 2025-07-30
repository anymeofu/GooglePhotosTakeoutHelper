"""
Type-Safe Processing Configuration Models

Comprehensive type-safe configuration models that replace loose dictionaries
with strongly typed, validated configuration objects. Provides compile-time
type checking, runtime validation, and clear documented interfaces.

Based on Dart reference: dart-version/lib/domain/models/processing_config_model.dart
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlbumBehavior(Enum):
    """Album handling behavior options."""
    SHORTCUT = "shortcut"
    DUPLICATE_COPY = "duplicate-copy"
    REVERSE_SHORTCUT = "reverse-shortcut"
    JSON = "json"
    NOTHING = "nothing"


class ExtensionFixingMode(Enum):
    """File extension fixing modes."""
    NONE = "none"
    STANDARD = "standard"
    CONSERVATIVE = "conservative"
    SOLO = "solo"


class DateDivisionLevel(Enum):
    """Date-based folder organization levels."""
    NONE = "none"          # No date organization
    YEAR = "year"          # Group by year (YYYY)
    MONTH = "month"        # Group by year-month (YYYY/MM)
    DAY = "day"            # Group by year-month-day (YYYY/MM/DD)
    HOUR = "hour"          # Group by year-month-day-hour (YYYY/MM/DD/HH)


class ProcessingMode(Enum):
    """Processing execution modes."""
    NORMAL = "normal"      # Standard processing
    DRY_RUN = "dry_run"    # Preview mode - no actual changes
    QUICK = "quick"        # Skip time-intensive operations
    VERBOSE = "verbose"    # Detailed logging and progress


class ValidationLevel(Enum):
    """Input validation strictness levels."""
    STRICT = "strict"      # Fail on any validation issues
    MODERATE = "moderate"  # Warn but continue on minor issues
    LENIENT = "lenient"    # Continue with minimal validation


@dataclass
class InputConfiguration:
    """Input source configuration."""
    input_path: Path
    use_zip_mode: bool = False
    zip_files: List[Path] = field(default_factory=list)
    temp_extraction_dir: Optional[Path] = None
    validation_level: ValidationLevel = ValidationLevel.MODERATE
    
    def __post_init__(self):
        """Post-initialization validation."""
        if isinstance(self.input_path, str):
            self.input_path = Path(self.input_path)
        
        if self.use_zip_mode and not self.zip_files:
            raise ValueError("ZIP mode requires at least one ZIP file")
        
        if not self.use_zip_mode and not self.input_path.exists():
            raise ValueError(f"Input path does not exist: {self.input_path}")


@dataclass
class OutputConfiguration:
    """Output destination configuration."""
    output_path: Path
    clean_output_first: bool = False
    create_directories: bool = True
    preserve_timestamps: bool = True
    dry_run: bool = False
    
    def __post_init__(self):
        """Post-initialization validation."""
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)


@dataclass
class AlbumConfiguration:
    """Album processing configuration."""
    album_behavior: AlbumBehavior = AlbumBehavior.SHORTCUT
    create_album_shortcuts: bool = True
    album_shortcut_path: Optional[Path] = None
    process_partner_sharing: bool = True
    separate_partner_albums: bool = True
    
    def validate(self) -> None:
        """Validate album configuration."""
        if self.album_behavior == AlbumBehavior.SHORTCUT:
            if not self.create_album_shortcuts:
                logger.warning("Shortcut album behavior but shortcuts disabled")


@dataclass
class MediaProcessingConfiguration:
    """Media file processing configuration."""
    extension_fixing_mode: ExtensionFixingMode = ExtensionFixingMode.STANDARD
    remove_duplicates: bool = True
    write_exif_metadata: bool = True
    guess_dates_from_filenames: bool = True
    transform_pixel_motion_photos: bool = False
    file_size_limit_mb: Optional[int] = None
    skip_metadata_extraction: bool = False
    
    def validate(self) -> None:
        """Validate media processing configuration."""
        if self.file_size_limit_mb is not None and self.file_size_limit_mb <= 0:
            raise ValueError("File size limit must be positive")


@dataclass
class DateTimeConfiguration:
    """Date and time processing configuration."""
    date_division_level: DateDivisionLevel = DateDivisionLevel.MONTH
    update_file_timestamps: bool = False  # Windows only
    prefer_metadata_dates: bool = True
    fallback_to_filename_dates: bool = True
    timezone_handling: str = "local"  # local, utc, preserve
    
    def validate(self) -> None:
        """Validate date/time configuration."""
        if self.update_file_timestamps and os.name != 'nt':
            logger.warning("File timestamp updates only supported on Windows")
            self.update_file_timestamps = False


@dataclass
class SystemConfiguration:
    """System resource and performance configuration."""
    max_threads: int = 4
    memory_limit_mb: Optional[int] = None
    enable_progress_reporting: bool = True
    log_level: str = "INFO"
    temp_directory: Optional[Path] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        if self.max_threads <= 0:
            self.max_threads = 1
        elif self.max_threads > cpu_count:
            logger.warning(f"Thread count ({self.max_threads}) exceeds CPU count ({cpu_count})")
            
        if self.memory_limit_mb is not None and self.memory_limit_mb <= 0:
            raise ValueError("Memory limit must be positive")
            
        if self.temp_directory and isinstance(self.temp_directory, str):
            self.temp_directory = Path(self.temp_directory)


@dataclass
class ProcessingConfig:
    """
    Comprehensive type-safe processing configuration.
    
    This replaces the loose dictionary-based configuration with a strongly
    typed, validated configuration model that provides compile-time type
    checking and runtime validation.
    """
    # Core configuration sections
    input_config: InputConfiguration
    output_config: OutputConfiguration
    album_config: AlbumConfiguration = field(default_factory=AlbumConfiguration)
    media_config: MediaProcessingConfiguration = field(default_factory=MediaProcessingConfiguration)
    datetime_config: DateTimeConfiguration = field(default_factory=DateTimeConfiguration)
    system_config: SystemConfiguration = field(default_factory=SystemConfiguration)
    
    # Processing metadata
    created_at: datetime = field(default_factory=datetime.now)
    config_version: str = "3.0.0"
    user_notes: Optional[str] = None
    
    # Legacy compatibility (for gradual migration)
    _legacy_dict: Optional[Dict[str, Any]] = field(default=None, init=False)
    
    def validate(self) -> None:
        """
        Perform comprehensive validation of the entire configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Validate each configuration section
            self.album_config.validate()
            self.media_config.validate()
            self.datetime_config.validate()
            
            # Cross-section validation
            self._validate_cross_dependencies()
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    def _validate_cross_dependencies(self) -> None:
        """Validate dependencies between different configuration sections."""
        # Check input/output compatibility
        if self.input_config.input_path == self.output_config.output_path:
            raise ValueError("Input and output paths cannot be the same")
        
        # Check album behavior compatibility
        if (self.album_config.album_behavior == AlbumBehavior.SHORTCUT and 
            not self.album_config.create_album_shortcuts):
            logger.warning("Shortcut album behavior but shortcuts creation disabled")
        
        # Check system resource constraints
        if (self.system_config.memory_limit_mb and 
            self.system_config.max_threads > 4 and 
            self.system_config.memory_limit_mb < 2048):
            logger.warning("High thread count with low memory limit may cause issues")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format for serialization.
        
        Returns:
            Dictionary representation of the configuration
        """
        def enum_to_str(obj):
            """Convert enum values to strings for serialization."""
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        config_dict = {}
        
        # Convert each section
        config_dict['input'] = {
            'input_path': str(self.input_config.input_path),
            'use_zip_mode': self.input_config.use_zip_mode,
            'zip_files': [str(zf) for zf in self.input_config.zip_files],
            'temp_extraction_dir': str(self.input_config.temp_extraction_dir) if self.input_config.temp_extraction_dir else None,
            'validation_level': self.input_config.validation_level.value
        }
        
        config_dict['output'] = {
            'output_path': str(self.output_config.output_path),
            'clean_output_first': self.output_config.clean_output_first,
            'create_directories': self.output_config.create_directories,
            'preserve_timestamps': self.output_config.preserve_timestamps,
            'dry_run': self.output_config.dry_run
        }
        
        config_dict['album'] = {
            'album_behavior': self.album_config.album_behavior.value,
            'create_album_shortcuts': self.album_config.create_album_shortcuts,
            'album_shortcut_path': str(self.album_config.album_shortcut_path) if self.album_config.album_shortcut_path else None,
            'process_partner_sharing': self.album_config.process_partner_sharing,
            'separate_partner_albums': self.album_config.separate_partner_albums
        }
        
        config_dict['media'] = {
            'extension_fixing_mode': self.media_config.extension_fixing_mode.value,
            'remove_duplicates': self.media_config.remove_duplicates,
            'write_exif_metadata': self.media_config.write_exif_metadata,
            'guess_dates_from_filenames': self.media_config.guess_dates_from_filenames,
            'transform_pixel_motion_photos': self.media_config.transform_pixel_motion_photos,
            'file_size_limit_mb': self.media_config.file_size_limit_mb,
            'skip_metadata_extraction': self.media_config.skip_metadata_extraction
        }
        
        config_dict['datetime'] = {
            'date_division_level': self.datetime_config.date_division_level.value,
            'update_file_timestamps': self.datetime_config.update_file_timestamps,
            'prefer_metadata_dates': self.datetime_config.prefer_metadata_dates,
            'fallback_to_filename_dates': self.datetime_config.fallback_to_filename_dates,
            'timezone_handling': self.datetime_config.timezone_handling
        }
        
        config_dict['system'] = {
            'max_threads': self.system_config.max_threads,
            'memory_limit_mb': self.system_config.memory_limit_mb,
            'enable_progress_reporting': self.system_config.enable_progress_reporting,
            'log_level': self.system_config.log_level,
            'temp_directory': str(self.system_config.temp_directory) if self.system_config.temp_directory else None
        }
        
        config_dict['metadata'] = {
            'created_at': self.created_at.isoformat(),
            'config_version': self.config_version,
            'user_notes': self.user_notes
        }
        
        return config_dict
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProcessingConfig':
        """
        Create configuration from dictionary format.
        
        Args:
            config_dict: Dictionary representation of configuration
        Returns:
            ProcessingConfig instance
        """
        # Extract sections
        input_data = config_dict.get('input', {})
        output_data = config_dict.get('output', {})
        album_data = config_dict.get('album', {})
        media_data = config_dict.get('media', {})
        datetime_data = config_dict.get('datetime', {})
        system_data = config_dict.get('system', {})
        metadata = config_dict.get('metadata', {})
        
        # Create input configuration
        input_config = InputConfiguration(
            input_path=Path(input_data['input_path']),
            use_zip_mode=input_data.get('use_zip_mode', False),
            zip_files=[Path(zf) for zf in input_data.get('zip_files', [])],
            temp_extraction_dir=Path(input_data['temp_extraction_dir']) if input_data.get('temp_extraction_dir') else None,
            validation_level=ValidationLevel(input_data.get('validation_level', 'moderate'))
        )
        
        # Create output configuration
        output_config = OutputConfiguration(
            output_path=Path(output_data['output_path']),
            clean_output_first=output_data.get('clean_output_first', False),
            create_directories=output_data.get('create_directories', True),
            preserve_timestamps=output_data.get('preserve_timestamps', True),
            dry_run=output_data.get('dry_run', False)
        )
        
        # Create album configuration
        album_config = AlbumConfiguration(
            album_behavior=AlbumBehavior(album_data.get('album_behavior', 'shortcut')),
            create_album_shortcuts=album_data.get('create_album_shortcuts', True),
            album_shortcut_path=Path(album_data['album_shortcut_path']) if album_data.get('album_shortcut_path') else None,
            process_partner_sharing=album_data.get('process_partner_sharing', True),
            separate_partner_albums=album_data.get('separate_partner_albums', True)
        )
        
        # Create media configuration
        media_config = MediaProcessingConfiguration(
            extension_fixing_mode=ExtensionFixingMode(media_data.get('extension_fixing_mode', 'standard')),
            remove_duplicates=media_data.get('remove_duplicates', True),
            write_exif_metadata=media_data.get('write_exif_metadata', True),
            guess_dates_from_filenames=media_data.get('guess_dates_from_filenames', True),
            transform_pixel_motion_photos=media_data.get('transform_pixel_motion_photos', False),
            file_size_limit_mb=media_data.get('file_size_limit_mb'),
            skip_metadata_extraction=media_data.get('skip_metadata_extraction', False)
        )
        
        # Create datetime configuration
        datetime_config = DateTimeConfiguration(
            date_division_level=DateDivisionLevel(datetime_data.get('date_division_level', 'month')),
            update_file_timestamps=datetime_data.get('update_file_timestamps', False),
            prefer_metadata_dates=datetime_data.get('prefer_metadata_dates', True),
            fallback_to_filename_dates=datetime_data.get('fallback_to_filename_dates', True),
            timezone_handling=datetime_data.get('timezone_handling', 'local')
        )
        
        # Create system configuration
        system_config = SystemConfiguration(
            max_threads=system_data.get('max_threads', 4),
            memory_limit_mb=system_data.get('memory_limit_mb'),
            enable_progress_reporting=system_data.get('enable_progress_reporting', True),
            log_level=system_data.get('log_level', 'INFO'),
            temp_directory=Path(system_data['temp_directory']) if system_data.get('temp_directory') else None
        )
        
        # Create main configuration
        config = cls(
            input_config=input_config,
            output_config=output_config,
            album_config=album_config,
            media_config=media_config,
            datetime_config=datetime_config,
            system_config=system_config,
            config_version=metadata.get('config_version', '3.0.0'),
            user_notes=metadata.get('user_notes')
        )
        
        # Set created_at if provided
        if 'created_at' in metadata:
            try:
                config.created_at = datetime.fromisoformat(metadata['created_at'])
            except ValueError:
                logger.warning("Invalid created_at timestamp, using current time")
        
        return config
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            file_path: Path to save the configuration file
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {file_path}: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'ProcessingConfig':
        """
        Load configuration from JSON file.
        
        Args:
            file_path: Path to load the configuration file from
        Returns:
            ProcessingConfig instance
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            raise
    
    def get_legacy_dict(self) -> Dict[str, Any]:
        """
        Get a legacy dictionary representation for backward compatibility.
        
        Returns:
            Dictionary compatible with old configuration format
        """
        if self._legacy_dict is None:
            self._legacy_dict = {
                'input_path': str(self.input_config.input_path),
                'output_path': str(self.output_config.output_path),
                'album_mode': self.album_config.album_behavior.value,
                'extension_fix_mode': self.media_config.extension_fixing_mode.value,
                'remove_duplicates': self.media_config.remove_duplicates,
                'write_exif': self.media_config.write_exif_metadata,
                'guess_from_name': self.media_config.guess_dates_from_filenames,
                'update_creation_time': self.datetime_config.update_file_timestamps,
                'dry_run': self.output_config.dry_run,
                'verbose': self.system_config.log_level in ['DEBUG', 'TRACE'],
                'max_threads': self.system_config.max_threads,
                'quick': False  # Derived from processing mode
            }
        return self._legacy_dict.copy()


# Factory functions for common configurations
def create_default_config(input_path: Union[str, Path], output_path: Union[str, Path]) -> ProcessingConfig:
    """
    Create a default processing configuration.
    
    Args:
        input_path: Input directory or ZIP file path
        output_path: Output directory path
    Returns:
        ProcessingConfig with default settings
    """
    input_config = InputConfiguration(input_path=Path(input_path))
    output_config = OutputConfiguration(output_path=Path(output_path))
    
    return ProcessingConfig(
        input_config=input_config,
        output_config=output_config
    )


def create_quick_config(input_path: Union[str, Path], output_path: Union[str, Path]) -> ProcessingConfig:
    """
    Create a configuration optimized for quick processing.
    
    Args:
        input_path: Input directory path
        output_path: Output directory path
    Returns:
        ProcessingConfig optimized for speed
    """
    config = create_default_config(input_path, output_path)
    
    # Quick processing optimizations
    config.media_config.write_exif_metadata = False
    config.datetime_config.update_file_timestamps = False
    config.media_config.transform_pixel_motion_photos = False
    config.system_config.max_threads = min(8, config.system_config.max_threads * 2)
    
    return config


def create_comprehensive_config(input_path: Union[str, Path], output_path: Union[str, Path]) -> ProcessingConfig:
    """
    Create a configuration with comprehensive processing enabled.
    
    Args:
        input_path: Input directory path
        output_path: Output directory path
    Returns:
        ProcessingConfig with all features enabled
    """
    config = create_default_config(input_path, output_path)
    
    # Enable all processing features
    config.media_config.write_exif_metadata = True
    config.media_config.guess_dates_from_filenames = True
    config.media_config.transform_pixel_motion_photos = True
    config.datetime_config.update_file_timestamps = True  # Windows only
    config.album_config.process_partner_sharing = True
    config.album_config.separate_partner_albums = True
    
    return config