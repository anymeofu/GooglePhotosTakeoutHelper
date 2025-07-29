# 🐍 Google Photos Takeout Helper - Python Edition

A **simple and hassle-free** Python implementation of the Google Photos Takeout Helper with both CLI and GUI interfaces. No complex setup - just Python!

## 🌟 Why Python Version?

- ✅ **Easy Setup**: Just install Python and pip install dependencies
- ✅ **No SDK Hassles**: No Dart SDK, Flutter SDK, or build tools needed  
- ✅ **Cross-Platform**: Works on Windows, macOS, and Linux
- ✅ **Lightweight**: Minimal dependencies, fast startup
- ✅ **Both Interfaces**: Command-line and GUI options included

## 🚀 Quick Start (Super Easy!)

### Prerequisites
- Python 3.8 or higher
- That's it! 🎉

### Installation & Usage

```bash
# 1. Navigate to Python directory
cd python/

# 2. Install dependencies (one command)
pip install -r requirements.txt

# 3A. Run CLI version
python gpth_cli.py process /path/to/takeout /path/to/output

# 3B. Or run GUI version
python gpth_gui.py
```

## 📋 Features

### ✨ What It Does
- 🗂️ **Organize by Date**: Creates year/month folder structure
- 🔍 **Remove Duplicates**: Finds and removes identical files
- 📅 **Extract Dates**: From EXIF, JSON metadata, or filenames
- 🎨 **Process Albums**: Organizes album information
- ⏰ **Fix Timestamps**: Updates file creation times
- 📊 **Progress Tracking**: Real-time progress in both CLI and GUI

### 🖥️ Command Line Interface
```bash
# Get help
python gpth_cli.py --help

# Analyze takeout structure
python gpth_cli.py analyze /path/to/takeout

# Process with options
python gpth_cli.py process input/ output/ --skip-albums --verbose

# Advanced options
python gpth_cli.py process input/ output/ \
  --keep-duplicates \
  --no-fix-time \
  --threads 8 \
  --verbose
```

### 🎨 Graphical Interface
```bash
# Launch GUI
python gpth_gui.py
```
- ✅ Intuitive point-and-click interface
- ✅ Real-time progress visualization  
- ✅ Built-in takeout analyzer
- ✅ All CLI features available
- ✅ Cross-platform desktop app

## 📦 Installation Options

### Option 1: Simple Run (Recommended)
```bash
cd python/
pip install -r requirements.txt
python gpth_cli.py --help
python gpth_gui.py
```

### Option 2: Install as Package
```bash
cd python/
pip install -e .

# Now available globally
gpth --help
gpth-gui
```

### Option 3: Create Executable
```bash
# Install pyinstaller
pip install pyinstaller

# Create CLI executable
pyinstaller --onefile gpth_cli.py

# Create GUI executable  
pyinstaller --onefile --windowed gpth_gui.py

# Find executables in dist/ folder
```

## 🔧 Resource Usage

| Aspect | Python CLI | Python GUI | Dart Version |
|--------|-----------|------------|--------------|
| **Setup Time** | 30 seconds | 30 seconds | 10+ minutes |
| **Dependencies** | ~50MB | ~50MB | ~1.5GB |
| **Memory Usage** | 50-150MB | 100-200MB | 150-400MB |
| **Startup Time** | <1 second | 2-3 seconds | 2-4 seconds |
| **Learning Curve** | None | None | Moderate |

## 📂 Project Structure

```
python/
├── requirements.txt         # Simple dependency list
├── setup.py                # Package installation
├── gpth_cli.py             # CLI launcher
├── gpth_gui.py             # GUI launcher
├── src/
│   ├── core/
│   │   └── gpth_core_api.py # Main processing logic
│   ├── cli/
│   │   └── gpth_cli.py      # Command-line interface
│   └── gui/
│       └── gpth_gui.py      # Tkinter GUI interface
└── README.md               # This file
```

## 💡 Examples

### CLI Examples
```bash
# Quick start
python gpth_cli.py process "C:\Google Takeout" "C:\Organized Photos"

# Analyze first
python gpth_cli.py analyze "C:\Google Takeout"

# Custom processing
python gpth_cli.py process input/ output/ \
  --skip-extras \
  --keep-duplicates \
  --threads 4 \
  --verbose

# Just organize, skip advanced features
python gpth_cli.py process input/ output/ \
  --skip-albums \
  --no-fix-time \
  --no-exiftool
```

### GUI Usage
1. Run `python gpth_gui.py`
2. Click "Browse" to select input/output folders
3. Configure options as needed
4. Click "Analyze" to preview
5. Click "Process" to start organization

## 🛠️ Troubleshooting

### Common Issues

**ImportError: No module named 'PIL'**
```bash
pip install pillow
```

**tkinter not found (Linux)**
```bash
sudo apt-get install python3-tk
```

**Permission errors**
```bash
# Run with appropriate permissions or choose different output folder
```

**Large memory usage**
```bash
# Reduce thread count
python gpth_cli.py process input/ output/ --threads 1
```

## 📊 Comparison: Python vs Dart

| Feature | Python Version | Dart Version | Winner |
|---------|---------------|--------------|--------|
| **Setup Difficulty** | ⭐ Very Easy | ⭐⭐⭐⭐ Hard | 🐍 Python |
| **Resource Usage** | ⭐⭐⭐ Light | ⭐⭐⭐ Light | 🤝 Tie |
| **Performance** | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Better | 🎯 Dart |
| **GUI Quality** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent | 🎯 Dart |
| **Maintainability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | 🐍 Python |
| **Learning Curve** | ⭐⭐⭐⭐⭐ None | ⭐⭐⭐ Moderate | 🐍 Python |

## 🎯 When to Choose Python Version

### Choose Python if:
- ✅ You want zero-hassle setup
- ✅ You're familiar with Python
- ✅ You prefer simple dependencies
- ✅ You need quick deployment
- ✅ You want to modify/extend the code easily

### Choose Dart if:
- ✅ You want the best possible GUI experience
- ✅ You don't mind complex setup
- ✅ You need maximum performance
- ✅ You want the most polished interface

## 🚀 Get Started Now

```bash
# Clone or download the project
git clone https://github.com/Xentraxx/GooglePhotosTakeoutHelper.git

# Go to Python directory  
cd GooglePhotosTakeoutHelper/python/

# Install and run in under 1 minute
pip install -r requirements.txt
python gpth_gui.py
```

**That's it!** No SDK installations, no build configurations, no dependency hell - just simple Python! 🎉

---

*Made with 💝 for users who prefer simplicity over complexity.*