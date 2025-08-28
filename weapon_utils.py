import json
import os
from path_utils import get_data_file_path

def load_weapon_data():
    """Load weapon data from JSON file."""
    weapon_file = get_data_file_path('weapons.json')
    try:
        with open(weapon_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading weapon data from {weapon_file}: {e}")
        return {"bows": [], "crossbows": [], "quarterstaves": [], "spears": [], "oneHandMaces": [], "twoHandMaces": []}

def get_weapon_type_key(weapon_type):
    """Convert weapon type display name to JSON key."""
    type_mapping = {
        "Bow": "bows",
        "Crossbow": "crossbows", 
        "Quarter Staff": "quarterstaves",
        "Quarterstaff": "quarterstaves",
        "Spear": "spears",
        "One Hand Mace": "oneHandMaces",
        "Two Hand Mace": "twoHandMaces"
    }
    return type_mapping.get(weapon_type)

def get_best_weapon_for_level(player_level, weapon_type):
    """Get the best weapon available for the given player level and weapon type."""
    if player_level is None or not weapon_type:
        return None
    
    weapon_data = load_weapon_data()
    weapon_key = get_weapon_type_key(weapon_type)
    
    if not weapon_key or weapon_key not in weapon_data:
        return None
    
    weapons = weapon_data[weapon_key]
    
    # Find the best weapon that the player can use
    available_weapons = [w for w in weapons if w["requiredLevel"] <= player_level]
    
    if not available_weapons:
        return None
    
    # Return the weapon with the highest required level (best weapon available)
    return max(available_weapons, key=lambda x: x["requiredLevel"])

def format_weapon_damage(weapon_info):
    """Format weapon damage for display."""
    if "physicalDamage" in weapon_info:
        return f"{weapon_info['physicalDamage']} Phys"
    elif "lightningDamage" in weapon_info:
        return f"{weapon_info['lightningDamage']} Lightning"
    elif "chaosDamage" in weapon_info:
        return f"{weapon_info['chaosDamage']} Chaos"
    elif "coldDamage" in weapon_info:
        return f"{weapon_info['coldDamage']} Cold"
    elif "fireDamage" in weapon_info:
        return f"{weapon_info['fireDamage']} Fire"
    else:
        return "Unknown Damage"

def format_weapon_stats(weapon_info):
    """Format weapon stats for display."""
    stats = []
    stats.append(f"Crit: {weapon_info['criticalHitChance']}%")
    stats.append(f"APS: {weapon_info['attacksPerSecond']}")
    if "weaponRange" in weapon_info:
        stats.append(f"Range: {weapon_info['weaponRange']}")
    return " | ".join(stats)
