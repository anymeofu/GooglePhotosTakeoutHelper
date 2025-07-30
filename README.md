# Google Photos Takeout Helper

A comprehensive Python tool for organizing Google Photos Takeout exports into a clean, structured photo library. Automatically handles duplicate detection, date extraction, album organization, and metadata preservation.

## 🚀 Quick Start

**Most users should start here:**
```bash
python gpth_gui.py
```

## 📋 Table of Contents

- [Installation](#installation)
- [Available Versions](#available-versions)
- [Features](#features)
- [Command Line Reference](#command-line-reference)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)
- [System Requirements](#system-requirements)
- [Deployment](#deployment)

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows, macOS, or Linux

### Setup
1. **Download or clone this repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the tool:**
   ```bash
   python gpth_gui.py
   ```

## Available Versions

This tool comes in **3 different versions** with clear, descriptive names:

### 1. 🖼️ Enhanced GUI (Best for Most Users)
**File:** `gpth_gui.py`
```bash
python gpth_gui.py
```
**Features:**
- Clean tabbed interface with all features
- Built-in help system (❓ Help button)
- System information checker (🔧 System Info button) 
- Input validation and space estimation
- Real-time progress tracking
- Perfect for beginners and power users alike

### 2. 💻 Interactive CLI (User-Friendly Command Line) 
**File:** `gpth_interactive.py`
```bash
# Interactive mode (recommended)
python gpth_interactive.py

# With system check
python gpth_interactive.py --system-check

# Version information
python gpth_interactive.py --version
```
**Features:**
- Interactive wizard mode
- System optimization checks
- Comprehensive error handling
- Great for command line users

**Available Flags:**
- `--version` - Show version information and exit
- `--system-check` - Run system analysis and optimization check only
- `--log-level {DEBUG,INFO,WARNING,ERROR}` - Set logging level (default: INFO)
- `--no-color` - Disable colored output

### 3. 🔧 Modular CLI (Advanced Control)
**File:** `gpth_modular.py`
```bash
# Interactive setup
python gpth_modular.py

# Full pipeline processing
python gpth_modular.py run /path/to/takeout /path/to/output

# Step-by-step processing
python gpth_modular.py step discover-media run_12345

# Resume from specific step
python gpth_modular.py continue run_id --from-step 3

# List all pipeline runs
python gpth_modular.py list --detailed

# Cleanup orphaned runs
python gpth_modular.py clean
```
**Features:**
- Individual pipeline steps
- Advanced debugging and resuming
- Fine control over process
- For developers/troubleshooting

## Features

### Core Processing
- **Smart Duplicate Detection** - Identifies and removes duplicate photos/videos
- **Intelligent Date Extraction** - Extracts dates from EXIF, JSON files, and filenames
- **Album Organization** - Reconstructs Google Photos albums with multiple strategies
- **Metadata Preservation** - Writes GPS coordinates and dates to EXIF data
- **Extension Fixing** - Corrects file extensions based on actual file content

### Organization Options
- **Date-based Folders** - Organize by year, year/month, or year/month/day
- **Album Strategies** - Multiple ways to handle Google Photos albums
- **Partner Sharing** - Separate shared photos from personal photos
- **Extra File Handling** - Skip or include edited versions and extra files

### Safety & Performance
- **Dry Run Mode** - Preview changes before applying them
- **Progress Tracking** - Real-time progress with detailed status
- **Error Recovery** - Comprehensive error handling with recovery options
- **System Optimization** - Checks available disk space and system resources
- **Cross-Platform** - Works on Windows, macOS, and Linux

## Command Line Reference

### Interactive CLI (`gpth_interactive.py`)

Basic usage:
```bash
python gpth_interactive.py [OPTIONS]
```

**Options:**
- `--version` - Show version information
- `--system-check` - Run system analysis only
- `--log-level {DEBUG,INFO,WARNING,ERROR}` - Set logging verbosity
- `--no-color` - Disable colored terminal output

**Examples:**
```bash
# Start interactive mode
python gpth_interactive.py

# Check system requirements
python gpth_interactive.py --system-check

# Debug mode with verbose logging
python gpth_interactive.py --log-level DEBUG
```

### Modular CLI (`gpth_modular.py`)

#### Full Pipeline Processing
```bash
python gpth_modular.py run INPUT_DIR OUTPUT_DIR [OPTIONS]
```

**Required Arguments:**
- `INPUT_DIR` - Path to Google Takeout directory
- `OUTPUT_DIR` - Path where organized photos will be saved

**Processing Options:**
- `--dry-run` - Test without making changes (recommended first)
- `--verbose` - Detailed output during processing
- `--quick` - Skip timestamp updates for faster processing

**Album Handling:**
- `--album-mode {shortcut,duplicate-copy,reverse-shortcut,json,nothing}`
  - `shortcut` - Create shortcuts to photos in albums (default)
  - `duplicate-copy` - Copy photos into album folders
  - `reverse-shortcut` - Photos in albums, shortcuts in date folders
  - `json` - Keep album info in JSON files only
  - `nothing` - Skip album processing

**Date Organization:**
- `--date-division {0,1,2,3}`
  - `0` - No date folders (default)
  - `1` - Organize by year (2023/)
  - `2` - Organize by year/month (2023/01-January/)
  - `3` - Organize by year/month/day (2023/01-January/01/)

**File Processing:**
- `--partner-shared` - Separate partner shared media into its own folder
- `--skip-extras` - Skip extra images ("-edited" versions, etc.)
- `--no-write-exif` - Skip writing GPS/dates to EXIF metadata
- `--transform-pixel-mp` - Convert Pixel Motion Photos (.MP/.MV) to .mp4
- `--no-guess-from-name` - Don't extract dates from filenames
- `--update-creation-time` - Update file creation time (Windows only)
- `--limit-filesize` - Skip files larger than 64MB

**Extension Fixing:**
- `--extension-fix-mode {none,standard,conservative,solo}`
  - `none` - Don't fix extensions
  - `standard` - Fix common extension issues (default)
  - `conservative` - Only fix obvious mismatches
  - `solo` - Fix extensions without other processing

**Performance:**
- `--max-threads {1-16}` - Number of processing threads (default: 4)

#### Step-by-Step Processing
```bash
python gpth_modular.py step STEP_NAME RUN_ID
```

**Available Steps:**
- `fix-extensions` - Correct file extensions
- `discover-media` - Find and catalog all media files
- `remove-duplicates` - Detect and remove duplicate files
- `extract-dates` - Extract dates from various sources
- `write-exif` - Write metadata to files
- `find-albums` - Discover album information
- `move-files` - Organize files into final structure
- `update-timestamps` - Update file timestamps

#### Pipeline Management
```bash
# Resume interrupted processing
python gpth_modular.py continue RUN_ID [--from-step N]

# List all pipeline runs
python gpth_modular.py list [--detailed]

# Pause running pipeline
python gpth_modular.py pause RUN_ID

# Cleanup orphaned runs
python gpth_modular.py clean
```

## Advanced Configuration

### Processing Examples

**Basic organization with albums:**
```bash
python gpth_modular.py run "C:\Takeout" "C:\Photos" --album-mode duplicate-copy
```

**Year-based organization with EXIF writing:**
```bash
python gpth_modular.py run "C:\Takeout" "C:\Photos" --date-division 1 --album-mode shortcut
```

**Conservative processing (safe mode):**
```bash
python gpth_modular.py run "C:\Takeout" "C:\Photos" --dry-run --skip-extras --no-write-exif
```

**Fast processing (skip timestamps):**
```bash
python gpth_modular.py run "C:\Takeout" "C:\Photos" --quick --max-threads 8
```

**Partner sharing separation:**
```bash
python gpth_modular.py run "C:\Takeout" "C:\Photos" --partner-shared --date-division 2
```

### Album Strategies Explained

1. **Shortcut (Default)** - Photos organized by date, with shortcuts in album folders
   - Best for most users
   - Saves disk space
   - Preserves both date and album organization

2. **Duplicate-Copy** - Photos copied into both date and album folders
   - Uses more disk space
   - Easier browsing in album folders
   - Good for sharing specific albums

3. **Reverse-Shortcut** - Photos in album folders, shortcuts in date folders
   - Album-centric organization
   - Date folders contain shortcuts
   - Good if you primarily browse by album

4. **JSON** - Album info preserved in JSON files only
   - Minimal organization impact
   - Preserves album metadata for later processing
   - Good for custom organization scripts

5. **Nothing** - Skip album processing entirely
   - Fastest processing
   - Date-only organization
   - Good for simple chronological organization

## Troubleshooting

### Common Issues

#### Permission Errors
**Problem:** "Permission denied" when accessing files
**Solutions:**
- Run as administrator (Windows) or with `sudo` (macOS/Linux)
- Check that input files aren't in use by other programs
- Ensure output directory is writable

#### Memory Issues
**Problem:** "Out of memory" errors with large libraries
**Solutions:**
- Use `--limit-filesize` to skip very large files
- Reduce `--max-threads` to 1 or 2
- Process libraries in smaller batches
- Ensure sufficient RAM (8GB+ recommended for large libraries)

#### Slow Processing
**Problem:** Processing takes very long
**Solutions:**
- Use `--quick` flag to skip timestamp updates
- Increase `--max-threads` (but don't exceed CPU cores)
- Use SSD storage for both input and output
- Skip EXIF writing with `--no-write-exif` if not needed

#### Missing Photos
**Problem:** Some photos don't appear in output
**Solutions:**
- Check for duplicates (they may have been removed)
- Look in partner-shared folder if using `--partner-shared`
- Check if files were skipped due to `--limit-filesize`
- Review processing logs for errors

#### Album Issues
**Problem:** Albums not created or incomplete
**Solutions:**
- Try different `--album-mode` settings
- Check that `metadata.json` files exist in input
- Some albums may be empty or contain only duplicates
- Use `list --detailed` to see processing status

#### Date Problems
**Problem:** Photos have wrong dates or sorted incorrectly
**Solutions:**
- Enable `--no-guess-from-name` if filename dates are wrong
- Check EXIF data exists in original files
- Some photos may not have reliable date information
- Use `--update-creation-time` on Windows for better sorting

### Error Recovery

If processing is interrupted:
1. **Resume where you left off:**
   ```bash
   python gpth_modular.py continue RUN_ID
   ```

2. **Resume from specific step:**
   ```bash
   python gpth_modular.py continue RUN_ID --from-step 4
   ```

3. **Start fresh if needed:**
   - Clean up with `python gpth_modular.py clean`
   - Delete partial output directory
   - Start processing again

### Debug Mode

For detailed troubleshooting:
```bash
python gpth_interactive.py --log-level DEBUG
```

Or for modular CLI:
```bash
python gpth_modular.py run "input" "output" --verbose
```

## System Requirements

### Minimum Requirements
- **OS:** Windows 10, macOS 10.14, or Ubuntu 18.04+
- **Python:** 3.7 or higher
- **RAM:** 4GB (8GB+ recommended for large libraries)
- **Storage:** 2x the size of your Google Takeout (for processing space)
- **CPU:** Any modern processor (multi-core recommended)

### Recommended Specifications
- **RAM:** 16GB+ for libraries over 100GB
- **Storage:** SSD for both input and output locations
- **CPU:** 4+ cores for faster processing
- **Free Space:** 3x your Takeout size for safe processing

### Storage Considerations
- **Input:** Your Google Takeout archive (can be on slower storage)
- **Output:** Organized photos directory (SSD recommended)
- **Temp Space:** Python may need additional space for processing
- **Safety Margin:** Keep 20% free space on your drives

## Deployment

### Standalone Deployment

For non-technical users, you can create a standalone executable:

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Create executable:**
   ```bash
   pyinstaller --onefile --windowed gpth_gui.py
   ```

3. **Bundle with dependencies:**
   ```bash
   pyinstaller --onefile --add-data "requirements.txt;." gpth_gui.py
   ```

### Docker Deployment

For server environments:

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "gpth_interactive.py"]
   ```

2. **Build and run:**
   ```bash
   docker build -t gpth .
   docker run -v /path/to/takeout:/input -v /path/to/output:/output gpth
   ```

### Network Storage

For processing files on network drives:

1. **Mount network drive properly**
2. **Use full paths in commands**
3. **Consider copying to local storage first for better performance**
4. **Use `--max-threads 1` to avoid network congestion**

## Quick Start Recommendation

**Most users:** Start with the **Enhanced GUI** (`python gpth_gui.py`)  
**Command line users:** Use **Interactive CLI** (`python gpth_interactive.py`)  
**Developers:** Use **Modular CLI** for debugging (`python gpth_modular.py`)

## Tips for Success

1. **Start with dry run:**
   ```bash
   python gpth_modular.py run "input" "output" --dry-run
   ```

2. **Test with small subset first**
3. **Keep a backup of your original Takeout files**
4. **Use SSD storage for faster processing**
5. **Monitor disk space during processing**
6. **Start with default settings before customizing**

## Getting Help

- Use the built-in help system in the GUI (❓ Help button)
- Run `--system-check` to verify your setup
- Check this README for detailed command options
- Review log files for specific error messages
- Try dry run mode to preview changes