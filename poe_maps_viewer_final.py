import dearpygui.dearpygui as dpg
import os
import json
import glob
import threading
import time
import re
import subprocess
import sys

class PoEMapsViewerFinal:
    def __init__(self):
        self.current_zone = ""
        self.current_level = 1
        self.player_level = None
        self.override_player_level = False
        self.settings = self.load_settings()
        self.image_registry = {}
        self.flask_image_registry = {}
        self.monitoring = False
        self.monitor_thread = None
        self.last_file_size = 0  # Use file size monitoring like original
        
        # Store current flask/weapon for regex generation
        self.current_flask = None
        self.current_weapon = None
        
        # Debouncing for resize events
        self.resize_timer = None
        
        # Initialize level fields from settings
        self.player_level = self.settings.get("player_level", None)
        self.override_player_level = bool(self.settings.get("override_player_level", False))
        
        # Initialize current_level from settings so UI shows correct data on startup
        self.current_level = self.settings.get("level", 1)
        
        print("Creating Dear PyGui context...")
        dpg.create_context()
        
        print("Loading flask images...")
        self.load_flask_images()
        
        print("Setting up theme...")
        self.setup_theme()
        
        print("Creating GUI...")
        self.create_gui()
        
        # Start monitoring by default if log path is available
        self.auto_start_monitoring()
        
        # Update UI with initial level from settings
        self.update_initial_display()
    
    def copy_to_clipboard_safe(self, text):
        """Safely copy text to clipboard using multiple fallback methods"""
        try:
            # Method 1: Try using Windows PowerShell (most reliable on Windows)
            if sys.platform == 'win32':
                try:
                    # Use PowerShell to set clipboard
                    cmd = ['powershell', '-command', f'Set-Clipboard -Value "{text}"']
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        print(f"Copied to clipboard via PowerShell: {text}")
                        return True
                except Exception as e:
                    print(f"PowerShell clipboard method failed: {e}")
            
            # Method 2: Try using clip.exe on Windows
            if sys.platform == 'win32':
                try:
                    # Use Windows clip.exe command
                    process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
                    process.communicate(input=text, timeout=5)
                    if process.returncode == 0:
                        print(f"Copied to clipboard via clip.exe: {text}")
                        return True
                except Exception as e:
                    print(f"clip.exe clipboard method failed: {e}")
            
            # Method 3: Try tkinter as last resort (but with better error handling)
            try:
                import tkinter as tk
                # Create a temporary, hidden tkinter root
                root = tk.Tk()
                root.withdraw()  # Hide the window immediately
                root.attributes('-alpha', 0)  # Make it fully transparent
                root.overrideredirect(True)  # Remove window decorations
                
                # Clear and set clipboard
                root.clipboard_clear()
                root.clipboard_append(text)
                root.update()  # Force update
                
                # Clean up immediately
                root.destroy()
                
                print(f"Copied to clipboard via tkinter: {text}")
                return True
            except Exception as e:
                print(f"Tkinter clipboard method failed: {e}")
            
            # If all methods failed
            print(f"All clipboard methods failed for: {text}")
            return False
            
        except Exception as e:
            print(f"Unexpected error in clipboard operation: {e}")
            return False

    def setup_theme(self):
        """Setup a premium dark theme"""
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                # Dark theme colors
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (26, 26, 26))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (36, 36, 36))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (60, 60, 60))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 80, 80))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 100, 100))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (240, 240, 240))

            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)

        dpg.bind_theme(global_theme)

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                # Set defaults for any missing keys
                defaults = {
                    "log_path": "",
                    "weapon_type": "", 
                    "level": 1,
                    "regex": '"increased rar|move"',
                    "player_level": None,
                    "override_player_level": False
                }
                for key, default in defaults.items():
                    if key not in settings:
                        settings[key] = default
                return settings
        except FileNotFoundError:
            return {"log_path": "", "weapon_type": "", "level": 1}

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)
                print("Settings saved successfully")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_flask_images(self):
        """Load flask images into texture registry"""
        flask_dir = "images/flasks"
        if os.path.exists(flask_dir):
            for flask_file in os.listdir(flask_dir):
                if flask_file.endswith(('.png', '.jpg', '.jpeg')):
                    flask_path = os.path.join(flask_dir, flask_file)
                    try:
                        # Load image with Dear PyGui's built-in loader
                        width, height, channels, data = dpg.load_image(flask_path)
                        if data is not None:
                            flask_name = flask_file.split('.')[0]
                            
                            with dpg.texture_registry():
                                texture_id = dpg.add_static_texture(width, height, data)
                                self.flask_image_registry[flask_name] = {
                                    'texture': texture_id,
                                    'width': width,
                                    'height': height
                                }
                            print(f"Loaded flask image: {flask_name}")
                    except Exception as e:
                        print(f"Error loading flask image {flask_file}: {e}")

    def load_map_image(self, image_path):
        """Load a map image and return texture info"""
        try:
            width, height, channels, data = dpg.load_image(image_path)
            if data is not None:
                with dpg.texture_registry():
                    texture_id = dpg.add_static_texture(width, height, data)
                    return {
                        'texture': texture_id,
                        'width': width,
                        'height': height,
                        'path': image_path
                    }
        except Exception as e:
            print(f"Error loading map image {image_path}: {e}")
        return None

    def create_gui(self):
        """Create the main GUI with single pane layout"""
        with dpg.window(label="PoE2 Maps Viewer", tag="main_window"):
            
            # Compact header with zone/level and General Regex button
            with dpg.group(horizontal=True):
                # Zone and level info (no labels)
                dpg.add_text("Unknown", tag="zone_text", color=(255, 215, 0))
                dpg.add_text("|", color=(100, 100, 100))
                dpg.add_text("Lv.1", tag="level_text", color=(0, 255, 100))
                
                # Push General Regex button to the right
                dpg.add_spacer(width=-1)  # Push to right
                dpg.add_button(label="General Regex", callback=self.copy_general_regex)
            
            dpg.add_separator()
            
            # Settings section - collapsed by default to save space
            with dpg.collapsing_header(label="Settings", default_open=False):
                with dpg.group(horizontal=True):
                    dpg.add_input_text(
                        label="PoE2 Log Path",
                        default_value=self.settings.get("log_path", ""),
                        width=300,
                        tag="log_path_input"
                    )
                    dpg.add_button(label="Browse", callback=self.browse_log_file)
                    dpg.add_button(label="Save Settings", callback=self.save_all_settings)
                
                with dpg.group(horizontal=True):
                    dpg.add_combo(
                        label="Weapon Type",
                        items=["Bow", "Crossbow", "Quarter Staff", "Spear", "One Hand Mace", "Two Hand Mace"],
                        default_value=self.settings.get("weapon_type", ""),
                        width=150,
                        tag="weapon_type_combo"
                    )
                    dpg.add_input_int(
                        label="Level",
                        default_value=self.settings.get("level", 1),
                        min_value=1,
                        max_value=100,
                        width=80,
                        tag="level_input",
                        callback=self.on_level_change
                    )
                    dpg.add_button(
                        label="Stop Monitoring",  # Default to showing Stop since we auto-start
                        callback=self.toggle_monitoring,
                        tag="monitor_button"
                    )
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Test with Clearfell", callback=self.test_clearfell)
                    dpg.add_button(label="Test with Grelwood", callback=self.test_grelwood)
                    dpg.add_button(label="Refresh", callback=self.refresh_display)
            
            dpg.add_separator()
            
            # Main content area - fully responsive layout
            with dpg.group(horizontal=True):
                
                # Left side - Flask and Weapon recommendations (narrower width)
                with dpg.child_window(width=200):
                        
                        # Flask section
                        dpg.add_text("Optimal Flask:", color=(200, 200, 200))
                        dpg.add_separator()
                        
                        with dpg.group(tag="flask_display_group"):
                            dpg.add_text("Select a zone to see flask", tag="flask_name_text")
                            dpg.add_text("", tag="flask_heal_text")
                            # Flask image will be added here dynamically
                        
                        # Flask regex button only (General Regex moved to header)
                        dpg.add_button(label="Flask Regex", callback=self.copy_flask_regex)
                        
                        dpg.add_spacer(height=20)
                        
                        # Weapon section
                        dpg.add_text("Optimal Weapon:", color=(200, 200, 200))
                        dpg.add_separator()
                        
                        with dpg.group(tag="weapon_display_group"):
                            dpg.add_text("Select a zone to see weapon", tag="weapon_name_text")
                            dpg.add_text("", tag="weapon_stats_text")
                
                # Right side - Map and Notes (responsive)
                with dpg.group():
                    # Map section - no header, maximum space
                    with dpg.group(tag="map_display_group"):
                        dpg.add_text("No zone selected", tag="map_placeholder")
                    
                    dpg.add_spacer(height=10)
                    
                    # Notes section - compact at bottom
                    with dpg.group(horizontal=True, tag="notes_display_group"):
                        dpg.add_text("Notes:", color=(255, 215, 0))
                        dpg.add_text("No notes available", tag="notes_display_text")

        dpg.set_primary_window("main_window", True)
        
        # Add minimal resize handler to update map sizes
        with dpg.item_handler_registry() as handler_registry:
            dpg.add_item_resize_handler(callback=self.on_resize)
        dpg.bind_item_handler_registry("main_window", handler_registry)

    def save_log_path(self):
        """Save the log path"""
        new_path = dpg.get_value("log_path_input")
        self.settings["log_path"] = new_path
        print(f"Saved log path: {new_path}")

    def test_clearfell(self):
        """Test with Clearfell data"""
        print("Testing with Clearfell")
        self.current_zone = "Clearfell"
        self.current_level = 3
        dpg.set_value("zone_text", self.current_zone)
        dpg.set_value("level_text", f"Lv.{self.current_level}")
        self.refresh_display()

    def test_grelwood(self):
        """Test with Grelwood data"""
        print("Testing with Grelwood")
        self.current_zone = "Grelwood"
        self.current_level = 5
        dpg.set_value("zone_text", self.current_zone)
        dpg.set_value("level_text", f"Lv.{self.current_level}")
        self.refresh_display()

    def find_zone_directory(self, zone_name):
        """Find the directory for a given zone name"""
        maps_dir = "maps"
        if not os.path.exists(maps_dir):
            return None
        
        for act_dir in os.listdir(maps_dir):
            act_path = os.path.join(maps_dir, act_dir)
            if os.path.isdir(act_path):
                for zone_dir in os.listdir(act_path):
                    zone_path = os.path.join(act_path, zone_dir)
                    if os.path.isdir(zone_path):
                        dir_zone_name = zone_dir.split('_', 1)[-1] if '_' in zone_dir else zone_dir
                        if dir_zone_name.lower() == zone_name.lower():
                            return zone_path
        return None

    def load_zone_notes(self, zone_name):
        """Load notes for a specific zone"""
        zone_dir = self.find_zone_directory(zone_name)
        if zone_dir:
            notes_path = os.path.join(zone_dir, "notes.txt")
            if os.path.exists(notes_path):
                try:
                    with open(notes_path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except Exception as e:
                    print(f"Error reading notes: {e}")
        return ""

    def get_zone_images(self, zone_name):
        """Get list of image files for a zone"""
        zone_dir = self.find_zone_directory(zone_name)
        if not zone_dir:
            return []
        
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(glob.glob(os.path.join(zone_dir, ext)))
        
        return image_files

    def clear_group_children(self, group_tag):
        """Clear all children from a group"""
        children = dpg.get_item_children(group_tag, slot=1) or []
        for child in children:
            if dpg.does_item_exist(child):
                dpg.delete_item(child)

    def update_flask_display(self):
        """Update flask display with current level"""
        try:
            from flask_utils import get_best_flask_for_level
            optimal_flask = get_best_flask_for_level(self.current_level)
            
            # Clear existing flask display
            self.clear_group_children("flask_display_group")
            
            if optimal_flask:
                # Store current flask for regex generation
                self.current_flask = optimal_flask
                
                flask_name = optimal_flask['name']
                flask_level = optimal_flask['requiredLevel']
                
                # Try to show flask image
                flask_key = flask_name.lower().replace(' ', '-')
                
                # Add new content to flask display
                with dpg.group(parent="flask_display_group"):
                    dpg.add_text(f"{flask_name}")
                    dpg.add_text(f"Required Level: {flask_level}")
                    
                    if flask_key in self.flask_image_registry:
                        flask_data = self.flask_image_registry[flask_key]
                        dpg.add_image(
                            flask_data['texture'],
                            width=min(flask_data['width'], 80),
                            height=min(flask_data['height'], 80)
                        )
                        print(f"Displayed flask image for: {flask_name}")
                    else:
                        dpg.add_text("(Image not available)", color=(150, 150, 150))
                        print(f"Flask image not found for: {flask_key}")
            else:
                with dpg.group(parent="flask_display_group"):
                    dpg.add_text("No flask available")
                    dpg.add_text(f"for level {self.current_level}")
        except Exception as e:
            print(f"Error loading flask: {e}")
            self.clear_group_children("flask_display_group")
            with dpg.group(parent="flask_display_group"):
                dpg.add_text("Flask data unavailable")

    def update_weapon_display(self):
        """Update weapon display with current level and weapon type"""
        # Clear existing weapon display
        self.clear_group_children("weapon_display_group")
        
        weapon_type = self.settings.get("weapon_type", "")
        
        if not weapon_type:
            # No weapon type selected
            with dpg.group(parent="weapon_display_group"):
                dpg.add_text("No weapon type selected")
                dpg.add_text("Select weapon type in settings")
            return
        
        try:
            # Import weapon utilities
            from weapon_utils import get_best_weapon_for_level, format_weapon_damage, format_weapon_stats
            optimal_weapon = get_best_weapon_for_level(self.current_level, weapon_type)
            
            with dpg.group(parent="weapon_display_group"):
                if optimal_weapon:
                    # Store current weapon for future use
                    self.current_weapon = optimal_weapon
                    
                    # Weapon name
                    dpg.add_text(f"{optimal_weapon['name']}", color=(102, 204, 255))
                    
                    # Required level
                    dpg.add_text(f"Req: Level {optimal_weapon['requiredLevel']}", color=(150, 150, 150))
                    
                    # Damage
                    damage_text = format_weapon_damage(optimal_weapon)
                    dpg.add_text(damage_text, color=(255, 204, 102))
                    
                    # Stats (crit, aps, range)
                    stats_text = format_weapon_stats(optimal_weapon)
                    dpg.add_text(stats_text, color=(204, 204, 204))
                    
                    print(f"Updated weapon: {optimal_weapon['name']} (Level {optimal_weapon['requiredLevel']})")
                else:
                    dpg.add_text(f"No {weapon_type} found")
                    dpg.add_text(f"for level {self.current_level}")
                    
        except ImportError:
            # Weapon utilities not available - show placeholder
            with dpg.group(parent="weapon_display_group"):
                dpg.add_text(f"Best {weapon_type}")
                dpg.add_text(f"for level {self.current_level}")
                dpg.add_text("(Weapon data coming soon)")
        except Exception as e:
            print(f"Error loading weapon: {e}")
            with dpg.group(parent="weapon_display_group"):
                dpg.add_text("Weapon data unavailable")

    def update_map_display(self):
        """Update map display with current zone images - keep previous map if no new maps found"""
        if not self.current_zone:
            return
            
        # Get zone images
        image_files = self.get_zone_images(self.current_zone)
        
        if image_files:
            print(f"Found {len(image_files)} map(s) for '{self.current_zone}' - updating display")
            
            # Clear existing map display only if we have new maps to show
            self.clear_group_children("map_display_group")
            
            with dpg.group(horizontal=True, parent="map_display_group"):
                # Display all maps side by side horizontally
                for i, image_file in enumerate(image_files):
                    map_data = self.load_map_image(image_file)
                    
                    if map_data:
                        # Calculate responsive image size
                        display_width, display_height = self.calculate_map_size(map_data, len(image_files))
                        
                        # Create a vertical group for each map (image + optional spacing)
                        with dpg.group():
                            dpg.add_image(
                                map_data['texture'],
                                width=display_width,
                                height=display_height
                            )
                        print(f"Displayed map image: {os.path.basename(image_file)} at {display_width}x{display_height}")
                        
                        # Add horizontal spacing between maps if there are multiple
                        if i < len(image_files) - 1:
                            dpg.add_spacer(width=10)
                    else:
                        dpg.add_text(f"Could not load map: {os.path.basename(image_file)}")
        else:
            print(f"No maps found for '{self.current_zone}' - keeping previous map")
            # Don't clear or change anything - keep previous map displayed

    def calculate_map_size(self, map_data, num_maps):
        """Calculate maximum map size using nearly 100% of available space"""
        try:
            # Get current viewport dimensions when needed
            viewport_width = dpg.get_viewport_client_width()
            viewport_height = dpg.get_viewport_client_height()
        except:
            # Reasonable defaults if viewport not ready
            viewport_width = 1200
            viewport_height = 800
        
        # Calculate maximum available space - ultra aggressive now
        # Account for: left panel (200px) + minimal padding (20px)
        available_width = max(400, viewport_width - 220)
        
        # Account for: compact header (~40px) + notes area (~40px) + title bar (~30px) + padding (20px)
        available_height = max(300, viewport_height - 130)
        
        # Use 98% of available space - maximum real estate!
        max_width = int(available_width * 0.98)
        max_height = int(available_height * 0.98)
        
        # Adjust for multiple maps side by side
        if num_maps > 1:
            max_width = (max_width - (num_maps - 1) * 15) // num_maps  # Small gaps
        
        # Scale to fit while maintaining aspect ratio
        width_scale = max_width / map_data['width']
        height_scale = max_height / map_data['height']
        scale = min(width_scale, height_scale)
        
        # Calculate final dimensions
        width = int(map_data['width'] * scale)
        height = int(map_data['height'] * scale)
        
        # Ensure reasonable minimums only
        width = max(200, width)
        height = max(150, height)
        
        print(f"Maximized map size: {width}x{height} (viewport: {viewport_width}x{viewport_height}, available: {available_width}x{available_height})")
        
        return width, height

    def update_notes_display(self):
        """Update notes display - compact single line format"""
        # Clear existing notes display
        self.clear_group_children("notes_display_group")
        
        notes = self.load_zone_notes(self.current_zone)
        with dpg.group(horizontal=True, parent="notes_display_group"):
            dpg.add_text("Notes:", color=(255, 215, 0))
            if notes:
                # Show notes in a single line, truncated if too long
                notes_text = notes.replace('\n', ' | ').strip()
                if len(notes_text) > 100:
                    notes_text = notes_text[:97] + "..."
                dpg.add_text(notes_text, tag="notes_display_text")
            else:
                dpg.add_text(f"No notes for {self.current_zone}", tag="notes_display_text")

    def update_initial_display(self):
        """Update the display with initial settings on startup"""
        try:
            # Update level display text to match current_level from settings
            dpg.set_value("level_text", f"Lv.{self.current_level}")
            
            # Update flask and weapon displays with initial level
            self.update_flask_display()
            self.update_weapon_display()
            
            print(f"Initial display updated with level {self.current_level} from settings")
        except Exception as e:
            print(f"Error updating initial display: {e}")
    
    def on_level_change(self):
        """Called when level input changes - update immediately"""
        try:
            new_level = dpg.get_value("level_input")
            self.current_level = new_level
            dpg.set_value("level_text", f"Lv.{new_level}")
            
            # Update displays that depend on level
            self.update_flask_display()
            self.update_weapon_display()
        except Exception as e:
            print(f"Error updating level: {e}")
    
    def refresh_display(self):
        """Refresh the entire display"""
        print(f"Refreshing display for zone: {self.current_zone}")
        
        if not self.current_zone:
            return
            
        # Update all sections
        self.update_flask_display()
        self.update_weapon_display() 
        self.update_map_display()
        self.update_notes_display()
    
    def on_resize(self):
        """Debounced resize handler - only update after resize stops"""
        if not self.current_zone:
            return
        
        # Cancel previous timer if it exists
        if self.resize_timer:
            self.resize_timer.cancel()
        
        # Set new timer to trigger after 200ms of no resize events
        self.resize_timer = threading.Timer(0.2, self.delayed_resize_update)
        self.resize_timer.start()
    
    def delayed_resize_update(self):
        """Actually update the map display after resize debouncing"""
        print("Window resize complete - updating map sizes")
        self.update_map_display()
        self.resize_timer = None

    def browse_log_file(self):
        """Browse for log file (placeholder - would need file dialog)"""
        print("Browse functionality would open a file dialog here")
        # Check original path first, then common location
        original_path = r"D:\Program Files (x86)\Grinding Gear Games\logs\Client.txt"
        common_path = os.path.expanduser("~\\Documents\\My Games\\Path of Exile 2\\Logs\\Client.txt")
        
        if os.path.exists(original_path):
            dpg.set_value("log_path_input", original_path)
            print(f"Found PoE2 log at original location: {original_path}")
        elif os.path.exists(common_path):
            dpg.set_value("log_path_input", common_path)
            print(f"Found PoE2 log at common location: {common_path}")
        else:
            print("PoE2 log location not found. Please set manually.")
    
    def save_all_settings(self):
        """Save all settings from UI"""
        self.settings["log_path"] = dpg.get_value("log_path_input")
        self.settings["weapon_type"] = dpg.get_value("weapon_type_combo")
        self.settings["level"] = dpg.get_value("level_input")
        self.save_settings()
        
        # Update current level from settings
        self.current_level = self.settings["level"]
        dpg.set_value("level_text", f"Lv.{self.current_level}")
        
        # Refresh display with new settings
        self.refresh_display()
    
    def init_file_monitoring(self, log_path):
        """Initialize file monitoring exactly like original"""
        if os.path.exists(log_path):
            self.last_file_size = os.path.getsize(log_path)
        else:
            self.last_file_size = 0
    
    def auto_start_monitoring(self):
        """Automatically start monitoring if log path is available and detect current zone/level"""
        log_path = self.settings.get("log_path", "")
        
        if log_path and os.path.exists(log_path):
            # Immediately check current zone and level from existing logs
            print("Detecting current zone and level from existing logs...")
            self.check_current_zone(log_path)
            self.check_player_level(log_path)
            
            # Start monitoring
            self.init_file_monitoring(log_path)
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_log, daemon=True)
            self.monitor_thread.start()
            print("Auto-started log monitoring")
        else:
            print("No valid log path in settings - monitoring not started")
            dpg.set_value("monitor_button", "Start Monitoring")
    
    def toggle_monitoring(self):
        """Toggle log file monitoring"""
        if not self.monitoring:
            log_path = dpg.get_value("log_path_input")
            if not log_path or not os.path.exists(log_path):
                print("Invalid log path - cannot start monitoring")
                return
            
            # Initialize file monitoring
            self.init_file_monitoring(log_path)
            
            # Immediately detect current zone/level before starting monitoring
            print("Detecting current zone and level...")
            self.check_current_zone(log_path)
            self.check_player_level(log_path)
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_log, daemon=True)
            self.monitor_thread.start()
            
            dpg.set_value("monitor_button", "Stop Monitoring")
            print("Started log monitoring")
        else:
            self.monitoring = False
            dpg.set_value("monitor_button", "Start Monitoring")
            print("Stopped log monitoring")
    
    def monitor_log(self):
        """Monitor the PoE2 log file - EXACT original implementation"""
        log_path = dpg.get_value("log_path_input")
        
        while self.monitoring:
            try:
                if os.path.exists(log_path):
                    current_size = os.path.getsize(log_path)
                    if current_size > self.last_file_size:
                        self.last_file_size = current_size
                        # Call zone and level checks
                        self.check_current_zone(log_path)
                        self.check_player_level(log_path)
                
                time.sleep(2)  # Check every 2 seconds like original
            except Exception as e:
                print(f"Error monitoring log file: {e}")
                time.sleep(5)  # Wait longer if there's an error
    
    def check_current_zone(self, log_path):
        """Check current zone - EXACT original implementation"""
        try:
            if not os.path.exists(log_path):
                return
            
            # Read the last 50 lines to find the most recent zone
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                dpg.set_value("zone_text", self.current_zone)
                self.refresh_display()
                print(f"Zone changed to: {current_zone}")
                
        except Exception as e:
            print(f"Error checking zone: {e}")
    
    def check_player_level(self, log_path):
        """Check player level - EXACT original implementation"""
        try:
            if not os.path.exists(log_path):
                return
            
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Search the last 200 lines for a level up message
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
                    self.current_level = found_level
                    dpg.set_value("level_text", f"Lv.{self.current_level}")
                    dpg.set_value("level_input", self.current_level)
                    self.refresh_display()
        except Exception as e:
            print(f"Error checking player level: {e}")
    
    def copy_flask_regex(self):
        """Copy flask-specific regex to clipboard"""
        try:
            if not self.current_flask:
                print("No current flask available for regex")
                return
            
            # Extract the unique prefix from flask name
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
            
            # Use safe clipboard copy method
            if self.copy_to_clipboard_safe(regex_pattern):
                print(f"Successfully copied flask regex: {regex_pattern}")
            else:
                print(f"Failed to copy flask regex: {regex_pattern}")
            
        except Exception as e:
            print(f"Error copying flask regex: {e}")
    
    def copy_general_regex(self):
        """Copy general regex from settings"""
        try:
            regex_text = self.settings.get("regex", '"increased rar|move"')
            
            # Use safe clipboard copy method
            if self.copy_to_clipboard_safe(regex_text):
                print(f"Successfully copied general regex: {regex_text}")
            else:
                print(f"Failed to copy general regex: {regex_text}")
            
        except Exception as e:
            print(f"Error copying general regex: {e}")

    def run(self):
        """Run the application"""
        print("Creating viewport...")
        dpg.create_viewport(
            title="PoE2 Maps Viewer",
            width=1200,
            height=800,
            min_width=1000,
            min_height=600
        )
        
        print("Setting up Dear PyGui...")
        dpg.setup_dearpygui()
        
        print("Showing viewport...")
        dpg.show_viewport()
        
        print("Starting Dear PyGui...")
        dpg.start_dearpygui()
        
        print("Cleaning up...")
        dpg.destroy_context()
        print("Done!")

def main():
    print("Starting PoE Maps Viewer - Final Edition...")
    app = PoEMapsViewerFinal()
    app.run()

if __name__ == "__main__":
    main()
