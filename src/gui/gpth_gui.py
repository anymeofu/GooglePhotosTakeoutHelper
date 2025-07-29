"""
Google Photos Takeout Helper - GUI Interface
Graphical user interface using tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.gpth_core_api import GpthCoreApi, ProcessingConfig, ProcessingResult

class GpthGui:
    """Main GUI application class"""
    def __init__(self, root):
        self.root = root
        self.root.title("Google Photos Takeout Helper")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        # Application state
        self.api: Optional[GpthCoreApi] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        # Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.skip_extras = tk.BooleanVar(value=True)
        self.skip_albums = tk.BooleanVar(value=False)
        self.keep_duplicates = tk.BooleanVar(value=False)
        self.fix_creation_time = tk.BooleanVar(value=True)
        self.use_exiftool = tk.BooleanVar(value=True)
        self.max_threads = tk.IntVar(value=4)
        self.verbose = tk.BooleanVar(value=False)
        self.dry_run = tk.BooleanVar(value=False)
        # Setup GUI
        self.create_widgets()
        self.center_window()
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check system dependencies and warn if missing"""
        try:
            config = ProcessingConfig(input_path="", output_path="")
            api = GpthCoreApi(config)
            
            # Check ExifTool
            exiftool_status = api.check_exiftool_status()
            if not exiftool_status['is_available']:
                messagebox.showwarning(
                    "Missing Dependency",
                    "ExifTool not found. Some features may be limited.\n\n"
                    "Install from: https://exiftool.org/"
                )
        except Exception:
            pass  # Ignore errors during dependency check
    def create_widgets(self):
        """Create and layout GUI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # Title
        title_label = ttk.Label(main_frame, text="Google Photos Takeout Helper", 
                               font=('TkDefaultFont', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        # Input path section
        ttk.Label(main_frame, text="Input Path:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input_path).grid(row=1, column=2, pady=5)
        # Output path section
        ttk.Label(main_frame, text="Output Path:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_path).grid(row=2, column=2, pady=5)
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Processing Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 10))
        options_frame.columnconfigure(1, weight=1)
        # First row of options
        ttk.Checkbutton(options_frame, text="Skip extras (edited versions, etc.)", 
                       variable=self.skip_extras).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Skip album organization", 
                       variable=self.skip_albums).grid(row=0, column=1, sticky=tk.W, pady=2)
        # Second row of options
        ttk.Checkbutton(options_frame, text="Keep duplicate files", 
                       variable=self.keep_duplicates).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Fix file creation times", 
                       variable=self.fix_creation_time).grid(row=1, column=1, sticky=tk.W, pady=2)
        # Third row of options
        ttk.Checkbutton(options_frame, text="Use ExifTool", 
                       variable=self.use_exiftool).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Verbose output",
                       variable=self.verbose).grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Third row of options
        ttk.Checkbutton(options_frame, text="Dry run (simulate only - saves time)",
                       variable=self.dry_run).grid(row=3, column=0, sticky=tk.W, pady=2)
        # Thread count
        thread_frame = ttk.Frame(options_frame)
        thread_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        ttk.Label(thread_frame, text="Max Threads:").pack(side=tk.LEFT)
        ttk.Spinbox(thread_frame, from_=1, to=16, textvariable=self.max_threads, width=5).pack(side=tk.LEFT, padx=(5, 0))
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, pady=(20, 10))
        ttk.Button(buttons_frame, text="Analyze", command=self.analyze_takeout).pack(side=tk.LEFT, padx=(0, 10))
        self.process_button = ttk.Button(buttons_frame, text="Process", command=self.process_takeout)
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))
        self.cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT)
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=8)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        # Progress text
        self.progress_text = scrolledtext.ScrolledText(progress_frame, height=10, state=tk.DISABLED)
        self.progress_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Configure grid weights for resizing
        main_frame.rowconfigure(5, weight=1)
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
    def browse_input_path(self):
        """Browse for input directory"""
        path = filedialog.askdirectory(title="Select Google Photos Takeout Folder")
        if path:
            self.input_path.set(path)
    def browse_output_path(self):
        """Browse for output directory"""
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_path.set(path)
    def log_message(self, message: str):
        """Add message to progress text area"""
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    def progress_callback(self, step: int, message: str):
        """Progress callback for API"""
        self.progress_var.set(step)
        self.log_message(f"[{step}/8] {message}")
    def validate_inputs(self) -> bool:
        """Validate user inputs"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input path")
            return False
        if not self.output_path.get():
            messagebox.showerror("Error", "Please select an output path")
            return False
        if not Path(self.input_path.get()).exists():
            messagebox.showerror("Error", "Input path does not exist")
            return False
        return True
    def get_config(self) -> ProcessingConfig:
        """Get processing configuration from GUI"""
        return ProcessingConfig(
            input_path=self.input_path.get(),
            output_path=self.output_path.get(),
            skip_extras=self.skip_extras.get(),
            skip_albums=self.skip_albums.get(),
            keep_duplicates=self.keep_duplicates.get(),
            fix_creation_time=self.fix_creation_time.get(),
            use_exiftool=self.use_exiftool.get(),
            max_threads=self.max_threads.get(),
            verbose=self.verbose.get(),
            dry_run=self.dry_run.get()
        )
    def analyze_takeout(self):
        """Analyze takeout structure"""
        if not self.validate_inputs():
            return
        try:
            config = self.get_config()
            api = GpthCoreApi(config)
            self.log_message("🔍 Analyzing takeout structure...")
            structure = api.discover_takeout_structure()
            # Clear progress text and show analysis results
            self.progress_text.config(state=tk.NORMAL)
            self.progress_text.delete(1.0, tk.END)
            self.progress_text.config(state=tk.DISABLED)
            self.log_message("📊 Takeout Structure Analysis:")
            self.log_message(f"   📁 Total files: {structure['total_files']}")
            self.log_message(f"   📸 Media files: {structure['media_files']}")
            self.log_message(f"   📄 JSON metadata files: {structure['json_files']}")
            self.log_message(f"   📷 Has Google Photos: {'Yes' if structure['has_photos'] else 'No'}")
            self.log_message(f"   🎨 Has albums: {'Yes' if structure['has_albums'] else 'No'}")
            self.log_message(f"   ⏱️  Estimated processing time: {structure['estimated_processing_time']:.1f} seconds")
            # Recommendations
            self.log_message("")
            self.log_message("💡 Recommendations:")
            if not structure['has_photos']:
                self.log_message("   ⚠️  This doesn't look like a Google Photos takeout")
            if structure['media_files'] == 0:
                self.log_message("   ❌ No media files found")
            elif structure['media_files'] < 100:
                self.log_message("   ✅ Small archive - processing should be quick")
            elif structure['media_files'] < 1000:
                self.log_message("   ⏳ Medium archive - processing will take a few minutes")
            else:
                self.log_message("   🕐 Large archive - processing may take 10+ minutes")
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Failed to analyze takeout: {str(e)}")
    def process_takeout(self):
        """Start processing in background thread"""
        if not self.validate_inputs():
            return
        if self.is_processing:
            return
        # Confirm processing
        config = self.get_config()
        result = messagebox.askyesno(
            "Confirm Processing",
            f"Process Google Photos takeout?\n\n"
            f"Input: {config.input_path}\n"
            f"Output: {config.output_path}\n\n"
            f"This may take several minutes depending on the size of your archive."
        )
        if not result:
            return
        # Start processing
        self.is_processing = True
        self.process_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        # Clear progress
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.progress_var.set(0)
        # Start background thread
        self.processing_thread = threading.Thread(target=self._process_worker, args=(config,))
        self.processing_thread.start()
    def _process_worker(self, config: ProcessingConfig):
        """Background worker for processing"""
        try:
            self.api = GpthCoreApi(config)
            self.api.set_progress_callback(self.progress_callback)
            self.log_message("🚀 Starting Google Photos Takeout Helper")
            self.log_message(f"Input: {config.input_path}")
            self.log_message(f"Output: {config.output_path}")
            self.log_message("")
            # Process the takeout
            result = self.api.process_takeout()
            # Update UI on main thread
            self.root.after(0, self._processing_complete, result)
        except Exception as e:
            error_result = ProcessingResult(success=False)
            error_result.errors.append(f"Processing failed: {str(e)}")
            self.root.after(0, self._processing_complete, error_result)
    def _processing_complete(self, result: ProcessingResult):
        """Handle processing completion on main thread"""
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        # Show results
        self.log_message("")
        if result.success:
            self.log_message("✅ Processing completed successfully!")
        else:
            self.log_message("❌ Processing failed!")
        self.log_message("")
        self.log_message("📊 Results:")
        self.log_message(f"   Total files: {result.total_files}")
        self.log_message(f"   Processed: {result.processed_files}")
        self.log_message(f"   Duplicates removed: {result.duplicates_removed}")
        self.log_message(f"   Albums found: {result.albums_found}")
        self.log_message(f"   Processing time: {result.processing_time:.2f} seconds")
        if result.errors:
            self.log_message("")
            self.log_message("❌ Errors:")
            for error in result.errors:
                self.log_message(f"   • {error}")
        if result.warnings:
            self.log_message("")
            self.log_message("⚠️  Warnings:")
            for warning in result.warnings:
                self.log_message(f"   • {warning}")
        # Show completion dialog
        if result.success:
            messagebox.showinfo("Success", "Processing completed successfully!")
        else:
            messagebox.showerror("Error", "Processing failed. See log for details.")
    def cancel_processing(self):
        """Cancel current processing"""
        if self.api and self.is_processing:
            self.api.cancel_processing()
            self.log_message("🛑 Cancellation requested...")
    def on_closing(self):
        """Handle window closing"""
        if self.is_processing:
            result = messagebox.askyesno(
                "Processing in Progress",
                "Processing is currently running. Do you want to cancel and exit?"
            )
            if result:
                if self.api:
                    self.api.cancel_processing()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Main entry point for GUI application"""
    root = tk.Tk()
    app = GpthGui(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Set application icon (optional)
    try:
        # You can add an icon file here if available
        # root.iconbitmap('icon.ico')
        pass
    except:
        pass
    
    root.mainloop()

if __name__ == '__main__':
    main()