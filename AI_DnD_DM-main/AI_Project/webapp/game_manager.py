"""Session helpers for the AI-driven web experience."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from AI_Project.ai_dungeon_master import AIDungeonMaster
from AI_Project.game_engine import (
    ActionProcessingError,
    DnDGameEngine,
    GameSetupError,
)


class GameError(Exception):
    """Base exception used by the web layer."""


@dataclass
class AIGameSession:
    """Wraps a ``DnDGameEngine`` instance with an identifier."""

    id: str
    engine: DnDGameEngine

    def serialize(self) -> Dict:
        state = self.engine.get_visible_game_state()
        state["id"] = self.id
        return state

    def player_action(self, action_text: str, actor: Optional[str] = None) -> Dict:
        event = self.engine.process_player_action(actor, action_text)
        return {"event": event}


_MODEL_PATH = Path(__file__).resolve().parents[1] / "dm_working"
_SHARED_DM = AIDungeonMaster(str(_MODEL_PATH))
_CATALOG_ENGINE = DnDGameEngine(ai_dm=_SHARED_DM)
_SESSIONS: Dict[str, AIGameSession] = {}


def available_characters() -> List[Dict]:
    return _CATALOG_ENGINE.get_available_characters()


def available_monsters() -> List[Dict]:
    return _CATALOG_ENGINE.get_available_monsters()


def create_session(character_ids: List[str], monster_ids: List[str], environment: Optional[str] = None) -> AIGameSession:
    try:
        engine = DnDGameEngine(ai_dm=_SHARED_DM)
        engine.start_new_game(character_ids, monster_ids, environment)
    except GameSetupError as exc:  # pragma: no cover - simple plumbing
        raise GameError(str(exc))

    session = AIGameSession(id=str(uuid.uuid4()), engine=engine)
    _SESSIONS[session.id] = session
    return session


def get_session(session_id: str) -> AIGameSession:
    if session_id not in _SESSIONS:
        raise GameError("Game not found")
    return _SESSIONS[session_id]


def apply_player_action(session_id: str, action_text: str, actor: Optional[str] = None) -> Dict:
    session = get_session(session_id)
    try:
        return session.player_action(action_text, actor)
    except ActionProcessingError as exc:  # pragma: no cover - simple plumbing
        raise GameError(str(exc))


def reset_sessions() -> None:
    _SESSIONS.clear()
