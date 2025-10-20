# simulations/loader.py
import json
import os

def get_data_path(data_dir='data'):
    """Get the correct path to data directory regardless of where script is run from"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  #Go up one level from simulations/
    data_path = os.path.join(project_root, data_dir)
    return data_path

def load_actions(data_dir='data'):
    """Loads actions data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'actions.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of actions dictionaries

def load_characters(data_dir='data'):
    """Loads character data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'characters.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of character dictionaries

def load_dice_mechanics(data_dir='data'):
    """Loads dice mechanics data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'dice_mechanics.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of dice mechanics dictionaries

def load_equipment(data_dir='data'):
    """Loads equipment data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'equipment.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of equipment dictionaries

def load_monsters(data_dir='data'):
    """Loads monster data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'monsters.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of monster dictionaries

def load_rules(data_dir='data'):
    """Loads ruleset data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'rules.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of ruleset dictionaries

def load_spells(data_dir='data'):
    """Loads spells data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'spells.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of spells dictionaries

def load_weapons(data_dir='data'):
    """Loads weapons data from the JSON file."""
    base_path = get_data_path(data_dir)
    filepath = os.path.join(base_path, 'weapons.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data #Returns the list of weapons dictionaries
