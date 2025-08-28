import os
import sys

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # We're running in development mode
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

def get_data_file_path(filename):
    """Get path to data file in data directory"""
    return get_resource_path(os.path.join('data', filename))

def get_image_file_path(relative_image_path):
    """Get path to image file"""
    return get_resource_path(relative_image_path)
