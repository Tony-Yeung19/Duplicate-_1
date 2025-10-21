"""Sample playable characters for the web UI."""
from copy import deepcopy

SAMPLE_PLAYERS = [
    {
        "id": "fighter-aria",
        "name": "Aria Ironheart",
        "class": "Fighter",
        "description": "A human battle master who leads from the front, blade flashing with practiced precision.",
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
                "description": "A sweeping strike honed on the training grounds of Waterdeep.",
            },
            {
                "name": "Precision Maneuver",
                "attack_bonus": 5,
                "damage_dice": "1d8",
                "damage_bonus": 5,
                "damage_type": "slashing",
                "description": "Expends a superiority die to drive the blade home with deadly focus.",
            },
        ],
    },
    {
        "id": "rogue-kai",
        "name": "Kai Swiftstep",
        "class": "Rogue",
        "description": "A lightfoot halfling who blends into the shadows before delivering a sneak attack.",
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
                "description": "A flourish of steel that seeks the chinks in an enemy's armor.",
            },
            {
                "name": "Sneak Attack",
                "attack_bonus": 6,
                "damage_dice": "2d6",
                "damage_bonus": 4,
                "damage_type": "piercing",
                "description": "Strikes from the shadows, rolling extra dice when the foe is distracted.",
            },
        ],
    },
    {
        "id": "cleric-lina",
        "name": "Lina Dawnwhisper",
        "class": "Cleric",
        "description": "A half-elf devotee of the Morninglord whose prayers kindle radiant fire.",
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
                "description": "Blessed steel that shatters undead with divine authority.",
            },
            {
                "name": "Guiding Bolt",
                "attack_bonus": 6,
                "damage_dice": "4d6",
                "damage_bonus": 0,
                "damage_type": "radiant",
                "description": "Calls down a lance of holy light, granting allies advantage on the next strike.",
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
