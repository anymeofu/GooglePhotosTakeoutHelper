"""
Interactive Presenter - UI/Business Logic Separation

This module implements the presenter pattern to separate UI concerns from business logic
in the interactive mode. It provides clean separation between user interface interactions
and the underlying processing logic.

Features:
- Clear separation of UI and business logic
- Testable presentation layer
- Consistent user interaction patterns
- Integration with type-safe configuration models
- Support for different UI modes (console, future GUI)

Based on Dart reference: dart-version/lib/presentation/interactive_presenter.dart
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Protocol, Union
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.processing_config import (
    ProcessingConfig, InputConfiguration, OutputConfiguration,
    AlbumConfiguration, MediaProcessingConfiguration, DateTimeConfiguration,
    SystemConfiguration, AlbumBehavior, ExtensionFixingMode, DateDivisionLevel,
    ValidationLevel, create_default_config
)
from ..services.zip_extraction_service import ZipExtractionService
from ..services.takeout_validator_service import TakeoutValidationService
from ..services.disk_space_service import DiskSpaceService
from ..services.progress_reporting_service import ProgressReporter

logger = logging.getLogger(__name__)


class UIMode(Enum):
    """User interface mode types."""
    CONSOLE = "console"
    GUI = "gui"
    SILENT = "silent"


@dataclass
class UserChoice:
    """Represents a user's choice from a selection."""
    value: Any
    display_text: str
    description: Optional[str] = None
    is_default: bool = False


@dataclass
class ValidationResult:
    """Result of user input validation."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    corrected_value: Any = None
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class IUserInterface(Protocol):
    """Protocol defining the user interface contract."""
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Display a message to the user."""
        ...
    def prompt_text(self, prompt: str, default: Optional[str] = None) -> str:
        """Prompt user for text input."""
        ...
    def prompt_choice(self, prompt: str, choices: List[UserChoice], 
                     allow_custom: bool = False) -> UserChoice:
        """Prompt user to select from choices."""
        ...
    def prompt_yes_no(self, prompt: str, default: Optional[bool] = None) -> bool:
        """Prompt user for yes/no input."""
        ...
    def prompt_path(self, prompt: str, must_exist: bool = True, 
                   is_directory: bool = True) -> Path:
        """Prompt user for file/directory path."""
        ...
    def show_progress(self, message: str) -> None:
        """Show progress indication.""" 
        ...
    def show_validation_result(self, result: ValidationResult) -> None:
        """Display validation results."""
        ...


class ConsoleInterface:
    """Console-based user interface implementation."""
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and self._supports_colors()
        self.colors = {
            'info': '\033[94m' if self.use_colors else '',
            'warning': '\033[93m' if self.use_colors else '',
            'error': '\033[91m' if self.use_colors else '',
            'success': '\033[92m' if self.use_colors else '',
            'reset': '\033[0m' if self.use_colors else '',
            'bold': '\033[1m' if self.use_colors else '',
            'dim': '\033[2m' if self.use_colors else ''
        }
    def _supports_colors(self) -> bool:
        """Check if terminal supports colors."""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and 
                os.name != 'nt') or os.getenv('FORCE_COLOR', '').lower() in ('1', 'true', 'yes')
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Display a colored message to the user."""
        color = self.colors.get(message_type, '')
        reset = self.colors['reset']
        emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }.get(message_type, '')
        print(f"{color}{emoji} {message}{reset}")
    def prompt_text(self, prompt: str, default: Optional[str] = None) -> str:
        """Prompt user for text input with optional default."""
        display_prompt = prompt
        if default:
            display_prompt += f" [{default}]"
        display_prompt += ": "
        while True:
            response = input(display_prompt).strip()
            if not response and default:
                response = default
            if response:
                return response
            self.show_message("Please provide a value", "warning")
    def prompt_choice(self, prompt: str, choices: List[UserChoice], 
                     allow_custom: bool = False) -> UserChoice:
        """Prompt user to select from numbered choices."""
        print(f"\n{self.colors['bold']}{prompt}{self.colors['reset']}")
        
        # Display choices
        for i, choice in enumerate(choices, 1):
            default_indicator = " (default)" if choice.is_default else ""
            description = f" - {choice.description}" if choice.description else ""
            print(f"{i}) {choice.display_text}{default_indicator}{description}")
        if allow_custom:
            print(f"{len(choices) + 1}) Enter custom value")
        while True:
            try:
                # Find default choice
                default_num = None
                for i, choice in enumerate(choices, 1):
                    if choice.is_default:
                        default_num = i
                        break
                # Get user input
                prompt_text = f"Choice [1-{len(choices)}"
                if allow_custom:
                    prompt_text += f", {len(choices) + 1}"
                if default_num:
                    prompt_text += f"] [{default_num}]: "
                else:
                    prompt_text += "]: "
                response = input(prompt_text).strip()
                # Handle default
                if not response and default_num:
                    return choices[default_num - 1]
                # Parse choice
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                elif allow_custom and choice_num == len(choices) + 1:
                    custom_value = input("Enter custom value: ").strip()
                    return UserChoice(value=custom_value, display_text=custom_value, description="Custom value")
                else:
                    self.show_message(f"Please enter a number between 1 and {len(choices)}", "warning")
            except ValueError:
                self.show_message("Please enter a valid number", "warning")
    def prompt_yes_no(self, prompt: str, default: Optional[bool] = None) -> bool:
        """Prompt user for yes/no input."""
        choices = []
        if default is True:
            choices.extend([
                UserChoice(value=True, display_text="Yes", is_default=True),
                UserChoice(value=False, display_text="No")
            ])
        elif default is False:
            choices.extend([
                UserChoice(value=True, display_text="Yes"),
                UserChoice(value=False, display_text="No", is_default=True)
            ])
        else:
            choices.extend([
                UserChoice(value=True, display_text="Yes"),
                UserChoice(value=False, display_text="No")
            ])
        choice = self.prompt_choice(prompt, choices)
        return choice.value
    def prompt_path(self, prompt: str, must_exist: bool = True, 
                   is_directory: bool = True) -> Path:
        """Prompt user for file/directory path with validation."""
        while True:
            path_str = self.prompt_text(prompt)
            path = Path(path_str)
            validation = self._validate_path(path, must_exist, is_directory)
            if validation.is_valid:
                return path
            self.show_validation_result(validation)
    def _validate_path(self, path: Path, must_exist: bool, is_directory: bool) -> ValidationResult:
        """Validate a file/directory path."""
        if must_exist and not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}"
            )
        if path.exists():
            if is_directory and not path.is_dir():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Path is not a directory: {path}"
                )
            elif not is_directory and not path.is_file():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Path is not a file: {path}"
                )
        return ValidationResult(is_valid=True)
    def show_progress(self, message: str) -> None:
        """Show progress indication."""
        print(f"{self.colors['dim']}⏳ {message}{self.colors['reset']}")
    def show_validation_result(self, result: ValidationResult) -> None:
        """Display validation results."""
        if not result.is_valid and result.error_message:
            self.show_message(result.error_message, "error")
        if result.warnings:
            for warning in result.warnings:
                self.show_message(warning, "warning")


class InteractivePresenter:
    """
    Presenter that orchestrates the interactive configuration process.
    
    Separates UI concerns from business logic and provides a clean,
    testable interface for interactive mode.
    """
    def __init__(self, 
                 ui: IUserInterface,
                 zip_service: ZipExtractionService,
                 validator: TakeoutValidationService,
                 space_service: DiskSpaceService,
                 progress_reporter: ProgressReporter):
        """
        Initialize the interactive presenter.
        
        Args:
            ui: User interface implementation
            zip_service: ZIP extraction service
            validator: Takeout validation service
            space_service: Disk space service
            progress_reporter: Progress reporting service
        """
        self.ui = ui
        self.zip_service = zip_service
        self.validator = validator
        self.space_service = space_service
        self.progress_reporter = progress_reporter
        self.current_config: Optional[ProcessingConfig] = None
    def run_interactive_configuration(self) -> ProcessingConfig:
        """
        Run the complete interactive configuration process.
        
        Returns:
            Fully configured ProcessingConfig
        """
        self.ui.show_message("🎨 Google Photos Takeout Helper - Interactive Configuration", "info")
        self.ui.show_message("=" * 60, "info")
        try:
            # Step-by-step configuration
            input_config = self._configure_input()
            output_config = self._configure_output()
            album_config = self._configure_albums()
            media_config = self._configure_media_processing()
            datetime_config = self._configure_datetime()
            system_config = self._configure_system()
            # Create and validate final configuration
            self.current_config = ProcessingConfig(
                input_config=input_config,
                output_config=output_config,
                album_config=album_config,
                media_config=media_config,
                datetime_config=datetime_config,
                system_config=system_config
            )
            # Validate configuration
            self._validate_configuration()
            # Perform space check
            self._check_disk_space()
            # Final confirmation
            self._final_confirmation()
            return self.current_config
        except KeyboardInterrupt:
            self.ui.show_message("\n❌ Configuration cancelled by user", "warning")
            sys.exit(1)
        except Exception as e:
            self.ui.show_message(f"❌ Configuration error: {e}", "error")
            sys.exit(1)
    def _configure_input(self) -> InputConfiguration:
        """Configure input source settings."""
        self.ui.show_message("\n📂 STEP 1: INPUT SOURCE", "info")
        # Data source choice
        source_choices = [
            UserChoice(value=False, display_text="Folder", 
                      description="Already extracted Google Takeout folder", is_default=True),
            UserChoice(value=True, display_text="ZIP files", 
                      description="ZIP files from Google Takeout (will be extracted automatically)")
        ]
        use_zip = self.ui.prompt_choice("Select your data source:", source_choices).value
        if use_zip:
            return self._configure_zip_input()
        else:
            return self._configure_folder_input()
    def _configure_zip_input(self) -> InputConfiguration:
        """Configure ZIP file input."""
        self.ui.show_message("📥 ZIP File Configuration", "info")
        zip_files = []
        self.ui.show_message("Enter ZIP file paths (press Enter without input when done):", "info")
        while True:
            if len(zip_files) == 0:
                prompt = "ZIP file"
            else:
                prompt = f"ZIP file {len(zip_files) + 1} (or press Enter to finish)"
            try:
                zip_path = self.ui.prompt_text(prompt)
                if not zip_path and len(zip_files) > 0:
                    break
                path = Path(zip_path)
                if not path.exists():
                    self.ui.show_message("File does not exist", "error")
                    continue
                if not path.suffix.lower() == '.zip':
                    if not self.ui.prompt_yes_no("File doesn't have .zip extension. Continue anyway?", False):
                        continue
                zip_files.append(path)
                self.ui.show_message(f"✅ Added: {path.name}", "success")
            except EOFError:
                break
        if not zip_files:
            self.ui.show_message("No ZIP files specified, switching to folder mode", "warning")
            return self._configure_folder_input()
        # Extraction directory
        default_extract_dir = Path.cwd() / "extracted_takeout"
        extract_dir_input = self.ui.prompt_text(
            f"Extraction directory [{default_extract_dir}]", 
            str(default_extract_dir)
        )
        extract_dir = Path(extract_dir_input)
        return InputConfiguration(
            input_path=extract_dir,  # Will be the extracted location
            use_zip_mode=True,
            zip_files=zip_files,
            temp_extraction_dir=extract_dir,
            validation_level=ValidationLevel.MODERATE
        )
    def _configure_folder_input(self) -> InputConfiguration:
        """Configure folder input."""
        input_path = self.ui.prompt_path("📁 Enter your extracted Takeout folder path:")
        
        # Validate Takeout structure
        self.ui.show_progress("Validating Takeout structure...")
        validation_result = self.validator.validate_takeout_structure(input_path)
        
        # Show validation results
        self.ui.show_message(f"📊 Validation Score: {validation_result.validation_score:.1f}/1.0", "info")
        self.ui.show_message(f"📁 Structure Type: {validation_result.structure_type}", "info")
        self.ui.show_message(f"📸 Media Files: {validation_result.total_media_files:,}", "info")
        if validation_result.user_guidance:
            self.ui.show_message(f"💡 {validation_result.user_guidance}", "info")
        # Handle recommendations
        if validation_result.recommended_input_path and validation_result.recommended_input_path != input_path:
            if self.ui.prompt_yes_no(f"📁 Use recommended path: {validation_result.recommended_input_path}?", True):
                input_path = validation_result.recommended_input_path
        return InputConfiguration(
            input_path=input_path,
            use_zip_mode=False,
            validation_level=ValidationLevel.MODERATE
        )
    def _configure_output(self) -> OutputConfiguration:
        """Configure output settings."""
        self.ui.show_message("\n📦 STEP 2: OUTPUT CONFIGURATION", "info")
        
        output_path = self.ui.prompt_path("📦 Enter output directory path:", must_exist=False)
        
        # Check if output directory exists and is not empty
        clean_first = False
        if output_path.exists() and any(output_path.iterdir()):
            self.ui.show_message(f"⚠️  Output directory exists and is not empty: {output_path}", "warning")
            choices = [
                UserChoice(value=False, display_text="Use anyway", is_default=True),
                UserChoice(value=True, display_text="Clean directory first")
            ]
            clean_first = self.ui.prompt_choice("How to handle existing content?", choices).value
        dry_run = self.ui.prompt_yes_no("🔍 Enable dry run mode (preview changes without making them)?", False)
        return OutputConfiguration(
            output_path=output_path,
            clean_output_first=clean_first,
            dry_run=dry_run
        )
    def _configure_albums(self) -> AlbumConfiguration:
        """Configure album processing settings."""
        self.ui.show_message("\n📁 STEP 3: ALBUM CONFIGURATION", "info")
        
        # Album behavior
        album_choices = [
            UserChoice(value=AlbumBehavior.SHORTCUT, display_text="Shortcuts", 
                      description="Create shortcuts/symlinks to files (recommended)", is_default=True),
            UserChoice(value=AlbumBehavior.DUPLICATE_COPY, display_text="Duplicate copies", 
                      description="Copy files to album folders (uses more space)"),
            UserChoice(value=AlbumBehavior.REVERSE_SHORTCUT, display_text="Reverse shortcuts", 
                      description="Keep originals in albums, shortcuts in main folders"),
            UserChoice(value=AlbumBehavior.JSON, display_text="JSON metadata only",
                      description="Create album info as JSON files"),
            UserChoice(value=AlbumBehavior.NOTHING, display_text="No album processing",
                      description="Skip album organization")
        ]
        album_behavior = self.ui.prompt_choice("🗂️  Album organization method:", album_choices).value
        
        return AlbumConfiguration(
            album_behavior=album_behavior,
            create_album_shortcuts=True,
            process_partner_sharing=True,
            separate_partner_albums=True
        )

    def _configure_media_processing(self) -> MediaProcessingConfiguration:
        """Configure media processing settings."""
        self.ui.show_message("\n🎨 STEP 4: MEDIA PROCESSING", "info")
        
        # Extension fixing
        fixing_choices = [
            UserChoice(value=ExtensionFixingMode.STANDARD, display_text="Standard",
                      description="Fix incorrect file extensions (recommended)", is_default=True),
            UserChoice(value=ExtensionFixingMode.CONSERVATIVE, display_text="Conservative",
                      description="Only fix obviously wrong extensions"),
            UserChoice(value=ExtensionFixingMode.NONE, display_text="None",
                      description="Keep original extensions"),
            UserChoice(value=ExtensionFixingMode.SOLO, display_text="Solo mode",
                      description="Minimal extension fixing")
        ]
        extension_fixing = self.ui.prompt_choice("🔧 File extension fixing:", fixing_choices).value
        
        # Duplicates handling
        remove_duplicates = self.ui.prompt_yes_no("🔍 Remove duplicate files?", True)
        
        return MediaProcessingConfiguration(
            extension_fixing_mode=extension_fixing,
            remove_duplicates=remove_duplicates,
            write_exif_metadata=True,
            guess_dates_from_filenames=True
        )

    def _configure_datetime(self) -> DateTimeConfiguration:
        """Configure date/time organization settings."""
        self.ui.show_message("\n📅 STEP 5: DATE/TIME ORGANIZATION", "info")
        
        # Date division
        division_choices = [
            UserChoice(value=DateDivisionLevel.MONTH, display_text="Year/Month",
                      description="Organize by year and month folders", is_default=True),
            UserChoice(value=DateDivisionLevel.YEAR, display_text="Year only",
                      description="Organize by year folders"),
            UserChoice(value=DateDivisionLevel.DAY, display_text="Year/Month/Day",
                      description="Organize by year/month/day folders"),
            UserChoice(value=DateDivisionLevel.NONE, display_text="No date folders",
                      description="Keep all files in root output folder")
        ]
        date_division = self.ui.prompt_choice("📂 Date organization method:", division_choices).value
        
        return DateTimeConfiguration(
            date_division_level=date_division,
            prefer_metadata_dates=True,
            fallback_to_filename_dates=True,
            timezone_handling="local"
        )

    def _configure_system(self) -> SystemConfiguration:
        """Configure system and performance settings."""
        self.ui.show_message("\n⚙️  STEP 6: SYSTEM CONFIGURATION", "info")
        
        # Parallel processing
        enable_parallel = self.ui.prompt_yes_no("🚀 Enable parallel processing?", True)
        
        max_workers = 4
        if enable_parallel:
            try:
                max_workers_input = self.ui.prompt_text("🔢 Maximum parallel workers [4]", "4")
                max_workers = int(max_workers_input)
                if max_workers < 1 or max_workers > 16:
                    self.ui.show_message("Using default value of 4 workers", "warning")
                    max_workers = 4
            except ValueError:
                self.ui.show_message("Invalid number, using default value of 4 workers", "warning")
                max_workers = 4
        else:
            max_workers = 1
        
        # Memory optimization
        optimize_memory = self.ui.prompt_yes_no("💾 Enable memory optimization for large datasets?", True)
        
        return SystemConfiguration(
            max_threads=max_workers,
            enable_progress_reporting=True,
            log_level="INFO"
        )

    def _validate_configuration(self) -> None:
        """Validate the complete configuration."""
        self.ui.show_message("\n✅ STEP 7: CONFIGURATION VALIDATION", "info")
        
        if not self.current_config:
            raise ValueError("No configuration to validate")
        
        # Basic validation
        validation_issues = []
        
        # Check input path
        if not self.current_config:
            raise ValueError("No configuration to validate")
            
        if self.current_config.input_config.use_zip_mode:
            for zip_file in self.current_config.input_config.zip_files:
                if not zip_file.exists():
                    validation_issues.append(f"ZIP file not found: {zip_file}")
        else:
            if not self.current_config.input_config.input_path.exists():
                validation_issues.append(f"Input path not found: {self.current_config.input_config.input_path}")
        
        # Check output path writability
        output_parent = self.current_config.output_config.output_path.parent
        if not output_parent.exists():
            validation_issues.append(f"Output parent directory not found: {output_parent}")
        
        if validation_issues:
            for issue in validation_issues:
                self.ui.show_message(f"❌ {issue}", "error")
            raise ValueError("Configuration validation failed")
        
        self.ui.show_message("✅ Configuration validation passed", "success")

    def _check_disk_space(self) -> None:
        """Check available disk space."""
        self.ui.show_message("\n💾 STEP 8: DISK SPACE CHECK", "info")
        self.ui.show_progress("Calculating space requirements...")
        
        try:
            if not self.current_config:
                raise ValueError("No configuration available for space check")
                
            space_info = self.space_service.calculate_space_requirements(
                [self.current_config.input_config.input_path],
                self.current_config.album_config.album_behavior.value
            )
            
            # Display space information
            input_size_gb = space_info.input_size_bytes / (1024**3)
            required_size_gb = space_info.total_required_bytes / (1024**3)
            
            self.ui.show_message(f"📊 Input size: {input_size_gb:.2f} GB", "info")
            self.ui.show_message(f"📦 Required space: {required_size_gb:.2f} GB", "info")
            
            # Check available space on output directory
            output_space = self.space_service.get_disk_space(self.current_config.output_config.output_path.parent)
            if output_space:
                available_gb = output_space.free_bytes / (1024**3)
                self.ui.show_message(f"💽 Available space: {available_gb:.2f} GB", "info")
                
                if space_info.total_required_bytes > output_space.free_bytes:
                    self.ui.show_message("❌ Insufficient disk space!", "error")
                    if not self.ui.prompt_yes_no("Continue anyway?", False):
                        raise ValueError("Insufficient disk space")
                else:
                    self.ui.show_message("✅ Sufficient disk space available", "success")
            else:
                self.ui.show_message("⚠️  Could not check available space", "warning")
        
        except Exception as e:
            self.ui.show_message(f"⚠️  Could not check disk space: {e}", "warning")
            if not self.ui.prompt_yes_no("Continue without space check?", True):
                raise ValueError("Space check required")

    def _final_confirmation(self) -> None:
        """Show final configuration summary and get user confirmation."""
        self.ui.show_message("\n📋 CONFIGURATION SUMMARY", "info")
        self.ui.show_message("=" * 50, "info")
        
        # Display configuration summary
        if not self.current_config:
            raise ValueError("No configuration available")
            
        config = self.current_config
        self.ui.show_message(f"📂 Input: {config.input_config.input_path}", "info")
        self.ui.show_message(f"📦 Output: {config.output_config.output_path}", "info")
        self.ui.show_message(f"🗂️  Albums: {config.album_config.album_behavior.value}", "info")
        self.ui.show_message(f"📅 Date org: {config.datetime_config.date_division_level.value}", "info")
        self.ui.show_message(f"🔧 Extensions: {config.media_config.extension_fixing_mode.value}", "info")
        self.ui.show_message(f"⚙️  Workers: {config.system_config.max_threads}", "info")
        
        if config.output_config.dry_run:
            self.ui.show_message("🔍 MODE: DRY RUN (no files will be modified)", "warning")
        
        # Final confirmation
        self.ui.show_message("\n" + "=" * 50, "info")
        if not self.ui.prompt_yes_no("🚀 Start processing with this configuration?", True):
            raise KeyboardInterrupt("Processing cancelled by user")
        
        self.ui.show_message("🎉 Configuration complete! Starting processing...", "success")


def create_console_presenter(
    zip_service: ZipExtractionService,
    validator: TakeoutValidationService,
    space_service: DiskSpaceService,
    progress_reporter: ProgressReporter
) -> InteractivePresenter:
    """
    Factory function to create a console-based interactive presenter.
    
    Args:
        zip_service: ZIP extraction service
        validator: Takeout validation service
        space_service: Disk space service
        progress_reporter: Progress reporting service
    
    Returns:
        Interactive presenter with console interface
    """
    console_ui = ConsoleInterface(use_colors=True)
    return InteractivePresenter(
        ui=console_ui,
        zip_service=zip_service,
        validator=validator,
        space_service=space_service,
        progress_reporter=progress_reporter
    )