"""
Google Photos Takeout Helper - Processing Pipeline
Main orchestrator that coordinates all processing steps
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

from .processing_steps import (
    ProcessingStep,
    ProcessingContext,
    StepResult,
    FixExtensionsStep,
    DiscoverMediaStep,
    RemoveDuplicatesStep,
    ExtractDatesStep,
    WriteExifStep,
    FindAlbumsStep,
    MoveFilesStep,
    UpdateCreationTimeStep
)
from .gpth_core_api import ProcessingConfig, ProcessingResult
from .error_handling import EnhancedErrorHandler, ErrorSeverity


@dataclass
class PipelineResult:
    """Results from pipeline execution"""
    success: bool
    total_duration: float
    step_results: List[StepResult] = field(default_factory=list)
    step_timings: Dict[str, float] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProcessingPipeline:
    """
    Main processing pipeline that orchestrates all 8 processing steps.
    
    This is the core orchestrator that coordinates:
    1. Fix Extensions - Correct mismatched file extensions
    2. Discover Media - Find and classify all media files
    3. Remove Duplicates - Eliminate duplicate files using content hashing
    4. Extract Dates - Determine timestamps from JSON, EXIF, and filenames
    5. Write EXIF - Embed metadata into files
    6. Find Albums - Detect and merge album relationships
    7. Move Files - Organize files using selected album strategy
    8. Update Creation Time - Sync file creation timestamps
    """
    
    def __init__(self, logger: logging.Logger, config: ProcessingConfig):
        self.logger = logger
        self.config = config
        self._progress_callback: Optional[Callable[[int, str, float], None]] = None
        self._cancel_requested = False
        
        # Initialize enhanced error handler
        self.error_handler = EnhancedErrorHandler(logger)
        
        # Initialize the 8 processing steps in fixed order
        self.steps = [
            FixExtensionsStep(),      # Step 1
            DiscoverMediaStep(),      # Step 2
            RemoveDuplicatesStep(),   # Step 3
            ExtractDatesStep(),       # Step 4
            WriteExifStep(),          # Step 5
            FindAlbumsStep(),         # Step 6
            MoveFilesStep(),          # Step 7
            UpdateCreationTimeStep(), # Step 8
        ]
        
        # Statistics tracking (enhanced with error stats)
        self.stats = {
            'files_processed': 0,
            'duplicates_removed': 0,
            'extensions_fixed': 0,
            'albums_found': 0,
            'coordinates_written': 0,
            'datetimes_written': 0,
            'creation_times_updated': 0,
            'extraction_method_stats': {},
            'errors_by_severity': {},
            'errors_by_category': {},
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
    
    def set_progress_callback(self, callback: Callable[[int, str, float], None]) -> None:
        """Set progress callback for real-time updates"""
        self._progress_callback = callback
    
    def cancel_processing(self) -> None:
        """Request cancellation of processing"""
        self._cancel_requested = True
        self.logger.info("Processing cancellation requested")
    
    def _update_progress(self, step_number: int, message: str, progress: float = 0.0) -> None:
        """Update progress if callback is set"""
        if self._progress_callback:
            self._progress_callback(step_number, message, progress)
        
        if self.config.verbose:
            self.logger.info(f"Step {step_number}/8: {message} ({progress:.1f}%)")
    
    def _is_critical_step(self, step: ProcessingStep) -> bool:
        """Determine if a step is critical (pipeline should stop if it fails)"""
        critical_steps = {
            'Discover Media',  # Must find files to process
            'Extract Dates',   # Date extraction is core functionality
        }
        return step.name in critical_steps
    
    def execute(self, input_path: Path, output_path: Path) -> PipelineResult:
        """
        Execute the complete processing pipeline
        
        Args:
            input_path: Source directory containing Google Photos takeout
            output_path: Target directory for organized output
            
        Returns:
            PipelineResult with success status, timing, and statistics
        """
        start_time = time.time()
        self.logger.info(f"Starting processing pipeline: {input_path} -> {output_path}")
        
        # Create processing context
        context = ProcessingContext(
            config=self.config,
            input_path=input_path,
            output_path=output_path,
            logger=self.logger,
            media_files=[],
            file_dates={},
            albums={},
            statistics=self.stats
        )
        
        step_results = []
        step_timings = {}
        
        try:
            # Execute each step sequentially
            for i, step in enumerate(self.steps):
                step_number = i + 1
                
                # Check for cancellation
                if self._cancel_requested:
                    self.logger.info("Processing cancelled by user")
                    break
                
                self.logger.info(f"\n--- Step {step_number}/8: {step.name} ---")
                self._update_progress(step_number, f"Starting {step.name}", 0.0)
                
                # Check if step should be skipped
                if step.should_skip(context):
                    self.logger.info(f"Skipping {step.name} (conditions not met)")
                    skip_result = StepResult(
                        name=step.name,
                        success=True,
                        duration=0.0,
                        message="Step skipped due to configuration",
                        data={'skipped': True}
                    )
                    step_results.append(skip_result)
                    continue
                
                # Execute the step
                step_start = time.time()
                try:
                    result = step.execute(context)
                    step_duration = time.time() - step_start
                    result.duration = step_duration
                    
                    step_results.append(result)
                    step_timings[step.name] = step_duration
                    
                    # Extract and merge statistics
                    self._extract_step_statistics(step, result)
                    
                    if result.success:
                        self.logger.info(f"✅ {step.name} completed in {step_duration:.2f}s")
                        if result.message:
                            self.logger.info(f"   {result.message}")
                        self._update_progress(step_number, f"Completed {step.name}", 100.0)
                    else:
                        self.logger.error(f"❌ {step.name} failed: {result.message}")
                        if result.error:
                            self.logger.error(f"   Error: {result.error}")
                        
                        # Stop if critical step fails
                        if self._is_critical_step(step):
                            self.logger.error("Critical step failed, stopping pipeline")
                            break
                    
                    # Special handling for solo modes
                    if step.name == "Fix Extensions" and not self.config.fix_mode:
                        # In solo extension fixing mode, stop here
                        if hasattr(self.config, 'extension_fix_solo') and self.config.extension_fix_solo:
                            self.logger.info("Extension fixing solo mode complete")
                            break
                
                except Exception as e:
                    step_duration = time.time() - step_start
                    error_result = StepResult(
                        name=step.name,
                        success=False,
                        duration=step_duration,
                        message=f"Unexpected error in {step.name}",
                        error=str(e)
                    )
                    step_results.append(error_result)
                    
                    self.logger.error(f"❌ {step.name} failed with error: {e}", exc_info=True)
                    
                    # Stop if critical step fails
                    if self._is_critical_step(step):
                        self.logger.error("Critical step failed, stopping pipeline")
                        break
            
            # Calculate final results
            total_duration = time.time() - start_time
            successful_steps = sum(1 for r in step_results if r.success)
            failed_steps = sum(1 for r in step_results if not r.success and not r.data.get('skipped'))
            skipped_steps = sum(1 for r in step_results if r.data.get('skipped'))
            
            success = failed_steps == 0 and not self._cancel_requested
            
            self.logger.info(f"\n=== Pipeline Complete ===")
            self.logger.info(f"Total duration: {total_duration:.2f}s")
            self.logger.info(f"Steps: {successful_steps} successful, {failed_steps} failed, {skipped_steps} skipped")
            self.logger.info(f"Files processed: {self.stats['files_processed']}")
            
            if self.stats['duplicates_removed'] > 0:
                self.logger.info(f"Duplicates removed: {self.stats['duplicates_removed']}")
            if self.stats['extensions_fixed'] > 0:
                self.logger.info(f"Extensions fixed: {self.stats['extensions_fixed']}")
            if self.stats['albums_found'] > 0:
                self.logger.info(f"Albums found: {self.stats['albums_found']}")
            
            return PipelineResult(
                success=success,
                total_duration=total_duration,
                step_results=step_results,
                step_timings=step_timings,
                statistics=self._build_final_statistics(),
                errors=[r.error for r in step_results if r.error],
                warnings=[]
            )
            
        except Exception as e:
            total_duration = time.time() - start_time
            self.logger.error(f"Pipeline failed with unexpected error: {e}", exc_info=True)
            
            return PipelineResult(
                success=False,
                total_duration=total_duration,
                step_results=step_results,
                step_timings=step_timings,
                statistics=self._build_final_statistics(),
                errors=[str(e)],
                warnings=[]
            )
    
    def _extract_step_statistics(self, step: ProcessingStep, result: StepResult) -> None:
        """Extract statistics from step results and merge into pipeline stats"""
        data = result.data or {}
        
        # Map step-specific statistics to pipeline statistics
        if step.name == "Discover Media":
            self.stats['files_processed'] = data.get('files_found', 0)
        
        elif step.name == "Remove Duplicates":
            self.stats['duplicates_removed'] = data.get('duplicates_removed', 0)
        
        elif step.name == "Fix Extensions":
            self.stats['extensions_fixed'] = data.get('extensions_fixed', 0)
        
        elif step.name == "Find Albums":
            self.stats['albums_found'] = data.get('albums_found', 0)
        
        elif step.name == "Write EXIF":
            self.stats['coordinates_written'] = data.get('coordinates_written', 0)
            self.stats['datetimes_written'] = data.get('datetimes_written', 0)
        
        elif step.name == "Update Creation Time":
            self.stats['creation_times_updated'] = data.get('creation_times_updated', 0)
        
        elif step.name == "Extract Dates":
            extraction_stats = data.get('extraction_method_stats', {})
            self.stats['extraction_method_stats'].update(extraction_stats)
    
    def _build_final_statistics(self) -> Dict[str, Any]:
        """Build final statistics dictionary for reporting"""
        return {
            'files_processed': self.stats['files_processed'],
            'duplicates_removed': self.stats['duplicates_removed'],
            'extensions_fixed': self.stats['extensions_fixed'],
            'albums_found': self.stats['albums_found'],
            'coordinates_written_to_exif': self.stats['coordinates_written'],
            'datetimes_written_to_exif': self.stats['datetimes_written'],
            'creation_times_updated': self.stats['creation_times_updated'],
            'extraction_method_statistics': self.stats['extraction_method_stats'],
            'dry_run_mode': self.config.dry_run
        }
    
    def convert_to_processing_result(self, pipeline_result: PipelineResult) -> ProcessingResult:
        """Convert PipelineResult to the legacy ProcessingResult format"""
        return ProcessingResult(
            success=pipeline_result.success,
            total_files=pipeline_result.statistics.get('files_processed', 0),
            processed_files=pipeline_result.statistics.get('files_processed', 0),
            duplicates_removed=pipeline_result.statistics.get('duplicates_removed', 0),
            albums_found=pipeline_result.statistics.get('albums_found', 0),
            errors=pipeline_result.errors,
            warnings=pipeline_result.warnings,
            processing_time=pipeline_result.total_duration
        )