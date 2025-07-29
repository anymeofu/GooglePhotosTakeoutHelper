# Google Photos Takeout Helper - Modular Pipeline Guide

## Overview

The modular pipeline system allows you to execute Google Photos processing steps individually or in ranges, with full state persistence and resume capability. This provides better control, debugging, and reproducibility for large processing tasks.

## Key Features

- **Step-by-Step Execution**: Run individual processing steps
- **State Persistence**: Human-readable JSON files track progress
- **Resume Capability**: Continue from failed or interrupted steps
- **CLI Interface**: Command-line tools for automation
- **Dry Run Support**: Test processing without making changes
- **Progress Tracking**: Detailed status and logging

## Pipeline Steps

The processing pipeline consists of 8 distinct steps:

1. **Fix Extensions** - Correct file extensions based on content
2. **Discover Media** - Find and catalog all media files
3. **Remove Duplicates** - Identify and handle duplicate files
4. **Extract Dates** - Parse creation dates from metadata
5. **Write EXIF** - Update EXIF data with correct timestamps
6. **Find Albums** - Discover album structure from JSON files
7. **Move Files** - Organize files into output structure
8. **Update Timestamps** - Set file system timestamps

## Quick Start

### 1. Run Full Pipeline

```bash
python gpth_cli.py run input_dir output_dir --verbose
```

### 2. Execute Individual Steps

```bash
# Start a pipeline (gets run ID)
python gpth_cli.py run input_dir output_dir

# Execute specific step
python gpth_cli.py step discover-media <run-id>
python gpth_cli.py step extract-dates <run-id>
```

### 3. Pause/Resume Operations

```bash
# Pause a running pipeline
python gpth_cli.py pause <run-id>

# Resume a paused pipeline
python gpth_cli.py resume <run-id>

# Resume from specific step
python gpth_cli.py resume <run-id> --from-step 4
```

### 4. Crash Recovery & Cleanup

```bash
# Clean up orphaned runs (crashed processes)
python gpth_cli.py cleanup

# Auto-cleanup without confirmation
python gpth_cli.py cleanup --auto
```

### 5. Check Status

```bash
# List all pipeline runs
python gpth_cli.py list

# Check detailed status
python gpth_cli.py status <run-id> --verbose
```

## CLI Commands

### `run` - Start Full Pipeline

```bash
python gpth_cli.py run INPUT_DIR OUTPUT_DIR [OPTIONS]
```

Options:
- `--dry-run`: Simulate without making changes
- `--verbose`: Enable detailed logging

### `step` - Execute Single Step

```bash
python gpth_cli.py step STEP_NAME RUN_ID
```

Available steps:
- `fix-extensions`
- `discover-media`
- `remove-duplicates`
- `extract-dates`
- `write-exif`
- `find-albums`
- `move-files`
- `update-timestamps`

### `status` - Check Pipeline Status

```bash
python gpth_cli.py status RUN_ID [--verbose]
```

### `pause` - Pause Running Pipeline

```bash
python gpth_cli.py pause RUN_ID
```

### `resume` - Resume Pipeline

```bash
# Resume paused pipeline
python gpth_cli.py resume RUN_ID

# Resume from specific step
python gpth_cli.py resume RUN_ID --from-step STEP_NUMBER
```

### `cleanup` - Clean Up Crashed Runs

```bash
# Interactive cleanup
python gpth_cli.py cleanup

# Automatic cleanup
python gpth_cli.py cleanup --auto
```

### `list` - List Pipeline Runs

```bash
python gpth_cli.py list
```

## Crash Recovery & Resilience

### Automatic Crash Detection

The system automatically detects when pipelines crash or are killed unexpectedly:

- **Process Monitoring**: Active processes are tracked with PID files
- **Orphan Detection**: Runs left in "running" state are detected on restart
- **Status Cleanup**: Crashed runs are marked as "failed" automatically

### Pause/Resume Operations

**Signal-based Control** (Unix/Linux):
```bash
# Send pause signal to running process
kill -USR1 <process-id>

# Send resume signal
kill -USR2 <process-id>
```

**CLI Commands**:
```bash
# Pause via CLI
python gpth_cli.py pause <run-id>

# Resume via CLI
python gpth_cli.py resume <run-id>
```

### Graceful Shutdown

The system handles shutdown gracefully:
- SIGTERM/SIGINT signals trigger cleanup
- Active processes are paused before termination
- State is preserved for later resumption

## State Management

### File Structure

```
pipeline_states/
├── runs/
│   ├── 20241201_143022_123.json    # Pipeline run data
│   └── 20241201_143045_456.json
├── steps/
│   ├── 20241201_143022_123_step_1.json  # Step state data
│   └── 20241201_143022_123_step_2.json
├── files/
│   └── media_catalog_20241201_143022_123.json
└── runs_index.json                 # Quick lookup index
```

### Pipeline Run Data

Each pipeline run is stored as a JSON file containing:

```json
{
  "id": "20241201_143022_123",
  "input_path": "/path/to/takeout",
  "output_path": "/path/to/output",
  "started_at": "2024-12-01T14:30:22.123456",
  "status": "running",
  "config": {
    "album_mode": "shortcut",
    "extension_fix_mode": "standard",
    "dry_run": false
  },
  "steps": [
    {
      "step_number": 1,
      "step_name": "fix_extensions",
      "display_name": "Fix Extensions",
      "status": "completed",
      "started_at": "2024-12-01T14:30:22.123456",
      "completed_at": "2024-12-01T14:30:25.789012",
      "duration": 3.67,
      "input_files_count": 1500,
      "output_files_count": 1500,
      "errors_count": 0
    }
  ]
}
```

## Advanced Usage

### Resume from Specific Step

```bash
# Resume from step 4 (if earlier steps completed)
python gpth_cli.py step extract-dates <run-id>
python gpth_cli.py step write-exif <run-id>
# ... continue with remaining steps
```

### Dry Run Mode

Always test with dry run first:

```bash
python gpth_cli.py run input_dir output_dir --dry-run --verbose
```

### Debugging Failed Steps

1. Check status with verbose output:
```bash
python gpth_cli.py status <run-id> --verbose
```

2. Review step state files:
```bash
cat pipeline_states/steps/<run-id>_step_2.json
```

3. Re-run failed step:
```bash
python gpth_cli.py step discover-media <run-id>
```

## Python API Usage

### Basic Pipeline Usage

```python
from src.core.modular_pipeline import ModularPipeline
from src.core.gpth_core_api import ProcessingConfig
from pathlib import Path
import logging

# Setup
config = ProcessingConfig(
    input_path="/path/to/takeout",
    output_path="/path/to/output",
    dry_run=True
)
state_dir = Path("./pipeline_states")
logger = logging.getLogger('gpth')

# Create pipeline
pipeline = ModularPipeline(config, state_dir, logger)

# Start run
run_id = pipeline.start_pipeline(
    Path("/path/to/takeout"), 
    Path("/path/to/output")
)

# Execute steps
for step_num in range(1, 9):
    result = pipeline.execute_step(run_id, step_num)
    if not result.success:
        print(f"Step {step_num} failed: {result.error}")
        break
```

### Individual Step Execution

```python
# Execute just step 2 (Discover Media)
result = pipeline.execute_step(run_id, 2)

# Check step state
step_state = pipeline.state_manager.get_step_state(run_id, 2)
media_files = step_state.get('media_files', [])
```

### Progress Monitoring

```python
def progress_callback(step: int, message: str, progress: float):
    print(f"Step {step}: {message} ({progress:.1f}%)")

pipeline.set_progress_callback(progress_callback)
```

## Configuration Options

### Processing Config

```python
ProcessingConfig(
    input_path="/path/to/takeout",        # Required
    output_path="/path/to/output",        # Required
    album_mode=AlbumMode.SHORTCUT,        # Album handling
    extension_fix_mode=ExtensionFixMode.STANDARD,  # Extension fixing
    dry_run=False,                        # Simulation mode
    verbose=False,                        # Detailed logging
    write_exif=True,                      # Update EXIF data
    update_creation_time=False,           # Update file timestamps
    max_threads=4,                        # Parallel processing
    skip_extras=True                      # Skip non-media files
)
```

## Best Practices

### 1. Always Test First
```bash
python gpth_cli.py run input_dir output_dir --dry-run --verbose
```

### 2. Monitor Progress
Use verbose mode to track detailed progress:
```bash
python gpth_cli.py status <run-id> --verbose
```

### 3. Resume on Failures
The system automatically saves state - you can resume from any step:
```bash
python gpth_cli.py step extract-dates <run-id>
```

### 4. Backup State Files
Keep copies of `pipeline_states/` for important runs:
```bash
cp -r pipeline_states/ pipeline_states_backup/
```

## Troubleshooting

### Common Issues

1. **Step fails with "Pipeline run not found"**
   - Check run ID with `python gpth_cli.py list`
   - Ensure `pipeline_states/` directory exists

2. **"Invalid step number" error**
   - Verify step name spelling
   - Use `python gpth_cli.py step --help` for valid options

3. **Permission errors**
   - Check write permissions for output directory
   - Verify input directory read permissions

### Debug Mode

Enable debug logging in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### State Recovery

If state files are corrupted, you can:

1. Delete the corrupted run: `rm pipeline_states/runs/<run-id>.json`
2. Start fresh with a new run ID
3. Manually edit JSON files if needed (they're human-readable)

## Integration

### With CI/CD Systems

```yaml
# GitHub Actions example
- name: Process Google Takeout
  run: |
    python gpth_cli.py run $INPUT_DIR $OUTPUT_DIR --dry-run
    if [ $? -eq 0 ]; then
      python gpth_cli.py run $INPUT_DIR $OUTPUT_DIR
    fi
```

### With Monitoring

```python
# Monitor pipeline progress
pipeline_run = pipeline.state_manager.get_pipeline_run(run_id)
completed_steps = len([s for s in pipeline_run.steps if s['status'] == 'completed'])
print(f"Progress: {completed_steps}/8 steps completed")
```

## Performance Tips

1. **Use appropriate thread count**: `--max-threads 8` for powerful machines
2. **Process in chunks**: For very large takeouts, break into smaller directories
3. **Use SSD storage**: State files benefit from fast I/O
4. **Monitor memory**: Large takeouts may require sufficient RAM

## Migration from Original System

To upgrade from the original monolithic pipeline:

1. **Test with dry run**:
   ```bash
   python gpth_cli.py run input_dir output_dir --dry-run
   ```

2. **Run modular pipeline**:
   ```bash
   python gpth_cli.py run input_dir output_dir
   ```

3. **Compare results** with your previous output

The modular system is designed to be fully compatible with existing workflows while providing enhanced control and reliability.