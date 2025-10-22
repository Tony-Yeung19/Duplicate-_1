"""Game management helpers for the combat web UI."""
from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Dict, List, Optional

from AI_Project.simulations.loader import load_monsters
from AI_Project.simulations.simulator import CombatSimulator

from .sample_players import SAMPLE_PLAYERS, all_player_templates, clone_player


class GameError(Exception):
    """Base exception for game related issues."""


class UnknownMonster(GameError):
    """Raised when the requested monster id cannot be located."""

class InvalidDiceRequest(GameError):
    """Raised when dice mechanics are requested with invalid parameters."""
def _sanitize_monster_name(name: str) -> str:
    return name.lower().replace(" ", "-")


def _prepare_monster_templates() -> Dict[str, dict]:
    monsters = {}
    for index, monster in enumerate(load_monsters()):
        hit_points = monster.get("hit_points")
        armor_class = monster.get("armor_class")
        actions = []
        ability_scores = monster.get("abilities", {}) or {}
        stats = {
            "strength": ability_scores.get("STR") or ability_scores.get("strength"),
            "dexterity": ability_scores.get("DEX") or ability_scores.get("dexterity"),
            "constitution": ability_scores.get("CON") or ability_scores.get("constitution"),
            "intelligence": ability_scores.get("INT") or ability_scores.get("intelligence"),
            "wisdom": ability_scores.get("WIS") or ability_scores.get("wisdom"),
            "charisma": ability_scores.get("CHA") or ability_scores.get("charisma"),
        }
        for action in monster.get("actions", []):
            if "attack_bonus" in action and "damage_dice" in action:
                actions.append(
                    {
                        "name": action.get("name", f"Attack {len(actions)+1}"),
                        "attack_bonus": action.get("attack_bonus", 0),
                        "damage_dice": action.get("damage_dice", "1d6"),
                        "damage_bonus": action.get("damage_bonus", 0),
                        "damage_type": action.get("damage_type", ""),
                        "attack_roll_bonus_dice": action.get("attack_roll_bonus_dice"),
                        "extra_damage_dice": action.get("extra_damage_dice"),
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
            "stats": {k: v for k, v in stats.items() if v is not None},
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

    def _autoplay_until_player_turn(self, events: Optional[List[dict]] = None) -> None:
        while not self.winner:
            current = self.initiative_order[self.turn_index]
            if current.get("current_hit_points", 0) <= 0:
                self._advance_turn()
                continue
            if current.get("type") != "monster":
                break
            monster_event = self._execute_monster_turn(current)
            if events is not None and monster_event is not None:
                events.append(monster_event)
            if self.winner:
                break
            self._advance_turn()

    def _execute_monster_turn(self, monster: dict) -> Optional[dict]:
        target = self._first_living(self.players)
        if target is None:
            self.winner = "monsters"
            message = "All heroes have fallen!"
            self.log.append(message)
            return {
                "actor": monster["name"],
                "type": "monster",
                "target": None,
                "hit": False,
                "critical": False,
                "damage": 0,
                "message": message,
                "target_remaining_hp": None,
                "target_defeated": True,
                "extra_messages": [message],
            }
        action = next((act for act in monster.get("actions", []) if act.get("name")), None)
        if action is None:
            message = f"{monster['name']} hesitates, unsure of what to do."
            self.log.append(message)
            return {
                "actor": monster["name"],
                "type": "monster",
                "target": target["name"],
                "hit": False,
                "critical": False,
                "damage": 0,
                "message": message,
                "target_remaining_hp": target.get("current_hit_points"),
                "target_defeated": False,
            }
        result = self.simulator.resolve_attack(monster, action["name"], target)
        self.log.append(result["message"])
        event: dict = {
            "actor": monster["name"],
            "type": "monster",
            "target": target["name"],
            "hit": result.get("hit", False),
            "critical": result.get("critical", False),
            "damage": result.get("damage", 0),
            "message": result.get("message"),
            "target_remaining_hp": target.get("current_hit_points"),
            "target_defeated": False,
        }
        if target["current_hit_points"] <= 0:
            defeat_message = f"{target['name']} has fallen!"
            self.log.append(defeat_message)
            event["target_defeated"] = True
            event.setdefault("extra_messages", []).append(defeat_message)
            if not self._first_living(self.players):
                self.winner = "monsters"
                victory_message = "All heroes have fallen!"
                self.log.append(victory_message)
                event.setdefault("extra_messages", []).append(victory_message)
        return event
    
    def _first_living(self, combatants: List[dict]) -> Optional[dict]:
        for combatant in combatants:
            if combatant.get("current_hit_points", 0) > 0:
                return combatant
        return None

    @property
    def current_turn(self) -> dict:
        return self.initiative_order[self.turn_index]

    def player_action(self, action_name: str) -> dict:
        events: List[dict] = []
        if self.winner:
            return {"events": events}
        current = self.current_turn
        if current.get("type") != "player":
            raise GameError("It is not the player's turn.")
        action = next((act for act in current.get("actions", []) if act["name"] == action_name), None)
        if action is None:
            raise GameError(f"{current['name']} cannot use {action_name}.")
        target = self._first_living(self.monsters)
        if target is None:
            self.winner = "players"
            message = "All foes lie defeated."
            self.log.append(message)
            events.append(
                {
                    "actor": current["name"],
                    "type": "player",
                    "target": None,
                    "hit": False,
                    "critical": False,
                    "damage": 0,
                    "message": message,
                    "target_remaining_hp": None,
                    "target_defeated": True,
                }
            )
            return {"events": events}
        result = self.simulator.resolve_attack(current, action_name, target)
        self.log.append(result["message"])
        event: dict = {
            "actor": current["name"],
            "type": "player",
            "target": target["name"],
            "hit": result.get("hit", False),
            "critical": result.get("critical", False),
            "damage": result.get("damage", 0),
            "message": result.get("message"),
            "target_remaining_hp": target.get("current_hit_points"),
            "target_defeated": False,
        }
        if target["current_hit_points"] <= 0:
            defeat_message = f"{target['name']} is defeated!"
            self.log.append(defeat_message)
            event["target_defeated"] = True
            event.setdefault("extra_messages", []).append(defeat_message)
            if not self._first_living(self.monsters):
                self.winner = "players"
                victory_message = "The heroes stand victorious!"
                self.log.append(victory_message)
                event.setdefault("extra_messages", []).append(victory_message)
        events.append(event)
        if not self.winner:
            self._advance_turn()
            self._autoplay_until_player_turn(events)
        return {"events": events}
    def _combatant_for_roll(self, candidates: List[dict]) -> dict:
        living = self._first_living(candidates)
        if living is not None:
            return living
        if candidates:
            return candidates[0]
        raise InvalidDiceRequest("No combatants available for this roll.")

    def perform_rule_based_roll(
        self,
        *,
        roller: str,
        ability: str,
        proficiency: bool = False,
        advantage: str = "normal",
        dc: Optional[int] = None,
    ) -> dict:
        if not ability:
            raise InvalidDiceRequest("An ability must be specified for dice rolls.")

        if dc is not None and dc < 0:
            raise InvalidDiceRequest("DC must be a positive integer.")

        ability_key = ability.lower()

        if roller == "player":
            combatant = self._combatant_for_roll(self.players)
        elif roller == "monster":
            combatant = self._combatant_for_roll(self.monsters)
        else:
            raise InvalidDiceRequest("roller must be either 'player' or 'monster'.")

        try:
            result = self.simulator.roll_d20_test(
                combatant,
                ability_key,
                proficiency=proficiency,
                dc=dc,
                advantage_state=advantage,
            )
        except ValueError as exc:
            raise InvalidDiceRequest(str(exc)) from exc

        self.log.append(result["message"])
        result["roller"] = combatant.get("name")
        result["roller_type"] = combatant.get("type", roller)
        return result
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
                "actions": self.simulator.describe_actions(combatant),
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
                "actions": self.simulator.describe_actions(current),
            } if current else None,
        }


def available_players() -> List[dict]:
    return [
        {
            "id": player["id"],
            "name": player["name"],
             "class": player.get("class"),
            "max_hit_points": player.get("max_hit_points", player.get("hit_points", 0)),
            "armor_class": player.get("armor_class"),
        }
        for player in all_player_templates()
    ]


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
