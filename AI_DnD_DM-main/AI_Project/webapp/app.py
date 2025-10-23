"""Flask application exposing the AI Dungeon Master via a web UI."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from .game_manager import (
    GameError,
    apply_player_action,
    available_characters,
    available_monsters,
    create_session,
    get_session,
    reset_sessions,
)

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/setup")
def get_setup():
    return jsonify({"characters": available_characters(), "monsters": available_monsters()})


@app.post("/api/start-game")
def start_game():
    data = request.get_json(force=True)
    character_ids = data.get("character_ids") or []
    monster_ids = data.get("monster_ids") or []
    environment = data.get("environment")

    if not character_ids or not monster_ids:
        return jsonify({"error": "Select at least one character and one monster."}), 400

    try:
        session = create_session(character_ids, monster_ids, environment)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"game": session.serialize()})


@app.get("/api/game/<game_id>")
def get_game(game_id: str):
    try:
        session = get_session(game_id)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"game": session.serialize()})


@app.post("/api/player-action")
def player_action():
    data = request.get_json(force=True)
    game_id = data.get("game_id")
    action_text = data.get("action")
    actor = data.get("actor")

    if not game_id or not action_text:
        return jsonify({"error": "game_id and action are required"}), 400

    try:
        result = apply_player_action(game_id, action_text, actor)
        session = get_session(game_id)
    except GameError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        return jsonify({"error": str(exc)}), status_code

    response = {"game": session.serialize(), **result}
    return jsonify(response)


@app.get("/api/reset")
def reset_games():
    reset_sessions()
    return jsonify({"status": "reset"})


def create_app() -> Flask:
    """Factory primarily for testing."""
    return app


if __name__ == "__main__":
    app.run(debug=True)
