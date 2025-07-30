#!/usr/bin/env python3
"""
Google Photos Takeout Helper - Production Application

A comprehensive, user-friendly tool for organizing and processing Google Photos Takeout exports.

Features:
- Interactive configuration with validation
- ZIP file extraction and processing
- Smart album organization
- Duplicate detection and removal
- Cross-platform compatibility
- Real-time progress tracking
- System optimization recommendations
- Comprehensive error handling with recovery

Usage:
    python gpth_app.py                    # Interactive mode
    python gpth_app.py --help            # Show help
    python gpth_app.py --system-check    # System analysis only

Author: Google Photos Takeout Helper Team
Version: 3.0.0
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

# Ensure src directory is in path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Core imports
from src.services.service_container import ServiceContainer
from src.cli.interactive_presenter import create_console_presenter
from src.models.processing_config import ProcessingConfig, create_default_config
from src.utils import (
    create_system_monitor, create_optimization_analyzer, print_system_analysis,
    create_default_recovery_manager, ErrorSeverity,
    with_error_handling, error_context
)

# Version information
__version__ = "3.0.0"
__author__ = "Google Photos Takeout Helper Team"


class GooglePhotosApp:
    """Main application class for Google Photos Takeout Helper."""
    
    def __init__(self):
        """Initialize the application."""
        self.container = ServiceContainer()
        self.recovery_manager = create_default_recovery_manager()
        self.system_monitor = create_system_monitor()
        self.setup_logging()
        self.register_services()
    
    def setup_logging(self):
        """Setup application logging."""
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / 'gpth_app.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Set library loggers to WARNING to reduce noise
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('psutil').setLevel(logging.WARNING)
    
    def register_services(self):
        """Register all services with the dependency injection container."""
        from src.services.zip_extraction_service import ZipExtractionService
        from src.services.takeout_validator_service import TakeoutValidationService
        from src.services.disk_space_service import DiskSpaceService
        from src.services.progress_reporting_service import ProgressReporter
        from src.services.enhanced_interactive_service import EnhancedInteractiveService
        
        # Register core services
        self.container.register_singleton(ZipExtractionService)
        self.container.register_singleton(TakeoutValidationService)
        self.container.register_singleton(DiskSpaceService)
        self.container.register_singleton(ProgressReporter)
        self.container.register_singleton(EnhancedInteractiveService)
    
    @with_error_handling(severity=ErrorSeverity.INFO)
    def show_banner(self):
        """Display application banner."""
        banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    Google Photos Takeout Helper v{__version__}                    ║
║                                                                              ║
║  📸 Organize your Google Photos Takeout exports with ease                   ║
║  🚀 Fast, reliable, and user-friendly                                       ║
║  🔧 Advanced features: ZIP extraction, albums, duplicates, optimization     ║
║                                                                              ║
║  Made with ❤️  by the GPTH Team                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    @with_error_handling(severity=ErrorSeverity.ERROR)
    def run_system_check(self):
        """Run comprehensive system analysis and optimization check."""
        print("\n🖥️  SYSTEM ANALYSIS & OPTIMIZATION")
        print("=" * 60)
        
        # Start monitoring
        self.system_monitor.start_monitoring()
        
        try:
            # Create analyzer and run analysis
            analyzer = create_optimization_analyzer(self.system_monitor)
            analysis = analyzer.analyze_system_performance()
            
            # Display results
            print_system_analysis(analysis)
            
            # Additional recommendations
            print(f"\n💡 Additional Tips:")
            print(f"  • Close unnecessary applications before processing")
            print(f"  • Use SSD storage for better performance")
            print(f"  • Ensure stable power supply for large operations")
            print(f"  • Keep at least 10% free disk space")
            
            return analysis.overall_performance.value != 'critical'
            
        finally:
            self.system_monitor.stop_monitoring()
    
    @with_error_handling(severity=ErrorSeverity.FATAL)
    def run_interactive_mode(self) -> bool:
        """Run the interactive configuration and processing mode."""
        try:
            # Get required services
            from src.services.zip_extraction_service import ZipExtractionService
            from src.services.takeout_validator_service import TakeoutValidationService
            from src.services.disk_space_service import DiskSpaceService
            from src.services.progress_reporting_service import ProgressReporter
            
            zip_service = self.container.get_service(ZipExtractionService)
            validator = self.container.get_service(TakeoutValidationService)
            space_service = self.container.get_service(DiskSpaceService)
            progress_reporter = self.container.get_service(ProgressReporter)
            
            # Create interactive presenter
            presenter = create_console_presenter(
                zip_service=zip_service,
                validator=validator,
                space_service=space_service,
                progress_reporter=progress_reporter
            )
            
            print("\n🎯 Starting Interactive Configuration...")
            
            # Run interactive configuration
            with error_context("interactive_configuration"):
                config = presenter.run_interactive_configuration()
            
            print(f"\n✅ Configuration complete! Ready to process your photos.")
            print(f"📁 Input: {config.input_config.input_path}")
            print(f"📦 Output: {config.output_config.output_path}")
            
            # Ask for final confirmation
            print(f"\n🚀 Ready to start processing!")
            response = input("Press Enter to begin processing, or 'q' to quit: ").strip().lower()
            
            if response == 'q':
                print(f"👋 Processing cancelled. Your configuration is saved for next time.")
                return True
            
            # TODO: Integrate with actual processing pipeline
            print(f"\n🔄 Processing would start here...")
            print(f"💡 Integration with existing processing pipeline coming soon!")
            print(f"📝 Your configuration has been validated and is ready to use.")
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Application interrupted by user. Goodbye!")
            return False
        except Exception as e:
            print(f"\n❌ Application error: {e}")
            return False
    
    @with_error_handling(severity=ErrorSeverity.ERROR)
    def run(self, args) -> int:
        """Run the main application."""
        self.show_banner()
        
        # Handle different modes
        if args.system_check:
            success = self.run_system_check()
            return 0 if success else 1
        
        elif args.version:
            print(f"Google Photos Takeout Helper version {__version__}")
            print(f"Author: {__author__}")
            return 0
        
        else:
            # Interactive mode (default)
            print(f"\n🎮 Welcome to Interactive Mode!")
            print(f"This mode will guide you through the entire process step by step.")
            
            # Optional system check
            print(f"\n🔍 Before we begin, let's check your system...")
            response = input("Run system optimization check? (Y/n): ").strip().lower()
            
            if response != 'n':
                system_ok = self.run_system_check()
                if not system_ok:
                    print(f"\n⚠️  System issues detected. Continue anyway? (y/N): ", end="")
                    if input().strip().lower() != 'y':
                        return 1
            
            # Run interactive mode
            success = self.run_interactive_mode()
            return 0 if success else 1


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Google Photos Takeout Helper - Organize your photo exports with ease",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gpth_app.py                    # Interactive mode (recommended)
  python gpth_app.py --system-check    # Check system performance
  python gpth_app.py --version         # Show version information

For more help and documentation, visit: https://github.com/your-repo/google-photos-takeout-helper
"""
    )
    
    parser.add_argument('--version', 
                       action='store_true',
                       help='Show version information and exit')
    
    parser.add_argument('--system-check', 
                       action='store_true',
                       help='Run system analysis and optimization check only')
    
    parser.add_argument('--log-level',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Set logging level (default: INFO)')
    
    parser.add_argument('--no-color',
                       action='store_true',
                       help='Disable colored output')
    
    return parser


def main() -> int:
    """Main entry point for the application."""
    try:
        # Parse arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Adjust logging level
        if hasattr(args, 'log_level'):
            logging.getLogger().setLevel(getattr(logging, args.log_level))
        
        # Create and run application
        app = GooglePhotosApp()
        result = app.run(args)
        return result if result is not None else 0
        
    except KeyboardInterrupt:
        print(f"\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        logging.exception("Fatal application error")
        return 1


if __name__ == "__main__":
    # Ensure we're running with Python 3.7+
    if sys.version_info < (3, 7):
        print("❌ Error: This application requires Python 3.7 or higher")
        print(f"   You are running Python {sys.version}")
        sys.exit(1)
    
    # Check for required dependencies
    try:
        import psutil
    except ImportError:
        print("❌ Error: Required dependency 'psutil' not found")
        print("   Install it with: pip install psutil")
        sys.exit(1)
    
    # Run the application
    exit_code = main()
    sys.exit(exit_code)