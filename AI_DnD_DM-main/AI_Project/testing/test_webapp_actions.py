"""Tests for interactive combat API endpoints."""
from __future__ import annotations

import os
import re
import sys
from unittest.mock import patch

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, REPO_ROOT)

from AI_Project.webapp.app import create_app


def _deterministic_roll(dice: str) -> int:
    """Return the maximum roll for deterministic combat outcomes."""
    match = re.match(r"(\d*)d(\d+)([+-]\d+)?", dice)
    if not match:
        raise AssertionError(f"Unexpected dice expression: {dice}")
    count = int(match.group(1) or 1)
    sides = int(match.group(2))
    modifier = int(match.group(3) or 0)
    return count * sides + modifier


def test_player_action_updates_state_and_events():
    app = create_app()
    app.testing = True
    client = app.test_client()

    with patch("AI_Project.simulations.simulator.roll_dice", side_effect=_deterministic_roll):
        start = client.post(
            "/api/start-game",
            json={"player_id": "fighter-aria", "monster_id": "goblin-0"},
        )
        assert start.status_code == 200
        start_payload = start.get_json()
        game_id = start_payload["game"]["id"]
        initial_hp = start_payload["game"]["monsters"][0]["current_hit_points"]

        action_response = client.post(
            "/api/player-action",
            json={"game_id": game_id, "action_name": "Longsword"},
        )

    assert action_response.status_code == 200
    payload = action_response.get_json()

    # Ensure the backend recorded the maneuver and exposed a structured event log.
    assert "events" in payload
    assert payload["events"], "Expected at least one combat event"
    player_event = payload["events"][0]
    assert player_event["type"] == "player"
    assert player_event["actor"] == "Aria Ironheart"
    assert player_event["hit"] is True
    assert player_event["damage"] > 0
    assert player_event.get("target_remaining_hp") is not None

    # The monster should have taken damage and the combat log should reflect it.
    updated_game = payload["game"]
    new_hp = updated_game["monsters"][0]["current_hit_points"]
    assert new_hp < initial_hp
    assert any("aria ironheart hits" in entry.lower() for entry in updated_game["log"])