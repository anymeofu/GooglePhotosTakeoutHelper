"""
Google Photos Takeout Helper - Process Monitoring and Recovery
Handles crash detection, pause/resume, and graceful shutdown
"""

import os
import signal
import time
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging
import json

from .pipeline_state import PipelineStateManager, PipelineStatus, StepStatus


class ProcessMonitor:
    """
    Monitors pipeline processes for crashes, handles pause/resume,
    and provides graceful shutdown capabilities
    """
    
    def __init__(self, state_dir: Path, logger: logging.Logger):
        self.state_dir = Path(state_dir)
        self.logger = logger
        self.state_manager = PipelineStateManager(state_dir, logger)
        
        # Process tracking
        self.active_processes: Dict[str, int] = {}  # run_id -> PID
        self.paused_runs: Set[str] = set()
        self.shutdown_requested = False
        
        # Monitoring thread
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_enabled = False
        
        # Process state files
        self.process_dir = self.state_dir / "processes"
        self.process_dir.mkdir(exist_ok=True)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Process monitor initialized")
    
    def _get_hostname(self) -> str:
        """Get hostname in a cross-platform way"""
        try:
            import socket
            return socket.gethostname()
        except Exception:
            return "unknown"
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown and pause/resume"""
        try:
            # Graceful shutdown on SIGTERM/SIGINT
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Pause/resume on SIGUSR1/SIGUSR2 (Unix only)
            if os.name == 'posix':
                try:
                    signal.signal(getattr(signal, 'SIGUSR1', None), self._pause_handler)
                    signal.signal(getattr(signal, 'SIGUSR2', None), self._resume_handler)
                except (OSError, ValueError, TypeError):
                    self.logger.debug("SIGUSR1/SIGUSR2 signals not available on this platform")
            
        except (OSError, ValueError) as e:
            self.logger.warning(f"Could not setup all signal handlers: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def _pause_handler(self, signum, frame):
        """Handle pause signal (SIGUSR1)"""
        self.logger.info("Received pause signal")
        self.pause_all_runs()
    
    def _resume_handler(self, signum, frame):
        """Handle resume signal (SIGUSR2)"""
        self.logger.info("Received resume signal")
        self.resume_all_runs()
    
    def register_process(self, run_id: str, pid: Optional[int] = None) -> None:
        """Register a process for monitoring"""
        if pid is None:
            pid = os.getpid()
        
        self.active_processes[run_id] = pid
        
        # Save process info to disk
        process_file = self.process_dir / f"{run_id}.json"
        process_info = {
            "run_id": run_id,
            "pid": pid,
            "started_at": datetime.now().isoformat(),
            "hostname": self._get_hostname(),
            "status": "running"
        }
        
        with open(process_file, 'w') as f:
            json.dump(process_info, f, indent=2)
        
        self.logger.info(f"Registered process for run {run_id}: PID {pid}")
    
    def unregister_process(self, run_id: str) -> None:
        """Unregister a process"""
        if run_id in self.active_processes:
            del self.active_processes[run_id]
        
        # Remove process file
        process_file = self.process_dir / f"{run_id}.json"
        if process_file.exists():
            process_file.unlink()
        
        # Remove from paused set
        self.paused_runs.discard(run_id)
        
        self.logger.info(f"Unregistered process for run {run_id}")
    
    def pause_run(self, run_id: str) -> bool:
        """Pause a specific pipeline run"""
        if run_id not in self.active_processes:
            self.logger.warning(f"Cannot pause run {run_id}: not found in active processes")
            return False
        
        pid = self.active_processes[run_id]
        
        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                self.logger.warning(f"Process {pid} for run {run_id} no longer exists")
                self._handle_crashed_process(run_id, pid)
                return False
            
            # Send SIGSTOP to pause process (Unix only)
            if hasattr(signal, 'SIGSTOP') and os.name == 'posix':
                os.kill(pid, signal.SIGSTOP)
                self.paused_runs.add(run_id)
                
                # Update state
                self.state_manager.update_pipeline_status(run_id, PipelineStatus.PAUSED)
                
                # Update process file
                self._update_process_status(run_id, "paused")
                
                self.logger.info(f"Paused run {run_id} (PID {pid})")
                return True
            else:
                self.logger.warning("Pause/resume not supported on this platform")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to pause run {run_id}: {e}")
            return False
    
    def resume_run(self, run_id: str) -> bool:
        """Resume a paused pipeline run"""
        if run_id not in self.paused_runs:
            self.logger.warning(f"Run {run_id} is not paused")
            return False
        
        if run_id not in self.active_processes:
            self.logger.warning(f"Cannot resume run {run_id}: not found in active processes")
            return False
        
        pid = self.active_processes[run_id]
        
        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                self.logger.warning(f"Process {pid} for run {run_id} no longer exists")
                self._handle_crashed_process(run_id, pid)
                return False
            
            # Send SIGCONT to resume process (Unix only)
            if hasattr(signal, 'SIGCONT') and os.name == 'posix':
                os.kill(pid, signal.SIGCONT)
                self.paused_runs.remove(run_id)
                
                # Update state
                self.state_manager.update_pipeline_status(run_id, PipelineStatus.RUNNING)
                
                # Update process file
                self._update_process_status(run_id, "running")
                
                self.logger.info(f"Resumed run {run_id} (PID {pid})")
                return True
            else:
                self.logger.warning("Pause/resume not supported on this platform")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to resume run {run_id}: {e}")
            return False
    
    def pause_all_runs(self) -> int:
        """Pause all active runs"""
        paused_count = 0
        for run_id in list(self.active_processes.keys()):
            if self.pause_run(run_id):
                paused_count += 1
        
        self.logger.info(f"Paused {paused_count} runs")
        return paused_count
    
    def resume_all_runs(self) -> int:
        """Resume all paused runs"""
        resumed_count = 0
        for run_id in list(self.paused_runs):
            if self.resume_run(run_id):
                resumed_count += 1
        
        self.logger.info(f"Resumed {resumed_count} runs")
        return resumed_count
    
    def start_monitoring(self, check_interval: int = 30) -> None:
        """Start background monitoring for crashed processes"""
        if self.monitor_enabled:
            return
        
        self.monitor_enabled = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"Started process monitoring (check interval: {check_interval}s)")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self.monitor_enabled = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self.logger.info("Stopped process monitoring")
    
    def _monitoring_loop(self, check_interval: int) -> None:
        """Main monitoring loop"""
        while self.monitor_enabled and not self.shutdown_requested:
            try:
                self._check_for_crashed_processes()
                self._cleanup_stale_runs()
                time.sleep(check_interval)
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
    
    def _check_for_crashed_processes(self) -> None:
        """Check for crashed processes and mark runs as failed"""
        for run_id, pid in list(self.active_processes.items()):
            if not psutil.pid_exists(pid):
                self.logger.warning(f"Detected crashed process: run {run_id}, PID {pid}")
                self._handle_crashed_process(run_id, pid)
    
    def _handle_crashed_process(self, run_id: str, pid: int) -> None:
        """Handle a crashed process"""
        # Mark pipeline as failed
        error_msg = f"Process crashed (PID {pid})"
        self.state_manager.update_pipeline_status(run_id, PipelineStatus.FAILED, error_msg)
        
        # Mark current running step as failed
        pipeline_run = self.state_manager.get_pipeline_run(run_id)
        if pipeline_run:
            for step in pipeline_run.steps:
                if step['status'] == StepStatus.RUNNING.value:
                    self.state_manager.complete_step(
                        run_id, step['step_number'], False,
                        error_message=f"Step failed due to process crash (PID {pid})"
                    )
                    break
        
        # Remove from active processes
        self.unregister_process(run_id)
        
        self.logger.error(f"Marked run {run_id} as failed due to process crash")
    
    def _cleanup_stale_runs(self) -> None:
        """Clean up stale process files and orphaned runs"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for process_file in self.process_dir.glob("*.json"):
            try:
                with open(process_file) as f:
                    process_info = json.load(f)
                
                # Check if process file is old
                started_at = datetime.fromisoformat(process_info['started_at'])
                if started_at < cutoff_time:
                    self.logger.info(f"Cleaning up stale process file: {process_file}")
                    process_file.unlink()
                    continue
                
                # Check if process is still running
                pid = process_info['pid']
                if not psutil.pid_exists(pid):
                    run_id = process_info['run_id']
                    self.logger.info(f"Cleaning up orphaned process: {run_id}")
                    self._handle_crashed_process(run_id, pid)
                    
            except Exception as e:
                self.logger.error(f"Error cleaning up process file {process_file}: {e}")
    
    def _update_process_status(self, run_id: str, status: str) -> None:
        """Update process status in process file"""
        process_file = self.process_dir / f"{run_id}.json"
        if process_file.exists():
            try:
                with open(process_file) as f:
                    process_info = json.load(f)
                
                process_info['status'] = status
                process_info['updated_at'] = datetime.now().isoformat()
                
                with open(process_file, 'w') as f:
                    json.dump(process_info, f, indent=2)
                    
            except Exception as e:
                self.logger.error(f"Failed to update process status: {e}")
    
    def recover_orphaned_runs(self) -> List[str]:
        """Detect and recover orphaned runs that were left in 'running' state"""
        recovered_runs = []
        
        # Check all runs in running state
        try:
            runs_index_file = self.state_dir / "runs_index.json"
            if runs_index_file.exists():
                with open(runs_index_file) as f:
                    runs_index = json.load(f)
                
                for run_id, run_info in runs_index.items():
                    if run_info.get('status') == PipelineStatus.RUNNING.value:
                        # Check if there's an active process
                        process_file = self.process_dir / f"{run_id}.json"
                        
                        if process_file.exists():
                            try:
                                with open(process_file) as f:
                                    process_info = json.load(f)
                                
                                pid = process_info['pid']
                                if not psutil.pid_exists(pid):
                                    # Process is gone, mark as failed
                                    self._handle_crashed_process(run_id, pid)
                                    recovered_runs.append(run_id)
                                    
                            except Exception as e:
                                self.logger.error(f"Error checking process file {process_file}: {e}")
                        else:
                            # No process file, likely crashed
                            self.state_manager.update_pipeline_status(
                                run_id, PipelineStatus.FAILED,
                                "Pipeline was left in running state without active process"
                            )
                            recovered_runs.append(run_id)
        
        except Exception as e:
            self.logger.error(f"Error recovering orphaned runs: {e}")
        
        if recovered_runs:
            self.logger.info(f"Recovered {len(recovered_runs)} orphaned runs: {recovered_runs}")
        
        return recovered_runs
    
    def get_active_runs(self) -> Dict[str, Dict]:
        """Get information about active runs"""
        active_runs = {}
        
        for run_id, pid in self.active_processes.items():
            try:
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    active_runs[run_id] = {
                        "pid": pid,
                        "status": "paused" if run_id in self.paused_runs else "running",
                        "cpu_percent": proc.cpu_percent(),
                        "memory_info": proc.memory_info()._asdict(),
                        "create_time": proc.create_time()
                    }
                else:
                    # Process is gone
                    self._handle_crashed_process(run_id, pid)
            except Exception as e:
                self.logger.error(f"Error getting process info for {run_id}: {e}")
        
        return active_runs
    
    def shutdown(self) -> None:
        """Graceful shutdown of the process monitor"""
        self.logger.info("Shutting down process monitor...")
        self.shutdown_requested = True
        
        # Pause all running processes
        if self.active_processes:
            paused_count = self.pause_all_runs()
            self.logger.info(f"Paused {paused_count} processes for graceful shutdown")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Clean up active processes
        for run_id in list(self.active_processes.keys()):
            self.unregister_process(run_id)
        
        self.logger.info("Process monitor shutdown complete")