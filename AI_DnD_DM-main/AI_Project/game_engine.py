"""High level game engine that links the web experience with the AI Dungeon Master."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .ai_dungeon_master import AIDungeonMaster
from .simulations.dice import roll_dice
from .simulations.loader import (
    load_characters,
    load_equipment,
    load_monsters,
    load_rules,
    load_spells,
    load_weapons,
)
from .simulations.simulator import CombatSimulator

_PLAYER_DATA_DIR = Path(__file__).resolve().parent / "player" / "player_data"


class GameSetupError(Exception):
    """Raised when a game cannot be initialised with the provided data."""


class ActionProcessingError(Exception):
    """Raised when an incoming action cannot be executed."""


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(filter(None, cleaned.split("-")))


class DnDGameEngine:
    """Coordinates characters, monsters, rules and the AI Dungeon Master."""

    def __init__(self, ai_model_path: Optional[str] = None, ai_dm: Optional[AIDungeonMaster] = None):
        self.ai_dm = ai_dm or AIDungeonMaster(ai_model_path)
        self.combat_simulator = CombatSimulator()

        # Load data files once to avoid repeated disk access.
        self.classes_data = load_characters()
        self.monsters_data = load_monsters()
        self.equipment_data = load_equipment()
        self.weapons_data = load_weapons()
        self.spells_data = load_spells()
        self.rules_data = load_rules()

        self.character_catalog = self._load_character_catalog()
        self.monster_catalog = self._build_monster_catalog()

        self.game_state: Dict[str, Any] = {}
        self._initiative_order: List[Dict[str, Any]] = []
        self._turn_index: int = 0
        self.reset_game()

    # ------------------------------------------------------------------
    # Data catalog helpers
    # ------------------------------------------------------------------
    def _load_character_catalog(self) -> Dict[str, Dict[str, Any]]:
        catalog: Dict[str, Dict[str, Any]] = {}
        if not _PLAYER_DATA_DIR.exists():
            return catalog

        for path in sorted(_PLAYER_DATA_DIR.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            character_id = data.get("id") or path.stem
            catalog[str(character_id)] = data
        return catalog

    def _build_monster_catalog(self) -> Dict[str, Dict[str, Any]]:
        catalog: Dict[str, Dict[str, Any]] = {}
        for index, monster in enumerate(self.monsters_data):
            name = monster.get("name") or f"Monster {index + 1}"
            slug = _slugify(name) or f"monster-{index}"
            monster_id = f"{slug}-{index}"
            catalog[monster_id] = monster
        return catalog

    # ------------------------------------------------------------------
    # Public catalogue API
    # ------------------------------------------------------------------
    def get_available_characters(self) -> List[Dict[str, Any]]:
        results = []
        for character_id, data in self.character_catalog.items():
            results.append(
                {
                    "id": character_id,
                    "name": data.get("name", character_id.title()),
                    "class": data.get("class", "Adventurer"),
                    "level": data.get("level", 1),
                    "max_hit_points": data.get("max_hit_points") or data.get("hit_points"),
                    "armor_class": data.get("armor_class", 10),
                }
            )
        return sorted(results, key=lambda entry: entry["name"].lower())

    def get_available_monsters(self) -> List[Dict[str, Any]]:
        results = []
        for monster_id, data in self.monster_catalog.items():
            results.append(
                {
                    "id": monster_id,
                    "name": data.get("name", monster_id.title()),
                    "type": data.get("type", "creature"),
                    "armor_class": data.get("armor_class", 10),
                    "hit_points": data.get("hit_points", 1),
                    "challenge_rating": data.get("challenge_rating"),
                }
            )
        return sorted(results, key=lambda entry: entry["name"].lower())

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------
    def reset_game(self) -> None:
        self.game_state = {
            "characters": [],
            "monsters": [],
            "environment": "Ancient Ruins",
            "combat_active": False,
            "round": 0,
            "current_turn": None,
            "initiative_order": [],
            "log": [],
            "winner": None,
        }
        self._initiative_order = []
        self._turn_index = 0

    def start_new_game(
        self,
        character_ids: Sequence[str],
        monster_ids: Sequence[str],
        environment: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not character_ids:
            raise GameSetupError("Select at least one hero to begin an encounter.")
        if not monster_ids:
            raise GameSetupError("Select at least one monster to challenge the party.")

        characters = [self._prepare_character(character_id) for character_id in character_ids]
        monsters = [self._prepare_monster(monster_id) for monster_id in monster_ids]

        self.reset_game()
        self.game_state["characters"] = characters
        self.game_state["monsters"] = monsters
        if environment:
            self.game_state["environment"] = environment

        if monsters:
            initiative = self.combat_simulator.roll_initiative(characters + monsters)
            self._initiative_order = initiative
            self.game_state["initiative_order"] = [combatant["name"] for combatant in initiative]
            self._turn_index = 0
            current = self._first_living_combatant()
            self.game_state["current_turn"] = current["name"] if current else None
            self.game_state["combat_active"] = True
            self.game_state["round"] = 1 if current else 0
        else:
            self.game_state["current_turn"] = characters[0]["name"] if characters else None

        intro_message = self._build_intro_message()
        self._log_event({"type": "system", "message": intro_message})
        return self.get_visible_game_state()

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def process_player_action(self, player_name: Optional[str], action_text: str) -> Dict[str, Any]:
        if not action_text.strip():
            raise ActionProcessingError("Provide an action for the heroes to attempt.")

        actor_name = player_name or self.game_state.get("current_turn")
        if not actor_name:
            raise ActionProcessingError("There is no active combatant at the moment.")

        actor = self._find_combatant(actor_name)
        if actor is None:
            raise ActionProcessingError(f"Unknown combatant '{actor_name}'.")
        if not self._is_combatant_alive(actor):
            raise ActionProcessingError(f"{actor_name} can no longer act.")

        dm_response = self.ai_dm.generate_response(self._game_state_for_ai(), action_text)
        command_results = [self.execute_game_command(command, actor_name) for command in dm_response.get("commands", [])]

        self.update_game_state()
        if self.game_state.get("combat_active") and not self.game_state.get("winner"):
            self.advance_turn()

        normalized_results = [self._normalize_command_result(result) for result in command_results]
        event = {
            "type": "turn",
            "actor": actor_name,
            "action": action_text,
            "narration": dm_response.get("narration", ""),
            "commands": dm_response.get("commands", []),
            "results": normalized_results,
            "round": self.game_state.get("round"),
            "dm_raw_response": dm_response.get("raw_response"),
        }
        self._log_event(event)
        return event

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------
    def execute_game_command(self, command: str, player_name: str) -> Any:
        try:
            command_lower = command.lower()
            if command_lower.startswith("!attack"):
                return self.resolve_attack(command, player_name)
            if command_lower.startswith("!cast"):
                return self.resolve_spell(command, player_name)
            if command_lower.startswith("!roll"):
                return self.resolve_dice_roll(command)
            if command_lower.startswith("!check"):
                return self.resolve_skill_check(command, player_name)
            if command_lower.startswith("!save"):
                return self.resolve_saving_throw(command, player_name)
            if command_lower.startswith("!init"):
                return self.handle_initiative(command)
            if command_lower.startswith("!use"):
                return self.use_ability(command, player_name)
            if command_lower.startswith("!move"):
                return self.handle_movement(command, player_name)
            return {"message": f"Command acknowledged: {command}"}
        except Exception as exc:  # pragma: no cover - defensive
            return {"message": f"Command failed: {exc}"}

    # ------------------------------------------------------------------
    # Core mechanics helpers
    # ------------------------------------------------------------------
    def resolve_attack(self, command: str, attacker_name: str) -> Dict[str, Any]:
        parts = command.split()
        action_name_parts: List[str] = []
        target_name_parts: List[str] = []
        if "-t" in parts:
            target_index = parts.index("-t")
            action_name_parts = parts[1:target_index]
            target_name_parts = parts[target_index + 1 :]
        else:
            action_name_parts = parts[1:]

        action_name = " ".join(action_name_parts).strip() or self._default_attack_for(attacker_name)
        target_name = " ".join(target_name_parts).strip()
        if not target_name:
            target = self._default_target_for(attacker_name)
            target_name = target["name"] if target else ""
        else:
            target = self._find_combatant(target_name)

        attacker = self._find_combatant(attacker_name)
        if attacker is None or target is None:
            return {"message": "Could not identify attacker or target."}

        if action_name:
            available_actions = [action.get("name", "").lower() for action in attacker.get("actions", [])]
            if action_name.lower() not in available_actions:
                action_name = self._default_attack_for(attacker_name)

        if action_name:
            result = self.combat_simulator.resolve_attack(attacker, action_name, target)
        else:
            result = {"message": f"{attacker_name} hesitates without a clear attack."}

        if isinstance(result, dict) and "message" in result:
            return result

        # Fallback formatting for unexpected structures
        return {"message": str(result)}

    def resolve_spell(self, command: str, caster_name: str) -> Dict[str, Any]:
        spell_part = command.replace("!cast", "", 1).strip()
        target_name = None
        if "-t" in spell_part:
            spell_name, _, target_fragment = spell_part.partition("-t")
            spell_part = spell_name.strip()
            target_name = target_fragment.strip()
        spell_name = spell_part

        spell = next((spell for spell in self.spells_data if spell.get("name", "").lower() == spell_name.lower()), None)
        if spell is None:
            return {"message": f"Spell '{spell_name or 'Unknown'}' is not recognised."}

        caster = self._find_combatant(caster_name)
        if caster is None:
            return {"message": f"Caster {caster_name} is not present."}

        if "damage" in spell:
            damage_info = spell["damage"]
            if isinstance(damage_info, dict):
                dice_notation = damage_info.get("dice")
                damage_type = damage_info.get("type", "")
            else:
                dice_notation = damage_info
                damage_type = ""
            if dice_notation:
                total = roll_dice(dice_notation)
                message = f"{caster_name} casts {spell_name}, dealing {total} {damage_type} damage."
            else:
                message = f"{caster_name} channels {spell_name}, but the effects are purely narrative."
        else:
            description = spell.get("description", "The magic swirls mysteriously.")
            message = f"{caster_name} casts {spell_name}. {description[:120]}"

        if target_name:
            message += f" Target: {target_name}."
        return {"message": message.strip()}

    def resolve_dice_roll(self, command: str) -> Dict[str, Any]:
        roll_text = command.replace("!roll", "", 1).strip() or "1d20"
        try:
            total = roll_dice(roll_text)
            return {"message": f"Dice roll {roll_text} = {total}"}
        except Exception:
            return {"message": f"Invalid dice notation: {roll_text}"}

    def resolve_skill_check(self, command: str, player_name: str) -> Dict[str, Any]:
        skill_name = command.replace("!check", "", 1).strip() or "Perception"
        roll = roll_dice("1d20")
        player = self._find_combatant(player_name)
        bonus = 0
        if player and "skills" in player and skill_name.title() in player["skills"]:
            bonus = player.get("proficiency_bonus", 2)
        total = roll + bonus
        return {"message": f"{player_name} rolls {skill_name.title()}: {roll} + {bonus} = {total}"}

    def resolve_saving_throw(self, command: str, player_name: str) -> Dict[str, Any]:
        ability = command.replace("!save", "", 1).strip().lower() or "dexterity"
        roll = roll_dice("1d20")
        player = self._find_combatant(player_name)
        bonus = 0
        if player:
            stats = player.get("stats", {})
            score = stats.get(ability) or stats.get(ability[:3])
            if score is not None:
                bonus = (score - 10) // 2
        total = roll + bonus
        return {"message": f"{player_name} attempts a {ability} save: {roll} + {bonus} = {total}"}

    def handle_initiative(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower()
        if "next" in command_lower:
            next_turn = self.advance_turn()
            if next_turn:
                return {"message": f"Initiative advances to {next_turn}."}
            return {"message": "No eligible combatant remains in the initiative order."}
        if "order" in command_lower:
            order = ", ".join(self.game_state.get("initiative_order", []))
            return {"message": f"Initiative order: {order}"}
        return {"message": "Initiative command noted."}

    def use_ability(self, command: str, player_name: str) -> Dict[str, Any]:
        ability_name = command.replace("!use", "", 1).strip() or "class feature"
        return {"message": f"{player_name} uses {ability_name}."}

    def handle_movement(self, command: str, player_name: str) -> Dict[str, Any]:
        movement = command.replace("!move", "", 1).strip() or "strategically"
        return {"message": f"{player_name} moves {movement}."}

    # ------------------------------------------------------------------
    # Game state utilities
    # ------------------------------------------------------------------
    def advance_turn(self) -> Optional[str]:
        if not self._initiative_order:
            self.game_state["current_turn"] = None
            return None

        for _ in range(len(self._initiative_order)):
            self._turn_index = (self._turn_index + 1) % len(self._initiative_order)
            if self._turn_index == 0:
                self.game_state["round"] += 1
            combatant = self._initiative_order[self._turn_index]
            if self._is_combatant_alive(combatant):
                self.game_state["current_turn"] = combatant["name"]
                return combatant["name"]

        self.game_state["current_turn"] = None
        return None

    def update_game_state(self) -> None:
        self._remove_defeated()
        self._sync_hp_fields()

        monsters_alive = any(self._is_combatant_alive(monster) for monster in self.game_state["monsters"])
        heroes_alive = any(self._is_combatant_alive(hero) for hero in self.game_state["characters"])

        if not monsters_alive and self.game_state.get("winner") is None:
            self.game_state["winner"] = "players" if heroes_alive else "draw"
            self.game_state["combat_active"] = False
            self.game_state["current_turn"] = None
            self._log_event({"type": "system", "message": "All monsters are defeated! Victory for the heroes."})
        elif not heroes_alive and self.game_state.get("winner") is None:
            self.game_state["winner"] = "monsters"
            self.game_state["combat_active"] = False
            self.game_state["current_turn"] = None
            self._log_event({"type": "system", "message": "The heroes fall. The monsters triumph."})

    def get_visible_game_state(self) -> Dict[str, Any]:
        return {
            "environment": self.game_state.get("environment"),
            "round": self.game_state.get("round") if self.game_state.get("combat_active") else None,
            "combat_active": self.game_state.get("combat_active", False),
            "current_turn": self.game_state.get("current_turn"),
            "initiative_order": list(self.game_state.get("initiative_order", [])),
            "winner": self.game_state.get("winner"),
            "characters": [self._summarise_character(character) for character in self.game_state.get("characters", [])],
            "monsters": [self._summarise_monster(monster) for monster in self.game_state.get("monsters", [])],
            "log": list(self.game_state.get("log", [])),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_character(self, character_id: str) -> Dict[str, Any]:
        if character_id not in self.character_catalog:
            raise GameSetupError(f"Character '{character_id}' could not be located.")
        character = deepcopy(self.character_catalog[character_id])
        character.setdefault("type", "player")
        current_hp = character.get("current_hit_points") or character.get("hit_points") or character.get("max_hit_points") or 1
        character["current_hit_points"] = current_hp
        character["hit_points"] = current_hp
        character.setdefault("max_hit_points", current_hp)
        character.setdefault("armor_class", 10)
        character.setdefault("proficiency_bonus", 2)
        character["initiative_bonus"] = self._dexterity_modifier(character.get("stats", {}))
        if not character.get("actions"):
            character["actions"] = [
                {
                    "name": "Attack",
                    "attack_bonus": character.get("proficiency_bonus", 2),
                    "damage_dice": "1d6",
                    "damage_bonus": self._dexterity_modifier(character.get("stats", {})),
                    "damage_type": "Bludgeoning",
                }
            ]
        return character

    def _prepare_monster(self, monster_id: str) -> Dict[str, Any]:
        if monster_id not in self.monster_catalog:
            raise GameSetupError(f"Monster '{monster_id}' could not be located.")
        monster = deepcopy(self.monster_catalog[monster_id])
        monster.setdefault("type", "monster")
        monster_hp = monster.get("hit_points") or monster.get("hp") or 1
        monster["current_hit_points"] = monster_hp
        monster["current_hp"] = monster_hp
        monster.setdefault("armor_class", 10)
        abilities = monster.get("abilities", {})
        monster["initiative_bonus"] = self._dexterity_modifier({
            "dexterity": abilities.get("DEX") or abilities.get("dexterity") or abilities.get("Dexterity"),
        })
        if not monster.get("actions"):
            monster["actions"] = [
                {
                    "name": "Claw",
                    "attack_bonus": 2,
                    "damage_dice": "1d6",
                    "damage_bonus": 1,
                    "damage_type": "Slashing",
                }
            ]
        return monster

    def _dexterity_modifier(self, stats: Dict[str, Any]) -> int:
        dex = stats.get("dexterity") or stats.get("Dexterity") or stats.get("dex") or stats.get("DEX")
        if isinstance(dex, int):
            return (dex - 10) // 2
        return 0

    def _first_living_combatant(self) -> Optional[Dict[str, Any]]:
        for combatant in self._initiative_order:
            if self._is_combatant_alive(combatant):
                return combatant
        return None

    def _default_attack_for(self, attacker_name: str) -> str:
        combatant = self._find_combatant(attacker_name)
        if not combatant:
            return "Attack"
        actions = combatant.get("actions") or []
        if not actions:
            return "Attack"
        return actions[0].get("name", "Attack")

    def _default_target_for(self, attacker_name: str) -> Optional[Dict[str, Any]]:
        attacker = self._find_combatant(attacker_name)
        if attacker and attacker.get("type") == "monster":
            pool = self.game_state.get("characters", [])
        else:
            pool = self.game_state.get("monsters", [])
        for combatant in pool:
            if self._is_combatant_alive(combatant):
                return combatant
        return None

    def _find_combatant(self, name: str) -> Optional[Dict[str, Any]]:
        for combatant in self.game_state.get("characters", []):
            if combatant.get("name") == name:
                return combatant
        for combatant in self.game_state.get("monsters", []):
            if combatant.get("name") == name:
                return combatant
        return None

    def _is_combatant_alive(self, combatant: Dict[str, Any]) -> bool:
        current_hp = combatant.get("current_hit_points")
        if current_hp is None:
            current_hp = combatant.get("current_hp")
        if current_hp is None:
            current_hp = combatant.get("hit_points")
        return current_hp is None or current_hp > 0

    def _remove_defeated(self) -> None:
        def _alive(entries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [entry for entry in entries if self._is_combatant_alive(entry)]

        self.game_state["characters"] = _alive(self.game_state.get("characters", []))
        self.game_state["monsters"] = _alive(self.game_state.get("monsters", []))
        living_names = {entry["name"] for entry in self.game_state["characters"] + self.game_state["monsters"]}
        self._initiative_order = [entry for entry in self._initiative_order if entry.get("name") in living_names]
        self.game_state["initiative_order"] = [entry.get("name") for entry in self._initiative_order]
        if self._initiative_order:
            self._turn_index %= len(self._initiative_order)
        else:
            self._turn_index = 0

    def _sync_hp_fields(self) -> None:
        for character in self.game_state.get("characters", []):
            current = character.get("current_hit_points") or character.get("hit_points")
            character["hit_points"] = current
        for monster in self.game_state.get("monsters", []):
            current = monster.get("current_hit_points") or monster.get("current_hp") or monster.get("hit_points")
            monster["current_hp"] = current
            monster["hit_points"] = monster.get("hit_points") or current

    def _summarise_character(self, character: Dict[str, Any]) -> Dict[str, Any]:
        current_hp = character.get("current_hit_points") or character.get("hit_points", 0)
        max_hp = character.get("max_hit_points") or current_hp
        status = "down" if current_hp <= 0 else "bloodied" if current_hp < max_hp / 2 else "healthy"
        return {
            "name": character.get("name"),
            "class": character.get("class", "Adventurer"),
            "hit_points": current_hp,
            "max_hit_points": max_hp,
            "armor_class": character.get("armor_class", 10),
            "status": status,
        }

    def _summarise_monster(self, monster: Dict[str, Any]) -> Dict[str, Any]:
        current_hp = monster.get("current_hit_points") or monster.get("current_hp") or monster.get("hit_points", 0)
        max_hp = monster.get("hit_points") or current_hp
        status = "defeated" if current_hp <= 0 else "bloodied" if current_hp < max_hp / 2 else "threatening"
        return {
            "name": monster.get("name"),
            "hp": current_hp,
            "max_hp": max_hp,
            "armor_class": monster.get("armor_class", 10),
            "status": status,
            "type": monster.get("type", "monster"),
        }

    def _build_intro_message(self) -> str:
        hero_names = ", ".join(character.get("name", "Hero") for character in self.game_state.get("characters", []))
        monster_names = ", ".join(monster.get("name", "Foe") for monster in self.game_state.get("monsters", []))
        if not monster_names:
            return f"{hero_names} prepare for adventure."
        return f"{hero_names} face off against {monster_names}. Roll initiative!"

    def _log_event(self, event: Dict[str, Any]) -> None:
        log = self.game_state.setdefault("log", [])
        entry = deepcopy(event)
        entry["index"] = len(log)
        log.append(entry)

    def _normalize_command_result(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, dict):
            message = result.get("message")
            details = {key: value for key, value in result.items() if key != "message"}
            return {"message": message or json.dumps(result), "details": details or None}
        return {"message": str(result)}

    def _game_state_for_ai(self) -> Dict[str, Any]:
        # Provide a trimmed snapshot of the game state to avoid accidental mutation.
        snapshot = deepcopy(self.game_state)
        snapshot.pop("log", None)
        return snapshot