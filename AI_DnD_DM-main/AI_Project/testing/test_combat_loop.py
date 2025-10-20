import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from simulations.simulator import CombatSimulator
from simulations.loader import load_monsters, load_characters

#1. LOAD the data from the JSON file
monsters_data = load_monsters()
players_data = load_characters()

#Find the Goblin definition
goblin_template = next(m for m in monsters_data if m['name'] == 'Goblin')

#2. PREPARE the data for the simulator.
#We need to add mutable state (like current_hp) to the immutable definition.
goblin = goblin_template.copy() #Create a copy to avoid altering the template
goblin['current_hit_points'] = goblin['hit_points'] #Add current HP

fighter = {
    "name": "Eldrin the Fighter",
    "armor_class": 18,
    "current_hit_points": 30,
    "hit_points": 30, # Added a max HP field for completeness
    "actions": [ # <- This is the crucial missing part!
        {
            "name": "Longsword",
            "type": "Melee Weapon Attack",
            "attack_bonus": 5, # Assuming +3 from Str, +2 from proficiency
            "damage_dice": "1d8",
            "damage_bonus": 3,
            "damage_type": "slashing"
        }
    ]
}

#3. USE the data
sim = CombatSimulator()
print("Initial HP:", fighter['current_hit_points'])

print("\n" + "="*50)
print("TESTING FULL COMBAT LOOP")
print("="*50)

# Reset the combatants to full health
goblin['current_hit_points'] = goblin['hit_points']
fighter['current_hit_points'] = 30

# Run the combat!

sim.run_simple_combat(goblin, fighter)
