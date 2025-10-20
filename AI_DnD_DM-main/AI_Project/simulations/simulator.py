from .dice import roll_dice  #Import the dice function to be used

class CombatSimulator:
    """
    A core rules engine for handling D&D 5e combat.
    """
    def __init__(self):
        self.combat_log = []
        print("CombatSimulator initialized!")

    def resolve_attack(self, attacker, attack_name, target):
        """
        Enhanced attack resolution with critical hits, damage types, and more.
        """
        # Find the attack data
        attack_data = None
        for action in attacker.get('actions', []):
            if action['name'] == attack_name:
                attack_data = action
                break
        
        if not attack_data:
            return {
                "hit": False,
                "damage": 0,
                "message": f"{attacker['name']} doesn't know how to use {attack_name}!"
            }
        
        #Roll attack with potential advantage/disadvantage
        attack_roll = roll_dice('1d20')
        is_critical = (attack_roll == 20)
        
        #Add attack bonus
        attack_total = attack_roll + attack_data['attack_bonus']
        
        #Check if hit (critical hits always hit)
        if is_critical or attack_total >= target['armor_class']:
            #Calculate damage
            if is_critical:
                #or critical hits, roll damage dice twice
                base_damage = roll_dice(attack_data['damage_dice']) + roll_dice(attack_data['damage_dice'])
                damage_dealt = base_damage + attack_data.get('damage_bonus', 0)
                message = f"CRITICAL HIT! {attacker['name']} hits {target['name']} with {attack_name} for {damage_dealt} {attack_data.get('damage_type', '')} damage!"
            else:
                damage_dealt = roll_dice(attack_data['damage_dice']) + attack_data.get('damage_bonus', 0)
                message = f"{attacker['name']} hits {target['name']} with {attack_name} for {damage_dealt} {attack_data.get('damage_type', '')} damage!"
            
            #Apply damage resistance/vulnerability (simplified)
            damage_dealt = self.apply_damage_modifiers(damage_dealt, attack_data.get('damage_type', ''), target)
            
            #Update target HP
            target['current_hit_points'] = max(0, target['current_hit_points'] - damage_dealt)
            
            return {
                "hit": True,
                "critical": is_critical,
                "damage": damage_dealt,
                "message": message,
                "target_hp": target['current_hit_points']
            }
        else:
            return {
                "hit": False,
                "damage": 0,
                "message": f"{attacker['name']} misses {target['name']} with {attack_name}!"
            }

    def apply_damage_modifiers(self, damage, damage_type, target):
        """Apply damage resistance and vulnerability."""
        #This is a simplified version - you'd expand this based on monster immunities
        if hasattr(target, 'damage_resistances') and damage_type in target.damage_resistances:
            damage = damage // 2  #Resistance halves damage
        if hasattr(target, 'damage_vulnerabilities') and damage_type in target.damage_vulnerabilities:
            damage = damage * 2  #Vulnerability doubles damage
        return damage
    
    def roll_initiative(self, combatants):
        """Roll initiative for all combatants and sort them in order."""
        initiatives = {}
        for combatant in combatants:
            initiative_roll = roll_dice('1d20') + combatant.get('initiative_bonus', 0)
            initiatives[combatant['name']] = initiative_roll
        
        #Sort by initiative (highest first)
        self.initiative_order = sorted(combatants, 
                                     key=lambda x: initiatives[x['name']], 
                                     reverse=True)
        return self.initiative_order
    
    def run_combat_round(self, combatants):
        """Run a single round of combat."""
        self.round_number += 1
        print(f"\n=== Round {self.round_number} ===")
        
        for combatant in self.initiative_order:
            if combatant['current_hit_points'] <= 0:
                continue  # Skip defeated combatants
            
            #AI decision making for monsters
            if combatant.get('type') == 'monster':
                self.ai_take_turn(combatant, combatants)
            else:
                #For players, you'd implement player input
                self.player_take_turn(combatant, combatants)
            
            #Check if combat should end
            if self.is_combat_over(combatants):
                break
    
    def ai_take_turn(self, monster, combatants):
        """Simple AI for monster decision making."""
        #Find all player targets
        players = [c for c in combatants if c.get('type') != 'monster' and c['current_hit_points'] > 0]
        
        if not players:
            return  # No valid targets
        
        #Simple strategy: attack the first available player with first available attack
        target = players[0]
        attack = monster['actions'][0]['name']  # Use first attack
        
        result = self.resolve_attack(monster, attack, target)
        print(result['message'])
    
    def player_take_turn(self, player, combatants):
        """Handle player's turn (simplified for now)."""
        #Find all monster targets
        monsters = [c for c in combatants if c.get('type') == 'monster' and c['current_hit_points'] > 0]
        
        if not monsters:
            return  # No valid targets
        
        #For now, just attack the first monster with the first attack
        target = monsters[0]
        attack = player['actions'][0]['name']
        
        result = self.resolve_attack(player, attack, target)
        print(result['message'])
    
    def is_combat_over(self, combatants):
        """Check if combat should end (all monsters or all players defeated)."""
        players_alive = any(c for c in combatants if c.get('type') != 'monster' and c['current_hit_points'] > 0)
        monsters_alive = any(c for c in combatants if c.get('type') == 'monster' and c['current_hit_points'] > 0)
        
        return not players_alive or not monsters_alive
    
    def run_full_combat(self, players, monsters):
        """Run a complete combat encounter."""
        all_combatants = players + monsters
        self.roll_initiative(all_combatants)
        
        print("Initiative order:")
        for i, combatant in enumerate(self.initiative_order, 1):
            print(f"{i}. {combatant['name']}")
        
        #Run rounds until combat is over
        while not self.is_combat_over(all_combatants):
            self.run_combat_round(all_combatants)
        
        #Determine winner
        players_alive = any(c for c in players if c['current_hit_points'] > 0)
        if players_alive:
            print("\nThe players are victorious!")
        else:
            print("\nThe monsters have defeated the party!")
        
        return players_alive
        
    def run_simple_combat(self, monster, player):
        """
        Runs a basic combat loop between a monster and a player.
        They will take turns attacking each other until one is defeated.
        """
        combatants = [monster, player]
        round_number = 1

        print(f"Combat started between {monster['name']} and {player['name']}!")

        #Loop until either the monster or player has 0 or fewer HP
        while monster['current_hit_points'] > 0 and player['current_hit_points'] > 0:
            print(f"\n--- Round {round_number} ---")

            #For each combatant in the list (monster, then player)
            for attacker in combatants:
                #Skip if the attacker is already defeated
                if attacker['current_hit_points'] <= 0:
                    continue

                #Determine who the target is (if attacker is monster, target player, and vice versa)
                target = player if attacker is monster else monster

                #For now, just use their first available attack action
                chosen_attack = attacker['actions'][0]['name']

                #Resolve the attack
                result = self.resolve_attack(attacker, chosen_attack, target)
                print(result['message'])

                #Check if the target was defeated by this attack
                if target['current_hit_points'] <= 0:
                    print(f"\n{target['name']} has been defeated!")
                    break # Break out of the for-loop early

            round_number += 1

        #Declare the winner
        if monster['current_hit_points'] <= 0:
            print(f"\nVictory! {player['name']} is victorious!")
        else:
            print(f"\nDefeat! {monster['name']} has won.")

 
class AdvancedCombatSimulator(CombatSimulator):
    def __init__(self):
        super().__init__()
    
    def get_state_representation(self, monsters, players):
        """
        Convert the game state into a numerical representation for the AI
        This is crucial for reinforcement learning
        """
        state = []
        
        #Add monster information
        for monster in monsters:
            if monster['current_hit_points'] > 0:
                state.extend([
                    monster['current_hit_points'] / monster['hit_points'],  # HP percentage
                    monster['armor_class'] / 30,  # Normalized AC
                    len(monster.get('actions', [])) / 10  # Number of actions
                ])
                #Add ability scores (normalized)
                if 'abilities' in monster:
                    for ability in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
                        state.append(monster['abilities'].get(ability, 10) / 20)
            else:
                # Pad with zeros for dead monsters
                state.extend([0] * 9)
        
        #Add player information
        for player in players:
            if player['current_hit_points'] > 0:
                state.extend([
                    player['current_hit_points'] / player['max_hit_points'],  # HP percentage
                    player['armor_class'] / 30,  # Normalized AC
                    len(player.get('actions', [])) / 10  # Number of actions
                ])
                #Add ability scores (normalized)
                for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                    state.append(player['stats'].get(ability, 10) / 20)
            else:
                # Pad with zeros for unconscious players
                state.extend([0] * 9)
        
        return state
    
    def get_valid_actions(self, monster, players):
        """
        Get all valid actions a monster can take given the current state
        """
        valid_actions = []
        
        #Add all attack actions
        for action in monster.get('actions', []):
            #Check if action can target any living player
            living_players = [p for p in players if p['current_hit_points'] > 0]
            if living_players:
                valid_actions.append(action['name'])
        
        #Add special abilities if any
        if 'special_abilities' in monster:
            for ability in monster['special_abilities']:
                valid_actions.append(ability['name'])
        
        return valid_actions