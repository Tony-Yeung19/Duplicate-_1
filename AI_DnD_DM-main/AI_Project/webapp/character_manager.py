"""Utilities for exposing character creation data via the web API."""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Dict, Iterable, List, Optional

from AI_Project.player import character_creation as creator


@lru_cache(maxsize=1)
def _base_resources() -> Dict[str, object]:
    """Load and cache the heavy reference data from disk."""

    return creator.load_resources()


def get_resources(force_reload: bool = False) -> Dict[str, object]:
    """Return a deep copy of the cached reference data."""

    if force_reload:
        _base_resources.cache_clear()
    return deepcopy(_base_resources())


def _expand_skill_options(skill_options: Iterable[str], rules_data: Optional[dict]) -> List[str]:
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


def list_classes() -> List[Dict[str, object]]:
    """Return summary information for all available classes."""

    resources = get_resources()
    result: List[Dict[str, object]] = []
    for cls in resources.get("classes", []):
        result.append(
            {
                "name": cls.get("class"),
                "hit_die": cls.get("hit_die"),
                "primary_ability": cls.get("primary_ability", []),
                "saves": cls.get("saves", []),
                "skill_choices": cls.get("skill_choices", 0),
                "skill_options": _expand_skill_options(
                    cls.get("skill_options", []), resources.get("rules")
                ),
                "armor_proficiencies": cls.get("armor_proficiencies", []),
                "weapon_proficiencies": cls.get("weapon_proficiencies", []),
            }
        )
    return result


def class_options(class_name: str) -> Dict[str, object]:
    """Return the detailed creation options for a specific class."""

    resources = get_resources()
    class_data = None
    for cls in resources.get("classes", []):
        if cls.get("class", "").lower() == class_name.lower():
            class_data = cls
            break
    if not class_data:
        raise KeyError(class_name)

    class_name = class_data.get("class", class_name)
    weapons = resources.get("weapons", {}).get("weapons", [])
    equipment = resources.get("equipment", {})

    weapon_proficiencies = class_data.get("weapon_proficiencies", [])
    available_weapons = [
        {
            "name": weapon.get("name"),
            "damage": weapon.get("damage"),
            "damage_type": weapon.get("damage_type"),
            "properties": weapon.get("properties", []),
        }
        for weapon in weapons
        if (
            weapon.get("category") in weapon_proficiencies
            or weapon.get("name") in weapon_proficiencies
            or "Any" in weapon_proficiencies
        )
    ]

    armor_proficiencies = class_data.get("armor_proficiencies", [])
    available_armor = [
        {
            "name": armor.get("name"),
            "type": armor.get("type"),
            "ac": armor.get("ac"),
        }
        for armor in equipment.get("armor", [])
        if (
            armor.get("type") in armor_proficiencies
            or armor.get("name") in armor_proficiencies
            or "Any" in armor_proficiencies
        )
    ]

    packs = [
        {
            "name": pack.get("name"),
            "contents": pack.get("contents", []),
        }
        for pack in equipment.get("packs", [])
        if not pack.get("common_users")
        or "Any" in pack.get("common_users", [])
        or class_name in pack.get("common_users", [])
    ]

    spells = [
        spell
        for spell in resources.get("spells", [])
        if class_name in spell.get("classes", [])
    ]
    cantrips = [
        {
            "name": spell.get("name"),
            "description": spell.get("description", ""),
        }
        for spell in spells
        if spell.get("level") == 0
    ]
    level_one_spells = [
        {
            "name": spell.get("name"),
            "description": spell.get("description", ""),
        }
        for spell in spells
        if spell.get("level") == 1
    ]

    spellcasting_features = [
        feature
        for feature in class_data.get("features", [])
        if feature.get("type") == "Spellcasting"
    ]

    return {
        "class": class_name,
        "hit_die": class_data.get("hit_die"),
        "skill_choices": class_data.get("skill_choices", 0),
        "skills": _expand_skill_options(class_data.get("skill_options", []), resources.get("rules")),
        "weapon_options": available_weapons,
        "armor_options": available_armor,
        "pack_options": packs,
        "spellcasting": spellcasting_features,
        "cantrips": cantrips,
        "level_one_spells": level_one_spells,
    }


def point_buy_info() -> Dict[str, object]:
    """Expose the standard point-buy budget and cost table."""

    budget, costs = creator.point_buy_budget()
    return {"budget": budget, "costs": costs}


def roll_scores(method: str) -> List[int]:
    """Generate a list of ability scores using the requested method."""

    scores = creator.roll_ability_scores(method)
    return sorted(scores, reverse=True)


def create_character(payload: Dict[str, object]) -> Dict[str, object]:
    """Build and persist a new character from API payload data."""

    name = (payload.get("name") or "Adventurer").strip()
    class_name = payload.get("class")
    if not class_name:
        raise ValueError("class is required")
    abilities = payload.get("abilities", {})
    skills = payload.get("skills", [])
    equipment_field = payload.get("equipment", [])
    if isinstance(equipment_field, dict):
        equipment_list = [value for value in equipment_field.values() if value]
    else:
        equipment_list = list(equipment_field)
    spells = payload.get("spells", [])
    description = payload.get("description", "")
    metadata = payload.get("metadata")

    resources = get_resources()
    character = creator.build_character_profile(
        character_name=name,
        class_name=class_name,
        abilities={k.lower(): v for k, v in abilities.items()},
        chosen_skills=skills,
        equipment_list=equipment_list,
        chosen_spells=spells,
        description=description,
        resources=resources,
        save=True,
        metadata=metadata,
    )

    return character


def list_custom_characters() -> List[Dict[str, object]]:
    """Return all characters created via the API or CLI."""

    return creator.list_saved_characters()


def load_custom_character(character_id: str) -> Dict[str, object]:
    """Load a specific saved character."""

    return creator.load_character(character_id)


def refresh_resources() -> None:
    """Force reload the resource cache (useful if the data files change)."""

    get_resources(force_reload=True)

