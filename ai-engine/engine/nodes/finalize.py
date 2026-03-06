# ai-engine/engine/nodes/finalize.py

import json
import os
import logging
from datetime import datetime, timezone

from engine.state import AgentState, FixStatus, RunStatus
from engine.config import calculate_score
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)


def finalize(state: AgentState) -> dict:
    """
    Node 11: Compute final score, timing, and write results.json.
    Always the last node in the graph.
    """
    emit(state, "node_start", "final", iteration=state["current_iteration"])

    end_time = datetime.now(timezone.utc).isoformat()
    start_time = state.get("start_time")

    # ── Compute total time ────────────────────────────────
    total_seconds = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            total_seconds = (end_dt - start_dt).total_seconds()
        except Exception:
            pass

    # ── Compute score ─────────────────────────────────────
    total_commits = len(state.get("commits", []))
    score_data = calculate_score(
        total_time_seconds=total_seconds or 9999,
        total_commits=total_commits,
    )

    from engine.state import ScoreCard
    score = ScoreCard(
        base_score=score_data["base_score"],
        speed_bonus=score_data["speed_bonus"],
        efficiency_penalty=score_data["efficiency_penalty"],
    )

    # ── Determine final status ────────────────────────────
    ci_runs = state.get("ci_runs", [])
    existing_status = state.get("final_status")
    skip_reason = state.get("skip_reason")
    failures = state.get("failures", [])

    if existing_status == RunStatus.PASSED.value:
        final_status = RunStatus.PASSED.value
    elif ci_runs and ci_runs[-1].status == RunStatus.PASSED:
        final_status = RunStatus.PASSED.value
    elif not failures and skip_reason:
        # Nothing to fix — unsupported language, no issues found, etc.
        final_status = RunStatus.NO_ISSUES.value
    else:
        fixes = state.get("fixes", [])
        all_fixed = fixes and all(f.status == FixStatus.FIXED for f in fixes)
        final_status = RunStatus.PASSED.value if all_fixed else RunStatus.FAILED.value

    # ── Build results payload ─────────────────────────────
    fixes        = state.get("fixes", [])
    failures     = state.get("failures", [])
    agent_errors = state.get("agent_errors", [])

    results = {
        "run_summary": {
            "repo_url":               state["repo_url"],
            "branch_prefix":          state.get("branch_prefix", ""),
            "branch_name":            state.get("branch_name"),
            "primary_language":       state.get("primary_language", "unknown"),
            "detected_languages":     state.get("detected_languages", []),
            "total_failures_detected": len(failures),
            "total_fixes_applied":    len([f for f in fixes if f.status == FixStatus.FIXED]),
            "total_fixes_failed":     len([f for f in fixes if f.status == FixStatus.FAILED]),
            "total_fixes_skipped":    len([f for f in fixes if f.status == FixStatus.SKIPPED]),
            "iterations_run":         state.get("current_iteration", 1),
            "max_iterations":         state.get("max_iterations", 5),
            "final_ci_status":        final_status,
            "skip_reason":            skip_reason,
            "start_time":             start_time,
            "end_time":               end_time,
            "total_time_seconds":     total_seconds,
        },
        "score_breakdown": score.model_dump(),
        "fixes": [
            {
                "file":           f.file,
                "bug_type":       f.bug_type.value,
                "line_number":    f.line,
                "commit_message": f.commit_message,
                "status":         f.status.value,
                "diff":           f.diff if f.diff else "",
            }
            for f in fixes
        ],
        "ci_timeline": [
            {
                "iteration":       r.iteration,
                "status":          r.status.value,
                "timestamp":       r.timestamp,
                "iteration_label": f"{r.iteration}/{state['max_iterations']}",
            }
            for r in ci_runs
        ],
        "agent_output": [f.to_agent_output() for f in failures],
        # Tool-level errors (missing tools, timeouts, infra issues)
        "agent_errors":  agent_errors,
    }

    # ── Write results.json to repo workspace ─────────────
    repo_path = state.get("repo_local_path")
    if repo_path and os.path.exists(repo_path):
        results_path = os.path.join(repo_path, "results.json")
        try:
            with open(results_path, "w") as fp:
                json.dump(results, fp, indent=2, default=str)
            logger.info("results.json written to %s", results_path)
        except Exception as e:
            logger.warning("Could not write results.json: %s", e)

    emit(state, "node_end", "final",
         final_status=final_status,
         failures_count=len(failures),
         fixes_count=len([f for f in fixes if f.status == FixStatus.FIXED]),
         skip_reason=skip_reason,
         agent_errors=agent_errors,
         iterations_run=state.get("current_iteration", 1))

    return {
        "end_time": end_time,
        "total_time_seconds": total_seconds,
        "final_status": final_status,
        "score": score,
    }
