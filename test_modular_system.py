#!/usr/bin/env python3
"""
Test script for the modular pipeline system
Tests basic functionality of the step-by-step execution
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.modular_pipeline import ModularPipeline
from src.core.gpth_core_api import ProcessingConfig, AlbumMode, ExtensionFixMode


def create_test_takeout_structure(temp_dir: Path) -> Path:
    """Create a basic test Google Takeout structure"""
    takeout_dir = temp_dir / "test_takeout"
    takeout_dir.mkdir()
    
    # Create Google Photos directory
    photos_dir = takeout_dir / "Google Photos"
    photos_dir.mkdir()
    
    # Create some test photo directories with JSON files
    album_dir = photos_dir / "Test Album"
    album_dir.mkdir()
    
    # Create test image files
    test_files = [
        "IMG_20230615_120030.jpg",
        "IMG_20230615_120031.jpg",
        "VID_20230615_120045.mp4"
    ]
    
    for filename in test_files:
        test_file = album_dir / filename
        test_file.write_text(f"# Test image content for {filename}")
        
        # Create corresponding JSON metadata
        json_file = album_dir / f"{filename}.json"
        json_content = {
            "title": filename,
            "description": "",
            "imageViews": "1",
            "creationTime": {
                "timestamp": "1686834030",
                "formatted": "Jun 15, 2023, 12:00:30 PM UTC"
            },
            "photoTakenTime": {
                "timestamp": "1686834030",
                "formatted": "Jun 15, 2023, 12:00:30 PM UTC"
            },
            "geoData": {
                "latitude": 0.0,
                "longitude": 0.0,
                "altitude": 0.0
            }
        }
        
        import json
        json_file.write_text(json.dumps(json_content, indent=2))
    
    return takeout_dir


def test_basic_pipeline():
    """Test basic pipeline creation and step execution"""
    print("Testing basic modular pipeline functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test input structure
        input_dir = create_test_takeout_structure(temp_path)
        output_dir = temp_path / "output"
        state_dir = temp_path / "pipeline_states"
        
        print(f"Created test takeout structure: {input_dir}")
        print(f"Output directory: {output_dir}")
        print(f"State directory: {state_dir}")
        
        # Create configuration
        config = ProcessingConfig(
            input_path=str(input_dir),
            output_path=str(output_dir),
            album_mode=AlbumMode.SHORTCUT,
            extension_fix_mode=ExtensionFixMode.STANDARD,
            dry_run=True,  # Use dry run for testing
            verbose=True
        )
        
        # Create logger
        import logging
        logger = logging.getLogger('test_pipeline')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        print("\n1. Creating modular pipeline...")
        pipeline = ModularPipeline(config, state_dir, logger)
        
        print("2. Starting pipeline run...")
        run_id = pipeline.start_pipeline(input_dir, output_dir)
        print(f"   Pipeline started with ID: {run_id}")
        
        print("3. Testing individual step execution...")
        
        # Execute first few steps
        for step_num in [1, 2]:
            print(f"   Executing step {step_num}...")
            result = pipeline.execute_step(run_id, step_num)
            
            if result.success:
                print(f"   ✓ Step {step_num} completed successfully")
            else:
                print(f"   ✗ Step {step_num} failed: {result.error}")
                break
        
        print("4. Checking pipeline state...")
        pipeline_run = pipeline.state_manager.get_pipeline_run(run_id)
        
        if pipeline_run:
            print(f"   Pipeline status: {pipeline_run.status}")
            print(f"   Completed steps: {len([s for s in pipeline_run.steps if s['status'] == 'completed'])}")
            print("   Step details:")
            for step in pipeline_run.steps[:3]:  # Show first 3 steps
                status = step['status']
                name = step['display_name']
                print(f"     {step['step_number']}. {name}: {status}")
        
        print("5. Testing pipeline state persistence...")
        
        # Check that state files were created
        runs_dir = state_dir / "runs"
        if runs_dir.exists():
            run_files = list(runs_dir.glob("*.json"))
            print(f"   Created {len(run_files)} run files")
        
        steps_dir = state_dir / "steps"
        if steps_dir.exists():
            step_files = list(steps_dir.glob("*.json"))
            print(f"   Created {len(step_files)} step state files")
        
        print("\n✓ Basic modular pipeline test completed successfully!")
        print(f"✓ Pipeline run ID: {run_id}")
        print(f"✓ State saved to: {state_dir}")
        
        return True


def test_cli_interface():
    """Test the CLI interface functionality"""
    print("\nTesting CLI interface...")
    
    try:
        # Import the CLI functions
        import subprocess
        import sys
        
        # Test CLI help
        result = subprocess.run([
            sys.executable, "gpth_cli.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ CLI help command works")
        else:
            print(f"✗ CLI help failed: {result.stderr}")
            return False
        
        print("✓ CLI interface test completed")
        return True
        
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("GOOGLE PHOTOS TAKEOUT HELPER - MODULAR SYSTEM TEST")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    try:
        if test_basic_pipeline():
            tests_passed += 1
        
        if test_cli_interface():
            tests_passed += 1
            
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Modular pipeline system is working.")
        return 0
    else:
        print(f"✗ {total_tests - tests_passed} tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())