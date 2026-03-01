# ai-engine/engine/nodes/language_detector.py

import os
import logging
from collections import Counter
from pathlib import Path

from engine.state import AgentState, Language
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

EXTENSION_MAP = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".go": Language.GO,
    ".java": Language.JAVA,
    ".rb": Language.RUBY,
}


def language_detector(state: AgentState) -> dict:
    """
    Node 2: Detect primary language from file extensions.
    """
    emit(state, "node_start", "detect_lang", iteration=state["current_iteration"])

    source_files = state.get("source_files", [])
    counts: Counter = Counter()

    for filepath in source_files:
        ext = Path(filepath).suffix.lower()
        lang = EXTENSION_MAP.get(ext)
        if lang:
            counts[lang] += 1

    if not counts:
        primary = Language.UNKNOWN
        detected = [Language.UNKNOWN.value]
    else:
        primary = counts.most_common(1)[0][0]
        detected = [lang.value for lang, _ in counts.most_common()]

    logger.info("Detected languages: %s | Primary: %s", detected, primary.value)

    emit(state, "node_end", "detect_lang", primary_language=primary.value)

    return {
        "primary_language": primary.value,
        "detected_languages": detected,
    }
