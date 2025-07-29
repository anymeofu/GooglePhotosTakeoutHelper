# 🐍 Google Photos Takeout Helper - Python Edition

A **production-ready modular Python implementation** of the Google Photos Takeout Helper with advanced crash recovery, step-by-step execution, and comprehensive state management.

## 🌟 Why This Python Version?

- ✅ **Modular Design**: Run individual pipeline steps or full workflow
- ✅ **Crash Recovery**: Never lose progress with automatic crash detection
- ✅ **Pause/Resume**: Full control over long-running operations
- ✅ **State Persistence**: Human-readable JSON state management
- ✅ **Production Ready**: Process monitoring, cleanup, and graceful shutdown
- ✅ **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- ExifTool (recommended for full metadata capabilities)

### Installation & Usage

```bash
# 1. Clone the repository
git clone https://github.com/YourRepo/GooglePhotosTakeoutHelper.git
cd GooglePhotosTakeoutHelper

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the modular pipeline
python gpth_cli.py run /path/to/takeout /path/to/output --verbose

# 4. Or run individual steps
python gpth_cli.py step discover-media <run-id>
python gpth_cli.py step remove-duplicates <run-id>
```

## 🏗️ Modular Pipeline Architecture

### 8-Step Processing Workflow
1. **Fix Extensions** - Content-based file extension correction
2. **Discover Media** - Media file cataloging with state persistence
3. **Remove Duplicates** - Intelligent duplicate detection and handling
4. **Extract Dates** - Metadata and JSON-based date extraction
5. **Write EXIF** - EXIF data updating with error recovery
6. **Find Albums** - Album structure discovery from Google JSON
7. **Move Files** - Atomic file organization with rollback capability
8. **Update Timestamps** - File system timestamp synchronization

### 🛡️ Production-Ready Features

**Crash-Resistant Pipeline:**
- ✅ **Never lose progress** - Automatic crash detection prevents "stuck running" status
- ✅ **Resume anywhere** - Continue from exact step where failure occurred  
- ✅ **Process monitoring** - Background tracking of pipeline health
- ✅ **Cleanup commands** - Automatic recovery from system crashes
- ✅ **Signal handling** - Graceful pause/resume via system signals

## 📖 Complete Documentation

**📋 For detailed usage instructions, examples, and advanced features, see:**
### **[📖 MODULAR PIPELINE GUIDE](MODULAR_PIPELINE_GUIDE.md)**

This comprehensive guide covers:
- Complete command reference with examples
- Step-by-step execution workflows
- Crash recovery and troubleshooting
- State management and monitoring
- Advanced configuration options
- Production deployment considerations

## 🎛️ Command Reference

### Core Operations
```bash
# Start a new pipeline run
gpth run input_dir output_dir [--verbose]

# Execute individual steps
gpth step <step-name> <run-id>

# Check pipeline status
gpth status <run-id> [--verbose]
gpth list

# Pause/Resume operations
gpth pause <run-id>
gpth resume <run-id> [--from-step N]

# Recovery operations
gpth cleanup [--auto]
```

### Available Steps
- `fix-extensions` - Fix file extensions based on content
- `discover-media` - Find and catalog media files
- `remove-duplicates` - Remove duplicate files
- `extract-dates` - Extract dates from metadata/JSON
- `write-exif` - Write EXIF metadata
- `find-albums` - Discover album structure
- `move-files` - Organize files into output structure
- `update-timestamps` - Update file creation times

## 🔧 System Requirements

### Required Dependencies
- **Python 3.8+**: Core runtime
- **Pillow**: Image processing and EXIF reading
- **Standard library**: json, pathlib, subprocess, signal

### Optional Dependencies
- **ExifTool**: Professional metadata writing (highly recommended)
- **python-magic**: Enhanced MIME type detection

### Platform Support
- **Windows**: PowerShell timestamp services, process monitoring
- **macOS**: SetFile integration, signal-based pause/resume
- **Linux**: Enhanced touch commands, full signal handling

## 💾 State Management

The modular pipeline uses JSON-based state persistence:

```
pipeline_states/
├── runs/              # Pipeline execution records
├── steps/             # Individual step state data  
├── files/             # Media catalogs and file lists
├── processes/         # Process tracking (PID, status)
└── runs_index.json    # Quick lookup index
```

## 🚨 Error Recovery

The system provides comprehensive crash recovery:

1. **Automatic Detection**: Scans for orphaned processes on startup
2. **Status Cleanup**: Marks crashed runs as "failed" with error context
3. **Resume Capability**: Continue from any step where processing stopped
4. **Graceful Shutdown**: Handles system termination signals properly

## 🤝 Contributing

We welcome contributions! The modular architecture makes it easy to:
- Add new processing steps
- Enhance existing functionality
- Improve error handling
- Add platform-specific optimizations

## 📄 License

This project is licensed under the same terms as the original Dart version.

---

**🚀 Ready to process your Google Photos takeout? Start with the [Modular Pipeline Guide](MODULAR_PIPELINE_GUIDE.md) for complete instructions!**