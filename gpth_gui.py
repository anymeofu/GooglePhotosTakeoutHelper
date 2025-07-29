#!/usr/bin/env python3
"""
Google Photos Takeout Helper - GUI Entry Point
Graphical user interface launcher
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from gui.gpth_gui import main

if __name__ == '__main__':
    main()