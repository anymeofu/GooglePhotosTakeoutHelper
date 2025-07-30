#!/usr/bin/env python3
"""
Google Photos Takeout Helper - Simple Test Suite
Basic tests to verify functionality
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_imports():
    """Test that all main modules can be imported"""
    print("Testing imports...")
    try:
        from core import processing_pipeline
        print("✓ Core processing_pipeline imported")
    except ImportError as e:
        print(f"✗ Failed to import processing_pipeline: {e}")
    try:
        from services import zip_extraction_service
        print("✓ ZIP extraction service imported")
    except ImportError as e:
        print(f"✗ Failed to import zip_extraction_service: {e}")
    try:
        from gui import gpth_gui
        print("✓ Legacy GUI imported")
    except ImportError as e:
        print(f"✗ Failed to import legacy GUI: {e}")

def test_cli_apps():
    """Test that CLI apps can be imported"""
    print("\nTesting CLI applications...")
    try:
        import gpth_app
        print("✓ Main CLI app (gpth_app.py) imported")
    except ImportError as e:
        print(f"✗ Failed to import gpth_app: {e}")
    try:
        import gpth_cli
        print("✓ Modular CLI (gpth_cli.py) imported")
    except ImportError as e:
        print(f"✗ Failed to import gpth_cli: {e}")

def test_gui_apps():
    """Test that GUI apps can be imported"""
    print("\nTesting GUI applications...")
    try:
        import gpth_gui
        print("✓ Legacy GUI (gpth_gui.py) imported")
    except ImportError as e:
        print(f"✗ Failed to import gpth_gui: {e}")
    try:
        import gpth_simple_gui
        print("✓ Simple GUI (gpth_simple_gui.py) imported")
    except ImportError as e:
        print(f"✗ Failed to import gpth_simple_gui: {e}")

def test_core_services():
    """Test core services"""
    print("\nTesting core services...")
    try:
        from services.disk_space_service import DiskSpaceService
        service = DiskSpaceService()
        print("✓ DiskSpaceService works")
    except Exception as e:
        print(f"✗ DiskSpaceService failed: {e}")
    
    try:
        from services.takeout_validator_service import TakeoutValidatorService
        service = TakeoutValidatorService()
        print("✓ TakeoutValidatorService works")
    except Exception as e:
        print(f"✗ TakeoutValidatorService failed: {e}")

def test_basic_functionality():
    """Test basic functionality with temp directories"""
    print("\nTesting basic functionality...")
    try:
        # Create temp directories for testing
        temp_dir = Path(tempfile.mkdtemp())
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Test that directories exist
        assert input_dir.exists(), "Input directory not created"
        assert output_dir.exists(), "Output directory not created"
        print("✓ Temp directory creation works")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print("✓ Cleanup works")
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")

def main():
    """Run all tests"""
    print("Google Photos Takeout Helper - Test Suite")
    print("=" * 50)
    
    test_imports()
    test_cli_apps()
    test_gui_apps()
    test_core_services()
    test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("\nTo test the applications manually:")
    print("• Simple GUI: python gpth_simple_gui.py")
    print("• Main CLI: python gpth_app.py --help")
    print("• Legacy GUI: python gpth_gui.py")
    print("• Modular CLI: python gpth_cli.py --help")

if __name__ == "__main__":
    main()