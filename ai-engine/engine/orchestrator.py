# ai-engine/engine/orchestrator.py

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from engine.state import AgentState, RunStatus, build_initial_state
from engine.nodes.repo_analyzer import repo_analyzer
from engine.nodes.language_detector import language_detector
from engine.nodes.static_analyzer import static_analyzer
from engine.nodes.test_runner import test_runner
from engine.nodes.failure_classifier import failure_classifier
from engine.nodes.fix_generator import fix_generator
from engine.nodes.patch_applier import patch_applier
from engine.nodes.git_commit import git_commit
from engine.nodes.create_pull_request import create_pull_request
from engine.nodes.ci_monitor import ci_monitor
from engine.nodes.finalize import finalize

logger = logging.getLogger(__name__)


# ── Conditional edge functions ────────────────────────────

def should_fix(state: AgentState) -> Literal["fix_generator", "finalize"]:
    """
    After classification: fix if THIS iteration found failures, else finalize.
    Uses current_iteration_failures so we don't re-process already-fixed issues
    from prior iterations.
    """
    # Use per-iteration failures when available, fall back to all failures
    failures = state.get("current_iteration_failures") or state.get("failures", [])
    if failures:
        return "fix_generator"
    return "finalize"


def should_iterate(state: AgentState) -> Literal["static_analyzer", "finalize"]:
    """
    After CI monitor: iterate again if still failing and under the limit.
    Increments current_iteration and resets per-iteration state before looping.
    """
    final_status    = state.get("final_status")
    current_iter    = state.get("current_iteration", 1)
    max_iterations  = state.get("max_iterations", 5)

    if final_status == RunStatus.PASSED.value:
        logger.info("CI passed — finalizing")
        return "finalize"

    if current_iter >= max_iterations:
        logger.info(
            "Max iterations (%d) reached — finalizing with status: %s",
            max_iterations, final_status,
        )
        return "finalize"

    logger.info(
        "CI still failing — starting iteration %d/%d",
        current_iter + 1, max_iterations,
    )
    return "static_analyzer"


def should_commit(state: AgentState) -> Literal["git_commit", "finalize"]:
    """After patch_applier: only commit if not read_only and fixes exist."""
    from engine.state import FixStatus
    if state.get("read_only"):
        return "finalize"
    # Use per-iteration fixes when available
    fixes = (
        state.get("current_iteration_fixes")
        or [f for f in state.get("fixes", []) if f.status == FixStatus.FIXED]
    )
    applied = [f for f in fixes if f.status == FixStatus.FIXED]
    if applied:
        return "git_commit"
    return "finalize"


# ── Build the graph ───────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────
    graph.add_node("repo_analyzer",      repo_analyzer)
    graph.add_node("language_detector",  language_detector)
    graph.add_node("static_analyzer",    static_analyzer)
    graph.add_node("test_runner",        test_runner)
    graph.add_node("failure_classifier", failure_classifier)
    graph.add_node("fix_generator",      fix_generator)
    graph.add_node("patch_applier",      patch_applier)
    graph.add_node("git_commit",         git_commit)
    graph.add_node("create_pull_request", create_pull_request)
    graph.add_node("ci_monitor",         ci_monitor)
    graph.add_node("finalize",           finalize)

    # ── Entry point ───────────────────────────────────────
    graph.set_entry_point("repo_analyzer")

    # ── Linear edges ─────────────────────────────────────
    graph.add_edge("repo_analyzer",      "language_detector")
    graph.add_edge("language_detector",  "static_analyzer")
    graph.add_edge("static_analyzer",    "test_runner")
    graph.add_edge("test_runner",        "failure_classifier")

    # ── Conditional: fix or finalize ──────────────────────
    graph.add_conditional_edges(
        "failure_classifier",
        should_fix,
        {
            "fix_generator": "fix_generator",
            "finalize":      "finalize",
        },
    )

    graph.add_edge("fix_generator", "patch_applier")

    # ── Conditional: commit or finalize ───────────────────
    graph.add_conditional_edges(
        "patch_applier",
        should_commit,
        {
            "git_commit": "git_commit",
            "finalize":   "finalize",
        },
    )

    graph.add_edge("git_commit",         "create_pull_request")
    graph.add_edge("create_pull_request", "ci_monitor")

    # ── Conditional: iterate or finalize ──────────────────
    graph.add_conditional_edges(
        "ci_monitor",
        should_iterate,
        {
            "static_analyzer": "static_analyzer",
            "finalize":        "finalize",
        },
    )

    graph.add_edge("finalize", END)

    return graph


# ── Compiled graph singleton ──────────────────────────────
_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


# ── Public entry point ────────────────────────────────────

def run_agent(
    repo_url: str,
    branch_prefix: str = "",
    github_token: str | None = None,
    max_iterations: int = 5,
    read_only: bool = False,
    observer=None,
) -> AgentState:
    """
    Main entry point for the agent.
    Returns the final AgentState after the graph completes.
    """
    logger.info(
        "Starting agent run: repo=%s branch_prefix=%s read_only=%s",
        repo_url, branch_prefix, read_only,
    )

    initial_state = build_initial_state(
        repo_url=repo_url,
        branch_prefix=branch_prefix,
        github_token=github_token,
        max_iterations=max_iterations,
        read_only=read_only,
        observer=observer,
    )

    graph = get_compiled_graph()

    try:
        final_state = graph.invoke(initial_state)
        logger.info(
            "Agent run complete: status=%s fixes=%d iterations=%d",
            final_state.get("final_status"),
            len(final_state.get("fixes", [])),
            final_state.get("current_iteration", 1),
        )
        return final_state

    except Exception as e:
        logger.exception("Agent run crashed: %s", e)
        # Return a minimal failed state so callers always get a structured response
        initial_state["final_status"] = RunStatus.FAILED.value
        initial_state["agent_errors"] = [
            f"Agent run crashed with unhandled exception: {type(e).__name__}: {e}"
        ]
        return initial_state
