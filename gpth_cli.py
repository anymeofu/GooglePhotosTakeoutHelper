#!/usr/bin/env python3
"""
Google Photos Takeout Helper - Modular CLI Entry Point
Simple CLI interface for step-by-step pipeline execution
"""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.modular_pipeline import ModularPipeline
from src.core.gpth_core_api import ProcessingConfig, AlbumMode, ExtensionFixMode


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger('gpth_cli')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger


def validate_takeout_structure(input_path: str) -> bool:
    """Simple validation of Google Takeout structure"""
    path = Path(input_path)
    if not path.exists():
        return False
    
    # Look for typical Google Takeout indicators
    takeout_indicators = [
        "Google Photos", "archive_browser.html", "Takeout"
    ]
    
    for item in path.iterdir():
        if any(indicator.lower() in item.name.lower() for indicator in takeout_indicators):
            return True
    
    return False


def create_config(args) -> ProcessingConfig:
    """Create ProcessingConfig from CLI arguments"""
    return ProcessingConfig(
        input_path=args.input_dir,
        output_path=args.output_dir,
        album_mode=AlbumMode(getattr(args, 'album_mode', 'shortcut')),
        extension_fix_mode=ExtensionFixMode(getattr(args, 'extension_fix', 'standard')),
        skip_extras=getattr(args, 'skip_extras', True),
        dry_run=getattr(args, 'dry_run', False),
        max_threads=getattr(args, 'max_threads', 4),
        verbose=getattr(args, 'verbose', False),
        write_exif=getattr(args, 'write_exif', True),
        update_creation_time=getattr(args, 'update_creation_time', False)
    )


def cmd_run(args):
    """Execute run command"""
    logger = setup_logging(getattr(args, 'verbose', False))
    
    try:
        # Validate paths
        input_path = Path(args.input_dir)
        output_path = Path(args.output_dir)
        
        if not input_path.exists():
            print(f"Error: Input directory does not exist: {input_path}")
            return 1
        
        # Validate takeout structure
        if not validate_takeout_structure(str(input_path)):
            print(f"Warning: Input directory may not be a valid Google Takeout structure")
        
        # Create config and pipeline
        config = create_config(args)
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(config, state_dir, logger)
        
        # Start pipeline
        run_id = pipeline.start_pipeline(input_path, output_path)
        
        print(f"Pipeline started with ID: {run_id}")
        print(f"Input: {input_path}")
        print(f"Output: {output_path}")
        
        # Execute all steps
        for step_num in range(1, 9):
            if pipeline._cancel_requested:
                break
            
            print(f"Executing step {step_num}/8...")
            result = pipeline.execute_step(run_id, step_num)
            
            if result.success:
                print(f"  ✓ Step {step_num} completed")
            else:
                print(f"  ✗ Step {step_num} failed: {result.error}")
                if step_num in [2, 4]:  # Critical steps
                    break
        
        print("Pipeline execution completed!")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_step(args):
    """Execute single step command"""
    logger = setup_logging(False)
    
    try:
        step_mapping = {
            'fix-extensions': 1,
            'discover-media': 2,
            'remove-duplicates': 3,
            'extract-dates': 4,
            'write-exif': 5,
            'find-albums': 6,
            'move-files': 7,
            'update-timestamps': 8
        }
        
        step_number = step_mapping.get(args.step_name)
        if not step_number:
            print(f"Error: Unknown step: {args.step_name}")
            return 1
        
        # Create pipeline with minimal config
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        
        # Execute step
        result = pipeline.execute_step(args.run_id, step_number)
        
        if result.success:
            print(f"Step {step_number} ({args.step_name}) completed successfully")
        else:
            print(f"Step {step_number} ({args.step_name}) failed: {result.error}")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_status(args):
    """Show pipeline status"""
    logger = setup_logging(False)
    
    try:
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        
        pipeline_run = pipeline.state_manager.get_pipeline_run(args.run_id)
        if not pipeline_run:
            print(f"Pipeline run not found: {args.run_id}")
            return 1
        
        print(f"Pipeline ID: {pipeline_run.id}")
        print(f"Status: {pipeline_run.status}")
        print(f"Input: {pipeline_run.input_path}")
        print(f"Output: {pipeline_run.output_path}")
        print(f"Started: {pipeline_run.started_at}")
        if pipeline_run.completed_at:
            print(f"Completed: {pipeline_run.completed_at}")
        
        if getattr(args, 'verbose', False):
            print("\nSteps:")
            for step in pipeline_run.steps:
                status = step['status']
                name = step['display_name']
                print(f"  {step['step_number']}. {name}: {status}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_list(args):
    """List pipeline runs"""
    logger = setup_logging(False)
    
    try:
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        
        runs = pipeline.state_manager.list_runs()
        
        if not runs:
            print("No pipeline runs found")
            return 0
        
        print(f"{'Run ID':<20} {'Status':<12} {'Started':<20}")
        print("-" * 60)
        
        for run in runs:
            started = run['started_at'][:19].replace('T', ' ')
            print(f"{run['id']:<20} {run['status']:<12} {started:<20}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_resume(args):
    """Resume pipeline execution"""
    logger = setup_logging(False)
    try:
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        # If from_step specified, resume from that step
        if getattr(args, 'from_step', None):
            result = pipeline.execute_step(args.run_id, args.from_step)
            if result.success:
                print(f"Resumed execution from step {args.from_step}")
                # Continue with remaining steps
                for step_num in range(args.from_step + 1, 9):
                    result = pipeline.execute_step(args.run_id, step_num)
                    if not result.success:
                        print(f"Step {step_num} failed: {result.error}")
                        break
            else:
                print(f"Failed to resume from step {args.from_step}: {result.error}")
                return 1
        else:
            # Resume paused pipeline
            if pipeline.resume_pipeline_execution(args.run_id):
                print(f"Resumed paused pipeline {args.run_id}")
            else:
                print(f"Failed to resume pipeline {args.run_id}")
                return 1
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def cmd_pause(args):
    """Pause pipeline execution"""
    logger = setup_logging(False)
    try:
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        if pipeline.pause_pipeline(args.run_id):
            print(f"Paused pipeline {args.run_id}")
        else:
            print(f"Failed to pause pipeline {args.run_id} (may not be running)")
            return 1
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def cmd_cleanup(args):
    """Clean up orphaned runs"""
    logger = setup_logging(False)
    try:
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        pipeline = ModularPipeline(temp_config, state_dir, logger)
        orphaned_runs = pipeline.cleanup_orphaned_runs()
        if orphaned_runs:
            if not getattr(args, 'auto', False):
                response = input(f"Found {len(orphaned_runs)} orphaned runs. Clean up? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    print("Cleanup cancelled")
                    return 0
            print(f"Cleaned up {len(orphaned_runs)} orphaned runs:")
            for run_id in orphaned_runs:
                print(f"  - {run_id}")
        else:
            print("No orphaned runs found")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='gpth',
        description='Google Photos Takeout Helper - Modular Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Start new pipeline
  python gpth_cli.py run input_dir output_dir
  
  # Execute single step
  python gpth_cli.py step fix-extensions <run-id>
  
  # Check status
  python gpth_cli.py status <run-id>
  
  # List all runs
  python gpth_cli.py list
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run full pipeline
    run_parser = subparsers.add_parser('run', help='Start new pipeline execution')
    run_parser.add_argument('input_dir', type=str, help='Input directory (Google Takeout folder)')
    run_parser.add_argument('output_dir', type=str, help='Output directory')
    run_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    run_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_parser.set_defaults(func=cmd_run)
    
    # Execute single step
    step_parser = subparsers.add_parser('step', help='Execute single step')
    step_parser.add_argument('step_name', choices=[
        'fix-extensions', 'discover-media', 'remove-duplicates', 'extract-dates',
        'write-exif', 'find-albums', 'move-files', 'update-timestamps'
    ], help='Step to execute')
    step_parser.add_argument('run_id', type=str, help='Pipeline run ID')
    step_parser.set_defaults(func=cmd_step)
    
    # Check status
    status_parser = subparsers.add_parser('status', help='Check pipeline status')
    status_parser.add_argument('run_id', type=str, help='Pipeline run ID')
    status_parser.add_argument('--verbose', '-v', action='store_true', help='Detailed status')
    status_parser.set_defaults(func=cmd_status)
    
    # List pipelines
    list_parser = subparsers.add_parser('list', help='List all pipeline runs')
    list_parser.set_defaults(func=cmd_list)
    
    # Resume pipeline
    resume_parser = subparsers.add_parser('resume', help='Resume pipeline execution')
    resume_parser.add_argument('run_id', type=str, help='Pipeline run ID')
    resume_parser.add_argument('--from-step', type=int, help='Resume from specific step')
    resume_parser.set_defaults(func=cmd_resume)
    
    # Pause pipeline
    pause_parser = subparsers.add_parser('pause', help='Pause running pipeline')
    pause_parser.add_argument('run_id', type=str, help='Pipeline run ID')
    pause_parser.set_defaults(func=cmd_pause)
    
    # Cleanup orphaned runs
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up orphaned/crashed runs')
    cleanup_parser.add_argument('--auto', action='store_true', help='Automatically clean up without confirmation')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())