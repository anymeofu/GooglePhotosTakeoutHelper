#!/usr/bin/env python3
"""
Basic test script for the new processing pipeline
"""

import tempfile
import logging
from pathlib import Path

# Set up Python path to import our modules
import sys
sys.path.insert(0, 'src')

from src.core.gpth_core_api import GooglePhotosTakeoutHelper, ProcessingConfig, AlbumMode, ExtensionFixMode

def test_pipeline():
    """Test the new processing pipeline with minimal configuration"""
    print("=== Testing Google Photos Takeout Helper Pipeline ===\n")
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"
        
        # Create test directories
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Create a fake test file
        test_file = input_dir / "test_image.jpg"
        test_file.write_text("fake image content")
        
        print(f"Created test input: {test_file}")
        print(f"Output directory: {output_dir}\n")
        
        # Configure processing
        config = ProcessingConfig(
            input_path=str(input_dir),
            output_path=str(output_dir),
            album_mode=AlbumMode.NOTHING,  # Simple mode for testing
            extension_fix_mode=ExtensionFixMode.NONE,  # Skip extension fixing
            verbose=True,
            dry_run=True  # Safe mode - don't actually move files
        )
        
        # Create the helper with progress callback
        def progress_callback(step: int, message: str, progress: float):
            print(f"Step {step}: {message} ({progress:.1f}%)")
        
        # Initialize the helper
        print("Initializing Google Photos Takeout Helper...")
        gpth = GooglePhotosTakeoutHelper(config)
        gpth.set_progress_callback(progress_callback)
        
        # Test pipeline execution
        print("\n--- Starting Pipeline Execution ---")
        try:
            result = gpth.process_takeout()
            
            print(f"\n--- Pipeline Results ---")
            print(f"Success: {result.success}")
            print(f"Total files: {result.total_files}")
            print(f"Processed files: {result.processed_files}")
            print(f"Processing time: {result.processing_time:.2f}s")
            print(f"Duplicates removed: {result.duplicates_removed}")
            print(f"Albums found: {result.albums_found}")
            
            if result.errors:
                print(f"\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")
            
            if result.warnings:
                print(f"\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
                    
            return result.success
            
        except Exception as e:
            print(f"\nTest failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_individual_services():
    """Test individual services"""
    print("\n=== Testing Individual Services ===\n")
    
    # Test MediaHashService
    try:
        from src.core.media_hash import MediaHashService
        
        logger = logging.getLogger('test')
        hash_service = MediaHashService(logger)
        
        # Test with this script file
        test_file = Path(__file__)
        file_hash = hash_service.calculate_file_hash(test_file)
        
        print(f"MediaHashService test:")
        print(f"  File: {test_file.name}")
        if file_hash:
            print(f"  Hash: {file_hash[:16]}... (truncated)")
        else:
            print(f"  Hash: Failed to calculate")
        print(f"  Cache stats: {hash_service.get_cache_stats()}")
        
    except Exception as e:
        print(f"MediaHashService test failed: {e}")
    
    # Test DuplicateDetectionService
    try:
        from src.core.duplicate_detection import DuplicateDetectionService
        from src.core.media_hash import MediaHashService
        
        logger = logging.getLogger('test')
        hash_service = MediaHashService(logger)
        dup_service = DuplicateDetectionService(logger, hash_service)
        
        # Test with current directory files
        test_files = [Path(__file__), Path("README_AI.md")]
        test_files = [f for f in test_files if f.exists()]
        
        if test_files:
            unique_files, duplicates = dup_service.find_duplicates(test_files)
            print(f"\nDuplicateDetectionService test:")
            print(f"  Input files: {len(test_files)}")
            print(f"  Unique files: {len(unique_files)}")
            print(f"  Duplicates: {len(duplicates)}")
        
    except Exception as e:
        print(f"DuplicateDetectionService test failed: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Google Photos Takeout Helper - Python Implementation Test")
    print("=" * 60)
    
    # Test individual services first
    test_individual_services()
    
    # Test the main pipeline
    success = test_pipeline()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Pipeline test completed successfully!")
        print("\nNext steps:")
        print("1. Test with real Google Photos takeout data")
        print("2. Implement EXIF writer service")
        print("3. Add comprehensive error handling")
        print("4. Performance optimization for large datasets")
    else:
        print("❌ Pipeline test failed!")
        print("Check the error messages above for debugging information.")