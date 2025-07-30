"""
Enhanced Interactive Service

Comprehensive interactive mode with all features from Dart version:
- Data source selection (ZIP vs folder)
- Complete configuration prompts
- Integration with validation and space checking services
- User guidance and recommendations

Implements all 15+ configuration options mentioned in bugs.md
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging

from src.services.zip_extraction_service import ZipExtractionService, create_zip_extraction_service
from src.services.takeout_validator_service import TakeoutValidationService, create_takeout_validator
from src.services.disk_space_service import DiskSpaceService, create_disk_space_service
from src.core.gpth_core_api import ProcessingConfig, AlbumMode, ExtensionFixMode

logger = logging.getLogger(__name__)


class EnhancedInteractiveService:
    """
    Enhanced interactive service providing comprehensive user prompts
    and intelligent guidance throughout the configuration process.
    """
    
    def __init__(self):
        self.zip_service = create_zip_extraction_service()
        self.validator = create_takeout_validator()
        self.space_service = create_disk_space_service()
        self.use_zip_mode = False
        self.temp_extraction_dir: Optional[Path] = None
    
    def run_enhanced_interactive_mode(self) -> Tuple[ProcessingConfig, Dict[str, Any]]:
        """
        Run the complete enhanced interactive mode.
        
        Returns:
            Tuple of (ProcessingConfig, additional_settings)
        """
        print("🎨 Google Photos Takeout Helper - Enhanced Interactive Mode")
        print("=" * 60)
        print("📋 This wizard will guide you through all configuration options")
        print()
        
        # Step 1: Data source selection
        print("=" * 20, "STEP 1: DATA SOURCE", "=" * 20)
        input_path, self.use_zip_mode = self._ask_data_source()
        
        # Step 2: Input validation
        print("\n" + "=" * 20, "STEP 2: VALIDATION", "=" * 20)
        validated_input = self._validate_and_guide_input(input_path)
        
        # Step 3: Output configuration
        print("\n" + "=" * 20, "STEP 3: OUTPUT SETUP", "=" * 20)
        output_path = self._ask_output_configuration()
        
        # Step 4: Album behavior
        print("\n" + "=" * 20, "STEP 4: ALBUM BEHAVIOR", "=" * 20)
        album_mode = self._ask_album_behavior()
        
        # Step 5: Date organization
        print("\n" + "=" * 20, "STEP 5: DATE ORGANIZATION", "=" * 20)
        date_division = self._ask_date_division()
        
        # Step 6: File handling
        print("\n" + "=" * 20, "STEP 6: FILE HANDLING", "=" * 20)
        extension_mode = self._ask_extension_fixing()
        partner_sharing = self._ask_partner_sharing()
        
        # Step 7: Metadata options
        print("\n" + "=" * 20, "STEP 7: METADATA OPTIONS", "=" * 20)
        write_exif = self._ask_exif_writing()
        guess_dates = self._ask_date_guessing()
        pixel_transform = self._ask_pixel_transform()
        
        # Step 8: System options
        print("\n" + "=" * 20, "STEP 8: SYSTEM OPTIONS", "=" * 20)
        update_timestamps = self._ask_creation_time_updates()
        max_workers = self._ask_thread_count()
        file_size_limit = self._ask_file_size_limiting()
        
        # Step 9: Processing options
        print("\n" + "=" * 20, "STEP 9: PROCESSING MODE", "=" * 20)
        dry_run, verbose = self._ask_processing_options()
        
        # Step 10: Space validation
        print("\n" + "=" * 20, "STEP 10: SPACE CHECK", "=" * 20)
        space_ok = self._perform_space_validation(validated_input, output_path, album_mode.value)
        if not space_ok:
            space_continue = input("\n⚠️  Continue anyway? [y/N]: ").lower().startswith('y')
            if not space_continue:
                print("❌ Processing cancelled due to space concerns")
                sys.exit(1)
        
        # Step 11: Final confirmation
        print("\n" + "=" * 20, "FINAL CONFIRMATION", "=" * 20)
        self._show_configuration_summary(validated_input, output_path, album_mode, 
                                       extension_mode, dry_run)
        
        confirm = input("\n✅ Start processing with these settings? [Y/n]: ")
        if confirm.lower() in ['n', 'no']:
            print("❌ Processing cancelled by user")
            sys.exit(0)
        
        # Create configuration
        config = ProcessingConfig(
            input_path=str(validated_input),
            output_path=str(output_path),
            album_mode=album_mode,
            extension_fix_mode=extension_mode,
            update_creation_time=update_timestamps,
            write_exif=write_exif,
            guess_from_name=guess_dates,
            verbose=verbose,
            max_threads=max_workers,
            dry_run=dry_run
        )
        
        # Additional settings for future use
        additional_settings = {
            'use_zip_mode': self.use_zip_mode,
            'temp_extraction_dir': self.temp_extraction_dir,
            'date_division': date_division,
            'partner_sharing': partner_sharing,
            'pixel_transform': pixel_transform,
            'file_size_limit_mb': file_size_limit
        }
        
        return config, additional_settings
    
    def _ask_data_source(self) -> Tuple[Path, bool]:
        """Ask user to select data source type."""
        print("📂 What type of data do you want to process?")
        print("1) 📁 Already extracted folder (Google Takeout unzipped)")
        print("2) 🗜️  ZIP files from Google Takeout (will extract automatically)")
        
        while True:
            choice = input("\nChoice [1]: ").strip() or "1"
            
            if choice == "1":
                path = self._ask_folder_path()
                return path, False
            elif choice == "2":
                zip_files = self._ask_zip_files()
                extraction_dir = self._ask_extraction_location()
                extracted_path = self._extract_zip_files(zip_files, extraction_dir)
                return extracted_path, True
            else:
                print("❌ Please enter 1 or 2")
    
    def _ask_folder_path(self) -> Path:
        """Ask for folder path with validation."""
        while True:
            path_str = input("📁 Enter the path to your extracted Takeout folder: ").strip()
            path = Path(path_str)
            
            if not path.exists():
                print(f"❌ Path does not exist: {path}")
                continue
                
            if not path.is_dir():
                print(f"❌ Path is not a directory: {path}")
                continue
                
            return path
    
    def _ask_zip_files(self) -> List[Path]:
        """Ask for ZIP file paths."""
        print("\n📥 Enter ZIP file paths (one per line, empty line to finish):")
        zip_files = []
        
        while True:
            zip_path = input(f"ZIP file {len(zip_files) + 1}: ").strip()
            if not zip_path:
                break
                
            path = Path(zip_path)
            if not path.exists():
                print(f"❌ File not found: {path}")
                continue
                
            if not path.suffix.lower() == '.zip':
                print(f"❌ Not a ZIP file: {path}")
                continue
                
            zip_files.append(path)
        
        if not zip_files:
            print("❌ No ZIP files specified, switching to folder mode")
            return [self._ask_folder_path()]
            
        return zip_files
    
    def _ask_extraction_location(self) -> Path:
        """Ask where to extract ZIP files."""
        print("\n📦 Where should ZIP files be extracted?")
        default_dir = Path.cwd() / "extracted_takeout"
        
        extract_path = input(f"Extraction directory [{default_dir}]: ").strip()
        if not extract_path:
            extract_path = default_dir
        else:
            extract_path = Path(extract_path)
            
        return extract_path
    
    def _extract_zip_files(self, zip_files: List[Path], extraction_dir: Path) -> Path:
        """Extract ZIP files and return the extracted path."""
        print(f"\n🗜️  Extracting {len(zip_files)} ZIP files to {extraction_dir}...")
        
        # Set up progress callback
        def progress_callback(progress):
            print(f"📁 {progress.current_file} ({progress.files_extracted}/{progress.total_files})")
        
        self.zip_service.set_progress_callback(progress_callback)
        
        try:
            result = self.zip_service.extract_zip_files(zip_files, extraction_dir)
            
            if result.success:
                print(f"✅ Successfully extracted {result.extracted_files} files")
                self.temp_extraction_dir = extraction_dir
                return result.extraction_path
            else:
                print(f"❌ Extraction failed: {'; '.join(result.errors)}")
                if result.warnings:
                    print(f"⚠️  Warnings: {'; '.join(result.warnings)}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            sys.exit(1)
    
    def _validate_and_guide_input(self, input_path: Path) -> Path:
        """Validate input structure and provide guidance."""
        print(f"🔍 Validating Takeout structure at: {input_path}")
        
        validation_result = self.validator.validate_takeout_structure(input_path)
        
        print(f"📊 Validation Score: {validation_result.validation_score:.1f}/1.0")
        print(f"📁 Structure Type: {validation_result.structure_type}")
        print(f"📸 Media Files Found: {validation_result.total_media_files}")
        print(f"💾 Estimated Size: {validation_result.estimated_size_mb:.1f} MB")
        
        # Show user guidance
        if validation_result.user_guidance:
            print(f"\n💡 {validation_result.user_guidance}")
        
        # Show issues and warnings
        if validation_result.issues:
            print(f"\n❌ Issues found:")
            for issue in validation_result.issues:
                print(f"   • {issue}")
        
        if validation_result.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in validation_result.warnings:
                print(f"   • {warning}")
        
        # Show recommendations
        if validation_result.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in validation_result.recommendations:
                print(f"   • {rec}")
        
        # Use recommended path if available
        if validation_result.recommended_input_path and validation_result.recommended_input_path != input_path:
            print(f"\n📁 Recommended input path: {validation_result.recommended_input_path}")
            use_recommended = input("Use recommended path? [Y/n]: ").lower()
            if use_recommended not in ['n', 'no']:
                return validation_result.recommended_input_path
        
        return input_path
    
    def _ask_output_configuration(self) -> Path:
        """Configure output directory."""
        while True:
            output_str = input("📦 Enter output directory path: ").strip()
            output_path = Path(output_str)
            
            # Check if directory exists and is not empty
            if output_path.exists() and any(output_path.iterdir()):
                print(f"⚠️  Output directory is not empty: {output_path}")
                print("1) Use anyway (files may be overwritten)")
                print("2) Choose different directory")
                print("3) Clear directory first")
                
                clean_choice = input("Choice [1]: ").strip() or "1"
                
                if clean_choice == "2":
                    continue
                elif clean_choice == "3":
                    import shutil
                    confirm = input("❗ Really delete all contents? [y/N]: ").lower().startswith('y')
                    if confirm:
                        shutil.rmtree(output_path)
                        output_path.mkdir(parents=True)
            
            return output_path
    
    def _ask_album_behavior(self) -> AlbumMode:
        """Ask about album organization behavior."""
        print("📁 How should albums be organized?")
        print("1) 📁 Shortcuts (recommended) - Create shortcuts in album folders")
        print("2) 📋 JSON metadata - Store album info in JSON files")
        print("3) 📄 Nothing - Photos by date only, no album organization")
        print("4) 🔄 Reverse shortcuts - Photos in albums, shortcuts in date folders")
        print("5) 📂 Duplicate copy - Copy files to both album and date folders")
        
        print("\n💡 Shortcuts save space by avoiding file duplication")
        print("💡 Duplicate copy uses 2x disk space but works with all software")
        
        while True:
            choice = input("\nChoice [1]: ").strip() or "1"
            
            album_modes = {
                "1": AlbumMode.SHORTCUT,
                "2": AlbumMode.JSON,
                "3": AlbumMode.NOTHING,
                "4": AlbumMode.REVERSE_SHORTCUT,
                "5": AlbumMode.DUPLICATE_COPY
            }
            
            if choice in album_modes:
                return album_modes[choice]
            else:
                print("❌ Please enter a number from 1-5")
    
    def _ask_date_division(self) -> int:
        """Ask about date-based folder organization."""
        print("\n📅 Date-based folder organization:")
        print("0) No date folders - all files in output directory")
        print("1) Year folders only (2023/)")
        print("2) Year-month folders (2023/01-January/)")
        print("3) Year-month-day folders (2023/01-January/15/)")
        
        while True:
            choice = input("Choice [2]: ").strip() or "2"
            try:
                level = int(choice)
                if level in [0, 1, 2, 3]:
                    return level
                else:
                    print("❌ Please enter 0, 1, 2, or 3")
            except ValueError:
                print("❌ Please enter a number")
    
    def _ask_extension_fixing(self) -> ExtensionFixMode:
        """Ask about file extension fixing."""
        print("\n🔧 File extension handling:")
        print("1) Standard fixes - Fix common issues (recommend)")
        print("2) Conservative - Only fix obvious problems")
        print("3) Aggressive - Fix all possible extension issues")
        print("4) None - Don't modify file extensions")
        
        print("\n💡 Standard mode fixes files like 'IMG_1234.JPG' → 'IMG_1234.jpg'")
        print("💡 Conservative mode only fixes clear mismatches")
        
        while True:
            choice = input("Choice [1]: ").strip() or "1"
            
            modes = {
                "1": ExtensionFixMode.STANDARD,
                "2": ExtensionFixMode.CONSERVATIVE,
                "3": ExtensionFixMode.SOLO,
                "4": ExtensionFixMode.NONE
            }
            
            if choice in modes:
                return modes[choice]
            else:
                print("❌ Please enter 1, 2, 3, or 4")
    
    def _ask_partner_sharing(self) -> bool:
        """Ask about handling partner-shared content."""
        print("\n👥 Partner-shared content handling:")
        print("Google Photos marks some content as shared by partners/family")
        
        choice = input("Separate partner-shared photos into different folders? [Y/n]: ")
        return not choice.lower().startswith('n')
    
    def _ask_exif_writing(self) -> bool:
        """Ask about EXIF metadata writing."""
        print("\n📊 EXIF metadata writing:")
        print("Write date/time information into photo EXIF data?")
        print("(Recommended for photo organizing software)")
        
        choice = input("Write EXIF metadata? [Y/n]: ")
        return not choice.lower().startswith('n')
    
    def _ask_date_guessing(self) -> bool:
        """Ask about date guessing from filenames."""
        print("\n🔤 Date extraction from filenames:")
        print("Try to extract dates from filenames like 'IMG_20230101_123456.jpg'?")
        print("(Used when EXIF data is missing)")
        
        choice = input("Guess dates from filenames? [Y/n]: ")
        return not choice.lower().startswith('n')
    
    def _ask_pixel_transform(self) -> bool:
        """Ask about Google Pixel motion photo transformation."""
        print("\n📱 Google Pixel motion photo handling:")
        print("Convert Google Pixel motion photos (.MP/.MV files) to .mp4 videos?")
        print("(Requires additional processing time)")
        
        choice = input("Transform Pixel motion photos? [y/N]: ")
        return choice.lower().startswith('y')
    
    def _ask_creation_time_updates(self) -> bool:
        """Ask about file creation time updates (Windows only)."""
        if os.name != 'nt':  # Not Windows
            print("\n📅 File timestamp updates not available on this platform")
            return False
            
        print("\n📅 File creation time updates (Windows):")
        print("Update file creation timestamps to match photo dates?")
        print("(May take additional time)")
        
        choice = input("Update file timestamps? [y/N]: ")
        return choice.lower().startswith('y')
    
    def _ask_thread_count(self) -> int:
        """Ask about number of processing threads."""
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        recommended = min(4, cpu_count)
        
        print(f"\n⚡ Processing threads:")
        print(f"Your system has {cpu_count} CPU cores")
        print(f"Recommended: {recommended} threads (balance of speed vs stability)")
        
        while True:
            choice = input(f"Number of threads [1-{cpu_count}] [{recommended}]: ").strip()
            if not choice:
                return recommended
                
            try:
                threads = int(choice)
                if 1 <= threads <= cpu_count:
                    return threads
                else:
                    print(f"❌ Please enter a number between 1 and {cpu_count}")
            except ValueError:
                print("❌ Please enter a number")
    
    def _ask_file_size_limiting(self) -> Optional[int]:
        """Ask about file size limiting for low-memory systems."""
        print("\n💾 File size limiting:")
        print("Skip processing very large files? (for low-memory systems)")
        print("Large files (>100MB) can cause memory issues on some systems")
        
        choice = input("Enable file size limiting? [y/N]: ").lower()
        if not choice.startswith('y'):
            return None
            
        while True:
            size_str = input("Maximum file size in MB [100]: ").strip() or "100"
            try:
                size_mb = int(size_str)
                if size_mb > 0:
                    return size_mb
                else:
                    print("❌ Please enter a positive number")
            except ValueError:
                print("❌ Please enter a number")
    
    def _ask_processing_options(self) -> Tuple[bool, bool]:
        """Ask about dry run and verbose options."""
        print("\n🔍 Processing mode:")
        dry_run = input("Dry run mode (preview changes without making them)? [y/N]: ").lower().startswith('y')
        
        print("\n📢 Output verbosity:")
        verbose = input("Verbose output (detailed progress information)? [y/N]: ").lower().startswith('y')
        
        return dry_run, verbose
    
    def _perform_space_validation(self, input_path: Path, output_path: Path, album_behavior: str) -> bool:
        """Perform disk space validation."""
        print("💾 Checking disk space requirements...")
        
        try:
            validation_result = self.space_service.validate_space_for_processing(
                [input_path], output_path, album_behavior
            )
            
            if validation_result.disk_info:
                space_info = self.space_service.format_space_info(validation_result.disk_info)
                print(f"💽 {space_info}")
            
            required_gb = validation_result.required_space / (1024 ** 3)
            available_gb = validation_result.available_space / (1024 ** 3)
            
            print(f"📊 Required space: {required_gb:.1f} GB")
            print(f"📊 Available space: {available_gb:.1f} GB")
            
            if validation_result.is_sufficient:
                print("✅ Sufficient disk space available")
                return True
            else:
                deficit_gb = validation_result.deficit_bytes / (1024 ** 3)
                print(f"❌ Insufficient space! Need {deficit_gb:.1f} GB more")
                
                if validation_result.recommendations:
                    print("\n💡 Recommendations:")
                    for rec in validation_result.recommendations:
                        print(f"   • {rec}")
                        
                return False
                
        except Exception as e:
            print(f"⚠️  Could not check disk space: {e}")
            return True  # Continue with warning
    
    def _show_configuration_summary(self, input_path: Path, output_path: Path, 
                                  album_mode: AlbumMode, extension_mode: ExtensionFixMode,
                                  dry_run: bool):
        """Show final configuration summary."""
        print("📋 Configuration Summary:")
        print("-" * 40)
        print(f"📁 Input: {input_path}")
        print(f"📦 Output: {output_path}")
        print(f"📁 Album mode: {album_mode.value}")
        print(f"🔧 Extension handling: {extension_mode.value}")
        print(f"🔍 Mode: {'DRY RUN (preview only)' if dry_run else 'FULL PROCESSING'}")
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE: No files will be moved or modified")


def create_enhanced_interactive_service() -> EnhancedInteractiveService:
    """Factory function to create enhanced interactive service."""
    return EnhancedInteractiveService()