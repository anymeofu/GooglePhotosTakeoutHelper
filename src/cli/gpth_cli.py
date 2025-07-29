"""
Google Photos Takeout Helper - CLI Interface
Command-line interface for the GPTH functionality
"""

import sys
import click
import logging
from pathlib import Path
from typing import Optional

from ..core.gpth_core_api import GpthCoreApi, ProcessingConfig, ProcessingResult

class ProgressReporter:
    """Simple progress reporter for CLI"""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.current_step = 0
        self.total_steps = 8
    def update(self, step: int, message: str) -> None:
        """Update progress display"""
        self.current_step = step
        if self.verbose:
            click.echo(f"[{step}/{self.total_steps}] {message}")
        else:
            # Simple progress indicator
            progress = "█" * step + "░" * (self.total_steps - step)
            click.echo(f"\r[{progress}] {message}", nl=False)
    def finish(self) -> None:
        """Finish progress display"""
        if not self.verbose:
            click.echo()  # New line

@click.group()
@click.version_option(version='4.1.0', prog_name='Google Photos Takeout Helper')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Google Photos Takeout Helper - Organize your Google Photos exports"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output_path', type=click.Path(file_okay=False, dir_okay=True))
@click.option('--skip-extras', is_flag=True, default=True, 
              help='Skip extra files (edited versions, etc.)')
@click.option('--skip-albums', is_flag=True, default=False,
              help='Skip album organization')
@click.option('--keep-duplicates', is_flag=True, default=False,
              help='Keep duplicate files instead of removing them')
@click.option('--no-fix-time', is_flag=True, default=False,
              help='Do not fix file creation times')
@click.option('--no-exiftool', is_flag=True, default=False,
              help='Do not use ExifTool for metadata')
@click.option('--threads', '-t', type=int, default=4,
              help='Number of threads for processing')
@click.option('--dry-run', is_flag=True, default=False,
              help='Simulate processing without making changes (saves time and processing power)')
@click.pass_context
def process(ctx, input_path, output_path, skip_extras, skip_albums,
           keep_duplicates, no_fix_time, no_exiftool, threads, dry_run):
    """Process Google Photos takeout archive
    
    INPUT_PATH: Path to the extracted Google Photos takeout folder
    OUTPUT_PATH: Path where organized photos should be placed
    """
    verbose = ctx.obj.get('verbose', False)
    
    # Create configuration
    config = ProcessingConfig(
        input_path=input_path,
        output_path=output_path,
        skip_extras=skip_extras,
        skip_albums=skip_albums,
        keep_duplicates=keep_duplicates,
        fix_creation_time=not no_fix_time,
        use_exiftool=not no_exiftool,
        max_threads=threads,
        verbose=verbose,
        dry_run=dry_run
    )
    
    # Setup progress reporting
    progress = ProgressReporter(verbose=verbose)
    
    # Create API instance
    api = GpthCoreApi(config)
    api.set_progress_callback(progress.update)
    
    try:
        # Display welcome message
        click.echo(click.style("🚀 Google Photos Takeout Helper", fg='blue', bold=True))
        click.echo(f"Input: {input_path}")
        click.echo(f"Output: {output_path}")
        click.echo()
        
        # Validate paths first
        click.echo("Validating paths...")
        valid, errors = api.validate_paths()
        if not valid:
            for error in errors:
                click.echo(click.style(f"❌ {error}", fg='red'))
            sys.exit(1)
        
        # Discover takeout structure
        click.echo("Analyzing takeout structure...")
        structure = api.discover_takeout_structure()
        
        click.echo(f"📁 Found {structure['total_files']} total files")
        click.echo(f"📸 Found {structure['media_files']} media files") 
        click.echo(f"📄 Found {structure['json_files']} metadata files")
        click.echo(f"⏱️  Estimated processing time: {structure['estimated_processing_time']:.1f} seconds")
        
        if not structure['has_photos']:
            click.echo(click.style("⚠️  Warning: No Google Photos folders detected", fg='yellow'))
        
        if structure['has_albums'] and not skip_albums:
            click.echo("🎨 Albums detected and will be processed")
        
        # Confirm processing
        if not click.confirm(f"\nProcess {structure['media_files']} media files?"):
            click.echo("Operation cancelled.")
            sys.exit(0)
        
        click.echo()
        click.echo("Processing takeout data...")
        
        # Process the takeout
        result = api.process_takeout()
        
        # Finish progress display
        progress.finish()
        
        # Display results
        if result.success:
            click.echo(click.style("✅ Processing completed successfully!", fg='green', bold=True))
        else:
            click.echo(click.style("❌ Processing failed!", fg='red', bold=True))
        
        click.echo()
        click.echo("📊 Results:")
        click.echo(f"   Total files: {result.total_files}")
        click.echo(f"   Processed: {result.processed_files}")
        click.echo(f"   Duplicates removed: {result.duplicates_removed}")
        click.echo(f"   Albums found: {result.albums_found}")
        click.echo(f"   Processing time: {result.processing_time:.2f} seconds")
        
        if result.errors:
            click.echo()
            click.echo(click.style("❌ Errors:", fg='red'))
            for error in result.errors:
                click.echo(f"   • {error}")
        
        if result.warnings:
            click.echo()
            click.echo(click.style("⚠️  Warnings:", fg='yellow'))
            for warning in result.warnings:
                click.echo(f"   • {warning}")
        
        if not result.success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("🛑 Processing cancelled by user", fg='yellow'))
        sys.exit(1)
    except Exception as e:
        click.echo()
        click.echo(click.style(f"💥 Unexpected error: {str(e)}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def analyze(ctx, input_path):
    """Analyze takeout structure without processing
    
    INPUT_PATH: Path to the extracted Google Photos takeout folder
    """
    verbose = ctx.obj.get('verbose', False)
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for analysis
        verbose=verbose
    )
    
    api = GpthCoreApi(config)
    
    try:
        click.echo(click.style("🔍 Analyzing Google Photos Takeout", fg='blue', bold=True))
        click.echo(f"Path: {input_path}")
        click.echo()
        
        structure = api.discover_takeout_structure()
        
        click.echo("📊 Takeout Structure Analysis:")
        click.echo(f"   📁 Total files: {structure['total_files']}")
        click.echo(f"   📸 Media files: {structure['media_files']}")
        click.echo(f"   📄 JSON metadata files: {structure['json_files']}")
        click.echo(f"   📷 Has Google Photos: {'Yes' if structure['has_photos'] else 'No'}")
        click.echo(f"   🎨 Has albums: {'Yes' if structure['has_albums'] else 'No'}")
        click.echo(f"   ⏱️  Estimated processing time: {structure['estimated_processing_time']:.1f} seconds")
        
        media_percentage = (structure['media_files'] / structure['total_files'] * 100) if structure['total_files'] > 0 else 0
        click.echo(f"   📊 Media file ratio: {media_percentage:.1f}%")
        
        # Recommendations
        click.echo()
        click.echo("💡 Recommendations:")
        if not structure['has_photos']:
            click.echo("   ⚠️  This doesn't look like a Google Photos takeout")
        if structure['media_files'] == 0:
            click.echo("   ❌ No media files found")
        elif structure['media_files'] < 100:
            click.echo("   ✅ Small archive - processing should be quick")
        elif structure['media_files'] < 1000:
            click.echo("   ⏳ Medium archive - processing will take a few minutes")
        else:
            click.echo("   🕐 Large archive - processing may take 10+ minutes")
        
        if structure['json_files'] == 0:
            click.echo("   ⚠️  No metadata files found - date extraction will be limited")
        
        if structure['has_albums']:
            click.echo("   🎨 Albums detected - use --skip-albums if you don't want them")
            
    except Exception as e:
        click.echo(click.style(f"💥 Analysis failed: {str(e)}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def validate(ctx, input_path):
    """Validate Google Photos takeout structure
    
    INPUT_PATH: Path to the extracted Google Photos takeout folder
    """
    verbose = ctx.obj.get('verbose', False)
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for validation
        verbose=verbose
    )
    
    api = GpthCoreApi(config)
    
    try:
        click.echo(click.style("🔍 Validating Google Photos Takeout", fg='blue', bold=True))
        click.echo(f"Path: {input_path}")
        click.echo()
        
        validation = api.validate_takeout_structure(input_path)
        
        if validation['is_valid']:
            click.echo(click.style("✅ Valid takeout structure", fg='green'))
        else:
            click.echo(click.style("❌ Invalid takeout structure", fg='red'))
        
        click.echo()
        click.echo("📝 Details:")
        for detail in validation['details']:
            click.echo(f"   • {detail}")
            
        if not validation['is_valid']:
            click.echo()
            click.echo("💡 Tips:")
            click.echo("   • Make sure you extracted all ZIP files to the same folder")
            click.echo("   • Look for folders named 'Photos from YYYY'")
            click.echo("   • Check if the path contains Google Photos export data")
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"💥 Validation failed: {str(e)}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def estimate(ctx, input_path):
    """Estimate disk space requirements
    
    INPUT_PATH: Path to the extracted Google Photos takeout folder
    """
    verbose = ctx.obj.get('verbose', False)
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for estimation
        verbose=verbose
    )
    
    api = GpthCoreApi(config)
    
    try:
        click.echo(click.style("📊 Estimating Space Requirements", fg='blue', bold=True))
        click.echo(f"Path: {input_path}")
        click.echo()
        
        estimate = api.estimate_space_requirements(input_path)
        
        def format_size(size_bytes):
            """Format size in bytes to human readable format"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        
        click.echo(f"📁 Current size: {format_size(estimate['current_size'])}")
        click.echo(f"📈 Estimated space needed: {format_size(estimate['estimated_required_space'])}")
        click.echo(f"➕ Additional space needed: {format_size(estimate['additional_space_needed'])}")
        click.echo(f"📊 Space multiplier: {estimate['space_multiplier']:.1f}x")
        click.echo(f"📄 File count: {estimate['file_count']:,}")
        
        # Check available space
        available = api.get_available_space(input_path)
        if available:
            click.echo(f"💾 Available space: {format_size(available)}")
            
            if available < estimate['estimated_required_space']:
                click.echo(click.style("⚠️  Warning: Insufficient disk space!", fg='red'))
                shortfall = estimate['estimated_required_space'] - available
                click.echo(f"   Need {format_size(shortfall)} more space")
            else:
                click.echo(click.style("✅ Sufficient disk space available", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"💥 Estimation failed: {str(e)}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.pass_context
def check_deps(ctx):
    """Check system dependencies"""
    verbose = ctx.obj.get('verbose', False)
    
    # Dummy config for API instantiation
    config = ProcessingConfig(input_path="", output_path="")
    api = GpthCoreApi(config)
    
    click.echo(click.style("🔧 System Dependencies Check", fg='blue', bold=True))
    click.echo()
    
    # Check Python dependencies
    deps_status = []
    
    # Check PIL/Pillow
    try:
        from PIL import Image, ExifTags
        deps_status.append(("Pillow (PIL)", True, "Image processing available"))
    except ImportError:
        deps_status.append(("Pillow (PIL)", False, "Install with: pip install pillow"))
    
    # Check dateutil
    try:
        from dateutil import parser
        deps_status.append(("python-dateutil", True, "Date parsing available"))
    except ImportError:
        deps_status.append(("python-dateutil", False, "Install with: pip install python-dateutil"))
    
    # Check tqdm
    try:
        from tqdm import tqdm
        deps_status.append(("tqdm", True, "Progress bars available"))
    except ImportError:
        deps_status.append(("tqdm", False, "Install with: pip install tqdm"))
    
    # Check ExifTool
    exiftool_info = api.check_exiftool_status()
    deps_status.append(("ExifTool", exiftool_info['is_available'], exiftool_info['message']))
    
    # Display results
    all_good = True
    for name, available, message in deps_status:
        if available:
            click.echo(click.style(f"✅ {name}", fg='green') + f" - {message}")
        else:
            click.echo(click.style(f"❌ {name}", fg='red') + f" - {message}")
            all_good = False
    
    click.echo()
    if all_good:
        click.echo(click.style("🎉 All dependencies are available!", fg='green', bold=True))
    else:
        click.echo(click.style("⚠️  Some dependencies are missing", fg='yellow', bold=True))
        click.echo("Run: pip install pillow python-dateutil tqdm")
        if not exiftool_info['is_available']:
            click.echo("Install ExifTool from: https://exiftool.org/")

@cli.command()
def info():
    """Show information about the tool"""
    click.echo(click.style("Google Photos Takeout Helper", fg='blue', bold=True))
    click.echo("Version: 4.1.0")
    click.echo()
    click.echo("This tool helps organize Google Photos takeout exports into a")
    click.echo("clean, chronological folder structure with proper metadata.")
    click.echo()
    click.echo("Features:")
    click.echo("  📁 Organize photos by date")
    click.echo("  🔗 Remove duplicates")
    click.echo("  📅 Extract dates from EXIF/metadata")
    click.echo("  🎨 Process albums")
    click.echo("  ⏰ Fix file timestamps")
    click.echo("  📊 Validate takeout structure")
    click.echo("  💾 Estimate space requirements")
    click.echo()
    click.echo("Available Commands:")
    click.echo("  analyze    - Analyze takeout structure")
    click.echo("  validate   - Validate takeout structure")
    click.echo("  estimate   - Estimate space requirements")
    click.echo("  process    - Process takeout data")
    click.echo("  check-deps - Check system dependencies")
    click.echo("  info       - Show this information")
    click.echo()
    click.echo("Usage Examples:")
    click.echo("  gpth analyze /path/to/takeout")
    click.echo("  gpth validate /path/to/takeout")
    click.echo("  gpth estimate /path/to/takeout")
    click.echo("  gpth process /path/to/takeout /path/to/output")
    click.echo("  gpth process input/ output/ --skip-albums --verbose")
    click.echo("  gpth check-deps")

if __name__ == '__main__':
    cli()