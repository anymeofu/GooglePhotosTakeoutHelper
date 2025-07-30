#!/usr/bin/env python3
"""
Google Photos Takeout Helper - Dual-Mode CLI
Interactive mode for beginners, modular mode for power users
"""

import argparse
import sys
import logging
import signal
import time
import threading
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.modular_pipeline import ModularPipeline
from src.core.gpth_core_api import ProcessingConfig, AlbumMode, ExtensionFixMode


class InteractiveCLI:
    """Interactive mode for user-friendly experience"""
    
    def __init__(self):
        self.pipeline: Optional[ModularPipeline] = None
        self.state_dir = Path.cwd() / "pipeline_states"
        self.logger = self._setup_logging()
        self.current_run_id: Optional[str] = None
        self.pause_requested = False
        self._setup_signal_handlers()
    
    def _setup_logging(self, verbose: bool = False) -> logging.Logger:
        logger = logging.getLogger('gpth')
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful pause"""
        def signal_handler(signum, frame):
            print("\n⏸️  Pausing... (Press any key to continue or Ctrl+C again to stop)")
            self.pause_requested = True
        signal.signal(signal.SIGINT, signal_handler)
    
    def run_interactive(self):
        """Main interactive experience"""
        print("🎨 Google Photos Takeout Helper - Interactive Mode")
        print("=" * 50)
        
        # Get input from user
        input_dir = input("📁 Enter your Google Takeout folder path: ").strip()
        if not Path(input_dir).exists():
            print("❌ Directory not found!")
            return 1
            
        output_dir = input("📦 Enter output folder path: ").strip()
        
        # Ask about options
        print("\n⚙️  Processing Options:")
        dry_run = input("🔍 Dry run (no changes)? [y/N]: ").lower().startswith('y')
        skip_timestamps = input("⚡ Quick mode (skip timestamps)? [y/N]: ").lower().startswith('y')
        
        album_mode = 'duplicate-copy'
        choice = input("\n📁 Album organization:\n1) Make copies (recommended)\n2) Shortcuts only\n3) No albums\nChoice [1]: ")
        if choice == '2':
            album_mode = 'shortcut'
        elif choice == '3':
            album_mode = 'nothing'
        
        # Check for existing runs
        temp_config = ProcessingConfig(input_path=input_dir, output_path=output_dir)
        temp_pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        existing_runs = [r for r in temp_pipeline.list_pipeline_runs(limit=10) 
                        if r.get('input_path') == input_dir and r.get('status') in ['paused', 'failed', 'running']]
        
        run_id = None
        if existing_runs:
            print(f"\n📋 Found existing run: {existing_runs[0]['id'][:12]}...")
            choice = input("Continue existing run? [Y/n]: ")
            if choice.lower() not in ['n', 'no']:
                run_id = existing_runs[0]['id']
                return self._interactive_resume(run_id)
        
        # Start new processing
        config = ProcessingConfig(
            input_path=input_dir,
            output_path=output_dir,
            album_mode=AlbumMode(album_mode),
            update_creation_time=not skip_timestamps,
            dry_run=dry_run
        )
        
        self.pipeline = ModularPipeline(config, self.state_dir, self.logger)
        run_id = self.pipeline.start_pipeline(Path(input_dir), Path(output_dir))
        self.current_run_id = run_id
        
        return self._interactive_execute(run_id)
    
    def _interactive_resume(self, run_id: str):
        """Interactive resume with options"""
        temp_config = ProcessingConfig(input_path="", output_path="")
        self.pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        
        status = self.pipeline.state_manager.get_pipeline_status(run_id)
        completed_steps = [s for s in status.get('steps', []) if s.get('status') == 'completed']
        failed_step = next((s for s in status.get('steps', []) if s.get('status') == 'failed'), None)
        
        if failed_step:
            print(f"\n⚠️  Step {failed_step['number']} ({failed_step['name']}) failed")
            choice = input("Resume options:\n1) Retry failed step\n2) Skip failed step\n3) Start from beginning\nChoice [1]: ")
            if choice == '2':
                # Skip and continue
                next_step = failed_step['number'] + 1
            elif choice == '3':
                # Start over
                next_step = 1
            else:
                # Retry failed step
                next_step = failed_step['number']
        else:
            # Resume from next step
            next_step = len(completed_steps) + 1
            
        return self._interactive_execute_from_step(run_id, next_step)
    
    def _interactive_execute(self, run_id: str):
        """Execute with interactive controls"""
        return self._interactive_execute_from_step(run_id, 1)
    
    def _interactive_execute_from_step(self, run_id: str, start_step: int):
        """Execute from specific step with pause/continue controls"""
        step_names = [
            "🔧 Fixing extensions", "🔍 Discovering media", "🗑️ Removing duplicates", 
            "📅 Extracting dates", "📝 Writing metadata", "📁 Finding albums",
            "📦 Moving files", "⏰ Updating timestamps"
        ]
        
        print(f"\n🚀 Starting from step {start_step}/8...")
        
        for step_num in range(start_step, 9):
            if self.pause_requested:
                choice = input("\n⏸️ Paused. Continue? [Y/n/q(uit)]: ")
                if choice.lower() == 'q':
                    print("🛑 Stopped by user")
                    return 0
                elif choice.lower() == 'n':
                    print("📋 You can resume later with: gpth continue")
                    return 0
                self.pause_requested = False
            
            print(f"\n{step_names[step_num-1]} (Step {step_num}/8)...")
            
            # Add progress monitoring in separate thread
            progress_thread = threading.Thread(target=self._show_progress, args=(step_num,))
            progress_thread.daemon = True
            progress_thread.start()
            
            try:
                if not self.pipeline:
                    # Initialize pipeline if not already done
                    temp_config = ProcessingConfig(input_path="", output_path="")
                    self.pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
                
                result = self.pipeline.execute_step(run_id, step_num)
                if not result.success:
                    print(f"❌ Step {step_num} failed: {result.error}")
                    choice = input("Options:\n1) Retry\n2) Skip\n3) Stop\nChoice [1]: ")
                    if choice == '2':
                        continue
                    elif choice == '3':
                        return 1
                    else:
                        step_num -= 1  # Retry
                        continue
                
                # Show results
                files_count = result.data.get('files_processed') or result.data.get('files_checked') or result.data.get('extensions_fixed')
                if files_count:
                    print(f"   ✅ Processed {files_count} items")
                elif result.message:
                    print(f"   ✅ {result.message}")
                else:
                    print(f"   ✅ Step completed")
                    
            except KeyboardInterrupt:
                choice = input("\n⏸️ Step interrupted. Continue? [Y/n]: ")
                if choice.lower() == 'n':
                    return 0
                step_num -= 1  # Retry step
                continue
        
        print(f"\n🎉 All done! Your photos are organized in the output folder.")
        return 0
    
    def _show_progress(self, step_num: int):
        """Show progress indicator during step execution"""
        while True:
            for char in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏":
                print(f"\r   {char} Processing...", end="", flush=True)
                time.sleep(0.1)


class ModularCLI:
    """Modular mode for power users"""
    
    def __init__(self):
        self.state_dir = Path.cwd() / "pipeline_states"
        self.logger = self._setup_logging()
    
    def _setup_logging(self, verbose: bool = False) -> logging.Logger:
        logger = logging.getLogger('gpth')
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def execute_full_pipeline(self, input_dir: str, output_dir: str, **options):
        """Execute full pipeline with options"""
        from src.core.gpth_core_api import ExtensionFixMode
        
        # Handle negated boolean options
        write_exif = not options.get('no_write_exif', False)
        guess_from_name = not options.get('no_guess_from_name', False)
        update_creation_time = options.get('update_creation_time', False) or not options.get('quick', False)
        
        config = ProcessingConfig(
            input_path=input_dir,
            output_path=output_dir,
            album_mode=AlbumMode(options.get('album_mode', 'duplicate-copy')),
            extension_fix_mode=ExtensionFixMode(options.get('extension_fix_mode', 'standard')),
            dry_run=options.get('dry_run', False),
            verbose=options.get('verbose', False),
            write_exif=write_exif,
            update_creation_time=update_creation_time,
            max_threads=options.get('max_threads', 4),
            skip_extras=options.get('skip_extras', True),
            guess_from_name=guess_from_name
        )
        
        # Set additional options that may need to be passed to steps
        if 'date_division' in options:
            config.date_division = options['date_division']
        if 'partner_shared' in options:
            config.divide_partner_shared = options['partner_shared']
        if 'transform_pixel_mp' in options:
            config.transform_pixel_mp = options['transform_pixel_mp']
        if 'limit_filesize' in options:
            config.limit_filesize = options['limit_filesize']
        if 'fix_mode' in options:
            config.fix_mode = options['fix_mode']
        
        pipeline = ModularPipeline(config, self.state_dir, self.logger)
        run_id = pipeline.start_pipeline(Path(input_dir), Path(output_dir))
        
        print(f"🚀 Pipeline started (ID: {run_id[:12]})")
        
        for step_num in range(1, 9):
            result = pipeline.execute_step(run_id, step_num)
            if not result.success:
                print(f"❌ Step {step_num} failed: {result.error}")
                return 1
            print(f"✅ Step {step_num} completed")
        
        print("🎉 Pipeline completed successfully!")
        return 0
    
    def execute_single_step(self, step_name: str, run_id: str):
        """Execute a single step"""
        step_mapping = {
            'fix-extensions': 1, 'discover-media': 2, 'remove-duplicates': 3,
            'extract-dates': 4, 'write-exif': 5, 'find-albums': 6,
            'move-files': 7, 'update-timestamps': 8
        }
        
        if step_name not in step_mapping:
            print(f"❌ Unknown step: {step_name}")
            return 1
        
        step_num = step_mapping[step_name]
        temp_config = ProcessingConfig(input_path="", output_path="")
        pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        
        print(f"🔧 Executing step {step_num}: {step_name}")
        result = pipeline.execute_step(run_id, step_num)
        
        if result.success:
            print(f"✅ Step completed: {result.message or 'Success'}")
            return 0
        else:
            print(f"❌ Step failed: {result.error}")
            return 1
    
    def list_runs(self, detailed: bool = False):
        """List pipeline runs"""
        temp_config = ProcessingConfig(input_path="", output_path="")
        pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        runs = pipeline.list_pipeline_runs(limit=10)
        
        if not runs:
            print("📋 No runs found")
            return 0
        
        status_icons = {'completed': '✅', 'running': '🔄', 'paused': '⏸️', 'failed': '❌', 'pending': '⏳'}
        
        print("📋 Recent pipeline runs:")
        for run in runs:
            icon = status_icons.get(run.get('status', 'unknown'), '❓')
            run_id = run.get('id', 'unknown')[:12]
            status = run.get('status', 'unknown')
            started = run.get('started_at', '')[:16].replace('T', ' ')
            print(f"{icon} {run_id} | {status:<10} | {started}")
            
            if detailed:
                # Show step progress
                steps_info = run.get('steps', [])
                completed = len([s for s in steps_info if s.get('status') == 'completed'])
                print(f"    Progress: {completed}/8 steps completed")
        
        return 0
    
    def continue_run(self, run_id: Optional[str] = None, from_step: Optional[int] = None):
        """Continue a pipeline run"""
        temp_config = ProcessingConfig(input_path="", output_path="")
        pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        
        if not run_id:
            # Find most recent incomplete run
            runs = pipeline.list_pipeline_runs(limit=10)
            incomplete = [r for r in runs if r.get('status') in ['paused', 'failed', 'running']]
            if not incomplete:
                print("📋 No incomplete runs found")
                return 0
            run_id = incomplete[0]['id']
            if run_id:
                print(f"📋 Continuing most recent run: {run_id[:12]}")
        
        if not run_id:
            print("❌ No run ID available")
            return 1
        
        if from_step:
            print(f"🔧 Resuming from step {from_step}")
            start_step = from_step
        else:
            # Determine next step
            status = pipeline.state_manager.get_pipeline_status(run_id)
            completed = [s for s in status.get('steps', []) if s.get('status') == 'completed']
            start_step = len(completed) + 1
        
        for step_num in range(start_step, 9):
            result = pipeline.execute_step(run_id, step_num)
            if not result.success:
                print(f"❌ Step {step_num} failed: {result.error}")
                return 1
            print(f"✅ Step {step_num} completed")
        
        return 0
    
    def pause_run(self, run_id: str):
        """Pause a running pipeline"""
        temp_config = ProcessingConfig(input_path="", output_path="")
        pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        
        if pipeline.pause_pipeline(run_id):
            print(f"⏸️ Paused pipeline {run_id[:12]}")
            return 0
        else:
            print(f"❌ Could not pause {run_id[:12]} (not running?)")
            return 1
    
    def cleanup_runs(self):
        """Clean up orphaned runs"""
        temp_config = ProcessingConfig(input_path="", output_path="")
        pipeline = ModularPipeline(temp_config, self.state_dir, self.logger)
        orphaned = pipeline.cleanup_orphaned_runs()
        
        if orphaned:
            print(f"🧹 Cleaned up {len(orphaned)} orphaned runs")
            for run_id in orphaned:
                print(f"   - {run_id[:12]}")
        else:
            print("✨ No cleanup needed")
        return 0


def main():
    """Main CLI entry point with dual modes"""
    parser = argparse.ArgumentParser(
        prog='gpth',
        description='Google Photos Takeout Helper - Interactive & Modular',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Interactive Mode (Beginner-Friendly):
  gpth                                    # Start interactive mode
  
Modular Mode (Power Users):
  gpth run input_dir output_dir           # Full pipeline
  gpth step discover-media run_12345      # Single step
  gpth continue [run_id] [--from-step N]  # Resume execution
  gpth pause run_12345                    # Pause running pipeline
  gpth list [--detailed]                  # List all runs
  gpth clean                              # Cleanup orphaned runs
  
Quick Processing:
  gpth process input output --quick       # Fast processing, skip modular
        ''')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Full pipeline run
    run_parser = subparsers.add_parser('run', help='Run full pipeline')
    run_parser.add_argument('input_dir', help='Input directory')
    run_parser.add_argument('output_dir', help='Output directory')
    run_parser.add_argument('--dry-run', action='store_true', help='Test without changes')
    run_parser.add_argument('--album-mode', choices=['shortcut', 'duplicate-copy', 'reverse-shortcut', 'json', 'nothing'],
                           default='duplicate-copy', help='Album handling strategy')
    run_parser.add_argument('--date-division', type=int, choices=[0, 1, 2, 3], default=0,
                           help='Date organization: 0=none, 1=year, 2=year/month, 3=year/month/day')
    run_parser.add_argument('--partner-shared', action='store_true', help='Separate partner shared media')
    run_parser.add_argument('--skip-extras', action='store_true', help='Skip extra images (like "-edited" versions)')
    run_parser.add_argument('--no-write-exif', action='store_true', help='Skip writing GPS/dates to EXIF metadata')
    run_parser.add_argument('--transform-pixel-mp', action='store_true', help='Transform Pixel Motion Photos (.MP/.MV) to .mp4')
    run_parser.add_argument('--no-guess-from-name', action='store_true', help='Skip extracting dates from filenames')
    run_parser.add_argument('--update-creation-time', action='store_true', help='Update file creation time (Windows only)')
    run_parser.add_argument('--limit-filesize', action='store_true', help='Skip files larger than 64MB')
    run_parser.add_argument('--extension-fix-mode', choices=['none', 'standard', 'conservative', 'solo'],
                           default='standard', help='Extension fixing mode')
    run_parser.add_argument('--fix-mode', action='store_true', help='Fix dates in any folder (not just Takeout)')
    run_parser.add_argument('--max-threads', type=int, default=4, help='Maximum number of threads (1-16)')
    run_parser.add_argument('--quick', action='store_true', help='Skip timestamps (same as --no-update-creation-time)')
    run_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    # Single step execution
    step_parser = subparsers.add_parser('step', help='Execute single step')
    step_parser.add_argument('step_name', choices=[
        'fix-extensions', 'discover-media', 'remove-duplicates', 'extract-dates',
        'write-exif', 'find-albums', 'move-files', 'update-timestamps'
    ], help='Step to execute')
    step_parser.add_argument('run_id', help='Pipeline run ID')
    
    # Continue execution
    continue_parser = subparsers.add_parser('continue', help='Continue pipeline')
    continue_parser.add_argument('run_id', nargs='?', help='Run ID (optional)')
    continue_parser.add_argument('--from-step', type=int, help='Start from specific step')
    
    # Pause execution
    pause_parser = subparsers.add_parser('pause', help='Pause running pipeline')
    pause_parser.add_argument('run_id', help='Pipeline run ID')
    
    # List runs
    list_parser = subparsers.add_parser('list', help='List pipeline runs')
    list_parser.add_argument('--detailed', action='store_true', help='Show detailed info')
    
    # Cleanup
    clean_parser = subparsers.add_parser('clean', help='Clean up orphaned runs')
    
    # Process (non-modular quick processing)
    process_parser = subparsers.add_parser('process', help='Quick processing (non-modular)')
    process_parser.add_argument('input_dir', help='Input directory')
    process_parser.add_argument('output_dir', help='Output directory')
    process_parser.add_argument('--quick', action='store_true', help='Skip timestamps')
    process_parser.add_argument('--dry-run', action='store_true', help='Test without changes')
    
    args = parser.parse_args()
    
    # Interactive mode if no command
    if not args.command:
        cli = InteractiveCLI()
        return cli.run_interactive()
    
    # Modular commands
    modular_cli = ModularCLI()
    
    if args.command == 'run':
        options = {
            'dry_run': args.dry_run,
            'album_mode': args.album_mode,
            'date_division': getattr(args, 'date_division', 0),
            'partner_shared': getattr(args, 'partner_shared', False),
            'skip_extras': getattr(args, 'skip_extras', False),
            'no_write_exif': getattr(args, 'no_write_exif', False),
            'transform_pixel_mp': getattr(args, 'transform_pixel_mp', False),
            'no_guess_from_name': getattr(args, 'no_guess_from_name', False),
            'update_creation_time': getattr(args, 'update_creation_time', False),
            'limit_filesize': getattr(args, 'limit_filesize', False),
            'extension_fix_mode': getattr(args, 'extension_fix_mode', 'standard'),
            'fix_mode': getattr(args, 'fix_mode', False),
            'max_threads': getattr(args, 'max_threads', 4),
            'quick': args.quick,
            'verbose': args.verbose
        }
        return modular_cli.execute_full_pipeline(args.input_dir, args.output_dir, **options)
    
    elif args.command == 'step':
        return modular_cli.execute_single_step(args.step_name, args.run_id)
    
    elif args.command == 'continue':
        return modular_cli.continue_run(
            getattr(args, 'run_id', None),
            getattr(args, 'from_step', None)
        )
    
    elif args.command == 'pause':
        return modular_cli.pause_run(args.run_id)
    
    elif args.command == 'list':
        return modular_cli.list_runs(getattr(args, 'detailed', False))
    
    elif args.command == 'clean':
        return modular_cli.cleanup_runs()
    
    elif args.command == 'process':
        # Quick non-modular processing
        interactive_cli = InteractiveCLI()
        options = {'dry_run': args.dry_run, 'timestamps': not args.quick}
        # Quick non-modular processing using modular CLI
        return modular_cli.execute_full_pipeline(args.input_dir, args.output_dir, **options)
    
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())