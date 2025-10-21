import sys
import os
import json
import time
import glob
import re
from typing import Dict, Iterable, List, Optional, Tuple

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

PLAYER_DATA_DIR = os.path.join(os.path.dirname(__file__), 'player_data')

from simulations.loader import (
    load_characters,
    load_equipment,
    load_weapons,
    load_spells,
    load_rules,
)
from simulations.dice import roll_dice


def _slugify(value: str) -> str:
    """Create a filesystem-friendly identifier from ``value``."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "hero"


def _ensure_player_dir() -> str:
    os.makedirs(PLAYER_DATA_DIR, exist_ok=True)
    return PLAYER_DATA_DIR


def load_resources() -> Dict[str, object]:
    """Load game reference data for character creation workflows."""
    return {
        "classes": load_characters(),
        "weapons": load_weapons(),
        "equipment": load_equipment(),
        "spells": load_spells(),
        "rules": load_rules(),
    }


def _character_filepath(character_id: str) -> str:
    return os.path.join(_ensure_player_dir(), f"{character_id}.json")


def _existing_character_ids() -> List[str]:
    if not os.path.isdir(PLAYER_DATA_DIR):
        return []
    pattern = os.path.join(PLAYER_DATA_DIR, "*.json")
    return [os.path.splitext(os.path.basename(path))[0] for path in glob.glob(pattern)]


def _unique_character_id(name: str) -> str:
    base = _slugify(name)
    if not base:
        base = "hero"
    existing = set(_existing_character_ids())
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def save_character(character: Dict[str, object]) -> Dict[str, object]:
    """Persist a character profile to disk."""
    character_id = character.get("id") or _unique_character_id(character.get("name", "hero"))
    character["id"] = character_id
    character.setdefault("type", "player")
    if "max_hit_points" in character and "current_hit_points" not in character:
        character["current_hit_points"] = character["max_hit_points"]
    filepath = _character_filepath(character_id)
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(character, handle, indent=2)
    return character


def list_saved_characters() -> List[Dict[str, object]]:
    """Return all saved characters from the player data directory."""
    characters: List[Dict[str, object]] = []
    if not os.path.isdir(PLAYER_DATA_DIR):
        return characters
    for path in glob.glob(os.path.join(PLAYER_DATA_DIR, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    data.setdefault("id", os.path.splitext(os.path.basename(path))[0])
                    data.setdefault("type", "player")
                    if "current_hit_points" not in data and "max_hit_points" in data:
                        data["current_hit_points"] = data["max_hit_points"]
                    characters.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return characters


def load_character(character_id: str) -> Dict[str, object]:
    """Load a previously created character by id."""
    filepath = _character_filepath(character_id)
    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)
        data.setdefault("id", character_id)
        data.setdefault("type", "player")
        if "current_hit_points" not in data and "max_hit_points" in data:
            data["current_hit_points"] = data["max_hit_points"]
    return data

def roll_ability_scores(method: str = "4d6-drop-lowest", rolls: int = 6) -> List[int]:
    """Return a list of generated ability scores."""

    method = method.lower()

    def roll(method_key: str) -> int:
        if method_key == "4d6-drop-lowest":
            dice = sorted([roll_dice("1d6") for _ in range(4)])
            return sum(dice[1:])
        if method_key == "3d6":
            return roll_dice("3d6")
        if method_key == "2d6+6":
            return roll_dice("2d6") + 6
        raise ValueError(f"Unknown ability score method: {method}")

    return [roll(method) for _ in range(rolls)]


def point_buy_budget() -> Tuple[int, Dict[int, int]]:
    """Return the standard 27-point point-buy budget and costs."""

    return 27, {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}


def calculate_modifier(score):
    """Calculates ability modifier from a score."""
    return (score - 10) // 2


def _expand_skill_options(skill_options: Iterable[str], rules_data: Optional[dict]) -> List[str]:
    """Return the concrete list of skill options for a class."""

    if not skill_options:
        return []

    if "Any" in skill_options:
        skills: List[str] = []
        if rules_data:
            for ability_skills in rules_data.get("skills", {}).values():
                if isinstance(ability_skills, list):
                    skills.extend(ability_skills)
        if not skills:
            skills = [
                "Acrobatics",
                "Animal Handling",
                "Arcana",
                "Athletics",
                "Deception",
                "History",
                "Insight",
                "Intimidation",
                "Investigation",
                "Medicine",
                "Nature",
                "Perception",
                "Performance",
                "Persuasion",
                "Religion",
                "Sleight of Hand",
                "Stealth",
                "Survival",
            ]
        return sorted(set(skills))

    return list(skill_options)

def get_valid_input(prompt, validation_func, error_msg="Invalid input. Please try again."):
    """Helper function to get valid input from user."""
    while True:
        try:
            user_input = input(prompt)
            if validation_func(user_input):
                return user_input
            else:
                print(error_msg)
        except (ValueError, IndexError) as e:
            print(error_msg)

def choose_skills(skill_options, number_to_choose):
    """
    Guides the user to choose a number of skills from a list.
    Returns a list of chosen skill names.
    """
    chosen_skills = []
    
    #If "Any" is specified, use all available skills from rules
    if skill_options == ["Any"]:
        #Load skills from rules
        rules_data = {}
        try:
            rules_data = load_rules()
            skill_options = []
            for ability_skills in rules_data.get("skills", {}).values():
                if isinstance(ability_skills, list):
                    skill_options.extend(ability_skills)
        except:
            #Fallback list if rules can't be loaded
            skill_options = [
                "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", 
                "History", "Insight", "Intimidation", "Investigation", "Medicine", 
                "Nature", "Perception", "Performance", "Persuasion", "Religion", 
                "Sleight of Hand", "Stealth", "Survival"
            ]
    
    print(f"\nChoose {number_to_choose} skill(s) from the following list:")
    for i, skill in enumerate(skill_options, 1):
        print(f"  {i}. {skill}")
    
    for choice_num in range(1, number_to_choose + 1):
        prompt = f"Enter choice #{choice_num} (1-{len(skill_options)}): "
        
        def validate_skill_choice(input_str):
            try:
                choice = int(input_str)
                if 1 <= choice <= len(skill_options):
                    skill_name = skill_options[choice - 1]
                    if skill_name not in chosen_skills:
                        return True
                return False
            except ValueError:
                return False
        
        choice = int(get_valid_input(prompt, validate_skill_choice))
        skill_name = skill_options[choice - 1]
        chosen_skills.append(skill_name)
        print(f"Added {skill_name} to your skills.")
    
    return chosen_skills

def choose_starting_equipment(character_class, weapons_data, equipment_data, classes_data):
    """
    Guides the user to choose starting equipment based on their class.
    Returns a list of equipment names and armor AC value.
    """
    equipment_choices = []
    armor_ac = 0
    armor_type = "None"
    
    #Find the class data
    class_data = None
    for cls in classes_data:
        if cls["class"] == character_class:
            class_data = cls
            break
    
    if not class_data:
        print(f"Warning: No equipment data found for {character_class}")
        return equipment_choices, armor_ac, armor_type
    
    #Get available weapons based on class proficiencies
    weapon_proficiencies = class_data.get("weapon_proficiencies", [])
    available_weapons = []
    
    for weapon in weapons_data["weapons"]:
        if (weapon["category"] in weapon_proficiencies or 
            weapon["name"] in weapon_proficiencies or
            "Any" in weapon_proficiencies):
            available_weapons.append(weapon)
    
    #Weapon selection
    if available_weapons:
        print(f"\nChoose your starting weapon (Weapon types you're proficient with: {', '.join(weapon_proficiencies)}):")
        for i, weapon in enumerate(available_weapons, 1):
            print(f"  {i}. {weapon['name']} ({weapon['damage_type']} Damage - {weapon['damage']} )")
        
        weapon_choice = int(get_valid_input(
            "Enter your choice: ",
            lambda x: x.isdigit() and 1 <= int(x) <= len(available_weapons)
        ))
        chosen_weapon = available_weapons[weapon_choice - 1]
        equipment_choices.append(chosen_weapon["name"])
    
    #Armor selection based on armor proficiencies
    armor_proficiencies = class_data.get("armor_proficiencies", [])
    available_armor = []
    
    for armor in equipment_data["armor"]:
        if ((armor["type"] in armor_proficiencies or 
            armor["name"] in armor_proficiencies) or
            "Any" in armor_proficiencies):
            available_armor.append(armor)
    
    if available_armor:
        print(f"\nChoose your armor (Armor Types/Protection you're proficient with {', '.join(armor_proficiencies)}):")
        for i, armor in enumerate(available_armor, 1):
            print(f"  {i}. {armor['name']} (AC: {armor['ac']}, {armor['type']})")
        
        armor_choice = int(get_valid_input(
            "Enter your choice (or 0 for no armor): ",
            lambda x: x.isdigit() and 0 <= int(x) <= len(available_armor)
        ))
        
        if armor_choice > 0:
            chosen_armor = available_armor[armor_choice - 1]
            equipment_choices.append(chosen_armor["name"])
            armor_ac = chosen_armor["ac"]
            armor_type = chosen_armor["type"]
    
    #Pack selection
    available_packs = equipment_data.get("packs", [])
    if available_packs:
        suitable_packs = []
        for pack in available_packs:
            common_users = pack.get("common_users", [])
            #Include pack if: 1) no specific users listed, 2) "Any" is specified, 3) character class is in common_users
            if not common_users or "Any" in common_users or character_class in common_users:
                suitable_packs.append(pack)
        
        if suitable_packs:
            print(f"\nChoose your adventuring pack:")
            for i, pack in enumerate(suitable_packs, 1):
                print(f"  {i}. {pack['name']}")
            
            pack_choice = int(get_valid_input(
                "Enter your choice: ",
                lambda x: x.isdigit() and 1 <= int(x) <= len(suitable_packs)
            ))
            chosen_pack = suitable_packs[pack_choice - 1]
            equipment_choices.append(chosen_pack["name"])
        else:
            print(f"\nNo suitable adventuring packs found for {character_class}.")
    
    return equipment_choices, armor_ac, armor_type

def calculate_ac(armor_ac, dex_mod, armor_type=None):
    """Calculate AC based on armor type and Dexterity modifier."""
    if armor_type == "Heavy":
        return armor_ac  #Heavy armor doesn't add Dex modifier
    elif armor_type == "Medium":
        return armor_ac + min(2, dex_mod)  #Medium armor max +2 from Dex
    else:  #Light armor or no armor
        return armor_ac + dex_mod


def build_character_profile(
    character_name: str,
    class_name: str,
    abilities: Dict[str, int],
    chosen_skills: Iterable[str],
    equipment_list: Iterable[str],
    chosen_spells: Optional[Iterable[str]] = None,
    description: str = "",
    resources: Optional[Dict[str, object]] = None,
    save: bool = True,
    metadata: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Create a fully populated character profile from structured selections."""

    resources = resources or load_resources()
    classes = resources.get("classes", [])
    weapons = resources.get("weapons", {})
    equipment = resources.get("equipment", {})
    spells = resources.get("spells", [])
    rules = resources.get("rules")

    class_data = None
    for cls in classes:
        if cls.get("class", "").lower() == class_name.lower():
            class_data = cls
            class_name = cls.get("class", class_name)
            break

    if not class_data:
        raise ValueError(f"Unknown class: {class_name}")

    normalized_abilities: Dict[str, int] = {}
    required_abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    for ability in required_abilities:
        if ability not in abilities:
            raise ValueError(f"Missing ability score for {ability}")
        normalized_abilities[ability] = int(abilities[ability])

    chosen_skills = list(dict.fromkeys(chosen_skills or []))
    skill_limit = int(class_data.get("skill_choices", 0) or 0)
    valid_skills = _expand_skill_options(class_data.get("skill_options", []), rules)
    if skill_limit and len(chosen_skills) > skill_limit:
        raise ValueError(f"Too many skills selected (max {skill_limit})")
    if valid_skills:
        for skill in chosen_skills:
            if skill not in valid_skills:
                raise ValueError(f"{skill} is not a valid skill choice for {class_name}")

    equipment_names = [item for item in (equipment_list or [])]

    armor_ac = 10
    armor_type = None
    shield_bonus = 0
    armor_entries = equipment.get("armor", [])
    for item_name in equipment_names:
        for armor in armor_entries:
            if armor.get("name", "").lower() == str(item_name).lower():
                if armor.get("type") == "Shield":
                    shield_bonus = max(shield_bonus, 2)
                else:
                    armor_ac = armor.get("ac", armor_ac)
                    armor_type = armor.get("type", armor_type)
                break

    dex_mod = calculate_modifier(normalized_abilities["dexterity"])
    con_mod = calculate_modifier(normalized_abilities["constitution"])

    armor_type_for_calc = armor_type if armor_type in {"Light", "Medium", "Heavy"} else None
    ac = calculate_ac(armor_ac, dex_mod, armor_type_for_calc) + shield_bonus

    hit_die = class_data.get("hit_die", "d8")
    try:
        hit_die_max = int(str(hit_die).replace("d", ""))
    except ValueError:
        hit_die_max = 8
    hp = hit_die_max + con_mod
    max_hp = max(hp, 1)

    proficiency_bonus = 2
    actions: List[Dict[str, object]] = []

    for item_name in equipment_names:
        for weapon in weapons.get("weapons", []):
            if weapon.get("name", "").lower() != str(item_name).lower():
                continue
            properties = weapon.get("properties", []) or []
            if "Finesse" in properties:
                ability_mod = max(calculate_modifier(normalized_abilities["strength"]), dex_mod)
            elif weapon.get("weapon_type") == "Melee":
                ability_mod = calculate_modifier(normalized_abilities["strength"])
            else:
                ability_mod = dex_mod
            actions.append(
                {
                    "name": weapon["name"],
                    "type": f"{weapon.get('weapon_type', 'Melee')} Weapon Attack",
                    "attack_bonus": proficiency_bonus + ability_mod,
                    "damage_dice": weapon.get("damage", "1d6"),
                    "damage_bonus": ability_mod,
                    "damage_type": weapon.get("damage_type", "damage"),
                    "properties": properties,
                }
            )
            break

    class_features = class_data.get("features", []) or []
    spellcasting_ability_map = {
        "Wizard": "intelligence",
        "Sorcerer": "charisma",
        "Warlock": "charisma",
        "Bard": "charisma",
        "Cleric": "wisdom",
        "Druid": "wisdom",
        "Paladin": "charisma",
        "Ranger": "wisdom",
    }

    for feature in class_features:
        if feature.get("level") != 1:
            continue
        action = {
            "name": feature.get("name", "Feature"),
            "type": feature.get("type", "Class Feature"),
            "description": feature.get("description", ""),
        }
        for prop in [
            "uses",
            "recharge",
            "action_type",
            "damage_dice",
            "damage_bonus",
            "damage_type",
            "healing_dice",
            "save_dc",
            "save_ability",
            "range",
            "conditions",
            "die_size",
            "spellcasting_ability",
            "spell_slots",
            "cantrips_known",
            "passive",
        ]:
            if prop in feature:
                action[prop] = feature[prop]

        feature_spell_ability = feature.get("spellcasting_ability")
        if not feature_spell_ability and class_name in spellcasting_ability_map:
            feature_spell_ability = spellcasting_ability_map[class_name]

        if feature.get("damage_dice") and feature_spell_ability:
            ability_mod = calculate_modifier(normalized_abilities[feature_spell_ability])
            action["attack_bonus"] = proficiency_bonus + ability_mod

        actions.append(action)

    chosen_spells = list(dict.fromkeys(chosen_spells or []))
    known_spells = {spell.get("name") for spell in spells if spell.get("name")}
    for spell_name in chosen_spells:
        if spell_name not in known_spells:
            raise ValueError(f"Unknown spell: {spell_name}")

    if class_name in spellcasting_ability_map:
        ability_key = spellcasting_ability_map[class_name]
        ability_mod = calculate_modifier(normalized_abilities[ability_key])
        save_dc = 8 + proficiency_bonus + ability_mod

        basic_cantrips = {
            "Wizard": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
            "Sorcerer": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
            "Warlock": {"name": "Eldritch Blast", "damage": "1d10", "type": "Force"},
            "Bard": {"name": "Vicious Mockery", "damage": "1d4", "type": "Psychic"},
            "Cleric": {"name": "Sacred Flame", "damage": "1d8", "type": "Radiant"},
            "Druid": {"name": "Produce Flame", "damage": "1d8", "type": "Fire"},
        }

        if class_name in basic_cantrips:
            cantrip = basic_cantrips[class_name]
            action = {
                "name": cantrip["name"],
                "type": "Spell Attack",
                "damage_dice": cantrip["damage"],
                "damage_bonus": 0,
                "damage_type": cantrip["type"],
            }
            if class_name == "Cleric":
                action["save_dc"] = save_dc
                action["save_ability"] = "DEX"
                action["description"] = "The target must succeed on a Dexterity saving throw or take radiant damage."
            else:
                action["attack_bonus"] = proficiency_bonus + ability_mod
            actions.append(action)

    initiative_bonus = dex_mod

    character: Dict[str, object] = {
        "id": None,
        "name": character_name,
        "class": class_name,
        "level": 1,
        "description": description or f"A fledgling level 1 {class_name}.",
        "stats": normalized_abilities,
        "hit_points": max_hp,
        "max_hit_points": max_hp,
        "current_hit_points": max_hp,
        "armor_class": ac,
        "skills": chosen_skills,
        "equipment": equipment_names,
        "spells": chosen_spells,
        "actions": actions,
        "proficiency_bonus": proficiency_bonus,
        "initiative_bonus": initiative_bonus,
        "type": "player",
    }

    if metadata:
        character.update(metadata)

    if save:
        character = save_character(character)
    else:
        # Ensure the character at least has a stable id even if unsaved.
        character.setdefault("id", _slugify(character_name))

    return character


def create_character():
    """Main function to guide through character creation."""
    print("=== D&D Character Creator ===\n")
    
    #Load game data
    classes = load_characters()
    weapons = load_weapons()
    equipment = load_equipment()
    spells = load_spells()
    
    #Step 1: Choose class
    print("Choose your class:")
    for i, cls in enumerate(classes, 1):
        print(f"{i}. {cls['class']} ({cls['hit_die']} Die to Hit)")
    
    class_choice = int(get_valid_input(
        "\nEnter class number: ",
        lambda x: x.isdigit() and 1 <= int(x) <= len(classes)
    ))
    chosen_class = classes[class_choice - 1]
    class_name = chosen_class['class']
    print(f"\nYou chose: {class_name}")
    
    #Step 2: Enter character name
    character_name = input("\nEnter your character's name: ").strip()
    
    #Step 3: Choose skills
    chosen_skills = choose_skills(
        chosen_class.get('skill_options', ["Any"]), 
        chosen_class.get('skill_choices', 2)
    )
    
    #Step 4: Choose equipment and spells
    equipment_list, armor_ac, armor_type = choose_starting_equipment(
        class_name, weapons, equipment, classes
    )

    spellcasting_classes = ["Wizard", "Sorcerer", "Warlock", "Bard", "Cleric", "Druid", "Paladin", "Ranger"]

    if class_name in spellcasting_classes:
        print(f"\n=== Spell Selection ===")
        print(f"As a {class_name}, you can prepare spells.")
        
        #Get available cantrips and 1st-level spells for this class
        available_cantrips = [spell for spell in spells if spell["level"] == 0 and class_name in spell.get("classes", [])]
        available_level1_spells = [spell for spell in spells if spell["level"] == 1 and class_name in spell.get("classes", [])]
        
        #Find the class data to get spellcasting info
        class_data = None
        for cls in classes:
            if cls["class"] == class_name:
                class_data = cls
                break
        
        #Get spellcasting limits from class features
        max_cantrips = 0
        max_spells = 0
        spellcasting_ability = None
        
        if class_data:
            for feature in class_data.get("features", []):
                if feature.get("type") == "Spellcasting":
                    max_cantrips = feature.get("cantrips_known", 0)
                    max_spells = feature.get("spell_slots", [0])[0]  #First element is level 1 slots
                    spellcasting_ability = feature.get("spellcasting_ability")
                    break
        
        #If no spellcasting feature found, use defaults based on class type
        if max_cantrips == 0 and max_spells == 0:
            if class_name in ["Wizard", "Sorcerer", "Bard", "Cleric", "Druid"]:
                max_cantrips = 3
                max_spells = 2
            else:  #Paladin, Ranger (half-casters)
                max_cantrips = 0
                max_spells = 0
        
        chosen_spells = []
        
        #Select cantrips
        if max_cantrips  > 0 and available_cantrips:
            actual_cantrips_to_choose = min(max_cantrips, len(available_cantrips))
            print(f"\nChoose {actual_cantrips_to_choose} cantrip(s):")
            for i, spell in enumerate(available_cantrips, 1):
                print(f"  {i}. {spell['name']} - {spell['description'][:80]}...")
            
            for i in range(actual_cantrips_to_choose):
                choice = int(get_valid_input(
                    f"Choose cantrip #{i+1}: ",
                    lambda x: x.isdigit() and 1 <= int(x) <= len(available_cantrips)
                ))

                chosen_spell = available_cantrips[choice-1]
                chosen_spells.append(chosen_spell["name"])
                print(f"Added {chosen_spell['name']} to your spells.")
        
        #Select 1st-level spells  
        if max_spells  > 0 and available_level1_spells:
            actual_spells_to_choose = min(max_spells, len(available_level1_spells))
            print(f"\nChoose {actual_spells_to_choose} 1st-level spell(s):")
            for i, spell in enumerate(available_level1_spells, 1):
                print(f"  {i}. {spell['name']} - {spell['description'][:80]}...")
            
            for i in range(actual_spells_to_choose):
                choice = int(get_valid_input(
                    f"Choose spell #{i+1}: ",
                    lambda x: x.isdigit() and 1 <= int(x) <= len(available_level1_spells)
                ))

                chosen_spell = available_level1_spells[choice-1]
                chosen_spells.append(chosen_spell["name"])
                print(f"Added {chosen_spell['name']} to your spells.")
        
        if not chosen_spells and max_cantrips + max_spells > 0:
            print(f"\nNote: No spells available in the database for {class_name} at level 1.")
    
        if chosen_spells:
            print(f"\nSpells chosen: {', '.join(chosen_spells)}")
    else:
        chosen_spells = []
    
    #Step 5: Generate ability scores (dice rolling method)
    print("\n\n=== Ability Scores ===")
    print("Choose your ability score generation method:")
    print("1. 4d6 drop lowest (traditional)")
    print("2. 3d6 (classic)")
    print("3. 2d6+6 (heroic)")
    print("4. Point Buy (balanced)")

    def point_buy_system():
        """Point buy system for balanced character creation."""
        print("\nUsing Point Buy system (27 points):")
        print("Score Cost: 8(0), 9(1), 10(2), 11(3), 12(4), 13(5), 14(7), 15(9)")
        
        point_costs = {8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9}
        abilities = {ability: 8 for ability in ["strength", "dexterity", "constitution", 
                                            "intelligence", "wisdom", "charisma"]}
        points_remaining = 27
        
        for ability in abilities:
            print(f"\nPoints remaining: {points_remaining}")
            print(f"Current {ability}: {abilities[ability]}")
            
            def validate_point_buy(input_str):
                try:
                    new_score = int(input_str)
                    if new_score in point_costs:
                        cost = point_costs[new_score] - point_costs[abilities[ability]]
                        return cost <= points_remaining and cost >= 0
                    return False
                except ValueError:
                    return False
            
            new_score = int(get_valid_input(
                f"Set {ability} score (8-15): ",
                validate_point_buy,
                "Invalid score or not enough points. Choose 8-15."
            ))
            
            cost = point_costs[new_score] - point_costs[abilities[ability]]
            points_remaining -= cost
            abilities[ability] = new_score
        
        return abilities

    method_choice = int(get_valid_input(
        "Enter method (1-4): ",
        lambda x: x.isdigit() and 1 <= int(x) <= 4
    ))

    if method_choice == 1:
        #4d6 drop lowest
        def roll_ability_score():
            rolls = [roll_dice("1d6") for _ in range(4)]
            rolls.sort()
            return sum(rolls[1:])
        method_name = "4d6 drop lowest"
        
    elif method_choice == 2:
        #3d6
        def roll_ability_score():
            return roll_dice("3d6")
        method_name = "3d6"
        
    elif method_choice == 3:
        #2d6+6
        def roll_ability_score():
            return roll_dice("2d6") + 6
        method_name = "2d6+6"
        
    else:  #method_choice == 4
        abilities = point_buy_system()
        method_name = "Point Buy"
        #Skip the rolling process below
        print(f"\nFinal ability scores using {method_name}:")
        for ability, score in abilities.items():
            print(f"{ability.capitalize()}: {score}")

    #Only roll if not using point buy
    if method_choice != 4:
        print(f"\nRolling ability scores using {method_name}!")

        #Roll for each ability
        rolled_scores = []
        for i in range(6):
            score = roll_ability_score()
            rolled_scores.append(score)
            print(f"Score {i+1}: {score}")
            time.sleep(0.8)   #small delay for dramatic effect

        #Let player assign scores
        print(f"\nRolled scores: {rolled_scores}")
        print("You can assign these scores to your abilities as you prefer.")
        rolled_scores.sort(reverse=True)
        print(f"Sorted scores (highest to lowest): {rolled_scores}")

        abilities = {
            "strength": 0, "dexterity": 0, "constitution": 0,
            "intelligence": 0, "wisdom": 0, "charisma": 0
        }

        temp_abilities = abilities.copy()
        for ability in abilities:
            prompt = f"\nAssign a score to {ability.capitalize()} (Available: {rolled_scores}): "
            
            def validate_score(input_str):
                try:
                    score = int(input_str)
                    return score in rolled_scores
                except ValueError:
                    return False
            
            score = int(get_valid_input(prompt, validate_score, 
                                    f"Invalid score. Available scores: {rolled_scores}"))
            temp_abilities[ability] = score
            rolled_scores.remove(score)
            print(f"Assigned {score} to {ability}. Remaining scores: {rolled_scores}")

        abilities = temp_abilities

        print()
        for ability in abilities:
            print(f"{ability.capitalize()}: {temp_abilities[ability]}")
    
    #Step 6: Calculate derived stats
    con_mod = calculate_modifier(abilities["constitution"])
    dex_mod = calculate_modifier(abilities["dexterity"])
    
    #Calculate HP (max at first level)
    hit_die_max = int(chosen_class['hit_die'].replace('d', ''))
    hp = hit_die_max + con_mod
    
    #Calculate AC
    ac = calculate_ac(armor_ac, dex_mod, armor_type)      
    
    #Step 7: Create actions based on equipment and class features
    actions = []

    proficiency_bonus = 2  #Level 1 characters have +2 Proficiency Bonus      

    for item in equipment_list:
        for weapon in weapons["weapons"]:
            if weapon["name"] == item:

                if "Finesse" in weapon.get("properties", []):
                    #Use higher of STR or DEX
                    ability_mod = max(calculate_modifier(abilities["strength"]), 
                                    calculate_modifier(abilities["dexterity"]))
                elif weapon["weapon_type"] == "Melee":
                    ability_mod = calculate_modifier(abilities["strength"])
                else:  #Ranged
                    ability_mod = calculate_modifier(abilities["dexterity"])
                
                attack_bonus = proficiency_bonus + ability_mod
                damage_bonus = ability_mod
                
                actions.append({
                    "name": weapon["name"],
                    "type": f"{weapon['weapon_type']} Weapon Attack",
                    "attack_bonus": attack_bonus,
                    "damage_dice": weapon["damage"],
                    "damage_bonus": damage_bonus,
                    "damage_type": weapon["damage_type"],
                    "properties": weapon.get("properties", [])
                })
                break
    
    class_data = None
    for cls in classes:
        if cls["class"] == class_name:
            class_data = cls
            break

    #Add class features
    if class_data:
        features = class_data.get("features", [])
        for feature in features:
            if feature["level"] == 1:  #Only add level 1 features
                action = {
                    "name": feature["name"],
                    "type": "Class Feature",
                    "description": feature["description"]
                }
                
                #Load additional feature details, if any
                dynamic_properties = [
                "uses", "recharge", "action_type", "damage_dice", "damage_bonus",
                "damage_type", "healing_dice", "save_dc", "save_ability", "range",
                "conditions", "die_size", "spellcasting_ability", "spell_slots",
                "cantrips_known", "passive"
                ]
                
                for prop in dynamic_properties:
                    if prop in feature:
                        action[prop] = feature[prop]
                
                #Add attack bonus for features that deal damage and have an associated ability
                if "damage_dice" in feature and "spellcasting_ability" in feature:
                    ability_mod = calculate_modifier(abilities[feature["spellcasting_ability"]])
                    action["attack_bonus"] = proficiency_bonus + ability_mod
                elif "damage_dice" in feature and class_name in spellcasting_ability:
                    ability_mod = calculate_modifier(abilities[spellcasting_ability[class_name]])
                    action["attack_bonus"] = proficiency_bonus + ability_mod
                
                actions.append(action)


    #Add class-specific actions
    spellcasting_ability = {
        "Wizard": "intelligence",
        "Sorcerer": "charisma", 
        "Warlock": "charisma",
        "Bard": "charisma",
        "Cleric": "wisdom",
        "Druid": "wisdom",
        "Paladin": "charisma",
        "Ranger": "wisdom"
    }

    if class_name in spellcasting_ability:
        ability_mod = calculate_modifier(abilities[spellcasting_ability[class_name]])
        save_dc = 8 + proficiency_bonus + ability_mod

    #Add basic cantrip actions
    basic_cantrips = {
        "Wizard": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
        "Sorcerer": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
        "Warlock": {"name": "Eldritch Blast", "damage": "1d10", "type": "Force"},
        "Bard": {"name": "Vicious Mockery", "damage": "1d4", "type": "Psychic"},
        "Cleric": {"name": "Sacred Flame", "damage": "1d8", "type": "Radiant"},
        "Druid": {"name": "Produce Flame", "damage": "1d8", "type": "Fire"}
    }
    
    if class_name in basic_cantrips:
        cantrip = basic_cantrips[class_name]
        actions.append({
            "name": cantrip["name"],
            "type": "Spell Attack",
            "attack_bonus": proficiency_bonus + ability_mod if class_name != "Cleric" else 0,
            "damage_dice": cantrip["damage"],
            "damage_bonus": 0,
            "damage_type": cantrip["type"],
            "save_dc": save_dc if class_name == "Cleric" else None,
            "save_ability": "DEX" if class_name == "Cleric" else None
        })
    
    #Step 8: Create character object
    character = {
        "name": character_name,
        "class": class_name,
        "level": 1,
        "stats": abilities,
        "hit_points": hp,
        "max_hit_points": hp,
        "armor_class": ac,
        "skills": chosen_skills,
        "equipment": equipment_list,
        "spells": chosen_spells,
        "actions": actions,
        "proficiency_bonus": proficiency_bonus
    }
    
    #Step 9: Create Directory (if it doesn't exist) and save character
    player_data_dir = os.path.join(os.path.dirname(__file__), 'player_data')
    os.makedirs(player_data_dir, exist_ok=True)

    filename = f"{character_name.replace(' ', '_')}.json"
    filepath = os.path.join(player_data_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(character, f, indent=2)
    
    print(f"\nCharacter created successfully!")
    print(f"Name: {character_name}")
    print(f"Class: {class_name}")
    print(f"HP: {hp}")
    print(f"AC: {ac}")
    print(f"Skills: {', '.join(chosen_skills)}")
    print(f"Equipment: {', '.join(equipment_list)}")
    if chosen_spells:
        print(f"Spells: {', '.join(chosen_spells)}")
    print(f"Saved to '{filename}'")
    
    return character

if __name__ == "__main__":
    create_character()
