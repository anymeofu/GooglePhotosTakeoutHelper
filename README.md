# 🐍 Google Photos Takeout Helper - Python Edition v3.0.0

A **production-ready modular Python implementation** of the Google Photos Takeout Helper with advanced crash recovery, step-by-step execution, comprehensive state management, **Phase 2 enhanced services**, and **Phase 3 architecture improvements**.

## 🌟 Why This Python Version?

- ✅ **Modular Design**: Run individual pipeline steps or full workflow
- ✅ **Crash Recovery**: Never lose progress with automatic crash detection
- ✅ **Pause/Resume**: Full control over long-running operations
- ✅ **State Persistence**: Human-readable JSON state management
- ✅ **Production Ready**: Process monitoring, cleanup, and graceful shutdown
- ✅ **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux
- 🆕 **ZIP Processing**: Secure automatic ZIP extraction with progress tracking
- 🆕 **Smart Validation**: Input structure validation with user guidance
- 🆕 **Space Management**: Intelligent disk space checking and recommendations
- 🆕 **Enhanced Interactive Mode**: Complete wizard with 15+ configuration options
- 🆕 **Advanced Progress Reporting**: Real-time progress with ETAs and detailed metrics
- 🔥 **Phase 3 - Architecture**: Dependency injection, type-safe config, error handling, system optimization

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

# 3. Run the new production-ready app (RECOMMENDED)
python gpth_app.py

# 4. Or system analysis only
python gpth_app.py --system-check

# 5. Or run the original modular pipeline
python gpth_cli.py interactive
python gpth_cli.py run /path/to/takeout /path/to/output --verbose
```

## 🆕 Phase 2: Enhanced Services (NEW)

### 🗜️ Automatic ZIP Processing
- **Secure Extraction**: Zip Slip attack prevention with path validation
- **Memory Efficient**: Streaming extraction for large files (>10GB)
- **Progress Tracking**: Real-time extraction progress with file counts
- **Cross-Platform**: Windows filename sanitization and Unicode support

### 🔍 Smart Input Validation
- **Structure Detection**: Automatic Takeout folder recognition
- **Content Analysis**: Media file counting and size estimation
- **User Guidance**: Detailed validation reports with recommendations
- **Path Optimization**: Suggests best input paths for processing

### 💾 Intelligent Space Management
- **Cross-Platform Checking**: Windows/macOS/Linux disk space detection
- **Album Behavior Calculations**: Space multipliers (shortcut=1.1x, duplicate-copy=2.0x)
- **Safety Margins**: Prevents mid-processing space failures
- **Smart Recommendations**: Platform-specific cleanup suggestions

### 🎯 Enhanced Interactive Mode
- **15+ Configuration Options**: Complete wizard covering all features
- **Data Source Selection**: ZIP vs folder with automatic extraction
- **Integrated Validation**: Built-in structure and space checking
- **Step-by-Step Guidance**: User-friendly interface with explanations

### 📊 Advanced Progress Reporting
- **Multi-Step Coordination**: Overall and per-step progress tracking
- **Real-Time Updates**: Progress bars with ETAs and throughput
- **Multiple Formats**: Console, tqdm bars, callback system
- **Performance Metrics**: Detailed timing and processing statistics

## 🔥 Phase 3: Enterprise Architecture (NEW)

### 🏗️ Dependency Injection System
- **Service Container**: Clean IoC container with singleton/transient lifetimes
- **Automatic Resolution**: Recursive dependency injection with circular detection
- **Type Safety**: Fully typed service registration and retrieval
- **Factory Support**: Custom factory functions and lazy initialization

### 📊 Type-Safe Configuration
- **Strongly Typed**: Replace dictionaries with validated dataclasses
- **Runtime Validation**: Cross-section dependency validation
- **Enum-Based Options**: Type-safe album behavior, date organization modes
- **Legacy Compatibility**: Gradual migration from dictionary-based config

### 🎨 UI/Business Logic Separation
- **Presenter Pattern**: Clean separation of UI concerns from business logic
- **Interactive Wizard**: Step-by-step configuration with real-time validation
- **Console Interface**: Professional colored output with user-friendly prompts
- **Modular Design**: Testable, maintainable interactive components

### 🛡️ Comprehensive Error Handling
- **Smart Recovery**: Automatic retry, fallback, skip, and user input strategies
- **Error Classification**: Hierarchical categorization by severity and type
- **Context Preservation**: Detailed error context with stack traces
- **Recovery Management**: Configurable recovery strategies per error category

### ⚡ System Resource Optimization
- **Real-Time Monitoring**: Cross-platform CPU, memory, disk monitoring
- **Performance Analysis**: Bottleneck detection and optimization recommendations
- **Intelligent Settings**: Auto-calculated optimal thread counts and memory limits
- **Platform-Specific**: Windows/macOS/Linux tailored optimizations

### 🚀 Production-Ready App (`gpth_app.py`)
```bash
# Interactive mode with system optimization
python gpth_app.py

# System analysis and recommendations
python gpth_app.py --system-check

# Professional output with error recovery
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
# Start a new pipeline run with basic options
gpth run input_dir output_dir [--verbose] [--dry-run]

# Full pipeline with all options
gpth run input_dir output_dir \
  --album-mode shortcut \
  --date-division 2 \
  --extension-fix standard \
  --max-threads 4 \
  --partner-shared \
  --skip-extras \
  --no-write-exif \
  --transform-pixel-mp \
  --no-guess-from-name \
  --update-creation-time \
  --limit-filesize \
  --fix-mode \
  --quick \
  --verbose \
  --dry-run

# Interactive mode (comprehensive GUI-like experience)
gpth interactive

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

### New CLI Arguments (Full GUI Parity)
```bash
# Album Processing
--album-mode [shortcut|duplicate-copy|reverse-shortcut|json|nothing]

# File Organization
--date-division [0|1|2|3]  # 0=single, 1=year, 2=month, 3=day folders

# Extension Handling
--extension-fix [none|standard|conservative|solo]

# Advanced Options
--partner-shared           # Handle partner shared photos specially
--skip-extras             # Skip extra files (default: true)
--no-write-exif          # Disable EXIF writing
--transform-pixel-mp     # Transform Pixel motion photos
--no-guess-from-name     # Disable date guessing from filenames
--update-creation-time   # Update file creation times
--limit-filesize         # Limit processing to smaller files
--fix-mode              # Enable fix mode for corrections

# Performance
--max-threads N         # Maximum worker threads (default: 4)
--quick                # Quick mode - skip timestamp updates

# Control
--dry-run              # Simulate without making changes
--verbose              # Verbose output
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