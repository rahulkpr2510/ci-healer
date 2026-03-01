# ai-engine/engine/nodes/fix_strategies.py

"""
Rule-based fix strategies as fallback when LLM fix_generator
returns no change or fails. Each strategy targets a specific bug type.
Import and call from fix_generator.py if LLM returns original code.
"""

import re
from engine.state import BugType


def apply_rule_based_fix(original_code: str, bug_type: BugType, description: str) -> str:
    """
    Attempts a deterministic fix based on the bug type.
    Returns fixed code, or original if no rule applies.
    """
    strategies = {
        BugType.IMPORT: _fix_unused_import,
        BugType.INDENTATION: _fix_indentation,
        BugType.LINTING: _fix_linting,
    }
    strategy = strategies.get(bug_type)
    if strategy:
        return strategy(original_code, description)
    return original_code


def _fix_unused_import(code: str, description: str) -> str:
    """Remove unused import lines identified in description."""
    # Extract module name from description
    match = re.search(r"'([^']+)'|\"([^\"]+)\"", description)
    if not match:
        return code

    module = match.group(1) or match.group(2)
    lines = code.splitlines(keepends=True)
    cleaned = [
        line for line in lines
        if not re.match(rf"^\s*import\s+{re.escape(module)}\s*$", line)
        and not re.match(rf"^\s*from\s+\S+\s+import\s+.*\b{re.escape(module)}\b", line)
    ]
    return "".join(cleaned)


def _fix_indentation(code: str, description: str) -> str:
    """Normalize mixed tabs/spaces to 4-space indentation."""
    lines = code.splitlines(keepends=True)
    fixed = []
    for line in lines:
        if "\t" in line:
            line = line.expandtabs(4)
        fixed.append(line)
    return "".join(fixed)


def _fix_linting(code: str, description: str) -> str:
    """Fix common linting issues: trailing whitespace, blank lines."""
    lines = code.splitlines()
    # Remove trailing whitespace
    lines = [line.rstrip() for line in lines]
    # Ensure file ends with single newline
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"
