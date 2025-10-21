"""Flask application exposing the combat simulator via a web UI."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from .character_manager import (
    class_options,
    create_character as create_new_character,
    list_classes,
    list_custom_characters,
    load_custom_character,
    point_buy_info,
    roll_scores,
)
from .game_manager import GameError, available_monsters, available_players, create_session

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


@app.get("/api/classes")
def get_classes():
    return jsonify({"classes": list_classes()})


@app.get("/api/classes/<class_name>")
def get_class(class_name: str):
    try:
        options = class_options(class_name)
    except KeyError:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"class": options})


@app.get("/api/point-buy")
def get_point_buy():
    return jsonify(point_buy_info())


@app.post("/api/ability-scores")
def post_ability_scores():
    data = request.get_json(force=True, silent=True) or {}
    method = data.get("method", "4d6-drop-lowest")
    try:
        scores = roll_scores(method)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"scores": scores})


@app.get("/api/characters")
def get_characters():
    characters = [
        {
            "id": character.get("id"),
            "name": character.get("name"),
            "class": character.get("class"),
            "max_hit_points": character.get("max_hit_points"),
            "armor_class": character.get("armor_class"),
            "description": character.get("description", ""),
        }
        for character in list_custom_characters()
    ]
    return jsonify({"characters": characters})


@app.get("/api/characters/<character_id>")
def get_character(character_id: str):
    try:
        character = load_custom_character(character_id)
    except (FileNotFoundError, OSError, ValueError):
        return jsonify({"error": "Character not found"}), 404
    return jsonify({"character": character})


@app.post("/api/characters")
def create_character():
    payload = request.get_json(force=True)
    try:
        character = create_new_character(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"character": character}), 201


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
