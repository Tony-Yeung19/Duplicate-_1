import json
import os
import sys
from ai_dungeon_master import AIDungeonMaster
from simulations.dice import roll_dice
from simulations.loader import load_characters, load_monsters, load_equipment, load_weapons, load_spells, load_rules
from simulations.simulator import CombatSimulator

# Add the player directory to path to import character_creation
player_dir = os.path.join(os.path.dirname(__file__), 'player')
sys.path.insert(0, player_dir)

from character_creation import create_character, calculate_modifier

class DnDGameEngine:
    def __init__(self, ai_model_path):
        self.ai_dm = AIDungeonMaster(ai_model_path)
        
        # Load all your game data
        self.classes_data = load_characters()
        self.monsters_data = load_monsters() 
        self.equipment_data = load_equipment()
        self.weapons_data = load_weapons()
        self.spells_data = load_spells()
        self.rules_data = load_rules()
        
        # Initialize combat simulator
        self.combat_simulator = CombatSimulator()
        
        # Game state
        self.game_state = {
            'characters': [],
            'monsters': [],
            'environment': 'Ancient Ruins',
            'current_turn': None,
            'combat_active': False,
            'round': 0,
            'initiative_order': []
        }
    
    def create_new_character(self):
        """Use your character_creation.py to create a new character"""
        print("\n" + "="*50)
        print("🎭 CHARACTER CREATION")
        print("="*50)
        
        # Call your existing character creation function
        character = create_character()
        
        # Add the character to the game state
        self.game_state['characters'].append(character)
        return character
    
    def load_existing_character(self):
        """Load an existing character from player_data"""
        player_data_dir = os.path.join('player', 'player_data')
        if not os.path.exists(player_data_dir):
            print("No existing characters found.")
            return None
        
        character_files = [f for f in os.listdir(player_data_dir) if f.endswith('.json')]
        if not character_files:
            print("No existing characters found.")
            return None
        
        print("\n📂 Existing characters:")
        for i, file in enumerate(character_files, 1):
            character_name = file.replace('.json', '')
            print(f"  {i}. {character_name}")
        
        print(f"  {len(character_files) + 1}. Create New Character")
        
        choice = input(f"\nChoose character (1-{len(character_files) + 1}): ").strip()
        
        try:
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(character_files):
                    character_file = character_files[choice_num - 1]
                    filepath = os.path.join(player_data_dir, character_file)
                    
                    with open(filepath, 'r') as f:
                        character = json.load(f)
                    
                    self.game_state['characters'].append(character)
                    print(f"✅ Loaded character: {character['name']}")
                    return character
                elif choice_num == len(character_files) + 1:
                    return self.create_new_character()
        except Exception as e:
            print(f"Error loading character: {e}")
        
        return None
    
    def setup_party(self):
        """Set up the player's party with character creation"""
        print("🎮 SETTING UP YOUR ADVENTURING PARTY")
        print("="*50)
        
        party_size = int(input("How many characters in your party? (1-4): ").strip() or "1")
        party_size = max(1, min(4, party_size))  # Clamp between 1-4
        
        for i in range(party_size):
            print(f"\n--- Character {i+1}/{party_size} ---")
            print("1. Create New Character")
            print("2. Load Existing Character")
            
            choice = input("Choose option (1-2): ").strip()
            
            if choice == "1":
                self.create_new_character()
            elif choice == "2":
                character = self.load_existing_character()
                if not character:
                    print("Creating new character instead...")
                    self.create_new_character()
            else:
                print("Creating new character...")
                self.create_new_character()
        
        print(f"\n✅ Party assembled: {', '.join([c['name'] for c in self.game_state['characters']])}")
    
    def choose_monsters(self):
        """Let the player/DM choose monsters for combat"""
        print("\n🐉 CHOOSE YOUR OPPONENTS")
        print("="*50)
        
        available_monsters = [m['name'] for m in self.monsters_data]
        print("Available monsters:", ", ".join(available_monsters))
        
        monster_choices = []
        while True:
            monster = input("Enter monster name (or 'done' to finish): ").strip()
            if monster.lower() == 'done':
                break
            
            if monster in available_monsters:
                monster_choices.append(monster)
                print(f"Added {monster}")
            else:
                print(f"Monster '{monster}' not found. Available: {', '.join(available_monsters)}")
        
        # If no monsters chosen, use some defaults based on party level
        if not monster_choices:
            print("Using default monsters...")
            monster_choices = ["Goblin", "Orc"]
        
        return monster_choices
    
    def start_game_sequence(self):
        """Complete game setup sequence"""
        print("🎲 D&D AI DUNGEON MASTER - NEW GAME")
        print("="*60)
        
        # Step 1: Party Setup
        self.setup_party()
        
        # Step 2: Choose Monsters
        monster_choices = self.choose_monsters()
        
        # Step 3: Start Combat
        print(f"\n⚔️ INITIATING COMBAT SEQUENCE")
        print("="*50)
        
        combat_result = self.start_combat(monster_choices)
        print(combat_result)
        
        # Step 4: Begin Game Loop
        print("\n🎯 COMBAT BEGINS!")
        print("Type actions like: 'I attack the goblin with my sword!', 'I cast Magic Missile!', 'I use Second Wind'")
        print("Type 'quit' to end the game\n")
    
    def start_combat(self, monster_names):
        """Start combat with specified monsters"""
        selected_monsters = []
        for name in monster_names:
            monster = next((m for m in self.monsters_data if m['name'].lower() == name.lower()), None)
            if monster:
                # Create a combat-ready monster copy
                combat_monster = monster.copy()
                combat_monster['current_hp'] = combat_monster.get('hp', 10)
                selected_monsters.append(combat_monster)
        
        self.game_state['monsters'] = selected_monsters
        self.game_state['combat_active'] = True
        self.game_state['round'] = 1
        
        # Set up initiative using your simulator
        all_combatants = self.game_state['characters'] + self.game_state['monsters']
        self.game_state['initiative_order'] = self.combat_simulator.roll_initiative(all_combatants)
        self.game_state['current_turn'] = self.game_state['initiative_order'][0] if self.game_state['initiative_order'] else None
        
        # Create combat introduction
        monster_list = ', '.join([m['name'] for m in self.game_state['monsters']])
        hero_list = ', '.join([c['name'] for c in self.game_state['characters']])
        
        intro = f"COMBAT STARTED!\n"
        intro += f"Heroes: {hero_list}\n"
        intro += f"Monsters: {monster_list}\n"
        intro += f"Initiative Order: {', '.join(self.game_state['initiative_order'])}\n"
        intro += f"First Turn: {self.game_state['current_turn']}"
        
        return intro

    # ... (keep all the other methods from the previous version: process_player_action, execute_game_command, resolve_attack, etc.)
    def process_player_action(self, player_name, action_text):
        """Process player action through AI DM and game mechanics"""
        # Update current turn
        self.game_state['current_turn'] = player_name
        
        # Get AI DM response
        dm_response = self.ai_dm.generate_response(self.game_state, action_text)
        
        # Execute any system commands
        command_results = []
        for command in dm_response['commands']:
            result = self.execute_game_command(command, player_name)
            command_results.append(result)
        
        # Update game state based on commands
        self.update_game_state()
        
        # Advance turn if in combat
        if self.game_state['combat_active']:
            self.advance_turn()
        
        return {
            'player': player_name,
            'action': action_text,
            'dm_narration': dm_response['narration'],
            'system_commands': dm_response['commands'],
            'command_results': command_results,
            'updated_state': self.get_visible_game_state()
        }

    def execute_game_command(self, command, player_name):
        """Execute game commands using your existing mechanics"""
        try:
            command_lower = command.lower()
            
            if command_lower.startswith('!attack'):
                return self.resolve_attack(command, player_name)
            elif command_lower.startswith('!cast'):
                return self.resolve_spell(command, player_name)  
            elif command_lower.startswith('!roll'):
                return self.resolve_dice_roll(command)
            elif command_lower.startswith('!check'):
                return self.resolve_skill_check(command, player_name)
            elif command_lower.startswith('!save'):
                return self.resolve_saving_throw(command, player_name)
            elif command_lower.startswith('!init'):
                return self.handle_initiative(command)
            elif command_lower.startswith('!use'):
                return self.use_ability(command, player_name)
            elif command_lower.startswith('!move'):
                return self.handle_movement(command, player_name)
            else:
                return f"Executed: {command}"
                
        except Exception as e:
            return f"Command failed: {e}"

    def resolve_attack(self, command, attacker_name):
        """Resolve attack using your CombatSimulator"""
        # Parse command: !attack weapon -t target
        parts = command.split()
        weapon_name = parts[1] if len(parts) > 1 else "Unarmed"
        target_name = None
        
        # Find target
        if '-t' in parts:
            target_index = parts.index('-t') + 1
            if target_index < len(parts):
                target_name = parts[target_index]
        
        # Find combatants
        attacker = next((c for c in self.game_state['characters'] if c['name'] == attacker_name), None)
        target = next((m for m in self.game_state['monsters'] if m['name'] == target_name), 
                     next((c for c in self.game_state['characters'] if c['name'] == target_name), None))
        
        if not attacker or not target:
            return f"Could not find attacker or target"
        
        # Use your CombatSimulator to resolve attack
        try:
            # Find the weapon in attacker's equipment
            weapon = None
            if 'equipment' in attacker:
                for item in attacker['equipment']:
                    if item.lower() == weapon_name.lower():
                        # Find weapon details
                        weapon = next((w for w in self.weapons_data['weapons'] if w['name'].lower() == weapon_name.lower()), None)
                        break
            
            if not weapon:
                weapon = {"name": "Unarmed", "damage": "1d4", "damage_type": "Bludgeoning"}
            
            # Use your simulator's resolve_attack method
            result = self.combat_simulator.resolve_attack(attacker, target, weapon)
            return result
            
        except Exception as e:
            # Fallback to simple resolution
            attack_roll = roll_dice("1d20")
            damage_roll = roll_dice(weapon.get('damage', '1d4'))
            
            # Simple hit calculation (target AC 12 as default)
            target_ac = target.get('armor_class', 12)
            if attack_roll >= target_ac:
                target['current_hp'] = max(0, target.get('current_hp', target.get('hp', 10)) - damage_roll)
                result = f"{attacker_name} hits {target_name} with {weapon_name} for {damage_roll} damage!"
                if target['current_hp'] <= 0:
                    result += f" {target_name} is defeated!"
            else:
                result = f"{attacker_name} misses {target_name} with {weapon_name}!"
            
            return result

    def resolve_spell(self, command, caster_name):
        """Resolve spell casting using your spells data"""
        parts = command.split()
        spell_name = ' '.join(parts[1:])  # Handle multi-word spell names
        
        # Remove target if present
        if '-t' in spell_name:
            spell_name = spell_name.split('-t')[0].strip()
        
        # Find spell in your spells data
        spell = next((s for s in self.spells_data if s['name'].lower() == spell_name.lower()), None)
        
        if not spell:
            return f"Spell '{spell_name}' not found."
        
        caster = next((c for c in self.game_state['characters'] if c['name'] == caster_name), None)
        if not caster:
            return f"Caster {caster_name} not found."
        
        # Check if caster has spell
        if 'spells' in caster and spell_name not in caster['spells']:
            return f"{caster_name} doesn't know {spell_name}."
        
        # Simple spell resolution
        if 'damage' in spell:
            damage = roll_dice(spell['damage'])
            return f"{caster_name} casts {spell_name} for {damage} {spell.get('damage_type', '')} damage!"
        else:
            return f"{caster_name} casts {spell_name}! {spell.get('description', '')[:100]}..."

    def resolve_dice_roll(self, command):
        """Resolve dice rolls using your dice system"""
        roll_text = command.replace('!roll', '').strip()
        try:
            result = roll_dice(roll_text)
            return f"Rolled {roll_text} = {result}"
        except Exception as e:
            return f"Invalid dice notation: {roll_text}"

    def resolve_skill_check(self, command, player_name):
        """Resolve skill checks using your rules"""
        skill = command.replace('!check', '').strip().title()
        roll = roll_dice("1d20")
        
        # Get player bonus if available
        player = next((c for c in self.game_state['characters'] if c['name'] == player_name), None)
        bonus = 0
        
        if player and 'skills' in player and skill in player['skills']:
            bonus = player['proficiency_bonus']  # Simplified
        
        total = roll + bonus
        return f"{player_name} makes a {skill} check: {roll} + {bonus} = {total}"

    def resolve_saving_throw(self, command, player_name):
        """Resolve saving throws"""
        ability = command.replace('!save', '').strip().lower()
        roll = roll_dice("1d20")
        
        player = next((c for c in self.game_state['characters'] if c['name'] == player_name), None)
        bonus = 0
        
        if player and 'stats' in player:
            ability_score = player['stats'].get(ability, 10)
            bonus = (ability_score - 10) // 2
        
        total = roll + bonus
        return f"{player_name} makes a {ability} save: {roll} + {bonus} = {total}"

    def handle_initiative(self, command):
        """Handle initiative commands"""
        if 'next' in command.lower():
            return self.advance_turn()
        elif 'add' in command.lower():
            # Add creature to initiative
            return "Initiative updated"
        else:
            return f"Current initiative: {', '.join(self.game_state['initiative_order'])}"

    def use_ability(self, command, player_name):
        """Use class ability"""
        ability = command.replace('!use', '').strip()
        return f"{player_name} uses {ability}!"

    def handle_movement(self, command, player_name):
        """Handle movement"""
        movement = command.replace('!move', '').strip()
        return f"{player_name} moves {movement}"

    def advance_turn(self):
        """Advance to next turn in initiative order"""
        if not self.game_state['initiative_order']:
            return "No initiative order set"
        
        current_index = self.game_state['initiative_order'].index(self.game_state['current_turn'])
        next_index = (current_index + 1) % len(self.game_state['initiative_order'])
        self.game_state['current_turn'] = self.game_state['initiative_order'][next_index]
        
        return f"Turn advanced to: {self.game_state['current_turn']}"

    def update_game_state(self):
        """Update game state after actions"""
        # Remove defeated monsters
        self.game_state['monsters'] = [m for m in self.game_state['monsters'] if m.get('current_hp', 1) > 0]
        
        # Remove defeated characters (for PvP scenarios)
        self.game_state['characters'] = [c for c in self.game_state['characters'] if c.get('hit_points', 1) > 0]
        
        # Update initiative order
        self.game_state['initiative_order'] = [
            name for name in self.game_state['initiative_order']
            if any(c['name'] == name for c in self.game_state['characters']) or 
               any(m['name'] == name for m in self.game_state['monsters'])
        ]
        
        # Check combat end
        if not self.game_state['monsters'] and self.game_state['combat_active']:
            self.game_state['combat_active'] = False
            self.game_state['round'] = 0
            self.game_state['initiative_order'] = []

    def get_visible_game_state(self):
        """Get game state visible to players"""
        return {
            'characters': [
                {
                    'name': c['name'],
                    'class': c.get('class', 'Unknown'),
                    'hit_points': c.get('hit_points', '?'),
                    'max_hit_points': c.get('max_hit_points', '?'),
                    'armor_class': c.get('armor_class', '?')
                } for c in self.game_state['characters']
            ],
            'monsters': [
                {
                    'name': m['name'],
                    'hp': m.get('current_hp', m.get('hp', '?')),
                    'max_hp': m.get('hp', '?'),
                    'armor_class': m.get('armor_class', '?')
                } for m in self.game_state['monsters']
            ],
            'environment': self.game_state['environment'],
            'combat_active': self.game_state['combat_active'],
            'current_turn': self.game_state['current_turn'],
            'round': self.game_state['round'] if self.game_state['combat_active'] else None
        }