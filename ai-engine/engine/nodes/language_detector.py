# ai-engine/engine/nodes/language_detector.py

import os
import logging
from collections import Counter
from pathlib import Path

from engine.state import AgentState, Language
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

# ── Extension → Language mapping ─────────────────────────
EXTENSION_MAP: dict[str, Language] = {
    # Python
    ".py": Language.PYTHON, ".pyw": Language.PYTHON, ".pyx": Language.PYTHON,
    # JavaScript
    ".js": Language.JAVASCRIPT, ".jsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT, ".cjs": Language.JAVASCRIPT,
    # TypeScript
    ".ts": Language.TYPESCRIPT, ".tsx": Language.TYPESCRIPT,
    ".mts": Language.TYPESCRIPT, ".cts": Language.TYPESCRIPT,
    # Go
    ".go": Language.GO,
    # Java
    ".java": Language.JAVA,
    # Ruby
    ".rb": Language.RUBY, ".rake": Language.RUBY, ".gemspec": Language.RUBY,
    # Rust
    ".rs": Language.RUST,
    # C#
    ".cs": Language.CSHARP, ".csx": Language.CSHARP,
    # C
    ".c": Language.C, ".h": Language.C,
    # C++
    ".cpp": Language.CPP, ".cc": Language.CPP, ".cxx": Language.CPP,
    ".hpp": Language.CPP, ".hxx": Language.CPP,
    # PHP
    ".php": Language.PHP, ".phps": Language.PHP, ".phtml": Language.PHP,
    # Swift
    ".swift": Language.SWIFT,
    # Kotlin
    ".kt": Language.KOTLIN, ".kts": Language.KOTLIN,
    # Scala
    ".scala": Language.SCALA, ".sc": Language.SCALA,
    # Shell
    ".sh": Language.SHELL, ".bash": Language.SHELL,
    ".zsh": Language.SHELL, ".fish": Language.SHELL,
    # R
    ".r": Language.R, ".R": Language.R, ".rmd": Language.R,
    # Dart
    ".dart": Language.DART,
    # Lua
    ".lua": Language.LUA,
    # Elixir
    ".ex": Language.ELIXIR, ".exs": Language.ELIXIR,
    # Haskell
    ".hs": Language.HASKELL, ".lhs": Language.HASKELL,
}

# ── Languages with full tool support ─────────────────────
# Tier-1: static analysis + integrated test runner + LLM fix
TIER1_LANGUAGES = {
    Language.PYTHON, Language.JAVASCRIPT, Language.TYPESCRIPT,
    Language.GO, Language.JAVA, Language.RUBY, Language.RUST, Language.CSHARP,
}

# ── Project-file fingerprints (boost counts for mixed repos) ─
PROJECT_FILE_HINTS: list[tuple[str, Language]] = [
    ("go.mod",            Language.GO),
    ("go.sum",            Language.GO),
    ("Cargo.toml",        Language.RUST),
    ("Cargo.lock",        Language.RUST),
    ("pom.xml",           Language.JAVA),
    ("build.gradle",      Language.JAVA),
    ("build.gradle.kts",  Language.KOTLIN),
    ("pubspec.yaml",      Language.DART),
    ("mix.exs",           Language.ELIXIR),
    ("stack.yaml",        Language.HASKELL),
    ("cabal.project",     Language.HASKELL),
    ("composer.json",     Language.PHP),
    ("Package.swift",     Language.SWIFT),
    ("Gemfile",           Language.RUBY),
    ("Gemfile.lock",      Language.RUBY),
]


def language_detector(state: AgentState) -> dict:
    """
    Node 2: Detect primary and all languages from file extensions and
    project-file fingerprinting. Supports every language in the Language enum.
    No language is skipped — all repos receive at minimum LLM-based analysis.
    """
    emit(state, "node_start", "detect_lang", iteration=state["current_iteration"])

    repo_path    = state.get("repo_local_path", "")
    source_files = state.get("source_files", [])
    counts: Counter = Counter()

    # ── Count by extension ────────────────────────────────
    for filepath in source_files:
        ext = Path(filepath).suffix.lower()
        lang = EXTENSION_MAP.get(ext)
        if lang:
            counts[lang] += 1

    # ── Boost by project-file fingerprints ───────────────
    if repo_path:
        for hint_file, lang in PROJECT_FILE_HINTS:
            if os.path.exists(os.path.join(repo_path, hint_file)):
                counts[lang] += 10
                logger.debug("Project hint file found: %s → %s", hint_file, lang.value)

    if not counts:
        primary  = Language.UNKNOWN
        detected = [Language.UNKNOWN.value]
    else:
        primary  = counts.most_common(1)[0][0]
        detected = [lang.value for lang, _ in counts.most_common()]

    # Derive support tier for logging + UI
    support_tier = (
        "full"    if primary in TIER1_LANGUAGES else
        "partial" if primary != Language.UNKNOWN else
        "none"
    )

    logger.info(
        "Language detection complete: primary=%s tier=%s all=%s",
        primary.value, support_tier, detected[:6],
    )

    # Only set skip_reason when we have truly zero recognisable files
    skip_reason: str | None = None
    if primary == Language.UNKNOWN:
        skip_reason = (
            "No recognisable source files detected. "
            "Please ensure the repository contains source code files."
        )

    emit(
        state, "node_end", "detect_lang",
        primary_language=primary.value,
        support_tier=support_tier,
    )

    return {
        "primary_language":   primary.value,
        "detected_languages": detected,
        "skip_reason":        skip_reason,
    }
