import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from simulations.simulator import CombatSimulator
from simulations.loader import load_monsters

#1. LOAD the data from the JSON file
monsters_data = load_monsters()
#Find the Goblin definition
goblin_template = next(m for m in monsters_data if m['name'] == 'Goblin')

#2. PREPARE the data for the simulator.
#We need to add mutable state (like current_hp) to the immutable definition.
goblin = goblin_template.copy() #Create a copy to avoid altering the template
goblin['current_hit_points'] = goblin['hit_points'] #Add current HP

fighter = {
    "name": "Eldrin the Fighter",
    "armor_class": 18,
    "current_hit_points": 30
}

#3. USE the data
sim = CombatSimulator()
print("Initial HP:", fighter['current_hit_points'])

# FORCE A HIT FOR TESTING: Temporarily lower the fighter's AC to 0.
original_ac = fighter['armor_class']
fighter['armor_class'] = 0

result = sim.resolve_attack(goblin, "Scimitar", fighter)
print(result['message'])
print("New HP:", fighter['current_hit_points'])

# Restore the AC for any further tests

fighter['armor_class'] = original_ac
