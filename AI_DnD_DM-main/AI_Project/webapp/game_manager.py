"""Game management helpers for the combat web UI."""
from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Dict, List, Optional

from AI_Project.simulations.loader import load_monsters
from AI_Project.simulations.simulator import CombatSimulator

from .character_manager import list_custom_characters
from .sample_players import SAMPLE_PLAYERS, clone_player


class GameError(Exception):
    """Base exception for game related issues."""


class UnknownMonster(GameError):
    """Raised when the requested monster id cannot be located."""


def _sanitize_monster_name(name: str) -> str:
    return name.lower().replace(" ", "-")


def _prepare_monster_templates() -> Dict[str, dict]:
    monsters = {}
    for index, monster in enumerate(load_monsters()):
        hit_points = monster.get("hit_points")
        armor_class = monster.get("armor_class")
        actions = []
        for action in monster.get("actions", []):
            if "attack_bonus" in action and "damage_dice" in action:
                actions.append(
                    {
                        "name": action.get("name", f"Attack {len(actions)+1}"),
                        "attack_bonus": action.get("attack_bonus", 0),
                        "damage_dice": action.get("damage_dice", "1d6"),
                        "damage_bonus": action.get("damage_bonus", 0),
                        "damage_type": action.get("damage_type", ""),
                    }
                )
        if not actions or not isinstance(hit_points, int) or not isinstance(armor_class, int):
            continue

        monster_id = f"{_sanitize_monster_name(monster['name'])}-{index}"
        monsters[monster_id] = {
            "id": monster_id,
            "name": monster["name"],
            "type": "monster",
            "hit_points": hit_points,
            "current_hit_points": hit_points,
            "armor_class": armor_class,
            "initiative_bonus": monster.get("dexterity", 0),
            "actions": actions,
            "description": monster.get("description", ""),
        }
    return monsters


MONSTER_TEMPLATES = _prepare_monster_templates()


class GameSession:
    """In-memory representation of a combat encounter."""

    def __init__(self, player_id: str, monster_id: str):
        if monster_id not in MONSTER_TEMPLATES:
            raise UnknownMonster(monster_id)

        self.id = str(uuid.uuid4())
        self.simulator = CombatSimulator()
        self.player = clone_player(player_id)
        self.monster = deepcopy(MONSTER_TEMPLATES[monster_id])
        self.players: List[dict] = [self.player]
        self.monsters: List[dict] = [self.monster]
        self.log: List[str] = []
        self.round: int = 1
        self.initiative_order: List[dict] = []
        self.turn_index: int = 0
        self.winner: Optional[str] = None

        self._initialize_combat()

    def _initialize_combat(self) -> None:
        # Reset HP in case templates were modified elsewhere
        for player in self.players:
            player["current_hit_points"] = player["max_hit_points"]
        for monster in self.monsters:
            monster["current_hit_points"] = monster["hit_points"]

        self.simulator.initiative_order = []
        self.simulator.round_number = 0
        combatants = self.players + self.monsters
        self.initiative_order = self.simulator.roll_initiative(combatants)
        # Ensure we start with a living combatant
        self.turn_index = 0
        self._skip_defeated()
        self._autoplay_until_player_turn()

    def _skip_defeated(self) -> None:
        for _ in range(len(self.initiative_order)):
            current = self.initiative_order[self.turn_index]
            if current.get("current_hit_points", 0) > 0:
                return
            self.turn_index = (self.turn_index + 1) % len(self.initiative_order)
        # Everyone defeated — this shouldn't happen during setup but guard anyway.
        self.winner = "draw"

    def _advance_turn(self) -> None:
        if not self.initiative_order:
            return
        previous_index = self.turn_index
        for _ in range(len(self.initiative_order)):
            self.turn_index = (self.turn_index + 1) % len(self.initiative_order)
            if self.turn_index == 0 and self.initiative_order:
                self.round += 1
            current = self.initiative_order[self.turn_index]
            if current.get("current_hit_points", 0) > 0:
                return
        self.turn_index = previous_index

    def _autoplay_until_player_turn(self) -> None:
        while not self.winner:
            current = self.initiative_order[self.turn_index]
            if current.get("current_hit_points", 0) <= 0:
                self._advance_turn()
                continue
            if current.get("type") != "monster":
                break
            self._execute_monster_turn(current)
            if self.winner:
                break
            self._advance_turn()

    def _execute_monster_turn(self, monster: dict) -> None:
        target = self._first_living(self.players)
        if target is None:
            self.winner = "monsters"
            self.log.append("All heroes have fallen!")
            return
        action = next((act for act in monster.get("actions", []) if act.get("name")), None)
        if action is None:
            self.log.append(f"{monster['name']} hesitates, unsure of what to do.")
            return
        result = self.simulator.resolve_attack(monster, action["name"], target)
        self.log.append(result["message"])
        if target["current_hit_points"] <= 0:
            self.log.append(f"{target['name']} has fallen!")
            if not self._first_living(self.players):
                self.winner = "monsters"

    def _first_living(self, combatants: List[dict]) -> Optional[dict]:
        for combatant in combatants:
            if combatant.get("current_hit_points", 0) > 0:
                return combatant
        return None

    @property
    def current_turn(self) -> dict:
        return self.initiative_order[self.turn_index]

    def player_action(self, action_name: str) -> None:
        if self.winner:
            return
        current = self.current_turn
        if current.get("type") != "player":
            raise GameError("It is not the player's turn.")
        action = next((act for act in current.get("actions", []) if act["name"] == action_name), None)
        if action is None:
            raise GameError(f"{current['name']} cannot use {action_name}.")
        target = self._first_living(self.monsters)
        if target is None:
            self.winner = "players"
            return
        result = self.simulator.resolve_attack(current, action_name, target)
        self.log.append(result["message"])
        if target["current_hit_points"] <= 0:
            self.log.append(f"{target['name']} is defeated!")
            if not self._first_living(self.monsters):
                self.winner = "players"
        if not self.winner:
            self._advance_turn()
            self._autoplay_until_player_turn()

    def serialize(self) -> dict:
        def serialize_combatant(combatant: dict) -> dict:
            max_hp = combatant.get("max_hit_points") or combatant.get("hit_points")
            return {
                "id": combatant["id"],
                "name": combatant["name"],
                "class": combatant.get("class"),
                "type": combatant.get("type", "unknown"),
                "current_hit_points": combatant.get("current_hit_points", max_hp),
                "max_hit_points": max_hp,
                "armor_class": combatant.get("armor_class"),
                "initiative_bonus": combatant.get("initiative_bonus", 0),
                "description": combatant.get("description", ""),
                "stats": combatant.get("stats", {}),
                "actions": [
                    {
                        "name": action["name"],
                        "attack_bonus": action.get("attack_bonus", 0),
                        "damage_dice": action.get("damage_dice", "1d6"),
                        "damage_bonus": action.get("damage_bonus", 0),
                        "damage_type": action.get("damage_type", ""),
                        "description": action.get("description", ""),
                    }
                    for action in combatant.get("actions", [])
                ],
            }

        current = self.current_turn if not self.winner else None
        return {
            "id": self.id,
            "players": [serialize_combatant(p) for p in self.players],
            "monsters": [serialize_combatant(m) for m in self.monsters],
            "log": self.log[-20:],
            "winner": self.winner,
            "round": self.round,
            "turn": {
                "name": current["name"],
                "type": current.get("type", "unknown"),
            } if current else None,
        }


def available_players() -> List[dict]:
    players: List[dict] = [
        {
            "id": player["id"],
            "name": player["name"],
            "class": player["class"],
            "max_hit_points": player["max_hit_points"],
            "armor_class": player["armor_class"],
            "type": "sample",
        }
        for player in SAMPLE_PLAYERS
    ]

    for player in list_custom_characters():
        players.append(
            {
                "id": player.get("id"),
                "name": player.get("name"),
                "class": player.get("class"),
                "max_hit_points": player.get("max_hit_points"),
                "armor_class": player.get("armor_class"),
                "type": "custom",
            }
        )

    return players


def available_monsters(limit: int = 25) -> List[dict]:
    monsters = list(MONSTER_TEMPLATES.values())[:limit]
    return [
        {
            "id": monster["id"],
            "name": monster["name"],
            "hit_points": monster["hit_points"],
            "armor_class": monster["armor_class"],
            "description": monster.get("description", ""),
        }
        for monster in monsters
    ]


def create_session(player_id: str, monster_id: str) -> GameSession:
    return GameSession(player_id, monster_id)
