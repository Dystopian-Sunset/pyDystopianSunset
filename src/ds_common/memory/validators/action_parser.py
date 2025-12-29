"""
Action parser for extracting structured information from player actions.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Common travel verbs
TRAVEL_VERBS = [
    "jump",
    "walk",
    "run",
    "travel",
    "go",
    "move",
    "head",
    "travel to",
    "go to",
    "move to",
    "teleport",
    "fly",
    "drive",
    "sneak",
    "crawl",
    "climb",
]

# Common action types
ACTION_TYPES = {
    "travel": ["jump", "walk", "run", "travel", "go", "move", "head", "teleport", "fly", "drive"],
    "interaction": ["talk", "speak", "ask", "tell", "say", "greet", "meet"],
    "combat": ["attack", "fight", "strike", "hit", "shoot", "kill"],
    "explore": ["explore", "search", "investigate", "examine", "look", "check"],
    "use": ["use", "activate", "open", "close", "pull", "push"],
}


def parse_action(action_text: str) -> dict[str, Any]:
    """
    Parse a player action to extract structured information.

    Args:
        action_text: The player's action text

    Returns:
        Dictionary with parsed action information:
        {
            "action_type": str,  # "travel", "interaction", "combat", etc.
            "method": str | None,  # "jump", "walk", "teleport", etc.
            "target": str | None,  # Target location or entity
            "source": str | None,  # Source location (if mentioned)
            "distance_implied": str,  # "short", "medium", "long", "instant"
            "raw_text": str,  # Original action text
        }
    """
    action_text = action_text.strip()
    action_lower = action_text.lower()

    result = {
        "action_type": "unknown",
        "method": None,
        "target": None,
        "source": None,
        "distance_implied": "medium",
        "raw_text": action_text,
    }

    # Detect action type
    for action_type, verbs in ACTION_TYPES.items():
        for verb in verbs:
            if verb in action_lower:
                result["action_type"] = action_type
                result["method"] = verb
                break
        if result["action_type"] != "unknown":
            break

    # For travel actions, extract more details
    if result["action_type"] == "travel" or any(verb in action_lower for verb in TRAVEL_VERBS):
        result["action_type"] = "travel"

        # Extract travel method
        for verb in TRAVEL_VERBS:
            if verb in action_lower:
                result["method"] = verb
                break

        # Extract target location (look for "to [location]" or "[verb] [location]")
        to_pattern = r"\bto\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)"
        direct_pattern = r"\b(jump|walk|run|travel|go|move|head|teleport|fly|drive)\s+(?:to\s+)?([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)"

        # Try "to [location]" pattern first
        to_match = re.search(to_pattern, action_text)
        if to_match:
            result["target"] = to_match.group(1).strip()
        else:
            # Try direct pattern
            direct_match = re.search(direct_pattern, action_text, re.IGNORECASE)
            if direct_match:
                result["target"] = direct_match.group(2).strip()

        # Extract source location (look for "from [location]" or "[location] to")
        from_pattern = r"\bfrom\s+([A-Z][a-zA-Z\s]+?)(?:\s+to|$|,|\.)"
        from_match = re.search(from_pattern, action_text)
        if from_match:
            result["source"] = from_match.group(1).strip()

        # Determine distance implied by method
        instant_methods = ["jump", "teleport", "instant"]
        short_methods = ["walk", "run", "sneak", "crawl"]
        long_methods = ["travel", "fly", "drive"]

        if result["method"]:
            method_lower = result["method"].lower()
            if any(m in method_lower for m in instant_methods):
                result["distance_implied"] = "instant"
            elif any(m in method_lower for m in short_methods):
                result["distance_implied"] = "short"
            elif any(m in method_lower for m in long_methods):
                result["distance_implied"] = "long"

    # Extract target for non-travel actions
    if result["action_type"] != "travel" and not result["target"]:
        # Look for capitalized words (likely entity names)
        capitalized_pattern = r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b"
        matches = re.findall(capitalized_pattern, action_text)
        if matches:
            # Take the last capitalized phrase as target (usually the object)
            result["target"] = matches[-1]

    return result
