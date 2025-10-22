from .dice import roll_dice  #Import the dice function to be used
from .rules_engine import get_rules_engine, RulesEngine



class RulesEngine:
    """
    Minimal damage rules:
      - resistance halves damage
      - vulnerability doubles damage
    Extend as needed.
    """
    def modify_damage(self, attacker, attack, target) -> int:
        dmg = int(getattr(attack, "damage", 0))
        dtype = getattr(attack, "type", None)

        # Expect lists/sets on the target; adapt if your model differs
        res = set(getattr(target, "resistances", []) or [])
        vul = set(getattr(target, "vulnerabilities", []) or [])

        if dtype and dtype in res:
            dmg = max(0, dmg // 2)
        if dtype and dtype in vul:
            dmg *= 2
        return dmg

def get_rules_engine() -> RulesEngine:
    return RulesEngine()



class CombatSimulator:
    """
    A core rules engine for handling D&D 5e combat.
    """
    def __init__(self, rules =None):
        self.combat_log = []
        self.round_number = 0
        self.initiative_order = []
        self.rules = rules or get_rules_engine()
        print("CombatSimulator initialized!")

    def log_event(self, message):
        """Store a combat event in the log and return the message for convenience."""
        self.combat_log.append(message)
        return message

    def describe_actions(self, combatant):
        """Return a serialisable summary of the combatant's available maneuvers."""
        actions = []
        for action in combatant.get('actions', []):
            name = action.get('name')
            if not name:
                continue
            actions.append({
                'name': name,
                'attack_bonus': action.get('attack_bonus', 0),
                'damage_dice': action.get('damage_dice', '1d6'),
                'damage_bonus': action.get('damage_bonus', 0),
                'damage_type': action.get('damage_type', ''),
                'attack_roll_bonus_dice': action.get('attack_roll_bonus_dice'),
                'extra_damage_dice': action.get('extra_damage_dice'),
                'description': action.get('description', ''),
            })
        return actions

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
            message = f"{attacker['name']} doesn't know how to use {attack_name}!"
            return {
                "hit": False,
                "damage": 0,
                "message": self.log_event(message)
            }
        
        # Roll attack with potential advantage/disadvantage
        attack_roll = roll_dice('1d20')
        is_critical = attack_roll == 20

        # Allow maneuvers or special attacks to add extra dice to the attack roll
        bonus_attack_roll = None
        bonus_attack_dice = attack_data.get('attack_roll_bonus_dice')
        if bonus_attack_dice:
            bonus_attack_roll = roll_dice(bonus_attack_dice)

        # Add attack bonus (and any static modifiers the action might grant)
        attack_total = attack_roll + attack_data['attack_bonus']
        attack_total += attack_data.get('attack_roll_bonus', 0)
        if bonus_attack_roll is not None:
            attack_total += bonus_attack_roll
        
        #Check if hit (critical hits always hit)
        if is_critical or attack_total >= target['armor_class']:
            #Calculate damage
            if is_critical:
                # For critical hits, roll damage dice twice
                base_damage = roll_dice(attack_data['damage_dice']) + roll_dice(attack_data['damage_dice'])
            else:
                base_damage = roll_dice(attack_data['damage_dice'])

            # Some maneuvers may add extra damage dice (e.g., superiority dice)
            extra_damage = 0
            extra_damage_dice = attack_data.get('extra_damage_dice')
            if extra_damage_dice:
                extra_damage = roll_dice(extra_damage_dice)
                if is_critical:
                    extra_damage += roll_dice(extra_damage_dice)

            damage_dealt = base_damage + extra_damage + attack_data.get('damage_bonus', 0)

            # Apply damage resistance/vulnerability (simplified)
            damage_dealt = self.apply_damage_modifiers(damage_dealt, attack_data.get('damage_type', ''), target)

            # Update target HP
            target['current_hit_points'] = max(0, target['current_hit_points'] - damage_dealt)

            # Build combat message with any maneuver details
            detail_parts = []
            if bonus_attack_roll is not None:
                detail_parts.append(f"+{bonus_attack_roll} to hit from maneuver")
            if extra_damage:
                detail_parts.append(f"+{extra_damage} bonus damage")
            detail_text = f" ({'; '.join(detail_parts)})" if detail_parts else ""

            if is_critical:
                prefix = "CRITICAL HIT! "
            else:
                prefix = ""

            message = (
                f"{prefix}{attacker['name']} hits {target['name']} with {attack_name} for {damage_dealt} "
                f"{attack_data.get('damage_type', '')} damage!{detail_text}"
            )

            return {
                "hit": True,
                "critical": is_critical,
                "damage": damage_dealt,
                "message": self.log_event(message),
                "target_hp": target['current_hit_points'],
                "attack_roll": attack_roll,
                "attack_total": attack_total,
                "bonus_attack_roll": bonus_attack_roll,
            }
        else:
            message = f"{attacker['name']} misses {target['name']} with {attack_name}!"
            return {
                "hit": False,
                "damage": 0,
                "message": self.log_event(message)
            }

    def apply_damage_modifiers(self, damage, damage_type, target):
        """Apply damage resistance and vulnerability."""
        #This is a simplified version - you'd expand this based on monster immunities
        if isinstance(target, dict):
            resistances = target.get('damage_resistances', [])
            vulnerabilities = target.get('damage_vulnerabilities', [])
        else:
            resistances = getattr(target, 'damage_resistances', [])
            vulnerabilities = getattr(target, 'damage_vulnerabilities', [])

        if damage_type and damage_type in resistances:
            damage = damage // 2  #Resistance halves damage
        if damage_type and damage_type in vulnerabilities:
            damage = damage * 2  #Vulnerability doubles damage
        return damage

    def roll_d20_test(
        self,
        combatant,
        ability_name,
        *,
        proficiency=False,
        dc=None,
        advantage_state="normal",
    ):
        """Resolve a d20 test for ``combatant`` following the loaded rules."""

        stats = combatant.get("stats", {}) or {}
        key = ability_name.lower()
        if key not in stats:
            raise ValueError(f"{combatant.get('name', 'Unknown')} lacks an ability score for {ability_name}.")

        score = stats[key]
        modifier = self.rules.ability_modifier(score)
        proficiency_bonus = self.rules.proficiency_bonus if proficiency else 0
        kept_roll, rolls = roll_d20(advantage_state)
        total = kept_roll + modifier + proficiency_bonus
        success = None if dc is None else total >= dc

        pretty_ability = key.capitalize()
        advantage_state = (advantage_state or "normal").lower()
        advantage_blurb = self.rules.advantage_summary(advantage_state)

        fragments = [f"{combatant['name']} attempts a {pretty_ability} test"]
        if advantage_state in {"advantage", "disadvantage"}:
            fragments.append(f"rolling with {advantage_state}")
        message = ", ".join(fragments) + "."
        detail = (
            f"d20: {kept_roll} (rolls: {', '.join(str(r) for r in rolls)})"
            f", modifier {modifier:+d}"
        )
        if proficiency_bonus:
            detail += f", proficiency {proficiency_bonus:+d}"
        detail += f" ⇒ total {total}"
        if dc is not None:
            outcome = "success" if success else "failure"
            detail += f" vs DC {dc} ({outcome})"
        message = f"{message} {detail}"

        rule_context = {
            "description": self.rules.d20_description,
            "steps": self.rules.d20_steps,
            "advantage": advantage_blurb,
        }

        return {
            "message": self.log_event(message),
            "roll": kept_roll,
            "rolls": rolls,
            "modifier": modifier,
            "proficiency": proficiency_bonus,
            "total": total,
            "dc": dc,
            "success": success,
            "advantage_state": advantage_state,
            "ability": pretty_ability,
            "rule_context": rule_context,
        }
    
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
        round_message = f"\n=== Round {self.round_number} ==="
        print(round_message)
        self.log_event(round_message)
        
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
        
        
    def player_take_turn(self, player, combatants):
        """Handle player's turn (simplified for now)."""
        #Find all monster targets
        monsters = [c for c in combatants if c.get('type') == 'monster' and c['current_hit_points'] > 0]

        if not monsters:
            return  # No valid targets

        # Surface the player's available maneuvers for higher level callers
        available_actions = self.describe_actions(player)
        if not available_actions:
            message = f"{player['name']} has no maneuvers available!"
            print(self.log_event(message))
            return

        #For now, just attack the first monster with the first available maneuver
        target = monsters[0]
        attack = available_actions[0]['name']

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
        self.round_number = 0
        self.combat_log = []
        self.roll_initiative(all_combatants)

        initiative_message = "Initiative order:"
        print(initiative_message)
        self.log_event(initiative_message)
        for i, combatant in enumerate(self.initiative_order, 1):
            entry = f"{i}. {combatant['name']}"
            print(entry)
            self.log_event(entry)
        
        #Run rounds until combat is over
        while not self.is_combat_over(all_combatants):
            self.run_combat_round(all_combatants)
        
        #Determine winner
        players_alive = any(c for c in players if c['current_hit_points'] > 0)
        if players_alive:
            victory_message = "\nThe players are victorious!"
            print(victory_message)
            self.log_event(victory_message)
        else:
            defeat_message = "\nThe monsters have defeated the party!"
            print(defeat_message)
            self.log_event(defeat_message)
        
        return players_alive
        
    def run_simple_combat(self, monster, player):
        """
        Runs a basic combat loop between a monster and a player.
        They will take turns attacking each other until one is defeated.
        """
        self.combat_log = []
        combatants = [monster, player]
        round_number = 1

        start_message = f"Combat started between {monster['name']} and {player['name']}!"
        print(start_message)
        self.log_event(start_message)

        #Loop until either the monster or player has 0 or fewer HP
        while monster['current_hit_points'] > 0 and player['current_hit_points'] > 0:
            round_banner = f"\n--- Round {round_number} ---"
            print(round_banner)
            self.log_event(round_banner)

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
                    defeat_message = f"\n{target['name']} has been defeated!"
                    print(defeat_message)
                    self.log_event(defeat_message)
                    break # Break out of the for-loop early

            round_number += 1

        #Declare the winner
        if monster['current_hit_points'] <= 0:
            victory_message = f"\nVictory! {player['name']} is victorious!"
            print(victory_message)
            self.log_event(victory_message)
        else:
            defeat_message = f"\nDefeat! {monster['name']} has won."
            print(defeat_message)
            self.log_event(defeat_message)

 
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