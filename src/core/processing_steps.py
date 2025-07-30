"""
Google Photos Takeout Helper - Processing Steps
Base classes and individual step implementations for the processing pipeline
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Import existing services
from .extension_fixing import ExtensionFixingService, ExtensionFixMode
from .date_extraction import DateExtractionService
from .album_detection import AlbumDetectionService
from .album_strategies import (
    AlbumStrategy, ShortcutStrategy, DuplicateCopyStrategy, 
    ReverseShortcutStrategy, JsonStrategy, NothingStrategy
)
from .path_generator import PathGenerator


@dataclass
class StepResult:
    """Result from a processing step execution"""
    name: str
    success: bool
    duration: float = 0.0
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingContext:
    """Context passed between processing steps"""
    config: Any  # ProcessingConfig
    input_path: Path
    output_path: Path
    logger: logging.Logger
    media_files: List[Path] = field(default_factory=list)
    file_dates: Dict[Path, Optional[datetime]] = field(default_factory=dict)
    albums: Dict[str, List[Path]] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)


class ProcessingStep(ABC):
    """Base class for all processing steps"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def execute(self, context: ProcessingContext) -> StepResult:
        """Execute this processing step"""
        pass
    
    def should_skip(self, context: ProcessingContext) -> bool:
        """Determine if this step should be skipped based on configuration"""
        return False


class FixExtensionsStep(ProcessingStep):
    """Step 1: Fix incorrect file extensions based on MIME type"""
    
    def __init__(self):
        super().__init__("Fix Extensions")
    
    def should_skip(self, context: ProcessingContext) -> bool:
        """Skip if extension fixing is disabled"""
        return context.config.extension_fix_mode == ExtensionFixMode.NONE
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Fix file extensions based on content"""
        try:
            service = ExtensionFixingService(
                context.logger,
                context.config.extension_fix_mode
            )
            
            # Process files in input directory
            service.fix_extensions_in_directory(context.input_path, dry_run=context.config.dry_run)
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Fixed {service.stats['extensions_fixed']} file extensions",
                data={
                    'extensions_fixed': service.stats['extensions_fixed'],
                    'files_checked': service.stats['files_checked']
                }
            )
            
        except Exception as e:
            context.logger.error(f"Extension fixing failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Extension fixing failed",
                error=str(e)
            )


class DiscoverMediaStep(ProcessingStep):
    """Step 2: Discover and classify all media files"""
    
    def __init__(self):
        super().__init__("Discover Media")
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Discover all media files in the input directory"""
        try:
            media_extensions = {
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw',
                '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'
            }
            
            media_files = []
            json_files = []
            
            # Discover files recursively
            for file_path in context.input_path.rglob('*'):
                if file_path.is_file():
                    if file_path.suffix.lower() in media_extensions:
                        media_files.append(file_path)
                    elif file_path.suffix.lower() == '.json':
                        json_files.append(file_path)
            
            # Filter out extras if configured
            if context.config.skip_extras:
                media_files = self._filter_extras(media_files)
            
            # Update context
            context.media_files = media_files
            
            context.logger.info(f"Discovered {len(media_files)} media files and {len(json_files)} metadata files")
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Found {len(media_files)} media files",
                data={
                    'files_found': len(media_files),
                    'json_files_found': len(json_files),
                    'extras_skipped': context.config.skip_extras,
                    'media_files': [str(f) for f in media_files]  # Save file paths for next steps
                }
            )
            
        except Exception as e:
            context.logger.error(f"Media discovery failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Media discovery failed",
                error=str(e)
            )
    
    def _filter_extras(self, media_files: List[Path]) -> List[Path]:
        """Filter out 'extras' files (edited versions, etc.)"""
        filtered = []
        for file_path in media_files:
            # Skip files that appear to be edited versions
            name_lower = file_path.name.lower()
            if any(keyword in name_lower for keyword in ['-edited', '_edited', '(1)', '(2)', 'copy']):
                continue
            filtered.append(file_path)
        return filtered


class RemoveDuplicatesStep(ProcessingStep):
    """Step 3: Remove duplicate files using content hashing"""
    
    def __init__(self):
        super().__init__("Remove Duplicates")
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Remove duplicate files based on content hash"""
        try:
            # This will use the MediaHashService and DuplicateDetectionService
            # For now, implement basic duplicate detection
            from .media_hash import MediaHashService
            from .duplicate_detection import DuplicateDetectionService
            
            hash_service = MediaHashService(context.logger)
            duplicate_service = DuplicateDetectionService(context.logger, hash_service)
            
            # Group files by content hash
            unique_files, duplicates = duplicate_service.find_duplicates(context.media_files)
            
            # Update context with unique files
            context.media_files = unique_files
            
            context.logger.info(f"Removed {len(duplicates)} duplicate files")
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Removed {len(duplicates)} duplicates, {len(unique_files)} unique files remain",
                data={
                    'duplicates_removed': len(duplicates),
                    'unique_files': len(unique_files)
                }
            )
            
        except ImportError:
            # Services not implemented yet, use basic duplicate detection
            context.logger.warning("Advanced duplicate detection not available, using basic detection")
            
            unique_files, duplicates = self._basic_duplicate_detection(context.media_files, context.logger)
            context.media_files = unique_files
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Removed {len(duplicates)} duplicates (basic detection)",
                data={
                    'duplicates_removed': len(duplicates),
                    'unique_files': len(unique_files)
                }
            )
            
        except Exception as e:
            context.logger.error(f"Duplicate removal failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Duplicate removal failed",
                error=str(e)
            )
    
    def _basic_duplicate_detection(self, media_files: List[Path], logger) -> tuple[List[Path], List[Path]]:
        """Basic duplicate detection using file size"""
        import hashlib
        from collections import defaultdict
        
        size_groups = defaultdict(list)
        
        # Group by file size first
        for file_path in media_files:
            try:
                size = file_path.stat().st_size
                size_groups[size].append(file_path)
            except OSError:
                continue
        
        unique_files = []
        duplicates = []
        
        for size, files in size_groups.items():
            if len(files) == 1:
                unique_files.extend(files)
            else:
                # Check content hash for files with same size
                hash_map = {}
                for file_path in files:
                    try:
                        hasher = hashlib.md5()
                        with open(file_path, 'rb') as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                hasher.update(chunk)
                        file_hash = hasher.hexdigest()
                        
                        if file_hash in hash_map:
                            duplicates.append(file_path)
                        else:
                            hash_map[file_hash] = file_path
                            unique_files.append(file_path)
                    except Exception as e:
                        logger.warning(f"Could not hash {file_path}: {e}")
                        unique_files.append(file_path)
        
        return unique_files, duplicates


class ExtractDatesStep(ProcessingStep):
    """Step 4: Extract dates from metadata, EXIF, and filenames"""
    
    def __init__(self):
        super().__init__("Extract Dates")
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Extract dates from all media files"""
        try:
            service = DateExtractionService(context.logger)
            file_dates = {}
            extraction_stats = {}
            
            for file_path in context.media_files:
                date_taken = service.extract_date_from_file(
                    file_path,
                    guess_from_name=context.config.guess_from_name
                )
                file_dates[file_path] = date_taken
                
                # Track extraction method for statistics
                if date_taken:
                    # This would track which method was used
                    extraction_stats['successful'] = extraction_stats.get('successful', 0) + 1
                else:
                    extraction_stats['failed'] = extraction_stats.get('failed', 0) + 1
            
            # Update context
            context.file_dates = file_dates
            
            successful = sum(1 for date in file_dates.values() if date is not None)
            failed = len(file_dates) - successful
            
            context.logger.info(f"Extracted dates: {successful} successful, {failed} failed")
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Extracted dates for {successful}/{len(file_dates)} files",
                data={
                    'dates_extracted': successful,
                    'dates_failed': failed,
                    'extraction_method_stats': extraction_stats,
                    'file_dates': {str(k): v.isoformat() if v else None for k, v in file_dates.items()}  # Save dates for next steps
                }
            )
            
        except Exception as e:
            context.logger.error(f"Date extraction failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Date extraction failed",
                error=str(e)
            )


class WriteExifStep(ProcessingStep):
    """Step 5: Write EXIF metadata to files using ExifTool"""
    
    def __init__(self):
        super().__init__("Write EXIF")
        self._exif_writer = None
    
    def should_skip(self, context: ProcessingContext) -> bool:
        """Skip if EXIF writing is disabled"""
        return not context.config.write_exif
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Write EXIF data to media files"""
        try:
            # Initialize EXIF writer if not already done
            if self._exif_writer is None:
                from ..services.exif_writer import get_exif_writer
                self._exif_writer = get_exif_writer()
                
                # Log EXIF writer status
                status = self._exif_writer.get_status()
                if status['exiftool_available']:
                    context.logger.info(f"Using ExifTool {status['exiftool_version']} for EXIF writing")
                else:
                    context.logger.warning("ExifTool not available - using fallback methods")
            
            coordinates_written = 0
            datetimes_written = 0
            failed_writes = 0
            
            for file_path in context.media_files:
                if not self._exif_writer.is_supported_file(file_path):
                    continue
                    
                date_taken = context.file_dates.get(file_path)
                success = True
                
                # Write datetime if available
                if date_taken:
                    if self._exif_writer.write_datetime(file_path, date_taken, context.config.dry_run):
                        datetimes_written += 1
                        context.logger.debug(f"Wrote/would write EXIF datetime to {file_path}")
                    else:
                        success = False
                
                # TODO: Write GPS coordinates if available in JSON metadata
                # This would require parsing GPS data from Google Photos JSON files
                # For now, we'll focus on datetime writing
                
                if not success:
                    failed_writes += 1
            
            # Create summary message
            if context.config.dry_run:
                message = f"Would write EXIF to {datetimes_written} files"
            else:
                message = f"Wrote EXIF metadata to {datetimes_written} files"
                if failed_writes > 0:
                    message += f" ({failed_writes} failed)"
            
            context.logger.info(message)
            
            return StepResult(
                name=self.name,
                success=True,
                message=message,
                data={
                    'coordinates_written': coordinates_written,
                    'datetimes_written': datetimes_written,
                    'failed_writes': failed_writes,
                    'dry_run': context.config.dry_run,
                    'exiftool_available': self._exif_writer.get_status()['exiftool_available']
                }
            )
            
        except Exception as e:
            context.logger.error(f"EXIF writing failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="EXIF writing failed",
                error=str(e)
            )


class FindAlbumsStep(ProcessingStep):
    """Step 6: Find and detect album relationships"""
    
    def __init__(self):
        super().__init__("Find Albums")
    
    def should_skip(self, context: ProcessingContext) -> bool:
        """Skip if album mode is 'nothing'"""
        from .gpth_core_api import AlbumMode
        return context.config.album_mode == AlbumMode.NOTHING
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Discover albums and map files to albums"""
        try:
            service = AlbumDetectionService(context.logger)
            albums = service.discover_albums(context.input_path)
            
            # Update context
            # Convert string paths to Path objects for context
            context.albums = {name: [Path(f) if isinstance(f, str) else f for f in files]
                             for name, files in albums.items()}
            
            context.logger.info(f"Found {len(albums)} albums")
            
            return StepResult(
                name=self.name,
                success=True,
                message=f"Found {len(albums)} albums",
                data={
                    'albums_found': len(albums),
                    'album_names': list(albums.keys()),
                    'albums': {name: [str(f) for f in files] for name, files in albums.items()}  # Save album mappings for next steps
                }
            )
            
        except Exception as e:
            context.logger.error(f"Album detection failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Album detection failed",
                error=str(e)
            )


class MoveFilesStep(ProcessingStep):
    """Step 7: Move files according to album strategy"""
    
    def __init__(self):
        super().__init__("Move Files")
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Move and organize files using the selected album strategy"""
        try:
            # Create path generator
            path_generator = PathGenerator(
                str(context.output_path),
                context.config.date_division,
                context.config.divide_partner_shared
            )
            
            # Select album strategy
            strategy = self._create_album_strategy(
                context.config.album_mode,
                path_generator,
                context.logger,
                context.config
            )
            
            # Process each file
            files_moved = 0
            for file_path in context.media_files:
                if context.config.dry_run:
                    context.logger.debug(f"Would move {file_path}")
                    files_moved += 1
                else:
                    date_taken = context.file_dates.get(file_path, datetime.now())
                    file_albums = self._get_file_albums(file_path, context.albums)
                    is_partner_shared = self._is_partner_shared(file_path)
                    
                    try:
                        if date_taken is not None:
                            strategy.process_file(file_path, date_taken, file_albums, is_partner_shared)
                        else:
                            # Use current time as fallback
                            strategy.process_file(file_path, datetime.now(), file_albums, is_partner_shared)
                        files_moved += 1
                    except Exception as e:
                        context.logger.warning(f"Could not move {file_path}: {e}")
            
            # Finalize strategy operations
            if not context.config.dry_run:
                strategy.finalize(context.media_files)
            
            message = f"Moved {files_moved} files" if not context.config.dry_run else f"Would move {files_moved} files"
            context.logger.info(message)
            
            return StepResult(
                name=self.name,
                success=True,
                message=message,
                data={
                    'files_moved': files_moved,
                    'dry_run': context.config.dry_run
                }
            )
            
        except Exception as e:
            context.logger.error(f"File moving failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="File moving failed",
                error=str(e)
            )
    
    def _create_album_strategy(self, album_mode, path_generator, logger, config) -> AlbumStrategy:
        """Create the appropriate album strategy"""
        from .gpth_core_api import AlbumMode
        
        if album_mode == AlbumMode.SHORTCUT:
            return ShortcutStrategy(path_generator, logger, config)
        elif album_mode == AlbumMode.DUPLICATE_COPY:
            return DuplicateCopyStrategy(path_generator, logger, config)
        elif album_mode == AlbumMode.REVERSE_SHORTCUT:
            return ReverseShortcutStrategy(path_generator, logger, config)
        elif album_mode == AlbumMode.JSON:
            return JsonStrategy(path_generator, logger, config)
        else:  # AlbumMode.NOTHING
            return NothingStrategy(path_generator, logger, config)
    
    def _get_file_albums(self, file_path: Path, albums: Dict[str, List[Path]]) -> List[str]:
        """Get list of album names that contain this file"""
        file_albums = []
        for album_name, album_files in albums.items():
            if file_path in album_files or str(file_path) in [str(f) for f in album_files]:
                file_albums.append(album_name)
        return file_albums
    
    def _is_partner_shared(self, file_path: Path) -> bool:
        """Determine if file is partner shared"""
        # Simple heuristic - look for partner indicators in path
        path_str = str(file_path).lower()
        return 'partner' in path_str or 'shared' in path_str


class UpdateCreationTimeStep(ProcessingStep):
    """Step 8: Update file creation timestamps using platform services"""
    
    def __init__(self):
        super().__init__("Update Creation Time")
        self._timestamp_service = None
    
    def should_skip(self, context: ProcessingContext) -> bool:
        """Skip if creation time updates are disabled"""
        return not context.config.update_creation_time
    
    def execute(self, context: ProcessingContext) -> StepResult:
        """Update file creation times to match extracted dates"""
        try:
            # Initialize platform services if not already done
            if self._timestamp_service is None:
                from ..services.platform_services import get_timestamp_service
                self._timestamp_service = get_timestamp_service()
                
                if self._timestamp_service:
                    platform_name = self._timestamp_service.get_platform_name()
                    context.logger.info(f"Using {platform_name} timestamp service")
                else:
                    context.logger.warning("No platform-specific timestamp service available")
            
            times_updated = 0
            creation_times_updated = 0
            access_mod_times_updated = 0
            
            for file_path in context.media_files:
                date_taken = context.file_dates.get(file_path)
                if date_taken and file_path.exists():
                    try:
                        if not context.config.dry_run and self._timestamp_service:
                            # Try to update creation time first (Windows/macOS)
                            creation_success = self._timestamp_service.update_creation_time(file_path, date_taken)
                            if creation_success:
                                creation_times_updated += 1
                            
                            # Always update access/modification time as fallback
                            access_mod_success = self._timestamp_service.update_access_and_modification_time(file_path, date_taken)
                            if access_mod_success:
                                access_mod_times_updated += 1
                            
                            if creation_success or access_mod_success:
                                times_updated += 1
                                context.logger.debug(f"Updated timestamps for {file_path}")
                            else:
                                context.logger.warning(f"Could not update any timestamps for {file_path}")
                        else:
                            # Dry run mode
                            times_updated += 1
                            context.logger.debug(f"Would update timestamps for {file_path}")
                            
                    except Exception as e:
                        context.logger.warning(f"Could not update timestamps for {file_path}: {e}")
            
            # Create detailed message
            if not context.config.dry_run:
                message_parts = []
                if creation_times_updated > 0:
                    message_parts.append(f"{creation_times_updated} creation times")
                if access_mod_times_updated > 0:
                    message_parts.append(f"{access_mod_times_updated} access/modification times")
                message = f"Updated {' and '.join(message_parts)}" if message_parts else f"Updated {times_updated} timestamps"
            else:
                message = f"Would update {times_updated} timestamps"
                
            context.logger.info(message)
            
            return StepResult(
                name=self.name,
                success=True,
                message=message,
                data={
                    'creation_times_updated': times_updated,
                    'creation_times_set': creation_times_updated,
                    'access_mod_times_set': access_mod_times_updated,
                    'dry_run': context.config.dry_run,
                    'platform_service': self._timestamp_service.get_platform_name() if self._timestamp_service else None
                }
            )
            
        except Exception as e:
            context.logger.error(f"Creation time update failed: {e}", exc_info=True)
            return StepResult(
                name=self.name,
                success=False,
                message="Creation time update failed",
                error=str(e)
            )