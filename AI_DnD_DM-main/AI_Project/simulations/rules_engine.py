"""Helpers for interpreting the ruleset stored in ``rules.json``."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List

from .loader import load_rules


@dataclass(frozen=True)
class RulesEngine:
    """Lightweight facade around the structured rules reference."""

    data: Dict[str, Any]

    @property
    def ability_table(self) -> List[Dict[str, Any]]:
        return list(self.data.get("ability_modifiers", {}).get("table", []))

    @property
    def proficiency_bonus(self) -> int:
        return int(self.data.get("proficiency", {}).get("level_1_bonus", 0))

    @property
    def d20_description(self) -> str:
        core = self.data.get("core_mechanics", {})
        return str(core.get("d20_test", {}).get("description", ""))

    @property
    def d20_steps(self) -> List[str]:
        core = self.data.get("core_mechanics", {})
        return list(core.get("d20_test", {}).get("steps", []))

    def advantage_summary(self, state: str) -> str:
        section = self.data.get("core_mechanics", {}).get("advantage_disadvantage", {})
        state = (state or "normal").lower()
        if state == "advantage":
            return str(section.get("advantage", ""))
        if state == "disadvantage":
            return str(section.get("disadvantage", ""))
        return str(section.get("description", ""))

    def ability_modifier(self, score: int) -> int:
        """Return the modifier for an ability score using the published table."""

        for entry in self.ability_table:
            raw_score = entry.get("score")
            if isinstance(raw_score, int):
                if score == raw_score:
                    return int(entry.get("modifier", 0))
            else:
                values = list(_ensure_iterable(raw_score))
                if not values:
                    continue
                low = min(values)
                high = max(values)
                if low <= score <= high:
                    return int(entry.get("modifier", 0))
        # Fall back to the common formula if the table is incomplete.
        return (int(score) - 10) // 2


def _ensure_iterable(value: Any) -> Iterable[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return value
    return [int(value)]


@lru_cache(maxsize=1)
def get_rules_engine() -> RulesEngine:
    """Return a cached :class:`RulesEngine` instance."""

    return RulesEngine(load_rules())


__all__ = ["RulesEngine", "get_rules_engine"]