# ai-engine/engine/nodes/patch_applier.py

import os
import subprocess
import logging

from engine.state import AgentState, Fix, FixStatus
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)


def patch_applier(state: AgentState) -> dict:
    """
    Node 7: Write fixed code back to disk.
    Updates fix status to FIXED or FAILED based on write success.
    """
    emit(state, "node_start", "patch", iteration=state["current_iteration"])

    fixes: list[Fix] = state.get("fixes", [])
    repo_path = state["repo_local_path"]
    updated_fixes: list[Fix] = []

    for fix in fixes:
        if fix.status != FixStatus.FIXED:
            updated_fixes.append(fix)
            continue

        abs_path = os.path.join(repo_path, fix.file)

        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(fix.after_snippet)

            # Build diff for storage
            diff_result = subprocess.run(
                ["git", "-C", repo_path, "diff", fix.file],
                capture_output=True, text=True,
            )
            fix.diff = diff_result.stdout

            logger.info("Patch applied: %s:%d", fix.file, fix.line)
            updated_fixes.append(fix)

        except Exception as e:
            logger.error("Patch failed for %s: %s", fix.file, e)
            fix.status = FixStatus.FAILED
            updated_fixes.append(fix)

        emit(state, "node_end", "patch",
             latest_fix={
                 "file": fix.file, "line": fix.line,
                 "bug_type": fix.bug_type.value, "status": fix.status.value,
                 "commit_message": fix.commit_message,
             },
             fixes_count=len([f for f in updated_fixes if f.status == FixStatus.FIXED]))

    return {"fixes": updated_fixes, "current_iteration_fixes": updated_fixes}
