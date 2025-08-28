import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import re
import time
import threading
from pathlib import Path
from PIL import Image, ImageTk
import glob
import pystray
from pystray import MenuItem as item
import io
import base64
import json
from flask_utils import get_best_flask_for_level, get_flask_image, create_fallback_flask_image
from weapon_utils import get_best_weapon_for_level, format_weapon_damage, format_weapon_stats

class PoEMapsViewer:
    def __init__(self):
        self.log_file_path = r"D:\Program Files (x86)\Grinding Gear Games\logs\Client.txt"
        self.maps_directory = r"D:\Docs\apps\poe-maps\maps"
        self.current_zone = "Unknown"
        self.last_file_size = 0
        self.running = True
        self.tray_icon = None
        self.window_visible = True
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("PoE2 Maps")
        
        # Level tracking
        self.player_level = None
        self.override_player_level = False
        
        # Make window borderless
        self.root.overrideredirect(True)
        
        # Set initial size - about twice as big
        self.root.geometry("800x600+100+100")
        
        # Make window always on top and transparent background
        self.root.attributes("-topmost", True)
        self.root.configure(bg='black')
        
        # Add drag and resize functionality
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.on_move)
        
        # Variables for resize functionality
        self.resizing = False
        self.resize_direction = None
        self.start_x = 0
        self.start_y = 0
        self.start_width = 0
        self.start_height = 0
        
        # Variables for smooth dragging
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Store original images for scaling
        self.original_images = []
        self.image_labels = []
        
        # Settings
        self.settings_file = os.path.join(self.maps_directory, '..', 'settings.json')
        self.settings = self.load_settings()
        # Initialize level fields from settings
        self.player_level = self.settings.get("player_level", None)
        self.override_player_level = bool(self.settings.get("override_player_level", False))
        self.settings_window = None
        
        # Create UI
        self.setup_ui()
        
        # Initialize file monitoring
        self.init_file_monitoring()
        
        # Setup system tray
        self.setup_system_tray()
        
        # Check current zone on startup
        self.check_current_zone()
        # Check player level on startup
        self.check_player_level()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def setup_ui(self):
        # Create main frame directly on root - no padding, no borders
        self.main_frame = tk.Frame(self.root, bg='black', bd=0)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal layout: flask panel on left, maps on right
        self.content_frame = tk.Frame(self.main_frame, bg='black', bd=0)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Flask panel on the left
        self.flask_frame = tk.Frame(self.content_frame, bg='black', bd=1, relief='solid', width=120)
        self.flask_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.flask_frame.pack_propagate(False)  # Maintain fixed width
        
        # Configure grid for images container (maps) and notes
        self.maps_container = tk.Frame(self.content_frame, bg='black', bd=0)
        self.maps_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Images frame
        self.images_frame = tk.Frame(self.maps_container, bg='black', bd=0)
        self.images_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notes frame (initially hidden)
        self.notes_frame = tk.Frame(self.maps_container, bg='black', bd=1, relief='solid')
        self.notes_label = tk.Label(
            self.notes_frame,
            text="",
            fg='#cccccc',
            bg='black',
            font=('Arial', 10),
            justify=tk.LEFT,
            wraplength=400,
            padx=10,
            pady=5,
            anchor='w'
        )
        
        # Initialize flask display
        self.flask_labels = {}  # Store flask UI elements
        self.current_flask = None
        self.setup_flask_display()
        
        # Initialize weapon display
        self.weapon_labels = {}  # Store weapon UI elements
        self.current_weapon = None
        self.weapon_frame_container = None
        self.setup_weapon_display()
        
        # Add copy button in top right
        self.add_copy_button()
        
        # Add resize grips
        self.add_resize_grips()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def init_file_monitoring(self):
        # Get initial file size
        if os.path.exists(self.log_file_path):
            self.last_file_size = os.path.getsize(self.log_file_path)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_log_file, daemon=True)
        self.monitor_thread.start()

    def monitor_log_file(self):
        while self.running:
            try:
                if os.path.exists(self.log_file_path):
                    current_size = os.path.getsize(self.log_file_path)
                    if current_size > self.last_file_size:
                        self.last_file_size = current_size
                        # Schedule zone and level checks on main thread
                        self.root.after_idle(self.check_current_zone)
                        self.root.after_idle(self.check_player_level)
                
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                print(f"Error monitoring log file: {e}")
                time.sleep(5)  # Wait longer if there's an error

    def check_player_level(self):
        """Detect latest level-up message and store the player's level unless overridden."""
        try:
            if not os.path.exists(self.log_file_path):
                return
            
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Search the last 200 lines for a level up message like:
            # ": NAME (CLASS) is now level NUMBER"
            level_regex = re.compile(r":\s*[^()]+\([^)]*\) is now level (\d+)")
            found_level = None
            for line in reversed(lines[-200:]):
                m = level_regex.search(line)
                if m:
                    found_level = int(m.group(1))
                    break
            
            if found_level is not None:
                # Update runtime
                old_level = self.player_level
                self.player_level = found_level
                # Persist only if not overridden
                if not self.override_player_level:
                    if self.settings.get("player_level") != found_level:
                        self.settings["player_level"] = found_level
                        self.save_settings()
                        print(f"Detected player level: {found_level}")
                
                # Update flask and weapon displays if level changed
                if old_level != found_level:
                    self.root.after_idle(self.update_flask_display)
                    self.root.after_idle(self.update_weapon_display)
        except Exception as e:
            print(f"Error checking player level: {e}")

    def check_current_zone(self):
        try:
            if not os.path.exists(self.log_file_path):
                return
            
            # Read the last 50 lines to find the most recent zone
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            zone_pattern = r'\[SCENE\] Set Source \[([^\]]+)\]'
            current_zone = None
            
            # Search backwards through recent lines
            for line in reversed(lines[-50:]):
                match = re.search(zone_pattern, line)
                if match:
                    zone_name = match.group(1)
                    if zone_name not in ["(null)", "(unknown)"]:
                        current_zone = zone_name
                        break
            
            if current_zone and current_zone != self.current_zone:
                self.current_zone = current_zone
                self.update_zone_display(current_zone)
                
        except Exception as e:
            print(f"Error checking zone: {e}")

    def update_zone_display(self, zone_name):
        print(f"Zone changed to: {zone_name}")  # Debug print
        
        # Find zone folder
        zone_folder = self.find_zone_folder(zone_name)
        
        if not zone_folder:
            print(f"No folder found for '{zone_name}' - keeping previous map")
            return  # Keep previous map open
        
        # Load images
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            image_files.extend(glob.glob(os.path.join(zone_folder, ext)))
        
        if not image_files:
            print(f"No images found in '{os.path.basename(zone_folder)}' - keeping previous map")
            return  # Keep previous map open
        
        # Only clear and update if we have new maps to show
        print(f"Found {len(image_files)} map(s) for '{zone_name}' - updating display")
        
        # Clear existing images
        for widget in self.images_frame.winfo_children():
            widget.destroy()
        
        # Display new images
        self.display_images(image_files)
        print(f"Loaded {len(image_files)} map(s) for '{zone_name}'")
        
        # Load and display notes if they exist
        self.display_notes(zone_folder)
        
        # Show window and auto-resize to fit content
        if not self.window_visible:
            self.show_window()
        else:
            self.root.after(100, self.resize_window_to_content)

    def display_images(self, image_files):
        # Clear previous data
        self.original_images = []
        self.image_labels = []
        
        # Load original images and store them
        for image_path in image_files:
            try:
                # Load original image
                pil_image = Image.open(image_path)
                self.original_images.append(pil_image.copy())
            except Exception as e:
                print(f"Error loading image {image_path}: {e}")
                continue
        
        # Create image labels and display scaled images
        self.scale_and_display_images()
        
        # Bind window resize event to rescale images
        self.root.bind('<Configure>', self.on_window_resize)

    def scale_and_display_images(self):
        if not self.original_images:
            return
            
        # Clear existing labels
        for label in self.image_labels:
            label.destroy()
        self.image_labels = []
        
        # Get available space (subtract padding, grip space, and space for notes)
        available_width = max(300, self.root.winfo_width() - 150)  # Account for flask panel
        total_height = max(200, self.root.winfo_height() - 30)
        
        # Reserve space for notes if they exist and are visible
        notes_height = 0
        if hasattr(self, 'notes_frame') and self.notes_frame.winfo_viewable():
            # Estimate notes height (font size + padding + border)
            notes_height = 50  # Conservative estimate for notes area
        
        available_height = total_height - notes_height
        
        # Calculate grid layout
        num_images = len(self.original_images)
        if num_images == 1:
            cols = 1
        else:
            cols = 2  # Default to 2 columns
        rows = (num_images + cols - 1) // cols
        
        # Calculate size per image slot
        slot_width = (available_width - (cols + 1) * 5) // cols  # 5px padding between images
        slot_height = (available_height - (rows + 1) * 5) // rows
        
        # Display scaled images
        for i, original_image in enumerate(self.original_images):
            row = i // cols
            col = i % cols
            
            try:
                # Create a copy to scale
                scaled_image = original_image.copy()
                
                # Scale to fit the slot while maintaining aspect ratio
                scaled_image.thumbnail((slot_width, slot_height), Image.Resampling.LANCZOS)
                
                # Convert to tkinter format
                tk_image = ImageTk.PhotoImage(scaled_image)
                
                # Create label
                image_label = tk.Label(
                    self.images_frame, 
                    image=tk_image, 
                    bg='black',
                    bd=0,
                    highlightthickness=0
                )
                image_label.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
                
                # Configure grid weights for centering
                self.images_frame.grid_rowconfigure(row, weight=1)
                self.images_frame.grid_columnconfigure(col, weight=1)
                
                # Keep reference to prevent garbage collection
                image_label.image = tk_image
                self.image_labels.append(image_label)
                
            except Exception as e:
                print(f"Error scaling image: {e}")
                continue

    def display_notes(self, zone_folder):
        """Display notes from notes.txt file if it exists in the zone folder."""
        try:
            notes_file = os.path.join(zone_folder, 'notes.txt')
            print(f"Checking for notes file: {notes_file}")  # Debug
            
            # Hide notes frame by default
            self.notes_frame.pack_forget()
            
            if os.path.exists(notes_file):
                print(f"Notes file exists: {notes_file}")  # Debug
                # Read notes content
                with open(notes_file, 'r', encoding='utf-8', errors='ignore') as f:
                    notes_content = f.read().strip()
                
                print(f"Notes content: '{notes_content}'")  # Debug
                
                if notes_content:
                    # Store notes content for window resizing
                    self.current_notes = notes_content
                    
                    # Update notes display
                    self.update_notes_display()
                    
                    print(f"Successfully displayed notes: {notes_content}")
                else:
                    print("Notes file is empty")
                    self.current_notes = None
            else:
                print(f"Notes file does not exist: {notes_file}")
                self.current_notes = None
                    
        except Exception as e:
            print(f"Error loading notes: {e}")
            self.current_notes = None
    
    def update_notes_display(self):
        """Update notes display with current window width."""
        if not hasattr(self, 'current_notes') or not self.current_notes:
            return
            
        # Update wraplength based on available width
        available_width = max(300, self.root.winfo_width() - 150)  # Account for flask panel + padding
        self.notes_label.configure(
            text=f"📝 {self.current_notes}",
            wraplength=available_width
        )
        
        # Pack the label first, then the frame
        self.notes_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Show notes frame below images
        self.notes_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Force GUI update
        self.root.update_idletasks()

    def on_window_resize(self, event):
        # Only rescale if the event is for the main window, not child widgets
        if event.widget == self.root and not self.resizing:
            # Use after_idle to avoid too many resize events
            self.root.after_idle(self.scale_and_display_images)
            self.root.after_idle(self.update_notes_display)

    def setup_flask_display(self):
        """Setup the flask display panel."""
        # Flask panel title
        title_label = tk.Label(
            self.flask_frame,
            text="Life Flask",
            fg='white',
            bg='black',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=(5, 10))
        
        # Life flask display
        flask_frame = tk.Frame(self.flask_frame, bg='black')
        flask_frame.pack(pady=5)
        
        self.flask_labels['image'] = tk.Label(
            flask_frame,
            bg='black',
            bd=1,
            relief='solid'
        )
        self.flask_labels['image'].pack()
        
        self.flask_labels['name'] = tk.Label(
            flask_frame,
            text="Life Flask",
            fg='#ff6666',
            bg='black',
            font=('Arial', 10),
            wraplength=110,
            justify=tk.CENTER
        )
        self.flask_labels['name'].pack(pady=(2, 0))
        
        self.flask_labels['level'] = tk.Label(
            flask_frame,
            text="Req: Level 1",
            fg='gray',
            bg='black',
            font=('Arial', 9)
        )
        self.flask_labels['level'].pack()
        
        self.flask_labels['healing'] = tk.Label(
            flask_frame,
            text="50 Life",
            fg='#ffcc66',
            bg='black',
            font=('Arial', 9, 'bold')
        )
        self.flask_labels['healing'].pack()
        
        # Regex copy button
        self.flask_regex_btn = tk.Button(
            flask_frame,
            text="Regex",
            command=self.copy_flask_regex,
            bg='darkred',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief='raised',
            width=10,
            height=1
        )
        self.flask_regex_btn.pack(pady=(5, 0))
        
        # Update flask display
        self.update_flask_display()
    
    def update_flask_display(self):
        """Update flask display based on current player level."""
        if not self.player_level:
            # Show default level 1 flasks
            effective_level = 1
        else:
            effective_level = self.player_level
        
        # Get best life flask for current level
        life_flask = get_best_flask_for_level(effective_level)
        
        # Update life flask
        if life_flask:
            self.current_flask = life_flask  # Store current flask info
            self.update_flask_ui(life_flask)
    
    def update_flask_ui(self, flask_info):
        """Update the UI for the life flask."""
        try:
            # Get flask image
            flask_image = get_flask_image(flask_info)
            
            if not flask_image:
                # Use fallback image
                flask_image = create_fallback_flask_image(flask_info['name'])
            
            if flask_image:
                # Resize image to fit in flask panel (60x60)
                flask_image = flask_image.copy()
                flask_image.thumbnail((60, 60), Image.Resampling.LANCZOS)
                
                # Convert to tkinter format
                tk_image = ImageTk.PhotoImage(flask_image)
                
                # Update image
                self.flask_labels['image'].configure(image=tk_image)
                self.flask_labels['image'].image = tk_image  # Keep reference
            
            # Update text labels
            self.flask_labels['name'].configure(text=flask_info['name'])
            self.flask_labels['level'].configure(text=f"Req: Level {flask_info['requiredLevel']}")
            self.flask_labels['healing'].configure(text=f"{flask_info['recovery']} Life")
            
            print(f"Updated life flask: {flask_info['name']} (Level {flask_info['requiredLevel']})")
            
        except Exception as e:
            print(f"Error updating life flask UI: {e}")
    
    def copy_flask_regex(self):
        """Copy flask-specific regex to clipboard."""
        try:
            if not self.current_flask:
                print("No current flask available for regex")
                return
            
            # Extract the unique prefix from flask name
            # For "Lesser Life Flask" -> "Lesser"
            # For "Olroth's Resolve" -> "Olroth's"
            flask_name = self.current_flask['name']
            
            # Get the first word (or first two if it ends with 's)
            name_parts = flask_name.split()
            if len(name_parts) > 1 and name_parts[0].endswith("'s"):
                # Handle possessive names like "Olroth's"
                flask_prefix = name_parts[0]
            else:
                # Handle regular names like "Lesser", "Medium", etc.
                flask_prefix = name_parts[0]
            
            # Create regex pattern: "prefix|charges per second"
            regex_pattern = f'"{flask_prefix}|charges per second"'
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(regex_pattern)
            
            # Flash button to show it worked
            self.flask_regex_btn.configure(text="Copied!")
            self.root.after(1000, lambda: self.flask_regex_btn.configure(text="Regex"))
            
            print(f"Copied flask regex: {regex_pattern}")
            
        except Exception as e:
            print(f"Error copying flask regex: {e}")
    
    def setup_weapon_display(self):
        """Setup the weapon display panel (only if weapon type is set)."""
        weapon_type = self.settings.get("weapon_base_type")
        
        if not weapon_type:
            # No weapon type set, don't show weapon section
            return
        
        # Create weapon section below flask section
        separator = tk.Frame(self.flask_frame, height=1, bg='gray')
        separator.pack(fill=tk.X, pady=10)
        
        # Weapon panel title
        weapon_title = tk.Label(
            self.flask_frame,
            text="Weapon",
            fg='white',
            bg='black',
            font=('Arial', 12, 'bold')
        )
        weapon_title.pack(pady=(5, 10))
        
        # Weapon display frame
        self.weapon_frame_container = tk.Frame(self.flask_frame, bg='black')
        self.weapon_frame_container.pack(pady=5)
        
        # Weapon name
        self.weapon_labels['name'] = tk.Label(
            self.weapon_frame_container,
            text="Weapon",
            fg='#66ccff',
            bg='black',
            font=('Arial', 10),
            wraplength=110,
            justify=tk.CENTER
        )
        self.weapon_labels['name'].pack()
        
        # Weapon level requirement
        self.weapon_labels['level'] = tk.Label(
            self.weapon_frame_container,
            text="Req: Level 1",
            fg='gray',
            bg='black',
            font=('Arial', 9)
        )
        self.weapon_labels['level'].pack()
        
        # Weapon damage
        self.weapon_labels['damage'] = tk.Label(
            self.weapon_frame_container,
            text="Damage",
            fg='#ffcc66',
            bg='black',
            font=('Arial', 9, 'bold')
        )
        self.weapon_labels['damage'].pack()
        
        # Weapon stats
        self.weapon_labels['stats'] = tk.Label(
            self.weapon_frame_container,
            text="Stats",
            fg='#cccccc',
            bg='black',
            font=('Arial', 8),
            wraplength=110,
            justify=tk.CENTER
        )
        self.weapon_labels['stats'].pack()
        
        # Update weapon display
        self.update_weapon_display()
    
    def update_weapon_display(self):
        """Update weapon display based on current player level and weapon type."""
        weapon_type = self.settings.get("weapon_base_type")
        
        if not weapon_type or not self.weapon_frame_container:
            return
        
        if not self.player_level:
            effective_level = 1
        else:
            effective_level = self.player_level
        
        # Get best weapon for current level and type
        best_weapon = get_best_weapon_for_level(effective_level, weapon_type)
        
        if best_weapon:
            self.current_weapon = best_weapon
            self.update_weapon_ui(best_weapon)
    
    def update_weapon_ui(self, weapon_info):
        """Update the UI for the weapon."""
        try:
            # Update text labels
            self.weapon_labels['name'].configure(text=weapon_info['name'])
            self.weapon_labels['level'].configure(text=f"Req: Level {weapon_info['requiredLevel']}")
            self.weapon_labels['damage'].configure(text=format_weapon_damage(weapon_info))
            self.weapon_labels['stats'].configure(text=format_weapon_stats(weapon_info))
            
            print(f"Updated weapon: {weapon_info['name']} (Level {weapon_info['requiredLevel']})")
            
        except Exception as e:
            print(f"Error updating weapon UI: {e}")

    def find_zone_folder(self, zone_name):
        if not os.path.exists(self.maps_directory):
            return None
        
        # Search through all act folders
        for act_folder in os.listdir(self.maps_directory):
            act_path = os.path.join(self.maps_directory, act_folder)
            if not os.path.isdir(act_path):
                continue
                
            for zone_folder in os.listdir(act_path):
                zone_path = os.path.join(act_path, zone_folder)
                if not os.path.isdir(zone_path):
                    continue
                
                # Check if zone name matches folder name
                # Remove number prefix (e.g., "1_Clearfell" -> "Clearfell")
                folder_name = zone_folder
                if '_' in folder_name:
                    folder_name = folder_name.split('_', 1)[1]
                
                # Case-insensitive matching
                if (zone_name.lower() in folder_name.lower() or 
                    folder_name.lower() in zone_name.lower()):
                    return zone_path
        
        return None

    # Copy button functionality
    def add_copy_button(self):
        def copy_regex():
            regex_text = self.settings.get("regex", "")
            self.root.clipboard_clear()
            self.root.clipboard_append(regex_text)
            # Flash the button to show it worked
            self.copy_btn.configure(text="Copied!")
            self.root.after(1000, lambda: self.copy_btn.configure(text="Regex"))
        
        self.copy_btn = tk.Button(
            self.root, 
            text="Regex", 
            command=copy_regex, 
            bg='darkgray', 
            fg='white', 
            font=('Arial', 8),
            bd=1,
            relief='raised',
            width=6,
            height=1
        )
        self.copy_btn.place(relx=1.0, y=5, anchor='ne')
        
        # Prevent the copy button from interfering with window dragging
        self.copy_btn.bind('<Button-1>', lambda e: e.stopPropagation() if hasattr(e, 'stopPropagation') else None)
    
    # Resize grips functionality
    def add_resize_grips(self):
        grip_size = 15
        
        # Bottom-right corner grip (most common)
        self.resize_grip_se = tk.Label(self.root, bg='gray', cursor='bottom_right_corner')
        self.resize_grip_se.place(relx=1.0, rely=1.0, width=grip_size, height=grip_size, anchor='se')
        self.resize_grip_se.bind('<Button-1>', lambda e: self.start_resize(e, 'se'))
        self.resize_grip_se.bind('<B1-Motion>', self.on_resize)
        self.resize_grip_se.bind('<ButtonRelease-1>', self.stop_resize)
        
        # Right edge grip
        self.resize_grip_e = tk.Label(self.root, bg='gray', cursor='sb_h_double_arrow')
        self.resize_grip_e.place(relx=1.0, rely=0.5, width=5, height=50, anchor='e')
        self.resize_grip_e.bind('<Button-1>', lambda e: self.start_resize(e, 'e'))
        self.resize_grip_e.bind('<B1-Motion>', self.on_resize)
        self.resize_grip_e.bind('<ButtonRelease-1>', self.stop_resize)
        
        # Bottom edge grip
        self.resize_grip_s = tk.Label(self.root, bg='gray', cursor='sb_v_double_arrow')
        self.resize_grip_s.place(relx=0.5, rely=1.0, width=50, height=5, anchor='s')
        self.resize_grip_s.bind('<Button-1>', lambda e: self.start_resize(e, 's'))
        self.resize_grip_s.bind('<B1-Motion>', self.on_resize)
        self.resize_grip_s.bind('<ButtonRelease-1>', self.stop_resize)

    def start_resize(self, event, direction):
        self.resizing = True
        self.resize_direction = direction
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_width = self.root.winfo_width()
        self.start_height = self.root.winfo_height()
        self.start_window_x = self.root.winfo_x()
        self.start_window_y = self.root.winfo_y()

    def on_resize(self, event):
        if not self.resizing:
            return
        
        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y
        
        new_width = self.start_width
        new_height = self.start_height
        new_x = self.start_window_x
        new_y = self.start_window_y
        
        # Calculate new dimensions based on resize direction
        if 'e' in self.resize_direction:  # East (right)
            new_width = max(300, self.start_width + dx)
        if 's' in self.resize_direction:  # South (bottom)
            new_height = max(200, self.start_height + dy)
            
        # Update window geometry
        self.root.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")

    def stop_resize(self, event):
        self.resizing = False
        self.resize_direction = None

    # Window dragging functionality - optimized for smoothness
    def start_move(self, event):
        # Don't start move if we're on a resize grip or copy button
        if self.resizing:
            return
        
        # Check if click is on copy button area
        if event.x < 60 and event.y < 30:  # Copy button area
            return
            
        self.dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.start_window_x = self.root.winfo_x()
        self.start_window_y = self.root.winfo_y()

    def stop_move(self, event):
        self.dragging = False

    def on_move(self, event):
        if self.dragging and not self.resizing:
            # Calculate new position based on mouse movement from start
            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y
            
            new_x = self.start_window_x + dx
            new_y = self.start_window_y + dy
            
            # Update window position directly without geometry string parsing
            self.root.wm_geometry(f"+{new_x}+{new_y}")

    # System tray functionality
    def create_tray_icon(self):
        # Create a simple icon using PIL
        icon_image = Image.new('RGB', (64, 64), color='red')
        return icon_image

    def load_settings(self):
        # Default settings
        default_settings = {
            "regex": '"increased rar|move"',
            "player_level": None,
            "override_player_level": False,
            "weapon_base_type": None
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Ensure all default keys exist
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            else:
                # Create settings file with defaults
                self.save_settings(default_settings)
                return default_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return default_settings
            
    def save_settings(self, settings=None):
        if settings is None:
            settings = self.settings
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            print("Settings saved successfully")
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def open_settings(self, icon=None, item=None):
        # Don't open multiple windows
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.focus_force()
            return
            
        # Create settings window
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("450x300")
        self.settings_window.resizable(True, True)
        self.settings_window.minsize(400, 280)
        
        # Make settings window always on top and bring to front
        self.settings_window.attributes("-topmost", True)
        self.settings_window.lift()
        self.settings_window.focus_force()
        
        # Add content
        frame = ttk.Frame(self.settings_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Regex setting
        ttk.Label(frame, text="Regex filter:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        regex_var = tk.StringVar(value=self.settings.get("regex", ""))
        regex_entry = ttk.Entry(frame, textvariable=regex_var, width=40)
        regex_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5))
        
        ttk.Label(frame, text="Example: 'increased rar|move' matches lines with either phrase").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Player level override
        override_var = tk.BooleanVar(value=bool(self.settings.get("override_player_level", False)))
        ttk.Checkbutton(frame, text="Override player level", variable=override_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 5))
        
        ttk.Label(frame, text="Level:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        level_var = tk.StringVar(value=str(self.settings.get("player_level") or ""))
        ttk.Entry(frame, textvariable=level_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        # Weapon base type setting
        ttk.Label(frame, text="Weapon base type:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        weapon_var = tk.StringVar(value=self.settings.get("weapon_base_type") or "")
        weapon_options = ["", "Bow", "Crossbow", "Quarter Staff", "Two Hand Mace", "One Hand Mace", "Spear"]
        weapon_dropdown = ttk.Combobox(frame, textvariable=weapon_var, values=weapon_options, width=27, state="readonly")
        weapon_dropdown.grid(row=4, column=1, sticky=tk.W+tk.E, pady=(10, 5))
        
        ttk.Label(frame, text="Select weapon type for tracking (leave empty for none)").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Button frame
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, sticky=tk.E+tk.W, pady=(10, 0))
        
        # Save button
        def save_settings():
            self.settings["regex"] = regex_var.get()
            self.settings["override_player_level"] = bool(override_var.get())
            try:
                lvl = int(level_var.get()) if level_var.get().strip() != "" else None
            except ValueError:
                lvl = self.settings.get("player_level")
            self.settings["player_level"] = lvl
            self.settings["weapon_base_type"] = weapon_var.get().strip() if weapon_var.get().strip() else None
            # Mirror runtime
            self.override_player_level = self.settings["override_player_level"]
            self.player_level = self.settings.get("player_level")
            
            self.save_settings()
            
            # Refresh UI based on new settings
            self.update_flask_display()
            
            # If weapon type changed, need to rebuild weapon section
            old_weapon_type = self.settings.get("weapon_base_type", None) 
            new_weapon_type = weapon_var.get().strip() if weapon_var.get().strip() else None
            
            if old_weapon_type != new_weapon_type:
                # Clear existing weapon section if it exists
                if self.weapon_frame_container:
                    self.weapon_frame_container.destroy()
                    self.weapon_frame_container = None
                    self.weapon_labels = {}
                
                # If new type is selected, create new weapon section
                if new_weapon_type:
                    self.setup_weapon_display()
            else:
                # Just update current weapon display
                self.update_weapon_display()
            
            self.settings_window.destroy()
            
        save_btn = ttk.Button(button_frame, text="Save", command=save_settings)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.settings_window.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Configure grid column weights
        frame.grid_columnconfigure(1, weight=1)
        
    def setup_system_tray(self):
        def setup_tray():
            icon_image = self.create_tray_icon()
            
            menu = (
                item('Show/Hide', self.toggle_window),
                item('Settings', self.open_settings),
                item('Exit', self.quit_application)
            )
            
            self.tray_icon = pystray.Icon("PoE2 Maps", icon_image, menu=menu)
            self.tray_icon.run()
        
        # Run tray icon in separate thread
        tray_thread = threading.Thread(target=setup_tray, daemon=True)
        tray_thread.start()

    def toggle_window(self, icon=None, item=None):
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()

    def hide_window(self):
        self.root.withdraw()
        self.window_visible = False

    def show_window(self):
        self.root.deiconify()
        self.window_visible = True
        self.resize_window_to_content()

    def resize_window_to_content(self):
        # Update the window to get proper dimensions
        self.root.update_idletasks()
        
        # Get required size
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        
        # Set minimum and maximum sizes
        min_width = 300
        min_height = 200
        max_width = 1400
        max_height = 1000
        
        # Apply constraints
        width = max(min_width, min(width, max_width))
        height = max(min_height, min(height, max_height))
        
        # Get current position to maintain it
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        
        # Update geometry
        self.root.geometry(f"{width}x{height}+{current_x}+{current_y}")

    def quit_application(self, icon=None, item=None):
        print("Exiting application...")
        self.running = False
        
        # Properly stop the tray icon first
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception as e:
                print(f"Error stopping tray icon: {e}")
        
        # Destroy the main window
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            print(f"Error destroying window: {e}")
        
        # Force exit if needed
        import os
        import sys
        try:
            os._exit(0)
        except:
            sys.exit(0)

    def on_closing(self):
        self.quit_application()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("Keyboard interrupt received")
            self.quit_application()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.quit_application()

if __name__ == "__main__":
    try:
        app = PoEMapsViewer()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")
