"""Flask application exposing the combat simulator via a web UI."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from AI_Project.player.character_engine import (
    CharacterCreationError,
    build_character,
    character_options,
    load_saved_characters,
    roll_ability_scores,
    save_character,
)

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

@app.get("/api/character-options")
def get_character_options():
    return jsonify(character_options())


@app.get("/api/characters")
def get_custom_characters():
    characters = [
        {
            "id": char["id"],
            "name": char["name"],
            "class": char.get("class"),
            "max_hit_points": char.get("max_hit_points", char.get("hit_points", 0)),
            "armor_class": char.get("armor_class"),
        }
        for char in load_saved_characters()
    ]
    return jsonify({"characters": characters})


@app.post("/api/character-abilities")
def post_character_abilities():
    data = request.get_json(force=True)
    method = data.get("method")
    if not method:
        return jsonify({"error": "method is required"}), 400
    try:
        scores = roll_ability_scores(method)
    except CharacterCreationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"method": method, "scores": scores})


@app.post("/api/characters")
def create_character_endpoint():
    payload = request.get_json(force=True)
    try:
        character = build_character(payload)
        character = save_character(character)
    except CharacterCreationError as exc:
        return jsonify({"error": str(exc)}), 400
    summary = {
        "id": character["id"],
        "name": character["name"],
        "class": character.get("class"),
        "max_hit_points": character.get("max_hit_points", character.get("hit_points", 0)),
        "armor_class": character.get("armor_class"),
    }
    return jsonify({"character": summary})
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
         result = session.player_action(action_name) or {}
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400

    response = {"game": session.serialize()}
    if result.get("events"):
        response["events"] = result["events"]
    return jsonify(response)

@app.get("/api/reset")
def reset_games():
    _sessions.clear()
    return jsonify({"status": "reset"})


def create_app() -> Flask:
    """Factory primarily for testing."""
    return app


if __name__ == "__main__":
    app.run(debug=True)
