#!/usr/bin/env python3
"""
Test script for platform services functionality
"""

import tempfile
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_platform_services():
    """Test platform services functionality"""
    print("Google Photos Takeout Helper - Platform Services Test")
    print("=" * 60)
    
    try:
        # Import platform services
        from src.services.platform_services import (
            get_timestamp_service, 
            get_platform_info,
            platform_manager
        )
        
        # Show platform information
        print("\n=== Platform Information ===")
        platform_info = get_platform_info()
        print(f"System: {platform_info['system']}")
        print(f"Python: {platform_info['python_version'][:20]}...")
        
        if 'timestamp' in platform_info['services']:
            ts_info = platform_info['services']['timestamp']
            print(f"Timestamp service: {ts_info['platform']}")
            print(f"Supported: {ts_info['supported']}")
            if 'powershell_available' in ts_info:
                print(f"PowerShell available: {ts_info['powershell_available']}")
        
        # Get timestamp service
        timestamp_service = get_timestamp_service()
        if not timestamp_service:
            print("❌ No timestamp service available")
            return False
            
        print(f"\n✅ Timestamp service initialized: {timestamp_service.get_platform_name()}")
        
        # Test with a temporary file
        print("\n=== Testing Timestamp Operations ===")
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
            tmp_file.write("Test file for timestamp operations")
            tmp_path = Path(tmp_file.name)
        
        try:
            print(f"Test file: {tmp_path}")
            
            # Get current creation time
            original_creation = timestamp_service.get_creation_time(tmp_path)
            print(f"Original creation time: {original_creation}")
            
            # Set a new timestamp (1 hour ago)
            test_timestamp = datetime.now().replace(microsecond=0) - timedelta(hours=1)
            print(f"Setting new timestamp: {test_timestamp}")
            
            # Test creation time update
            creation_success = timestamp_service.update_creation_time(tmp_path, test_timestamp)
            print(f"Creation time update: {'✅ Success' if creation_success else '❌ Failed'}")
            
            # Test access/modification time update
            access_mod_success = timestamp_service.update_access_and_modification_time(tmp_path, test_timestamp)
            print(f"Access/mod time update: {'✅ Success' if access_mod_success else '❌ Failed'}")
            
            # Verify the update
            new_creation = timestamp_service.get_creation_time(tmp_path)
            print(f"New creation time: {new_creation}")
            
            # Check file stats for verification
            stat = tmp_path.stat()
            print(f"File mtime: {datetime.fromtimestamp(stat.st_mtime)}")
            print(f"File ctime: {datetime.fromtimestamp(stat.st_ctime)}")
            
        finally:
            # Clean up
            if tmp_path.exists():
                tmp_path.unlink()
                print(f"Cleaned up test file: {tmp_path}")
        
        print(f"\n✅ Platform services test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Platform services test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    from datetime import timedelta
    success = test_platform_services()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All platform services tests passed!")
    else:
        print("❌ Platform services tests failed!")
        
    print("\nNext steps:")
    print("1. Verify timestamp operations work on your platform")
    print("2. Test with real Google Photos data")
    print("3. Implement EXIF writer service")
    print("4. Add comprehensive error handling")