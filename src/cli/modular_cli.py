"""
Modular CLI interface for Google Photos Takeout Helper
Supports individual step execution and pipeline management
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..core.modular_pipeline import ModularPipeline
from ..core.pipeline_state import PipelineStatus, StepStatus
from ..core.gpth_core_api import GooglePhotosTakeoutHelper, ProcessingConfig, AlbumMode, ExtensionFixMode


class ModularCLI:
    """CLI interface for modular pipeline execution"""
    
    def __init__(self):
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('gpth_cli')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for modular CLI"""
        parser = argparse.ArgumentParser(
            prog='gpth',
            description='Google Photos Takeout Helper - Modular Pipeline',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  # Start new pipeline
  gpth run input_dir output_dir
  
  # Execute single step
  gpth step fix-extensions <run-id>
  gpth step discover-media <run-id>
  
  # Execute step ranges
  gpth steps 1-3 <run-id>
  gpth steps 4-8 <run-id>
  
  # Resume pipeline
  gpth resume <run-id>
  gpth resume <run-id> --from-step 4
  
  # Pipeline management
  gpth list
  gpth status <run-id>
  gpth reset <run-id>
  gpth export <run-id>
            '''
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Run full pipeline
        run_parser = subparsers.add_parser('run', help='Start new pipeline execution')
        run_parser.add_argument('input_dir', type=str, help='Input directory (Google Takeout folder)')
        run_parser.add_argument('output_dir', type=str, help='Output directory')
        run_parser.add_argument('--album-mode', choices=['shortcut', 'duplicate-copy', 'reverse-shortcut', 'json', 'nothing'], 
                               default='shortcut', help='Album handling mode')
        run_parser.add_argument('--extension-fix', choices=['none', 'standard', 'conservative', 'solo'], 
                               default='standard', help='Extension fixing mode')
        run_parser.add_argument('--skip-extras', action='store_true', default=True, help='Skip extra files')
        run_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
        run_parser.add_argument('--max-threads', type=int, default=4, help='Maximum worker threads')
        run_parser.add_argument('--verbose', action='store_true', help='Verbose output')
        run_parser.add_argument('--write-exif', action='store_true', default=True, help='Write EXIF data')
        run_parser.add_argument('--update-creation-time', action='store_true', help='Update file creation times')
        
        # Execute single step
        step_parser = subparsers.add_parser('step', help='Execute single step')
        step_parser.add_argument('step_name', choices=[
            'fix-extensions', 'discover-media', 'remove-duplicates', 'extract-dates',
            'write-exif', 'find-albums', 'move-files', 'update-timestamps'
        ], help='Step to execute')
        step_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        
        # Execute step ranges
        steps_parser = subparsers.add_parser('steps', help='Execute range of steps')
        steps_parser.add_argument('range', type=str, help='Step range (e.g., 1-3, 4-8)')
        steps_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        
        # Resume pipeline
        resume_parser = subparsers.add_parser('resume', help='Resume pipeline execution')
        resume_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        resume_parser.add_argument('--from-step', type=int, help='Resume from specific step')
        
        # List pipelines
        list_parser = subparsers.add_parser('list', help='List all pipeline runs')
        list_parser.add_argument('--status', choices=['pending', 'running', 'completed', 'failed'], 
                               help='Filter by status')
        
        # Check status
        status_parser = subparsers.add_parser('status', help='Check pipeline status')
        status_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        status_parser.add_argument('--verbose', '-v', action='store_true', help='Detailed status')
        
        # Reset pipeline
        reset_parser = subparsers.add_parser('reset', help='Reset pipeline to initial state')
        reset_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        reset_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
        
        # Export summary
        export_parser = subparsers.add_parser('export', help='Export pipeline summary')
        export_parser.add_argument('run_id', type=str, help='Pipeline run ID')
        export_parser.add_argument('--format', choices=['json', 'yaml', 'text'], default='json',
                                 help='Export format')
        export_parser.add_argument('--output', type=str, help='Output file path')
        
        return parser
    
    def _create_config(self, args) -> ProcessingConfig:
        """Create ProcessingConfig from CLI arguments"""
        return ProcessingConfig(
            input_path=args.input_dir,
            output_path=args.output_dir,
            album_mode=AlbumMode(args.album_mode),
            extension_fix_mode=ExtensionFixMode(args.extension_fix),
            skip_extras=args.skip_extras,
            dry_run=args.dry_run,
            max_threads=args.max_threads,
            verbose=args.verbose,
            write_exif=args.write_exif,
            update_creation_time=args.update_creation_time
        )
    
    def _create_pipeline_from_run(self, run_id: str) -> ModularPipeline:
        """Create pipeline instance from existing run"""
        # Use a temporary config - the real config will be loaded from state
        temp_config = ProcessingConfig(input_path="", output_path="")
        state_dir = Path.cwd() / "pipeline_states"
        return ModularPipeline(temp_config, state_dir, self.logger)
    
    def _validate_takeout_structure(self, input_path: str) -> bool:
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
    
    def run_command(self, args) -> int:
        """Execute run command"""
        try:
            # Validate paths
            input_path = Path(args.input_dir)
            output_path = Path(args.output_dir)
            
            if not input_path.exists():
                print(f"Error: Input directory does not exist: {input_path}")
                return 1
            
            # Validate takeout structure
            if not self._validate_takeout_structure(str(input_path)):
                print(f"Warning: Input directory may not be a valid Google Takeout structure")
            
            # Create config
            config = self._create_config(args)
            
            # Create pipeline
            state_dir = Path.cwd() / "pipeline_states"
            pipeline = ModularPipeline(config, state_dir, self.logger)
            
            # Start pipeline
            run_id = pipeline.start_pipeline(input_path, output_path)
            
            print(f"Pipeline started with ID: {run_id}")
            print(f"Input: {input_path}")
            print(f"Output: {output_path}")
            
            # Execute all steps
            try:
                for step_num in range(1, 9):
                    if pipeline._cancel_requested:
                        break
                    
                    print(f"Executing step {step_num}/8...")
                    result = pipeline.execute_step(run_id, step_num)
                    
                    if result.success:
                        print(f"  ✓ Step {step_num} completed")
                        if hasattr(result, 'duration') and result.duration:
                            print(f"    Duration: {result.duration:.2f}s")
                    else:
                        print(f"  ✗ Step {step_num} failed: {result.error}")
                        # Continue with next step unless it's a critical failure
                        if step_num in [2, 4]:  # Critical steps
                            break
                
                # Get final result
                pipeline_run = pipeline.state_manager.get_pipeline_run(run_id)
                if pipeline_run and pipeline_run.status == PipelineStatus.COMPLETED:
                    print(f"Pipeline completed successfully!")
                else:
                    print(f"Pipeline completed with some failures")
                    return 1
                    
            except Exception as e:
                print(f"Pipeline execution failed: {e}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def step_command(self, args) -> int:
        """Execute step command"""
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
            
            step_number = step_mapping[args.step_name]
            
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Execute step
            result = pipeline.execute_step(args.run_id, step_number)
            
            if result.success:
                print(f"Step {step_number} ({args.step_name}) completed successfully")
                if hasattr(result, 'duration') and result.duration:
                    print(f"Execution time: {result.duration:.2f}s")
            else:
                print(f"Step {step_number} ({args.step_name}) failed: {result.error}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def steps_command(self, args) -> int:
        """Execute steps command"""
        try:
            # Parse range
            if '-' not in args.range:
                print("Error: Invalid range format. Use format like '1-3' or '4-8'")
                return 1
            
            start_str, end_str = args.range.split('-', 1)
            try:
                start_step = int(start_str)
                end_step = int(end_str)
            except ValueError:
                print("Error: Range must contain valid numbers")
                return 1
            
            if start_step < 1 or end_step > 8 or start_step > end_step:
                print("Error: Invalid step range. Steps must be 1-8 and start <= end")
                return 1
            
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Execute step range
            success_count = 0
            for step_num in range(start_step, end_step + 1):
                print(f"Executing step {step_num}...")
                result = pipeline.execute_step(args.run_id, step_num)
                
                if result.success:
                    print(f"  ✓ Step {step_num} completed")
                    success_count += 1
                else:
                    print(f"  ✗ Step {step_num} failed: {result.error}")
                    if step_num in [2, 4]:  # Critical steps
                        break
            
            if success_count == (end_step - start_step + 1):
                print(f"All steps {start_step}-{end_step} completed successfully")
            else:
                print(f"Steps {start_step}-{end_step} completed with some failures")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def resume_command(self, args) -> int:
        """Execute resume command"""
        try:
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Resume pipeline
            result = pipeline.resume_pipeline(args.run_id, args.from_step)
            
            if result['success']:
                print(f"Pipeline resumed and completed successfully")
                if 'total_time' in result:
                    print(f"Total time: {result['total_time']:.2f}s")
            else:
                print(f"Pipeline resume failed: {result.get('error', 'Unknown error')}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def list_command(self, args) -> int:
        """Execute list command"""
        try:
            # Create pipeline to access state manager
            pipeline = self._create_pipeline_from_run("dummy")
            
            # Get all pipeline runs
            runs = pipeline.state_manager.list_runs()
            
            if args.status:
                # Filter by status
                status_filter = args.status
                runs = [run for run in runs if run.get('status') == status_filter]
            
            if not runs:
                print("No pipeline runs found")
                return 0
            
            # Display runs
            print(f"{'Run ID':<20} {'Status':<12} {'Created':<20} {'Input Path'}")
            print("-" * 80)
            
            for run in runs:
                created = run['started_at'][:19].replace('T', ' ')  # Format datetime
                input_path = run['input_path'][:40] + "..." if len(run['input_path']) > 43 else run['input_path']
                print(f"{run['id']:<20} {run['status']:<12} {created:<20} {input_path}")
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def status_command(self, args) -> int:
        """Execute status command"""
        try:
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Get pipeline status
            pipeline_run = pipeline.state_manager.get_pipeline_run(args.run_id)
            if not pipeline_run:
                print(f"Pipeline run not found: {args.run_id}")
                return 1
            
            # Display basic status
            print(f"Pipeline ID: {pipeline_run.id}")
            print(f"Status: {pipeline_run.status}")
            print(f"Created: {pipeline_run.started_at[:19].replace('T', ' ')}")
            if pipeline_run.completed_at:
                print(f"Completed: {pipeline_run.completed_at[:19].replace('T', ' ')}")
            print(f"Input Path: {pipeline_run.input_path}")
            print(f"Output Path: {pipeline_run.output_path}")
            
            if args.verbose:
                print("\nStep Details:")
                print(f"{'Step':<3} {'Name':<20} {'Status':<12} {'Duration':<10} {'Files'}")
                print("-" * 65)
                
                step_names = [
                    "Fix Extensions", "Discover Media", "Remove Duplicates", "Extract Dates",
                    "Write EXIF", "Find Albums", "Move Files", "Update Timestamps"
                ]
                
                for step in pipeline_run.steps:
                    step_num = step['step_number']
                    name = step_names[step_num - 1]
                    status = step['status']
                    duration = f"{step.get('duration', 0):.1f}s" if step.get('duration') else "N/A"
                    files = step.get('files_processed', 0)
                    
                    print(f"{step_num:<3} {name:<20} {status:<12} {duration:<10} {files}")
                
                # Show error if failed
                if pipeline_run.status == PipelineStatus.FAILED.value and pipeline_run.error_message:
                    print(f"\nError: {pipeline_run.error_message}")
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def reset_command(self, args) -> int:
        """Execute reset command"""
        try:
            if not args.confirm:
                response = input(f"Are you sure you want to reset pipeline {args.run_id}? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    print("Reset cancelled")
                    return 0
            
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Reset pipeline
            success = pipeline.reset_pipeline(args.run_id)
            
            if success:
                print(f"Pipeline {args.run_id} reset successfully")
            else:
                print(f"Failed to reset pipeline {args.run_id}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def export_command(self, args) -> int:
        """Execute export command"""
        try:
            # Create pipeline
            pipeline = self._create_pipeline_from_run(args.run_id)
            
            # Export summary
            summary = pipeline.export_summary(args.run_id)
            
            if args.format == 'json':
                output = json.dumps(summary, indent=2, default=str)
            elif args.format == 'yaml':
                try:
                    import yaml
                    output = yaml.dump(summary, default_flow_style=False)
                except ImportError:
                    print("Error: yaml package required for YAML export")
                    return 1
            else:  # text format
                output = self._format_text_summary(summary)
            
            if args.output:
                # Write to file
                output_path = Path(args.output)
                output_path.write_text(output)
                print(f"Summary exported to {output_path}")
            else:
                # Print to stdout
                print(output)
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def _format_text_summary(self, summary: dict) -> str:
        """Format summary as human-readable text"""
        lines = []
        lines.append(f"Pipeline Summary: {summary['id']}")
        lines.append(f"Status: {summary['status']}")
        lines.append(f"Created: {summary['created_at']}")
        lines.append(f"Updated: {summary['updated_at']}")
        lines.append(f"Input: {summary['input_path']}")
        lines.append(f"Output: {summary['output_path']}")
        lines.append("")
        
        lines.append("Steps:")
        step_names = [
            "Fix Extensions", "Discover Media", "Remove Duplicates", "Extract Dates",
            "Write EXIF", "Find Albums", "Move Files", "Update Timestamps"
        ]
        
        for step in summary['steps']:
            step_num = step['step_number']
            name = step_names[step_num - 1]
            status = step['status']
            duration = step.get('duration', 0)
            files = step.get('files_processed', 0)
            
            lines.append(f"  {step_num}. {name}: {status}")
            if duration:
                lines.append(f"     Duration: {duration:.2f}s")
            if files:
                lines.append(f"     Files: {files}")
        
        if summary.get('error'):
            lines.append("")
            lines.append(f"Error: {summary['error']}")
        
        return '\n'.join(lines)
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """Main CLI entry point"""
        parser = self.create_parser()
        args = parser.parse_args(argv)
        
        if not args.command:
            parser.print_help()
            return 1
        
        # Route to appropriate command handler
        command_map = {
            'run': self.run_command,
            'step': self.step_command,
            'steps': self.steps_command,
            'resume': self.resume_command,
            'list': self.list_command,
            'status': self.status_command,
            'reset': self.reset_command,
            'export': self.export_command
        }
        
        handler = command_map.get(args.command)
        if not handler:
            print(f"Unknown command: {args.command}")
            return 1
        
        return handler(args)


def main():
    """CLI entry point"""
    cli = ModularCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()