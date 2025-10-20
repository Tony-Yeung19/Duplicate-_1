"""Sample playable characters for the web UI."""
from copy import deepcopy

SAMPLE_PLAYERS = [
    {
        "id": "fighter-aria",
        "name": "Aria Ironheart",
        "class": "Fighter",
        "max_hit_points": 32,
        "armor_class": 17,
        "initiative_bonus": 2,
        "stats": {
            "strength": 16,
            "dexterity": 14,
            "constitution": 16,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 11,
        },
        "actions": [
            {
                "name": "Longsword",
                "attack_bonus": 5,
                "damage_dice": "1d8",
                "damage_bonus": 3,
                "damage_type": "slashing",
            },
            {
                "name": "Heavy Crossbow",
                "attack_bonus": 4,
                "damage_dice": "1d10",
                "damage_bonus": 2,
                "damage_type": "piercing",
            },
        ],
    },
    {
        "id": "rogue-kai",
        "name": "Kai Swiftstep",
        "class": "Rogue",
        "max_hit_points": 26,
        "armor_class": 15,
        "initiative_bonus": 4,
        "stats": {
            "strength": 10,
            "dexterity": 18,
            "constitution": 12,
            "intelligence": 13,
            "wisdom": 14,
            "charisma": 12,
        },
        "actions": [
            {
                "name": "Rapier",
                "attack_bonus": 6,
                "damage_dice": "1d8",
                "damage_bonus": 4,
                "damage_type": "piercing",
            },
            {
                "name": "Shortbow",
                "attack_bonus": 6,
                "damage_dice": "1d6",
                "damage_bonus": 4,
                "damage_type": "piercing",
            },
        ],
    },
    {
        "id": "cleric-lina",
        "name": "Lina Dawnwhisper",
        "class": "Cleric",
        "max_hit_points": 28,
        "armor_class": 18,
        "initiative_bonus": 1,
        "stats": {
            "strength": 14,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 11,
            "wisdom": 16,
            "charisma": 13,
        },
        "actions": [
            {
                "name": "Warhammer",
                "attack_bonus": 5,
                "damage_dice": "1d8",
                "damage_bonus": 3,
                "damage_type": "bludgeoning",
            },
            {
                "name": "Sacred Flame",
                "attack_bonus": 5,
                "damage_dice": "1d8",
                "damage_bonus": 0,
                "damage_type": "radiant",
            },
        ],
    },
]


def clone_player(player_id):
    """Return a deep copy of the player template matching ``player_id``."""
    for template in SAMPLE_PLAYERS:
        if template["id"] == player_id:
            player = deepcopy(template)
            player["current_hit_points"] = player["max_hit_points"]
            player["type"] = "player"
            return player
    raise KeyError(f"Unknown player id: {player_id}")
