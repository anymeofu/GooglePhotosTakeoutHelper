"""
Google Photos Takeout Helper - Modular Pipeline Controller
Step-by-step execution system with state persistence
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
import logging

from .pipeline_state import PipelineStateManager, PipelineStatus, StepStatus
from .processing_steps import (
    ProcessingStep, ProcessingContext, StepResult,
    FixExtensionsStep, DiscoverMediaStep, RemoveDuplicatesStep, ExtractDatesStep,
    WriteExifStep, FindAlbumsStep, MoveFilesStep, UpdateCreationTimeStep
)
from .gpth_core_api import ProcessingConfig
from .error_handling import EnhancedErrorHandler
from .process_monitor import ProcessMonitor


class ModularPipeline:
    """
    Modular pipeline controller that can execute steps individually or in sequence
    with full state persistence and resume capability
    """
    
    def __init__(self, config: ProcessingConfig, state_dir: Path, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.state_manager = PipelineStateManager(state_dir, logger)
        self.error_handler = EnhancedErrorHandler(logger)
        self.process_monitor = ProcessMonitor(state_dir, logger)
        
        # Initialize processing steps
        self.steps = {
            1: FixExtensionsStep(),
            2: DiscoverMediaStep(),
            3: RemoveDuplicatesStep(),
            4: ExtractDatesStep(),
            5: WriteExifStep(),
            6: FindAlbumsStep(),
            7: MoveFilesStep(),
            8: UpdateCreationTimeStep()
        }
        
        self._progress_callback: Optional[Callable[[int, str, float], None]] = None
        self._cancel_requested = False
        self.current_run_id: Optional[str] = None
        
    def set_progress_callback(self, callback: Callable[[int, str, float], None]) -> None:
        """Set progress callback for real-time updates"""
        self._progress_callback = callback
    
    def cancel_processing(self) -> None:
        """Request cancellation of processing"""
        self._cancel_requested = True
        if self.current_run_id:
            self.state_manager.update_pipeline_status(
                self.current_run_id, PipelineStatus.CANCELLED
            )
        self.logger.info("Processing cancellation requested")
    
    def _update_progress(self, step_number: int, message: str, progress: float = 0.0) -> None:
        """Update progress if callback is set"""
        if self._progress_callback:
            self._progress_callback(step_number, message, progress)
        if self.config.verbose:
            self.logger.info(f"Step {step_number}/8: {message} ({progress:.1f}%)")
    
    def start_pipeline(self, input_path: Path, output_path: Path) -> str:
        """Start a new pipeline run and return the run ID"""
        config_dict = {
            "album_mode": self.config.album_mode.value if hasattr(self.config.album_mode, 'value') else str(self.config.album_mode),
            "extension_fix_mode": self.config.extension_fix_mode.value if hasattr(self.config.extension_fix_mode, 'value') else str(self.config.extension_fix_mode),
            "write_exif": self.config.write_exif,
            "update_creation_time": self.config.update_creation_time,
            "dry_run": self.config.dry_run,
            "verbose": self.config.verbose,
            "max_threads": getattr(self.config, 'max_threads', 4),
            "skip_extras": getattr(self.config, 'skip_extras', True),
            "guess_from_name": getattr(self.config, 'guess_from_name', True)
        }
        
        self.current_run_id = self.state_manager.create_pipeline_run(
            input_path, output_path, config_dict
        )
        
        # Register with process monitor and start monitoring
        self.process_monitor.register_process(self.current_run_id)
        self.process_monitor.start_monitoring()
        
        self.logger.info(f"Started pipeline run {self.current_run_id}")
        return self.current_run_id
    
    def execute_step(self, run_id: str, step_number: int) -> StepResult:
        """Execute a specific step in the pipeline"""
        if step_number not in self.steps:
            raise ValueError(f"Invalid step number: {step_number}")
        
        # Get pipeline run
        pipeline_run = self.state_manager.get_pipeline_run(run_id)
        if not pipeline_run:
            raise ValueError(f"Pipeline run not found: {run_id}")
        
        step = self.steps[step_number]
        step_name = step.name
        
        self.logger.info(f"Executing Step {step_number}: {step_name}")
        self._update_progress(step_number, f"Starting {step_name}", 0.0)
        
        # Mark step as started
        self.state_manager.start_step(run_id, step_number)
        
        # Create processing context from pipeline state
        context = self._create_context_from_state(pipeline_run, step_number)
        
        start_time = time.time()
        try:
            # Check if step should be skipped
            if step.should_skip(context):
                skip_reason = f"Step skipped due to configuration: {self.config.extension_fix_mode.value if step_number == 1 else 'conditions not met'}"
                self.logger.info(f"Skipping {step_name}: {skip_reason}")
                self.state_manager.skip_step(run_id, step_number, skip_reason)
                
                result = StepResult(
                    name=step_name,
                    success=True,
                    duration=0.0,
                    message=skip_reason,
                    data={'skipped': True}
                )
                self._update_progress(step_number, f"Skipped {step_name}", 100.0)
                return result
            
            # Execute the step
            result = step.execute(context)
            duration = time.time() - start_time
            result.duration = duration
            
            # Save step results to state
            self.state_manager.complete_step(
                run_id, step_number, result.success,
                input_count=len(context.media_files) if context.media_files else 0,
                output_count=result.data.get('files_processed', 0),
                error_count=1 if result.error else 0,
                state_data=result.data,
                error_message=result.error,
                duration=duration
            )
            
            # Save file operations if any
            if result.data and 'file_operations' in result.data:
                for op in result.data['file_operations']:
                    self.state_manager.save_file_operation(
                        run_id, step_number, Path(op['file']), op['operation'], op.get('details', {})
                    )
            
            if result.success:
                self.logger.info(f"✅ {step_name} completed in {duration:.2f}s")
                if result.message:
                    self.logger.info(f"   {result.message}")
                self._update_progress(step_number, f"Completed {step_name}", 100.0)
            else:
                self.logger.error(f"❌ {step_name} failed: {result.message}")
                if result.error:
                    self.logger.error(f"   Error: {result.error}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_message = str(e)
            
            self.logger.error(f"❌ {step_name} failed with exception: {e}", exc_info=True)
            
            # Save error to state
            self.state_manager.complete_step(
                run_id, step_number, False,
                error_count=1,
                error_message=error_message,
                duration=duration
            )
            
            result = StepResult(
                name=step_name,
                success=False,
                duration=duration,
                message=f"Unexpected error in {step_name}",
                error=error_message
            )
            return result
    
    def execute_pipeline(self, input_path: Path, output_path: Path, 
                        start_step: int = 1, end_step: int = 8) -> Dict[str, Any]:
        """Execute a range of pipeline steps"""
        # Start new pipeline run
        run_id = self.start_pipeline(input_path, output_path)
        
        try:
            step_results = []
            
            for step_num in range(start_step, end_step + 1):
                # Check for cancellation
                if self._cancel_requested:
                    self.logger.info("Processing cancelled by user")
                    self.state_manager.update_pipeline_status(run_id, PipelineStatus.CANCELLED)
                    break
                
                result = self.execute_step(run_id, step_num)
                step_results.append(result)
                
                # Stop if critical step fails
                if not result.success and step_num in [2, 4]:  # Discover Media, Extract Dates
                    self.logger.error("Critical step failed, stopping pipeline")
                    self.state_manager.update_pipeline_status(
                        run_id, PipelineStatus.FAILED, f"Critical step {step_num} failed"
                    )
                    break
            
            # Update final pipeline status
            success = all(r.success or r.data.get('skipped', False) for r in step_results)
            if success and not self._cancel_requested:
                self.state_manager.update_pipeline_status(run_id, PipelineStatus.COMPLETED)
            elif not self._cancel_requested:
                self.state_manager.update_pipeline_status(run_id, PipelineStatus.FAILED)
            
            return self.get_pipeline_result(run_id)
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            self.state_manager.update_pipeline_status(
                run_id, PipelineStatus.FAILED, str(e)
            )
            return self.get_pipeline_result(run_id)
    
    def resume_pipeline(self, run_id: str, from_step: Optional[int] = None) -> Dict[str, Any]:
        """Resume pipeline execution from a specific step or last failed step"""
        pipeline_run = self.state_manager.get_pipeline_run(run_id)
        if not pipeline_run:
            raise ValueError(f"Pipeline run not found: {run_id}")

        # Determine starting step
        if from_step is None:
            # Find last incomplete step
            from_step = 9  # Default to "completed"
            for step in pipeline_run.steps:
                if step["status"] in [StepStatus.PENDING.value, StepStatus.FAILED.value]:
                    from_step = step["step_number"]
                    break

        # Ensure from_step is not None
        if from_step is None:
            from_step = 1

        if from_step > 8:
            self.logger.info("Pipeline already completed")
            return self.get_pipeline_result(run_id)

        self.logger.info(f"Resuming pipeline from step {from_step}")
        
        # Update pipeline status to running
        self.state_manager.update_pipeline_status(run_id, PipelineStatus.RUNNING)
        
        # Execute remaining steps
        self.current_run_id = run_id
        step_results = []
        
        for step_num in range(from_step, 9):
            if self._cancel_requested:
                break
                
            result = self.execute_step(run_id, step_num)
            step_results.append(result)
            
            if not result.success and step_num in [2, 4]:
                break
        
        # Update final status
        success = all(r.success or r.data.get('skipped', False) for r in step_results)
        if success and not self._cancel_requested:
            self.state_manager.update_pipeline_status(run_id, PipelineStatus.COMPLETED)
        elif not self._cancel_requested:
            self.state_manager.update_pipeline_status(run_id, PipelineStatus.FAILED)
        
        return self.get_pipeline_result(run_id)
    
    def get_pipeline_result(self, run_id: str) -> Dict[str, Any]:
        """Get comprehensive pipeline results"""
        return self.state_manager.get_pipeline_status(run_id)
    
    def list_pipeline_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent pipeline runs"""
        return self.state_manager.list_runs(limit)
    
    def reset_pipeline(self, run_id: str) -> bool:
        """Reset pipeline to initial state"""
        return self.state_manager.reset_pipeline(run_id)
    
    def export_summary(self, run_id: str) -> Dict[str, Any]:
        """Export human-readable summary"""
        return self.state_manager.export_summary(run_id)
    
    def _create_context_from_state(self, pipeline_run, step_number: int) -> ProcessingContext:
        """Create processing context from pipeline state"""
        # Reconstruct context from previous steps' state
        context = ProcessingContext(
            config=self.config,
            input_path=Path(pipeline_run.input_path),
            output_path=Path(pipeline_run.output_path),
            logger=self.logger,
            media_files=[],
            file_dates={},
            albums={},
            statistics={}
        )
        
        # Load state from previous steps
        for i in range(1, step_number):
            step_state = self.state_manager.get_step_state(pipeline_run.id, i)
            
            if i == 2 and 'media_files' in step_state:  # Discover Media
                context.media_files = [Path(f) for f in step_state['media_files']]
            
            if i == 4 and 'file_dates' in step_state:  # Extract Dates
                context.file_dates = {
                    Path(k): datetime.fromisoformat(v) if v else None
                    for k, v in step_state['file_dates'].items()
                }
            
            if i == 6 and 'albums' in step_state:  # Find Albums
                context.albums = {
                    k: [Path(f) for f in v] for k, v in step_state['albums'].items()
                }
            
            # Merge statistics
            if step_state:
                context.statistics.update(step_state)
        
        return context
    
    def pause_pipeline(self, run_id: str) -> bool:
        """Pause a pipeline run"""
        return self.process_monitor.pause_run(run_id)
    
    def resume_pipeline_execution(self, run_id: str) -> bool:
        """Resume a paused pipeline run"""
        return self.process_monitor.resume_run(run_id)
    
    def get_active_processes(self) -> Dict[str, Dict]:
        """Get information about active pipeline processes"""
        return self.process_monitor.get_active_runs()
    
    def cleanup_orphaned_runs(self) -> List[str]:
        """Clean up runs that were left in 'running' state due to crashes"""
        return self.process_monitor.recover_orphaned_runs()
    
    def shutdown_gracefully(self) -> None:
        """Gracefully shutdown the pipeline system"""
        self.process_monitor.shutdown()
        if self.current_run_id:
            self.process_monitor.unregister_process(self.current_run_id)