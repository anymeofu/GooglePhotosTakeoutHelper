"""
Album Processing Strategies
Ported from Dart implementation - handles different album modes
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from .path_generator import PathGenerator


class AlbumStrategy(ABC):
    """Base class for album processing strategies"""
    
    def __init__(self, path_generator: PathGenerator, logger, config):
        self.path_generator = path_generator
        self.logger = logger
        self.config = config
    
    @abstractmethod
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        """Process a single file according to this strategy"""
        pass
    
    @abstractmethod
    def finalize(self, all_files: List[Path]) -> None:
        """Perform any final operations after all files are processed"""
        pass


class ShortcutStrategy(AlbumStrategy):
    """Creates symbolic links from album folders to files in ALL_PHOTOS"""
    
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        # Step 1: Move file to ALL_PHOTOS (or PARTNER_SHARED)
        target_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
        moved_file = self._move_single_file(file_path, target_dir, date_taken)
        
        # Step 2: Create symbolic links in album folders
        for album_name in file_albums:
            try:
                album_dir = self.path_generator.generate_target_directory(album_name, date_taken, is_partner_shared)
                album_dir.mkdir(parents=True, exist_ok=True)
                link_path = album_dir / moved_file.name
                
                if not self.config.dry_run:
                    if link_path.exists():
                        link_path.unlink()
                    link_path.symlink_to(moved_file)
                    self.logger.debug(f"Created symlink {link_path} -> {moved_file}")
                else:
                    self.logger.info(f"DRY RUN: Would create symlink {link_path} -> {moved_file}")
            except Exception as e:
                self.logger.warning(f"Could not create symlink for {album_name}: {e}")
    
    def _move_single_file(self, file_path: Path, target_dir: Path, date_taken: datetime) -> Path:
        """Move a single file to target directory with conflict resolution"""
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = target_dir / file_path.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_file = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not self.config.dry_run:
            shutil.move(str(file_path), str(dest_file))
            self.logger.debug(f"Moved {file_path} to {dest_file}")
        else:
            self.logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
        
        return dest_file
    
    def finalize(self, all_files: List[Path]) -> None:
        """No finalization needed for shortcut mode"""
        pass


class DuplicateCopyStrategy(AlbumStrategy):
    """Creates actual file copies in both ALL_PHOTOS and album folders"""
    
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        # Step 1: Move file to ALL_PHOTOS (or PARTNER_SHARED)
        target_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
        moved_file = self._move_single_file(file_path, target_dir, date_taken)
        
        # Step 2: Copy file to each album folder
        for album_name in file_albums:
            try:
                album_dir = self.path_generator.generate_target_directory(album_name, date_taken, is_partner_shared)
                album_dir.mkdir(parents=True, exist_ok=True)
                copy_path = album_dir / moved_file.name
                
                if not self.config.dry_run:
                    shutil.copy2(moved_file, copy_path)
                    self.logger.debug(f"Copied {moved_file} to {copy_path}")
                else:
                    self.logger.info(f"DRY RUN: Would copy {moved_file} to {copy_path}")
            except Exception as e:
                self.logger.warning(f"Could not copy to {album_name}: {e}")
    
    def _move_single_file(self, file_path: Path, target_dir: Path, date_taken: datetime) -> Path:
        """Move a single file to target directory with conflict resolution"""
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = target_dir / file_path.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_file = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not self.config.dry_run:
            shutil.move(str(file_path), str(dest_file))
            self.logger.debug(f"Moved {file_path} to {dest_file}")
        else:
            self.logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
        
        return dest_file
    
    def finalize(self, all_files: List[Path]) -> None:
        """No finalization needed for duplicate copy mode"""
        pass


class ReverseShortcutStrategy(AlbumStrategy):
    """Files stay in albums, shortcuts created in ALL_PHOTOS"""
    
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        if file_albums:
            # Move file to first album
            first_album = file_albums[0]
            album_dir = self.path_generator.generate_target_directory(first_album, date_taken, is_partner_shared)
            moved_file = self._move_single_file(file_path, album_dir, date_taken)
            
            # Create symlink in ALL_PHOTOS
            all_photos_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
            all_photos_dir.mkdir(parents=True, exist_ok=True)
            link_path = all_photos_dir / moved_file.name
            
            if not self.config.dry_run:
                if link_path.exists():
                    link_path.unlink()
                link_path.symlink_to(moved_file)
                self.logger.debug(f"Created reverse symlink {link_path} -> {moved_file}")
            else:
                self.logger.info(f"DRY RUN: Would create reverse symlink {link_path} -> {moved_file}")
            
            # Create symlinks in other albums
            for album_name in file_albums[1:]:
                try:
                    other_album_dir = self.path_generator.generate_target_directory(album_name, date_taken, is_partner_shared)
                    other_album_dir.mkdir(parents=True, exist_ok=True)
                    other_link_path = other_album_dir / moved_file.name
                    
                    if not self.config.dry_run:
                        if other_link_path.exists():
                            other_link_path.unlink()
                        other_link_path.symlink_to(moved_file)
                        self.logger.debug(f"Created album symlink {other_link_path} -> {moved_file}")
                    else:
                        self.logger.info(f"DRY RUN: Would create album symlink {other_link_path} -> {moved_file}")
                except Exception as e:
                    self.logger.warning(f"Could not create symlink in {album_name}: {e}")
        else:
            # No albums, move to ALL_PHOTOS anyway
            target_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
            self._move_single_file(file_path, target_dir, date_taken)
    
    def _move_single_file(self, file_path: Path, target_dir: Path, date_taken: datetime) -> Path:
        """Move a single file to target directory with conflict resolution"""
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = target_dir / file_path.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_file = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not self.config.dry_run:
            shutil.move(str(file_path), str(dest_file))
            self.logger.debug(f"Moved {file_path} to {dest_file}")
        else:
            self.logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
        
        return dest_file
    
    def finalize(self, all_files: List[Path]) -> None:
        """No finalization needed for reverse shortcut mode"""
        pass


class JsonStrategy(AlbumStrategy):
    """Creates albums-info.json with metadata"""
    
    def __init__(self, path_generator: PathGenerator, logger, config):
        super().__init__(path_generator, logger, config)
        self._album_info: Dict[str, List[str]] = {}
    
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        # Move file to ALL_PHOTOS (or PARTNER_SHARED)
        target_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
        moved_file = self._move_single_file(file_path, target_dir, date_taken)
        
        # Track album associations for JSON file
        file_name = moved_file.name
        for album_name in file_albums:
            if album_name not in self._album_info:
                self._album_info[album_name] = []
            self._album_info[album_name].append(file_name)
    
    def _move_single_file(self, file_path: Path, target_dir: Path, date_taken: datetime) -> Path:
        """Move a single file to target directory with conflict resolution"""
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = target_dir / file_path.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_file = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not self.config.dry_run:
            shutil.move(str(file_path), str(dest_file))
            self.logger.debug(f"Moved {file_path} to {dest_file}")
        else:
            self.logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
        
        return dest_file
    
    def finalize(self, all_files: List[Path]) -> None:
        """Generate albums-info.json file"""
        output_path = Path(self.config.output_path)
        json_path = output_path / 'albums-info.json'
        
        album_data = {
            'albums': self._album_info,
            'metadata': {
                'generated': datetime.now().isoformat(),
                'total_albums': len(self._album_info),
                'total_files': len(all_files),
                'strategy': 'json',
            },
        }
        
        if not self.config.dry_run:
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(album_data, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Generated albums-info.json with {len(self._album_info)} albums")
            except Exception as e:
                self.logger.error(f"Could not create albums-info.json: {e}")
        else:
            self.logger.info(f"DRY RUN: Would generate albums-info.json with {len(self._album_info)} albums")


class NothingStrategy(AlbumStrategy):
    """Ignores albums, moves everything to ALL_PHOTOS chronologically"""
    
    def process_file(self, file_path: Path, date_taken: datetime, 
                    file_albums: List[str], is_partner_shared: bool) -> None:
        # Simply move to ALL_PHOTOS (or PARTNER_SHARED) - ignore albums
        target_dir = self.path_generator.generate_target_directory(None, date_taken, is_partner_shared)
        self._move_single_file(file_path, target_dir, date_taken)
    
    def _move_single_file(self, file_path: Path, target_dir: Path, date_taken: datetime) -> Path:
        """Move a single file to target directory with conflict resolution"""
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = target_dir / file_path.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_file = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not self.config.dry_run:
            shutil.move(str(file_path), str(dest_file))
            self.logger.debug(f"Moved {file_path} to {dest_file}")
        else:
            self.logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
        
        return dest_file
    
    def finalize(self, all_files: List[Path]) -> None:
        """No finalization needed for nothing mode"""
        pass


def create_album_strategy(album_mode, path_generator: PathGenerator, logger, config) -> AlbumStrategy:
    """Factory function to create the appropriate album strategy"""
    from .gpth_core_api import AlbumMode
    
    if album_mode == AlbumMode.SHORTCUT:
        return ShortcutStrategy(path_generator, logger, config)
    elif album_mode == AlbumMode.DUPLICATE_COPY:
        return DuplicateCopyStrategy(path_generator, logger, config)
    elif album_mode == AlbumMode.REVERSE_SHORTCUT:
        return ReverseShortcutStrategy(path_generator, logger, config)
    elif album_mode == AlbumMode.JSON:
        return JsonStrategy(path_generator, logger, config)
    elif album_mode == AlbumMode.NOTHING:
        return NothingStrategy(path_generator, logger, config)
    else:
        raise ValueError(f"Unknown album mode: {album_mode}")