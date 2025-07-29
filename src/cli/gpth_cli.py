"""
Google Photos Takeout Helper - CLI Interface
Command-line interface for the GPTH functionality
"""

import sys
import click
import logging
from pathlib import Path
from typing import Optional

from ..core.gpth_core_api import GooglePhotosTakeoutHelper, ProcessingConfig, ProcessingResult, AlbumMode, ExtensionFixMode

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
@click.option('--output', '-o', 'output_path', type=click.Path(file_okay=False, dir_okay=True),
              help='Output directory for organized photos')
@click.option('--albums', type=click.Choice(['shortcut', 'duplicate-copy', 'reverse-shortcut', 'json', 'nothing']),
              default='shortcut', help='Album handling mode')
@click.option('--divide-to-dates', type=click.IntRange(0, 3), default=0,
              help='Date-based folder structure: 0=single folder, 1=year, 2=year/month, 3=year/month/day')
@click.option('--divide-partner-shared', is_flag=True, default=False,
              help='Separate partner shared media into PARTNER_SHARED folder')
@click.option('--skip-extras', is_flag=True, default=True,
              help='Skip extra images like "-edited" versions')
@click.option('--write-exif/--no-write-exif', default=True,
              help='Write GPS coordinates and dates to EXIF metadata')
@click.option('--transform-pixel-mp', is_flag=True, default=False,
              help='Convert Pixel Motion Photos (.MP/.MV) to .mp4')
@click.option('--guess-from-name/--no-guess-from-name', default=True,
              help='Extract dates from filenames')
@click.option('--update-creation-time', is_flag=True, default=False,
              help='Update creation time to match modified time (Windows only)')
@click.option('--limit-filesize', is_flag=True, default=False,
              help='Skip files larger than 64MB (for low-RAM systems)')
@click.option('--fix-extensions', type=click.Choice(['none', 'standard', 'conservative', 'solo']),
              default='standard', help='Extension fixing mode')
@click.option('--dry-run', is_flag=True, default=False,
              help='Simulate processing without making changes')
@click.option('--max-threads', type=click.IntRange(1, 16), default=4,
              help='Maximum number of processing threads')
@click.pass_context
def process(ctx, input_path, output_path, albums, divide_to_dates, divide_partner_shared,
           skip_extras, write_exif, transform_pixel_mp, guess_from_name, 
           update_creation_time, limit_filesize, fix_extensions, dry_run, max_threads):
    """Process Google Photos Takeout export"""
    
    if not output_path:
        output_path = str(Path(input_path).parent / "organized_photos")
        click.echo(f"No output path specified, using: {output_path}")
    
    # Create configuration
    config = ProcessingConfig(
        input_path=input_path,
        output_path=output_path,
        album_mode=AlbumMode(albums),
        date_division=divide_to_dates,
        divide_partner_shared=divide_partner_shared,
        skip_extras=skip_extras,
        write_exif=write_exif,
        transform_pixel_mp=transform_pixel_mp,
        guess_from_name=guess_from_name,
        update_creation_time=update_creation_time,
        limit_filesize=limit_filesize,
        extension_fix_mode=ExtensionFixMode(fix_extensions),
        verbose=ctx.obj['verbose'],
        fix_mode=False,
        dry_run=dry_run,
        max_threads=max_threads
    )
    
    # Show configuration summary
    if dry_run:
        click.echo(click.style("DRY RUN MODE - No files will be modified", fg='yellow'))
    
    click.echo(f"Input:  {input_path}")
    click.echo(f"Output: {output_path}")
    click.echo(f"Album mode: {albums}")
    if divide_to_dates > 0:
        division_names = ["single folder", "year", "year/month", "year/month/day"]
        click.echo(f"Date organization: {division_names[divide_to_dates]}")
    if divide_partner_shared:
        click.echo("Partner shared media will be separated")
    
    # Initialize and run
    progress = ProgressReporter(ctx.obj['verbose'])
    gpth = GooglePhotosTakeoutHelper(config)
    gpth.set_progress_callback(lambda msg, current=None, total=None: progress.update(progress.current_step + 1, str(msg)))
    
    try:
        result = gpth.process_takeout()
        progress.finish()
        
        if result.success:
            mode_text = "DRY RUN - " if dry_run else ""
            click.echo(click.style(f"✓ {mode_text}Processing completed successfully!", fg='green'))
            click.echo(f"Total files: {result.total_files}")
            click.echo(f"Processed: {result.processed_files}")
            if result.duplicates_removed > 0:
                click.echo(f"Duplicates removed: {result.duplicates_removed}")
            if result.albums_found > 0:
                click.echo(f"Albums found: {result.albums_found}")
            click.echo(f"Processing time: {result.processing_time:.1f} seconds")
        else:
            click.echo(click.style("✗ Processing failed!", fg='red'))
            for error in result.errors:
                click.echo(f"Error: {error}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\nProcessing cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def analyze(ctx, input_path):
    """Analyze Google Photos Takeout structure"""
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for analysis
        verbose=ctx.obj['verbose']
    )
    
    gpth = GooglePhotosTakeoutHelper(config)
    
    try:
        structure = gpth.discover_takeout_structure()
        
        click.echo(f"📁 Takeout Structure Analysis")
        click.echo(f"Total files: {structure['total_files']}")
        click.echo(f"Media files: {structure['media_files']}")
        click.echo(f"JSON metadata files: {structure['json_files']}")
        click.echo(f"Has Photos folders: {'Yes' if structure['has_photos'] else 'No'}")
        click.echo(f"Has Albums: {'Yes' if structure['has_albums'] else 'No'}")
        click.echo(f"Estimated processing time: {structure['estimated_processing_time']:.1f} minutes")
        
    except Exception as e:
        click.echo(click.style(f"Error analyzing structure: {e}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def validate(ctx, input_path):
    """Validate Google Photos Takeout structure"""
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for validation
        verbose=ctx.obj['verbose']
    )
    
    gpth = GooglePhotosTakeoutHelper(config)
    
    try:
        # Use validation method that exists
        is_valid = gpth.validate_takeout_structure()
        result = {
            'is_valid': is_valid,
            'message': 'Valid Google Photos Takeout structure' if is_valid else 'Invalid structure',
            'details': []
        }
        
        if result['is_valid']:
            click.echo(click.style("✓ Valid Google Photos Takeout structure", fg='green'))
            click.echo(result['message'])
            for detail in result['details']:
                click.echo(f"  • {detail}")
        else:
            click.echo(click.style("✗ Invalid Takeout structure", fg='red'))
            click.echo(result['message'])
            for detail in result['details']:
                click.echo(f"  • {detail}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"Error validating structure: {e}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--albums', type=click.Choice(['shortcut', 'duplicate-copy', 'reverse-shortcut', 'json', 'nothing']),
              default='shortcut', help='Album handling mode for estimation')
@click.pass_context
def estimate(ctx, input_path, albums):
    """Estimate disk space requirements"""
    
    config = ProcessingConfig(
        input_path=input_path,
        output_path="",  # Not needed for estimation
        album_mode=AlbumMode(albums),
        verbose=ctx.obj['verbose']
    )
    
    gpth = GooglePhotosTakeoutHelper(config)
    
    try:
        estimates = gpth.estimate_space_requirements()
        
        click.echo(f"💾 Space Requirements Estimate")
        click.echo(f"Input size: {estimates['input_size_gb']:.2f} GB")
        click.echo(f"Estimated output size: {estimates['output_size_gb']:.2f} GB")
        click.echo(f"Available space: {estimates['available_space_gb']:.2f} GB")
        click.echo(f"Album mode: {albums}")
        click.echo(f"Space multiplier: {estimates['space_multiplier']:.1f}x")
        
        if estimates['warning']:
            click.echo(click.style(f"⚠️  {estimates['warning']}", fg='yellow'))
        else:
            click.echo(click.style("✓ Sufficient space available", fg='green'))
            
    except Exception as e:
        click.echo(click.style(f"Error estimating space: {e}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('folder_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--write-exif/--no-write-exif', default=True,
              help='Write GPS coordinates and dates to EXIF metadata')
@click.option('--update-creation-time', is_flag=True, default=False,
              help='Update creation time to match modified time (Windows only)')
@click.option('--dry-run', is_flag=True, default=False,
              help='Simulate processing without making changes')
@click.option('--max-threads', type=click.IntRange(1, 16), default=4,
              help='Maximum number of processing threads')
@click.pass_context
def fix(ctx, folder_path, write_exif, update_creation_time, dry_run, max_threads):
    """Fix dates in any folder (not just Takeout)"""
    
    if dry_run:
        click.echo(click.style("DRY RUN MODE - No files will be modified", fg='yellow'))
    
    config = ProcessingConfig(
        input_path=folder_path,
        output_path=folder_path,  # Fix in place
        write_exif=write_exif,
        update_creation_time=update_creation_time,
        verbose=ctx.obj['verbose'],
        fix_mode=True,
        dry_run=dry_run,
        max_threads=max_threads
    )
    
    click.echo(f"Fixing dates in: {folder_path}")
    
    progress = ProgressReporter(ctx.obj['verbose'])
    gpth = GooglePhotosTakeoutHelper(config)
    gpth.set_progress_callback(lambda msg, current=None, total=None: progress.update(progress.current_step + 1, str(msg)))
    
    try:
        result = gpth.fix_dates_in_folder()
        progress.finish()
        
        if result.success:
            mode_text = "DRY RUN - " if dry_run else ""
            click.echo(click.style(f"✓ {mode_text}Date fixing completed!", fg='green'))
            click.echo(f"Files processed: {result.processed_files}")
            click.echo(f"Processing time: {result.processing_time:.1f} seconds")
        else:
            click.echo(click.style("✗ Date fixing failed!", fg='red'))
            for error in result.errors:
                click.echo(f"Error: {error}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\nProcessing cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)

@cli.command('check-deps')
@click.pass_context
def check_deps(ctx):
    """Check for required dependencies"""
    
    config = ProcessingConfig(input_path=".", output_path=".")  # Dummy config
    gpth = GooglePhotosTakeoutHelper(config)
    
    try:
        # Check ExifTool
        exif_status = gpth.check_exiftool_status()
        
        click.echo("🔧 Dependency Check")
        click.echo(f"ExifTool: {'✓ Available' if exif_status['available'] else '✗ Not found'}")
        
        if exif_status['available']:
            click.echo(f"  Version: {exif_status['version']}")
            click.echo(f"  Path: {exif_status['path']}")
            click.echo(click.style("  All features available", fg='green'))
        else:
            click.echo(click.style("  Limited functionality - some features may not work", fg='yellow'))
            click.echo("  Install ExifTool for full functionality:")
            click.echo("    • Windows: choco install exiftool")
            click.echo("    • Mac: brew install exiftool")
            click.echo("    • Linux: sudo apt install libimage-exiftool-perl")
        
        # Check Python dependencies
        try:
            import PIL
            click.echo("PIL/Pillow: ✓ Available")
        except ImportError:
            click.echo(click.style("PIL/Pillow: ✗ Not found", fg='red'))
            click.echo("  Install with: pip install Pillow")
        
        try:
            import dateutil
            click.echo("python-dateutil: ✓ Available")
        except ImportError:
            click.echo(click.style("python-dateutil: ✗ Not found", fg='red'))
            click.echo("  Install with: pip install python-dateutil")
        
        try:
            import tqdm
            click.echo("tqdm: ✓ Available")
        except ImportError:
            click.echo(click.style("tqdm: ✗ Not found", fg='red'))
            click.echo("  Install with: pip install tqdm")
            
    except Exception as e:
        click.echo(click.style(f"Error checking dependencies: {e}", fg='red'))
        sys.exit(1)

@cli.command()
@click.pass_context
def info(ctx):
    """Show information about Google Photos Takeout Helper"""
    
    click.echo("📸 Google Photos Takeout Helper v4.1.0")
    click.echo("")
    click.echo("Transform your chaotic Google Photos Takeout into organized photo libraries")
    click.echo("with proper dates, albums, and metadata.")
    click.echo("")
    click.echo("Features:")
    click.echo("  • Organizes photos chronologically with correct dates")
    click.echo("  • Restores album structure with multiple handling options")
    click.echo("  • Fixes timestamps from JSON metadata and EXIF data")
    click.echo("  • Writes GPS coordinates and timestamps back to media files")
    click.echo("  • Removes duplicates automatically")
    click.echo("  • Handles special formats (HEIC, Motion Photos, etc.)")
    click.echo("  • Fixes mismatches of file name and mime type")
    click.echo("")
    click.echo("Commands:")
    click.echo("  process    - Process Google Photos Takeout export")
    click.echo("  analyze    - Analyze Takeout structure")
    click.echo("  validate   - Validate Takeout structure")
    click.echo("  estimate   - Estimate space requirements")
    click.echo("  fix        - Fix dates in any folder")
    click.echo("  check-deps - Check dependencies")
    click.echo("  info       - Show this information")
    click.echo("")
    click.echo("For help on a specific command, use: gpth <command> --help")

def main():
    """Entry point for the CLI"""
    cli()

if __name__ == '__main__':
    main()