import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from pathlib import Path
import sys
import os

# Add the src directory to the Python path to import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from core.gpth_core_api import GooglePhotosTakeoutHelper, ProcessingConfig, AlbumMode, ExtensionFixMode
except ImportError:
    print("Could not import core module. Please run from the project root directory.")
    sys.exit(1)


class GPTHGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Photos Takeout Helper - Python GUI")
        self.root.geometry("900x800")
        
        # Variables for form inputs
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.input_type = tk.StringVar(value="folder")  # folder or zip
        self.album_mode = tk.StringVar(value="shortcut")
        self.date_division = tk.IntVar(value=0)
        self.partner_shared = tk.BooleanVar(value=False)
        self.skip_extras = tk.BooleanVar(value=False)
        self.write_exif = tk.BooleanVar(value=True)
        self.transform_pixel_mp = tk.BooleanVar(value=False)
        self.guess_from_name = tk.BooleanVar(value=True)
        self.update_creation_time = tk.BooleanVar(value=False)
        self.limit_filesize = tk.BooleanVar(value=False)
        self.extension_fix_mode = tk.StringVar(value="standard")
        self.verbose = tk.BooleanVar(value=False)
        self.fix_mode = tk.BooleanVar(value=False)
        self.dry_run = tk.BooleanVar(value=False)
        self.max_threads = tk.IntVar(value=4)
        
        self.gpth = None
        self.processing = False
        
        self.setup_gui()
        
    def setup_gui(self):
        # Create main container with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable tabs
        self.setup_main_tab(notebook)
        self.setup_advanced_tab(notebook)
        self.setup_processing_tab(notebook)
        
        # Create bottom frame for processing controls
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(bottom_frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to process")
        self.status_label.pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill=tk.X)
        
        self.validate_btn = ttk.Button(button_frame, text="Validate Input", command=self.validate_input)
        self.validate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.estimate_btn = ttk.Button(button_frame, text="Estimate Space", command=self.estimate_space)
        self.estimate_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.help_btn = ttk.Button(button_frame, text="❓ Help", command=self.show_help)
        self.help_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.system_btn = ttk.Button(button_frame, text="🔧 System Info", command=self.check_system_info)
        self.system_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.process_btn = ttk.Button(button_frame, text="Start Processing", command=self.start_processing)
        self.process_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT)
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def setup_main_tab(self, notebook):
        # Create main tab with scrollable content
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main Settings")
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(main_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Input section
        input_frame = ttk.LabelFrame(scrollable_frame, text="Input Selection", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Input type selection
        type_frame = ttk.Frame(input_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(type_frame, text="Input Type:").pack(anchor=tk.W)
        
        ttk.Radiobutton(type_frame, text="Use extracted Takeout folder", 
                       variable=self.input_type, value="folder").pack(anchor=tk.W)
        ttk.Radiobutton(type_frame, text="Select ZIP files from Google Takeout", 
                       variable=self.input_type, value="zip").pack(anchor=tk.W)
        
        # Input path
        path_frame = ttk.Frame(input_frame)
        path_frame.pack(fill=tk.X)
        
        ttk.Label(path_frame, text="Input Path:").pack(anchor=tk.W)
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Entry(path_entry_frame, textvariable=self.input_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_entry_frame, text="Browse", command=self.browse_input).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Output section
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output Settings", padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_frame, text="Output Folder:").pack(anchor=tk.W)
        out_entry_frame = ttk.Frame(output_frame)
        out_entry_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Entry(out_entry_frame, textvariable=self.output_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_entry_frame, text="Browse", command=self.browse_output).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Album handling section
        album_frame = ttk.LabelFrame(scrollable_frame, text="Album Handling", padding=10)
        album_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(album_frame, text="Album Mode:").pack(anchor=tk.W)
        
        album_options = [
            ("shortcut", "Shortcut (Recommended) - Symbolic links, saves space"),
            ("duplicate-copy", "Duplicate Copy - Real copies in each album"),
            ("reverse-shortcut", "Reverse Shortcut - Files stay in albums, links in ALL_PHOTOS"),
            ("json", "JSON - Single folder + albums-info.json metadata"),
            ("nothing", "Nothing - Ignore albums, chronological only")
        ]
        
        for value, text in album_options:
            ttk.Radiobutton(album_frame, text=text, variable=self.album_mode, value=value).pack(anchor=tk.W)
        
        # Date organization section
        date_frame = ttk.LabelFrame(scrollable_frame, text="Date Organization", padding=10)
        date_frame.pack(fill=tk.X)
        
        ttk.Label(date_frame, text="Folder Structure for ALL_PHOTOS:").pack(anchor=tk.W)
        
        date_options = [
            (0, "Single folder (no date division)"),
            (1, "Organize by year (YYYY/)"),
            (2, "Organize by year and month (YYYY/MM/)"),
            (3, "Organize by year, month, and day (YYYY/MM/DD/)")
        ]
        
        for value, text in date_options:
            ttk.Radiobutton(date_frame, text=text, variable=self.date_division, value=value).pack(anchor=tk.W)
        
        # Partner shared option
        ttk.Checkbutton(date_frame, text="Separate partner shared media into PARTNER_SHARED folder", 
                       variable=self.partner_shared).pack(anchor=tk.W, pady=(10, 0))
        
    def setup_advanced_tab(self, notebook):
        # Create advanced tab with scrollable content
        advanced_tab = ttk.Frame(notebook)
        notebook.add(advanced_tab, text="Advanced Options")
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(advanced_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(advanced_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # File processing section
        file_frame = ttk.LabelFrame(scrollable_frame, text="File Processing", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(file_frame, text="Skip extra images (like \"-edited\" versions)", 
                       variable=self.skip_extras).pack(anchor=tk.W)
        ttk.Checkbutton(file_frame, text="Write GPS coordinates and dates to EXIF metadata", 
                       variable=self.write_exif).pack(anchor=tk.W)
        ttk.Checkbutton(file_frame, text="Transform Pixel Motion Photos (.MP/.MV) to .mp4", 
                       variable=self.transform_pixel_mp).pack(anchor=tk.W)
        ttk.Checkbutton(file_frame, text="Extract dates from filenames", 
                       variable=self.guess_from_name).pack(anchor=tk.W)
        ttk.Checkbutton(file_frame, text="Update creation time to match modified time (Windows only)", 
                       variable=self.update_creation_time).pack(anchor=tk.W)
        ttk.Checkbutton(file_frame, text="Skip files larger than 64MB (for low-RAM systems)", 
                       variable=self.limit_filesize).pack(anchor=tk.W)
        
        # Extension fixing section
        ext_frame = ttk.LabelFrame(scrollable_frame, text="Extension Fixing", padding=10)
        ext_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(ext_frame, text="Extension Fix Mode:").pack(anchor=tk.W)
        
        ext_options = [
            ("none", "None - Don't fix extensions"),
            ("standard", "Standard - Fix extensions but skip TIFF-based files (Recommended)"),
            ("conservative", "Conservative - Skip TIFF-based and JPEG files for maximum safety"),
            ("solo", "Solo - Fix extensions then exit (preprocessing mode)")
        ]
        
        for value, text in ext_options:
            ttk.Radiobutton(ext_frame, text=text, variable=self.extension_fix_mode, value=value).pack(anchor=tk.W)
        
        # Special modes section
        special_frame = ttk.LabelFrame(scrollable_frame, text="Special Modes", padding=10)
        special_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(special_frame, text="Fix mode - Fix dates in any folder (not just Takeout)", 
                       variable=self.fix_mode).pack(anchor=tk.W)
        ttk.Checkbutton(special_frame, text="Verbose logging - Show detailed output", 
                       variable=self.verbose).pack(anchor=tk.W)
        
    def setup_processing_tab(self, notebook):
        # Create processing tab with scrollable content
        processing_tab = ttk.Frame(notebook)
        notebook.add(processing_tab, text="Processing Options")
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(processing_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(processing_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Performance section
        perf_frame = ttk.LabelFrame(scrollable_frame, text="Performance Settings", padding=10)
        perf_frame.pack(fill=tk.X, pady=(0, 10))
        
        threads_frame = ttk.Frame(perf_frame)
        threads_frame.pack(fill=tk.X)
        
        ttk.Label(threads_frame, text="Max Threads:").pack(side=tk.LEFT)
        ttk.Spinbox(threads_frame, from_=1, to=16, textvariable=self.max_threads, width=5).pack(side=tk.LEFT, padx=(10, 0))
        
        # Safety options
        safety_frame = ttk.LabelFrame(scrollable_frame, text="Safety Options", padding=10)
        safety_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(safety_frame, text="Dry run - Simulate processing without making changes", 
                       variable=self.dry_run).pack(anchor=tk.W)
        
        # Add help text for dry run
        help_text = ttk.Label(safety_frame, 
                             text="Dry run mode will analyze your files and show what would be done\nwithout actually moving or modifying any files. Use this to test settings.",
                             foreground="gray")
        help_text.pack(anchor=tk.W, padx=(20, 0))
        
        # Dependency check section
        dep_frame = ttk.LabelFrame(scrollable_frame, text="Dependencies", padding=10)
        dep_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(dep_frame, text="Check ExifTool Installation", command=self.check_dependencies).pack(anchor=tk.W)
        
    def browse_input(self):
        if self.input_type.get() == "zip":
            filetypes = [("ZIP files", "*.zip"), ("All files", "*.*")]
            files = filedialog.askopenfilenames(title="Select Google Takeout ZIP files", filetypes=filetypes)
            if files:
                self.input_path.set(";".join(files))  # Multiple files separated by semicolon
        else:
            directory = filedialog.askdirectory(title="Select Takeout folder")
            if directory:
                self.input_path.set(directory)
    
    def browse_output(self):
        directory = filedialog.askdirectory(title="Select output folder")
        if directory:
            self.output_path.set(directory)
    
    def log_message(self, message):
        """Add message to log output"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.log_message(message)
    
    def validate_input(self):
        """Validate the input structure"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input path")
            return
            
        def validate_thread():
            try:
                self.update_status("Validating input structure...")
                
                # Create config from GUI settings
                config = self.create_config()
                
                # Initialize GPTH
                self.gpth = GooglePhotosTakeoutHelper(config)
                
                # Validate structure
                is_valid = self.gpth.validate_takeout_structure()
                
                if is_valid:
                    self.update_status("✓ Input structure is valid")
                    messagebox.showinfo("Validation", "Input structure is valid and ready for processing!")
                else:
                    self.update_status("✗ Invalid input structure")
                    messagebox.showerror("Validation", "Input structure is not valid. Please check the logs for details.")
                    
            except Exception as e:
                self.update_status(f"Validation failed: {str(e)}")
                messagebox.showerror("Error", f"Validation failed: {str(e)}")
        
        threading.Thread(target=validate_thread, daemon=True).start()
    
    def estimate_space(self):
        """Estimate space requirements"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input path")
            return
            
        def estimate_thread():
            try:
                self.update_status("Estimating space requirements...")
                
                # Create config from GUI settings
                config = self.create_config()
                
                # Initialize GPTH
                self.gpth = GooglePhotosTakeoutHelper(config)
                
                # Get space estimates
                estimates = self.gpth.estimate_space_requirements()
                
                message = f"""Space Requirements Estimate:

Input Size: {estimates['input_size_gb']:.2f} GB
Estimated Output Size: {estimates['output_size_gb']:.2f} GB
Available Space: {estimates['available_space_gb']:.2f} GB

Album Mode: {self.album_mode.get()}
Space Efficiency: {estimates['space_multiplier']:.1f}x

{estimates['warning'] if estimates['warning'] else 'Sufficient space available!'}"""
                
                self.update_status("Space estimation completed")
                messagebox.showinfo("Space Estimation", message)
                
            except Exception as e:
                self.update_status(f"Space estimation failed: {str(e)}")
                messagebox.showerror("Error", f"Space estimation failed: {str(e)}")
        
        threading.Thread(target=estimate_thread, daemon=True).start()
    
    def check_dependencies(self):
        """Check ExifTool installation"""
        def check_thread():
            try:
                self.update_status("Checking ExifTool installation...")
                
                # Create temporary config for dependency checking
                config = ProcessingConfig(
                    input_path="",
                    output_path=""
                )
                gpth = GooglePhotosTakeoutHelper(config)
                
                status = gpth.check_exiftool_status()
                
                # Handle both 'is_available' and 'available' keys for compatibility
                is_available = status.get('is_available', status.get('available', False))
                
                if is_available:
                    version = status.get('version', 'Unknown')
                    path = status.get('path', 'System PATH')
                    message = f"✓ ExifTool is available\nVersion: {version}\nPath: {path}"
                    self.update_status("ExifTool check completed - Available")
                    messagebox.showinfo("ExifTool Status", message)
                else:
                    message = f"""✗ ExifTool not found

ExifTool is recommended for full functionality including:
- Writing GPS coordinates to media files
- Supporting all image/video formats
- Advanced metadata handling

To install ExifTool:
- Windows: Download from exiftool.org or use 'choco install exiftool'
- Mac: 'brew install exiftool'
- Linux: 'sudo apt install libimage-exiftool-perl'

The tool will still work without ExifTool but with limited EXIF writing capabilities."""
                    
                    self.update_status("ExifTool check completed - Not found")
                    messagebox.showwarning("ExifTool Status", message)
                    
            except Exception as e:
                self.update_status(f"Dependency check failed: {str(e)}")
                messagebox.showerror("Error", f"Dependency check failed: {str(e)}")
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def create_config(self):
        """Create ProcessingConfig from GUI settings"""
        return ProcessingConfig(
            input_path=self.input_path.get(),
            output_path=self.output_path.get(),
            album_mode=AlbumMode(self.album_mode.get()),
            date_division=self.date_division.get(),
            divide_partner_shared=self.partner_shared.get(),
            skip_extras=self.skip_extras.get(),
            write_exif=self.write_exif.get(),
            transform_pixel_mp=self.transform_pixel_mp.get(),
            guess_from_name=self.guess_from_name.get(),
            update_creation_time=self.update_creation_time.get(),
            limit_filesize=self.limit_filesize.get(),
            extension_fix_mode=ExtensionFixMode(self.extension_fix_mode.get()),
            verbose=self.verbose.get(),
            fix_mode=self.fix_mode.get(),
            dry_run=self.dry_run.get(),
            max_threads=self.max_threads.get()
        )
    
    def start_processing(self):
        """Start the main processing"""
        if not self.input_path.get() or not self.output_path.get():
            messagebox.showerror("Error", "Please select both input and output paths")
            return
        
        if self.processing:
            messagebox.showwarning("Warning", "Processing is already running")
            return
        
        # Confirm dry run mode
        if self.dry_run.get():
            result = messagebox.askyesno("Dry Run Mode", 
                                       "Dry run mode is enabled. This will simulate processing without making changes.\n\n"
                                       "Do you want to continue?")
            if not result:
                return
        
        self.processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar.start()
        
        def processing_thread():
            try:
                self.update_status("Starting processing...")
                
                # Create config from GUI settings
                config = self.create_config()
                
                # Initialize GPTH
                self.gpth = GooglePhotosTakeoutHelper(config)
                
                # Set up progress callback
                def progress_callback(message, current=None, total=None):
                    if current is not None and total is not None:
                        progress_text = f"{message} ({current}/{total})"
                    else:
                        progress_text = message
                    self.root.after(0, lambda: self.update_status(progress_text))
                
                self.gpth.set_progress_callback(progress_callback)
                
                # Run processing
                if config.fix_mode:
                    result = self.gpth.fix_dates_in_folder()
                else:
                    result = self.gpth.process_takeout()
                
                if result:
                    mode_text = "DRY RUN - " if config.dry_run else ""
                    self.update_status(f"✓ {mode_text}Processing completed successfully!")
                    
                    if config.dry_run:
                        messagebox.showinfo("Success", "Dry run completed! Check the logs to see what would be done.")
                    else:
                        messagebox.showinfo("Success", "Processing completed successfully!")
                else:
                    self.update_status("✗ Processing failed")
                    messagebox.showerror("Error", "Processing failed. Check the logs for details.")
                
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
                messagebox.showerror("Error", f"Processing failed: {str(e)}")
            finally:
                self.processing = False
                self.root.after(0, lambda: [
                    self.progress_bar.stop(),
                    self.process_btn.config(state=tk.NORMAL),
                    self.cancel_btn.config(state=tk.DISABLED)
                ])
        
        threading.Thread(target=processing_thread, daemon=True).start()
    
    def cancel_processing(self):
        """Cancel the current processing"""
        if self.gpth and hasattr(self.gpth, 'cancel'):
            self.gpth.cancel()
            self.update_status("Cancelling processing...")
        else:
            self.processing = False
            self.progress_bar.stop()
            self.process_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
            self.update_status("Processing cancelled")

    def show_help(self):
        """Show comprehensive help information"""
        help_text = """🎯 How to use Google Photos Takeout Helper:

1️⃣ GET YOUR GOOGLE PHOTOS DATA:
   • Go to Google Takeout (takeout.google.com)
   • Select 'Photos' and download your archive
   • You'll get ZIP file(s) or can extract to a folder

2️⃣ SELECT INPUT:
   • Choose the folder you extracted OR
   • Select the ZIP files you downloaded

3️⃣ SELECT OUTPUT:
   • Choose an empty folder where organized photos will go
   • Don't use the same folder as input!

4️⃣ CHOOSE ORGANIZATION:
   • Date: How to organize by date (year/month folders)
   • Albums: How to handle your photo albums

5️⃣ PROCESSING OPTIONS:
   • Start with "Dry Run" to preview changes
   • Enable EXIF writing for location/date info
   • Keep other settings as default for best results

6️⃣ START PROCESSING:
   • Click "Validate Input" to check everything
   • Click "Start Processing" to begin organizing

❓ TIPS:
   • Always do a dry run first to see what will happen
   • Make sure you have enough disk space
   • Processing can take a while for large photo collections
   • Your original photos in Takeout won't be changed
"""
        # Create help window
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - How to Use")
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        # Create scrollable text
        text_frame = tk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 9))
        help_scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=help_scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        help_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.insert("1.0", help_text)
        text_widget.configure(state="disabled")

    def check_system_info(self):
        """Enhanced system information check"""
        import platform
        python_version = platform.python_version()
        system = f"{platform.system()} {platform.release()}"
        # Check dependencies
        deps = []
        try:
            from PIL import Image
            deps.append("✅ Pillow (image processing)")
        except ImportError:
            deps.append("❌ Pillow (recommended: pip install Pillow)")
        try:
            import json
            deps.append("✅ JSON support")
        except ImportError:
            deps.append("❌ JSON support")
        # Check ExifTool
        import subprocess
        try:
            subprocess.run("exiftool -ver", shell=True, capture_output=True, check=True)
            deps.append("✅ ExifTool (metadata support)")
        except:
            deps.append("⚠️ ExifTool (optional: for better metadata support)")
        system_info = f"""System Information:

🖥️ Operating System: {system}
🐍 Python Version: {python_version}

📦 Dependencies:
{chr(10).join(deps)}

💡 This system should work fine with Google Photos Takeout Helper!
"""
        messagebox.showinfo("System Information", system_info)


def main():
    """Main entry point for the GUI application"""
    root = tk.Tk()
    app = GPTHGui(root)
    
    # Set minimum window size
    root.minsize(800, 600)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()