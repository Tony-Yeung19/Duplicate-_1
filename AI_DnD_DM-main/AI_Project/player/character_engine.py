"""Utility helpers for programmatic character creation.

This module lifts the rules knowledge that originally lived inside the
interactive ``character_creation.py`` script and exposes functions that can be
used from other entrypoints (for example the Flask web UI).  The goal is to
mirror the tabletop flow: load reference data, validate a player's choices and
produce a combat-ready character sheet that the simulator understands.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from AI_Project.simulations.dice import roll_dice
from AI_Project.simulations.loader import (
    load_characters,
    load_equipment,
    load_rules,
    load_spells,
    load_weapons,
)


ABILITY_SCORES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]


class CharacterCreationError(Exception):
    """Raised when a submitted character configuration is invalid."""


@dataclass
class ReferenceData:
    """All data files required to build a character."""

    classes: List[dict]
    weapons: dict
    equipment: dict
    spells: List[dict]
    rules: dict


def calculate_modifier(score: int) -> int:
    """Return the D&D ability modifier for ``score``."""

    return (score - 10) // 2


def calculate_ac(base_ac: int, dex_mod: int, armor_type: Optional[str] = None, shield_bonus: int = 0) -> int:
    """Compute final armour class applying armour/shield rules."""

    if armor_type == "Heavy":
        ac = base_ac
    elif armor_type == "Medium":
        ac = base_ac + min(2, dex_mod)
    elif armor_type == "Light":
        ac = base_ac + dex_mod
    else:
        ac = 10 + dex_mod  # Unarmoured
    return max(10, ac + shield_bonus)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "hero"


def _player_data_dir() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "player_data"))
    os.makedirs(root, exist_ok=True)
    return root


def load_reference_data() -> ReferenceData:
    return ReferenceData(
        classes=load_characters(),
        weapons=load_weapons(),
        equipment=load_equipment(),
        spells=load_spells(),
        rules=load_rules(),
    )


def get_class_template(class_name: str, data: ReferenceData) -> dict:
    for cls in data.classes:
        if cls["class"].lower() == class_name.lower():
            return cls
    raise CharacterCreationError(f"Unknown class: {class_name}")


def _rules_skill_list(rules: dict) -> List[str]:
    skills: List[str] = []
    for ability_skills in rules.get("skills", {}).values():
        if isinstance(ability_skills, list):
            skills.extend(ability_skills)
    return sorted(set(skills))


def skill_options_for_class(class_template: dict, rules: dict) -> List[str]:
    skill_options = class_template.get("skill_options", [])
    if skill_options == ["Any"]:
        return _rules_skill_list(rules)
    return skill_options


def _weapon_allowed(weapon: dict, proficiencies: Sequence[str]) -> bool:
    return (
        weapon["category"] in proficiencies
        or weapon["name"] in proficiencies
        or "Any" in proficiencies
    )


def weapon_options_for_class(class_template: dict, data: ReferenceData) -> List[dict]:
    proficiencies = class_template.get("weapon_proficiencies", [])
    return [
        weapon
        for weapon in data.weapons.get("weapons", [])
        if _weapon_allowed(weapon, proficiencies)
    ]


def armor_options_for_class(class_template: dict, data: ReferenceData) -> List[dict]:
    proficiencies = class_template.get("armor_proficiencies", [])
    return [
        armor
        for armor in data.equipment.get("armor", [])
        if (
            armor.get("type") in proficiencies
            or armor.get("name") in proficiencies
            or "Any" in proficiencies
        )
    ]


def pack_options_for_class(class_template: dict, data: ReferenceData) -> List[dict]:
    suitable = []
    for pack in data.equipment.get("packs", []):
        users = pack.get("common_users", [])
        if not users or "Any" in users or class_template["class"] in users:
            suitable.append(pack)
    return suitable


def spell_options_for_class(class_template: dict, data: ReferenceData) -> Dict[str, List[dict]]:
    class_name = class_template["class"]
    cantrips = [
        spell
        for spell in data.spells
        if spell.get("level") == 0 and class_name in spell.get("classes", [])
    ]
    level_one = [
        spell
        for spell in data.spells
        if spell.get("level") == 1 and class_name in spell.get("classes", [])
    ]
    limits = {
        "cantrips_known": 0,
        "spell_slots": 0,
        "spellcasting_ability": None,
    }
    for feature in class_template.get("features", []):
        if feature.get("type") == "Spellcasting" and feature.get("level", 1) == 1:
            limits["cantrips_known"] = feature.get("cantrips_known", limits["cantrips_known"])
            slots = feature.get("spell_slots", [])
            if slots:
                limits["spell_slots"] = slots[0]
            limits["spellcasting_ability"] = feature.get("spellcasting_ability")
            break
    return {
        "cantrips": cantrips,
        "level_1": level_one,
        "limits": limits,
    }


ABILITY_METHODS = {
    "4d6-drop-lowest": {
        "label": "4d6 drop lowest",
        "description": "Roll four d6, drop the lowest die for each score.",
        "roller": lambda: _roll_drop_lowest(),
    },
    "3d6": {
        "label": "3d6",
        "description": "Classic method: roll 3d6 for each ability.",
        "roller": lambda: [roll_dice("3d6") for _ in range(6)],
    },
    "2d6+6": {
        "label": "2d6 + 6",
        "description": "Heroic method providing a higher floor.",
        "roller": lambda: [roll_dice("2d6") + 6 for _ in range(6)],
    },
}


def _roll_drop_lowest() -> List[int]:
    scores: List[int] = []
    for _ in range(6):
        rolls = sorted([roll_dice("1d6") for _ in range(4)])
        scores.append(sum(rolls[1:]))
    return scores


def roll_ability_scores(method: str) -> List[int]:
    if method not in ABILITY_METHODS:
        raise CharacterCreationError(f"Unknown ability generation method: {method}")
    return sorted(ABILITY_METHODS[method]["roller"](), reverse=True)


def point_buy_cost(scores: Dict[str, int]) -> int:
    cost_map = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    total = 0
    for ability in ABILITY_SCORES:
        score = scores.get(ability, 8)
        if score not in cost_map:
            raise CharacterCreationError("Point buy scores must be between 8 and 15.")
        total += cost_map[score]
    return total


def _validate_abilities(abilities: Dict[str, int]) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    for ability in ABILITY_SCORES:
        value = abilities.get(ability)
        if value is None:
            raise CharacterCreationError(f"Missing ability score: {ability}")
        if not isinstance(value, int):
            raise CharacterCreationError(f"Ability score for {ability} must be an integer")
        if value < 1 or value > 30:
            raise CharacterCreationError(f"Ability score for {ability} must be between 1 and 30")
        normalized[ability] = value
    return normalized


def _validate_skills(selected: Sequence[str], class_template: dict, rules: dict) -> List[str]:
    choice_limit = class_template.get("skill_choices", 0)
    allowed = skill_options_for_class(class_template, rules)
    selected_unique = list(dict.fromkeys(selected))
    if len(selected_unique) != len(selected):
        raise CharacterCreationError("Duplicate skills selected")
    if choice_limit and len(selected_unique) != choice_limit:
        raise CharacterCreationError(
            f"{class_template['class']} requires choosing {choice_limit} skills"
        )
    for skill in selected_unique:
        if skill not in allowed:
            raise CharacterCreationError(f"{skill} is not available for {class_template['class']}")
    return selected_unique


def _validate_equipment(
    equipment: Dict[str, Optional[str]],
    class_template: dict,
    data: ReferenceData,
) -> Tuple[List[str], Optional[dict]]:
    weapon_name = equipment.get("weapon")
    armor_name = equipment.get("armor")
    pack_name = equipment.get("pack")
    items: List[str] = []

    if weapon_name:
        valid_weapons = weapon_options_for_class(class_template, data)
        weapon = next((w for w in valid_weapons if w["name"] == weapon_name), None)
        if not weapon:
            raise CharacterCreationError(f"{class_template['class']} cannot start with {weapon_name}")
        items.append(weapon_name)

    chosen_armor: Optional[dict] = None
    if armor_name:
        valid_armor = armor_options_for_class(class_template, data)
        armor = next((a for a in valid_armor if a["name"] == armor_name), None)
        if not armor:
            raise CharacterCreationError(f"{class_template['class']} cannot wear {armor_name}")
        items.append(armor_name)
        if armor.get("type") != "Shield":
            chosen_armor = armor

    if pack_name:
        valid_packs = pack_options_for_class(class_template, data)
        pack = next((p for p in valid_packs if p["name"] == pack_name), None)
        if not pack:
            raise CharacterCreationError(f"{class_template['class']} cannot take the {pack_name}")
        items.append(pack_name)

    return items, chosen_armor


def _shield_bonus(equipment: Iterable[str], data: ReferenceData) -> int:
    total = 0
    for armor in data.equipment.get("armor", []):
        if armor.get("type") == "Shield" and armor.get("name") in equipment:
            total += armor.get("ac", 0)
    return total


def _spellcasting_defaults(class_template: dict) -> Tuple[Optional[str], int, int]:
    ability = None
    cantrips = 0
    spells = 0
    for feature in class_template.get("features", []):
        if feature.get("type") == "Spellcasting" and feature.get("level", 1) == 1:
            ability = feature.get("spellcasting_ability")
            cantrips = feature.get("cantrips_known", cantrips)
            slots = feature.get("spell_slots", [])
            if slots:
                spells = slots[0]
            break
    return ability, cantrips, spells


def _validate_spells(
    selected: Sequence[str],
    class_template: dict,
    data: ReferenceData,
) -> List[str]:
    ability, max_cantrips, max_spells = _spellcasting_defaults(class_template)
    if not ability:
        return []

    options = spell_options_for_class(class_template, data)
    allowed_names = {spell["name"] for spell in options["cantrips"] + options["level_1"]}
    selected_unique = list(dict.fromkeys(selected))
    for spell in selected_unique:
        if spell not in allowed_names:
            raise CharacterCreationError(f"{spell} is not available to {class_template['class']}")

    cantrips_selected = [
        spell for spell in selected_unique if spell in {s["name"] for s in options["cantrips"]}
    ]
    level_spells_selected = [
        spell
        for spell in selected_unique
        if spell in {s["name"] for s in options["level_1"]}
    ]

    if len(cantrips_selected) > max_cantrips:
        raise CharacterCreationError(f"Select at most {max_cantrips} cantrip(s)")
    if len(level_spells_selected) > max_spells:
        raise CharacterCreationError(f"Select at most {max_spells} level 1 spell(s)")

    return selected_unique


def build_actions(
    equipment_items: Sequence[str],
    abilities: Dict[str, int],
    class_template: dict,
    data: ReferenceData,
) -> List[dict]:
    actions: List[dict] = []
    proficiency_bonus = 2

    finesse_mod = max(calculate_modifier(abilities["strength"]), calculate_modifier(abilities["dexterity"]))

    for weapon in data.weapons.get("weapons", []):
        if weapon["name"] not in equipment_items:
            continue
        if weapon["weapon_type"] == "Melee":
            ability_mod = calculate_modifier(abilities["strength"])
        else:
            ability_mod = calculate_modifier(abilities["dexterity"])
        if "Finesse" in weapon.get("properties", []):
            ability_mod = finesse_mod

        actions.append(
            {
                "name": weapon["name"],
                "type": f"{weapon['weapon_type']} Weapon Attack",
                "attack_bonus": proficiency_bonus + ability_mod,
                "damage_dice": weapon["damage"],
                "damage_bonus": ability_mod,
                "damage_type": weapon.get("damage_type", ""),
                "properties": weapon.get("properties", []),
                "description": ", ".join(weapon.get("properties", [])),
            }
        )

    ability_key, _, _ = _spellcasting_defaults(class_template)
    if ability_key:
        ability_mod = calculate_modifier(abilities.get(ability_key, 10))
        save_dc = 8 + proficiency_bonus + ability_mod
        basic_cantrips = {
            "Wizard": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
            "Sorcerer": {"name": "Fire Bolt", "damage": "1d10", "type": "Fire"},
            "Warlock": {"name": "Eldritch Blast", "damage": "1d10", "type": "Force"},
            "Bard": {"name": "Vicious Mockery", "damage": "1d4", "type": "Psychic"},
            "Cleric": {"name": "Sacred Flame", "damage": "1d8", "type": "Radiant"},
            "Druid": {"name": "Produce Flame", "damage": "1d8", "type": "Fire"},
        }
        if class_template["class"] in basic_cantrips:
            cantrip = basic_cantrips[class_template["class"]]
            actions.append(
                {
                    "name": cantrip["name"],
                    "type": "Spell Attack",
                    "attack_bonus": proficiency_bonus + ability_mod
                    if class_template["class"] != "Cleric"
                    else 0,
                    "damage_dice": cantrip["damage"],
                    "damage_bonus": 0,
                    "damage_type": cantrip["type"],
                    "save_dc": save_dc if class_template["class"] == "Cleric" else None,
                    "save_ability": "DEX" if class_template["class"] == "Cleric" else None,
                }
            )

    proficiency = 2
    for feature in class_template.get("features", []):
        if feature.get("level", 1) != 1:
            continue
        action = {
            "name": feature.get("name"),
            "type": feature.get("type", "Class Feature"),
            "description": feature.get("description", ""),
        }
        for key in [
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
            if key in feature:
                action[key] = feature[key]

        damage_dice = feature.get("damage_dice")
        spell_ability = feature.get("spellcasting_ability")
        if damage_dice and spell_ability:
            ability_mod = calculate_modifier(abilities.get(spell_ability, 10))
            action["attack_bonus"] = proficiency + ability_mod
        actions.append(action)

    return actions


def build_character(payload: dict, data: Optional[ReferenceData] = None) -> dict:
    data = data or load_reference_data()

    name = payload.get("name", "").strip()
    if not name:
        raise CharacterCreationError("Character name is required")

    class_name = payload.get("class")
    if not class_name:
        raise CharacterCreationError("Class is required")

    class_template = get_class_template(class_name, data)

    abilities = _validate_abilities(payload.get("ability_scores", {}))
    if payload.get("ability_method") == "point-buy":
        if point_buy_cost(abilities) > 27:
            raise CharacterCreationError("Point buy allocations exceed 27 points")

    skills = _validate_skills(payload.get("skills", []), class_template, data.rules)

    items, selected_armor = _validate_equipment(payload.get("equipment", {}), class_template, data)

    spells = _validate_spells(payload.get("spells", []), class_template, data)

    con_mod = calculate_modifier(abilities["constitution"])
    dex_mod = calculate_modifier(abilities["dexterity"])

    hit_die = class_template.get("hit_die", "d8")
    hit_die_size = int(hit_die.replace("d", "")) if isinstance(hit_die, str) else 8
    max_hp = hit_die_size + con_mod

    armor_ac = selected_armor.get("ac", 10) if selected_armor else 10
    armor_type = selected_armor.get("type") if selected_armor else None
    shield_bonus = _shield_bonus(items, data)
    armor_class = calculate_ac(armor_ac, dex_mod, armor_type, shield_bonus)

    actions = build_actions(items, abilities, class_template, data)

    character_id = payload.get("id") or _unique_character_id(name)

    character = {
        "id": character_id,
        "name": name,
        "class": class_template["class"],
        "level": 1,
        "type": "player",
        "stats": abilities,
        "skills": skills,
        "equipment": items,
        "spells": spells,
        "actions": actions,
        "proficiency_bonus": 2,
        "max_hit_points": max_hp,
        "hit_points": max_hp,
        "current_hit_points": max_hp,
        "armor_class": armor_class,
        "description": payload.get(
            "description", f"A newly forged {class_template['class']} ready for adventure."
        ),
    }
    return character


def _unique_character_id(name: str) -> str:
    base = _slugify(name)
    candidate = base
    counter = 1
    existing = {player["id"] for player in load_saved_characters()}
    while candidate in existing:
        counter += 1
        candidate = f"{base}-{counter}"
    return candidate


def save_character(character: dict) -> dict:
    character = dict(character)
    if "id" not in character:
        character["id"] = _unique_character_id(character.get("name", ""))

    filepath = os.path.join(_player_data_dir(), f"{character['id']}.json")
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(character, handle, indent=2)
    return character


def load_saved_characters() -> List[dict]:
    directory = _player_data_dir()
    characters: List[dict] = []
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                character = json.load(handle)
                if "id" not in character:
                    character["id"] = filename[:-5]
                characters.append(character)
        except (OSError, json.JSONDecodeError):
            continue
    return characters


def load_character(character_id: str) -> dict:
    path = os.path.join(_player_data_dir(), f"{character_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(character_id)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def character_options() -> dict:
    data = load_reference_data()
    options = []
    for cls in data.classes:
        options.append(
            {
                "class": cls["class"],
                "hit_die": cls.get("hit_die"),
                "skill_choices": cls.get("skill_choices", 0),
                "skill_options": skill_options_for_class(cls, data.rules),
                "weapon_options": weapon_options_for_class(cls, data),
                "armor_options": armor_options_for_class(cls, data),
                "pack_options": pack_options_for_class(cls, data),
                "spell_options": spell_options_for_class(cls, data),
            }
        )
    return {
        "classes": options,
        "ability_methods": [
            {
                "id": method_id,
                "label": payload["label"],
                "description": payload["description"],
            }
            for method_id, payload in ABILITY_METHODS.items()
        ],
    }