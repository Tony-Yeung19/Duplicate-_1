"""Flask application exposing the combat simulator via a web UI."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from .game_manager import (
    GameError,
    available_monsters,
    available_players,
    create_session,
)

app = Flask(__name__, static_folder="static", template_folder="templates")
_sessions = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/players")
def get_players():
    return jsonify({"players": available_players()})


@app.get("/api/monsters")
def get_monsters():
    return jsonify({"monsters": available_monsters()})


@app.post("/api/start-game")
def start_game():
    data = request.get_json(force=True)
    player_id = data.get("player_id")
    monster_id = data.get("monster_id")
    if not player_id or not monster_id:
        return jsonify({"error": "player_id and monster_id are required"}), 400

    try:
        session = create_session(player_id, monster_id)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400

    _sessions[session.id] = session
    return jsonify({"game": session.serialize()})


@app.get("/api/game/<game_id>")
def get_game(game_id: str):
    session = _sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game not found"}), 404
    return jsonify({"game": session.serialize()})


@app.post("/api/player-action")
def player_action():
    data = request.get_json(force=True)
    game_id = data.get("game_id")
    action_name = data.get("action_name")
    if not game_id or not action_name:
        return jsonify({"error": "game_id and action_name are required"}), 400

    session = _sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game not found"}), 404

    try:
        session.player_action(action_name)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"game": session.serialize()})


@app.get("/api/reset")
def reset_games():
    _sessions.clear()
    return jsonify({"status": "reset"})


def create_app() -> Flask:
    """Factory primarily for testing."""
    return app


if __name__ == "__main__":
    app.run(debug=True)
