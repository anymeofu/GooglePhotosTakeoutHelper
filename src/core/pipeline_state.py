"""
Google Photos Takeout Helper - Pipeline State Management
JSON-based state persistence for modular pipeline execution
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"  
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """Individual step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed" 
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class PipelineRun:
    """Represents a pipeline execution run"""
    id: str
    input_path: str
    output_path: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = PipelineStatus.PENDING.value
    config: Dict[str, Any] = field(default_factory=dict)
    total_files: int = 0
    error_message: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)

class PipelineStateManager:
    """Manages pipeline state persistence using human-readable JSON files"""
    
    def __init__(self, state_dir: Path, logger: logging.Logger):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        
        # Create subdirectories for organization
        (self.state_dir / "runs").mkdir(exist_ok=True)
        (self.state_dir / "steps").mkdir(exist_ok=True)
        (self.state_dir / "files").mkdir(exist_ok=True)
        
        self.logger.info(f"Pipeline state manager initialized: {self.state_dir}")

    def _generate_run_id(self) -> str:
        """Generate a unique run ID based on timestamp"""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    def create_pipeline_run(self, input_path: Path, output_path: Path, config: Dict[str, Any]) -> str:
        """Create a new pipeline run and return its ID"""
        run_id = self._generate_run_id()
        
        # Initialize 8 steps
        steps = []
        step_names = [
            "fix_extensions", "discover_media", "remove_duplicates", "extract_dates",
            "write_exif", "find_albums", "move_files", "update_timestamps"
        ]
        
        for i, step_name in enumerate(step_names, 1):
            steps.append({
                "step_number": i,
                "step_name": step_name,
                "display_name": step_name.replace("_", " ").title(),
                "status": StepStatus.PENDING.value,
                "started_at": None,
                "completed_at": None,
                "duration": 0.0,
                "input_files_count": 0,
                "output_files_count": 0,
                "errors_count": 0,
                "error_message": None,
                "state_data": {},
                "file_operations": []
            })

        pipeline_run = PipelineRun(
            id=run_id,
            input_path=str(input_path),
            output_path=str(output_path),
            started_at=datetime.now().isoformat(),
            status=PipelineStatus.RUNNING.value,
            config=config,
            steps=steps
        )
        
        # Save to JSON file
        run_file = self.state_dir / "runs" / f"{run_id}.json"
        with open(run_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(pipeline_run), f, indent=2, ensure_ascii=False)
        
        # Create index file for easy discovery
        self._update_runs_index(run_id, pipeline_run)
        
        self.logger.info(f"Created pipeline run {run_id}: {input_path} -> {output_path}")
        return run_id

    def _update_runs_index(self, run_id: str, pipeline_run: PipelineRun) -> None:
        """Update the runs index file for quick lookup"""
        index_file = self.state_dir / "runs_index.json"
        
        # Load existing index
        index = {}
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            except Exception:
                index = {}
        
        # Add/update this run
        index[run_id] = {
            "input_path": pipeline_run.input_path,
            "output_path": pipeline_run.output_path,
            "started_at": pipeline_run.started_at,
            "status": pipeline_run.status,
            "file": f"runs/{run_id}.json"
        }
        
        # Save updated index
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get pipeline run by ID"""
        run_file = self.state_dir / "runs" / f"{run_id}.json"
        if not run_file.exists():
            return None
        
        try:
            with open(run_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return PipelineRun(**data)
        except Exception as e:
            self.logger.error(f"Failed to load pipeline run {run_id}: {e}")
            return None

    def save_pipeline_run(self, pipeline_run: PipelineRun) -> None:
        """Save pipeline run to disk"""
        run_file = self.state_dir / "runs" / f"{pipeline_run.id}.json"
        with open(run_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(pipeline_run), f, indent=2, ensure_ascii=False)
        
        # Update index
        self._update_runs_index(pipeline_run.id, pipeline_run)

    def update_pipeline_status(self, run_id: str, status: PipelineStatus, error_message: Optional[str] = None) -> None:
        """Update pipeline run status"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        pipeline_run.status = status.value
        if status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
            pipeline_run.completed_at = datetime.now().isoformat()
        if error_message:
            pipeline_run.error_message = error_message
        
        self.save_pipeline_run(pipeline_run)

    def start_step(self, run_id: str, step_number: int) -> None:
        """Mark a step as started"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        step = pipeline_run.steps[step_number - 1]
        step["status"] = StepStatus.RUNNING.value
        step["started_at"] = datetime.now().isoformat()
        
        self.save_pipeline_run(pipeline_run)

    def complete_step(self, run_id: str, step_number: int, success: bool, 
                     input_count: int = 0, output_count: int = 0, 
                     error_count: int = 0, state_data: Optional[Dict] = None,
                     error_message: Optional[str] = None, duration: float = 0.0) -> None:
        """Mark a step as completed with results"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        step = pipeline_run.steps[step_number - 1]
        step["status"] = StepStatus.COMPLETED.value if success else StepStatus.FAILED.value
        step["completed_at"] = datetime.now().isoformat()
        step["duration"] = duration
        step["input_files_count"] = input_count
        step["output_files_count"] = output_count
        step["errors_count"] = error_count
        if state_data:
            step["state_data"] = state_data
        if error_message:
            step["error_message"] = error_message
        
        self.save_pipeline_run(pipeline_run)

    def skip_step(self, run_id: str, step_number: int, reason: str = "") -> None:
        """Mark a step as skipped"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        step = pipeline_run.steps[step_number - 1]
        step["status"] = StepStatus.SKIPPED.value
        step["completed_at"] = datetime.now().isoformat()
        if reason:
            step["state_data"]["skip_reason"] = reason
        
        self.save_pipeline_run(pipeline_run)

    def save_file_operation(self, run_id: str, step_number: int, file_path: Path, 
                          operation: str, details: Dict[str, Any]) -> None:
        """Save file operation details"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        step = pipeline_run.steps[step_number - 1]
        step["file_operations"].append({
            "file_path": str(file_path),
            "operation": operation,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        self.save_pipeline_run(pipeline_run)

    def get_step_state(self, run_id: str, step_number: int) -> Dict[str, Any]:
        """Get state data for a specific step"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return {}
        
        return pipeline_run.steps[step_number - 1]["state_data"]

    def set_step_state(self, run_id: str, step_number: int, state_data: Dict[str, Any]) -> None:
        """Set state data for a specific step"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return
        
        pipeline_run.steps[step_number - 1]["state_data"] = state_data
        self.save_pipeline_run(pipeline_run)

    def find_latest_run(self, input_path: Path, output_path: Path) -> Optional[PipelineRun]:
        """Find the most recent pipeline run for given paths"""
        index_file = self.state_dir / "runs_index.json"
        if not index_file.exists():
            return None
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # Find matching runs
            matching_runs = []
            for run_id, run_info in index.items():
                if (run_info["input_path"] == str(input_path) and 
                    run_info["output_path"] == str(output_path)):
                    matching_runs.append((run_id, run_info["started_at"]))
            
            if not matching_runs:
                return None
            
            # Sort by started_at and get the latest
            latest_run_id = sorted(matching_runs, key=lambda x: x[1], reverse=True)[0][0]
            return self.get_pipeline_run(latest_run_id)
        
        except Exception as e:
            self.logger.error(f"Failed to find latest run: {e}")
            return None

    def list_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent pipeline runs"""
        index_file = self.state_dir / "runs_index.json"
        if not index_file.exists():
            return []
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # Sort by started_at and return recent runs
            runs = []
            for run_id, run_info in index.items():
                runs.append({"id": run_id, **run_info})
            
            return sorted(runs, key=lambda x: x["started_at"], reverse=True)[:limit]
        
        except Exception as e:
            self.logger.error(f"Failed to list runs: {e}")
            return []

    def get_pipeline_status(self, run_id: str) -> Dict[str, Any]:
        """Get comprehensive pipeline status"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return {"error": "Pipeline run not found"}
        
        # Calculate progress
        completed_steps = sum(1 for step in pipeline_run.steps 
                            if step["status"] in [StepStatus.COMPLETED.value, StepStatus.SKIPPED.value])
        total_steps = len(pipeline_run.steps)
        progress_percentage = (completed_steps / total_steps) * 100
        
        # Find current step
        current_step = None
        for step in pipeline_run.steps:
            if step["status"] == StepStatus.RUNNING.value:
                current_step = step
                break
        
        if not current_step and pipeline_run.status == PipelineStatus.RUNNING.value:
            # Find next pending step
            for step in pipeline_run.steps:
                if step["status"] == StepStatus.PENDING.value:
                    current_step = step
                    break
        
        return {
            "run_id": pipeline_run.id,
            "status": pipeline_run.status,
            "input_path": pipeline_run.input_path,
            "output_path": pipeline_run.output_path,
            "started_at": pipeline_run.started_at,
            "completed_at": pipeline_run.completed_at,
            "progress_percentage": progress_percentage,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": current_step,
            "steps": pipeline_run.steps,
            "total_files": pipeline_run.total_files,
            "error_message": pipeline_run.error_message
        }

    def reset_pipeline(self, run_id: str) -> bool:
        """Reset pipeline to initial state"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return False
        
        # Reset all steps
        for step in pipeline_run.steps:
            step["status"] = StepStatus.PENDING.value
            step["started_at"] = None
            step["completed_at"] = None
            step["duration"] = 0.0
            step["input_files_count"] = 0
            step["output_files_count"] = 0
            step["errors_count"] = 0
            step["error_message"] = None
            step["state_data"] = {}
            step["file_operations"] = []
        
        # Reset pipeline
        pipeline_run.status = PipelineStatus.PENDING.value
        pipeline_run.completed_at = None
        pipeline_run.error_message = None
        
        self.save_pipeline_run(pipeline_run)
        self.logger.info(f"Reset pipeline run {run_id}")
        return True

    def export_summary(self, run_id: str) -> Dict[str, Any]:
        """Export a human-readable summary of the pipeline run"""
        pipeline_run = self.get_pipeline_run(run_id)
        if not pipeline_run:
            return {"error": "Pipeline run not found"}
        
        summary = {
            "pipeline_summary": {
                "run_id": pipeline_run.id,
                "input_path": pipeline_run.input_path,
                "output_path": pipeline_run.output_path,
                "started_at": pipeline_run.started_at,
                "completed_at": pipeline_run.completed_at,
                "status": pipeline_run.status,
                "total_duration": self._calculate_total_duration(pipeline_run),
                "configuration": pipeline_run.config
            },
            "step_summary": [],
            "file_operations_summary": {
                "total_files_processed": 0,
                "operations_by_type": {}
            }
        }
        
        # Steps summary
        for step in pipeline_run.steps:
            step_summary = {
                "step": f"{step['step_number']}. {step['display_name']}",
                "status": step["status"],
                "duration": f"{step['duration']:.2f}s" if step['duration'] > 0 else "N/A",
                "files_processed": step["input_files_count"],
                "files_output": step["output_files_count"],
                "errors": step["errors_count"]
            }
            
            if step["error_message"]:
                step_summary["error"] = step["error_message"]
            
            summary["step_summary"].append(step_summary)
            
            # Count file operations
            for op in step["file_operations"]:
                op_type = op["operation"]
                summary["file_operations_summary"]["operations_by_type"][op_type] = \
                    summary["file_operations_summary"]["operations_by_type"].get(op_type, 0) + 1
                summary["file_operations_summary"]["total_files_processed"] += 1
        
        return summary

    def _calculate_total_duration(self, pipeline_run: PipelineRun) -> str:
        """Calculate total pipeline duration"""
        if pipeline_run.completed_at and pipeline_run.started_at:
            start = datetime.fromisoformat(pipeline_run.started_at)
            end = datetime.fromisoformat(pipeline_run.completed_at)
            duration = (end - start).total_seconds()
            return f"{duration:.2f}s"
        return "N/A"