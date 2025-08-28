import json
import os
from PIL import Image

def load_flask_data():
    """Load flask data from JSON file."""
    flask_file = os.path.join(os.path.dirname(__file__), 'public', 'data', 'flasks.json')
    try:
        with open(flask_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading flask data: {e}")
        return {"lifeFlasks": [], "uniqueFlasks": []}

def get_best_flask_for_level(player_level):
    """Get the best life flask available for the given player level."""
    if player_level is None:
        return None
    
    flask_data = load_flask_data()
    
    # Combine regular life flasks and unique life flasks
    all_flasks = flask_data.get("lifeFlasks", []) + [f for f in flask_data.get("uniqueFlasks", []) if "life" in f.get("type", "").lower()]
    
    # Find the best flask that the player can use
    available_flasks = [f for f in all_flasks if f["requiredLevel"] <= player_level]
    
    if not available_flasks:
        return None
    
    # Return the flask with the highest required level (best flask available)
    return max(available_flasks, key=lambda x: x["requiredLevel"])

def get_flask_image(flask_info):
    """Get PIL Image for the given flask from local file."""
    if not flask_info:
        return None
    
    try:
        # Get image path relative to project root
        image_path = os.path.join(os.path.dirname(__file__), flask_info["imageUrl"])
        
        if os.path.exists(image_path):
            return Image.open(image_path)
        else:
            print(f"Flask image not found: {image_path}")
            return None
    except Exception as e:
        print(f"Error loading flask image: {e}")
        return None

def create_fallback_flask_image(flask_name):
    """Create a simple fallback life flask image if local file not found."""
    try:
        # Simple red rectangle as fallback for life flask
        image = Image.new('RGB', (64, 64), color="#ff4444")
        return image
    except Exception as e:
        print(f"Error creating fallback image: {e}")
        return None
