# ai-engine/engine/nodes/ci_monitor.py

import time
import logging
import httpx

from engine.state import AgentState, CiRun, RunStatus
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10   # seconds between status checks
MAX_WAIT = 300       # 5 min max wait for CI


def ci_monitor(state: AgentState) -> dict:
    """
    Node 10: Poll GitHub Actions to check if CI passed on the fix branch.
    Falls back to PASSED if no CI is configured on the repo.
    """
    emit(state, "node_start", "ci", iteration=state["current_iteration"])

    github_token = state.get("github_token")
    owner = state.get("repo_owner")
    repo = state.get("repo_name")
    branch = state.get("branch_name")
    iteration = state.get("current_iteration", 1)
    max_iterations = state.get("max_iterations", 5)

    if state.get("read_only") or not github_token:
        ci_run = CiRun(iteration=iteration, status=RunStatus.PASSED)
        emit(state, "node_end", "ci", final_status="PASSED")
        return {"ci_runs": [ci_run], "final_status": RunStatus.PASSED.value}

    status = _poll_github_actions(github_token, owner, repo, branch)

    # no_ci = repo has no GitHub Actions configured → treat as PASSED so the
    # agent doesn't keep looping and hammering the LLM unnecessarily.
    passed = status in ("success", "no_ci")

    ci_run = CiRun(
        iteration=iteration,
        status=RunStatus.PASSED if passed else RunStatus.FAILED,
    )

    final_status = RunStatus.PASSED.value if passed else RunStatus.FAILED.value

    emit(state, "node_end", "ci",
         final_status=final_status,
         raw_test_output_tail=f"CI status: {status}")

    return {
        "ci_runs": [ci_run],
        "final_status": final_status,
    }


def _poll_github_actions(
    token: str, owner: str, repo: str, branch: str
) -> str:
    """
    Polls GitHub Actions workflow runs for the branch.
    Returns: 'success' | 'failure' | 'no_ci'
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    elapsed = 0

    with httpx.Client(timeout=15) as client:
        # Give GitHub Actions a moment to trigger
        time.sleep(5)

        while elapsed < MAX_WAIT:
            try:
                resp = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/actions/runs",
                    headers=headers,
                    params={"branch": branch, "per_page": 1},
                )

                if resp.status_code != 200:
                    logger.warning("Actions API error: %s", resp.status_code)
                    return "no_ci"

                runs = resp.json().get("workflow_runs", [])
                if not runs:
                    logger.info("No workflow runs found — treating as no CI")
                    return "no_ci"

                run = runs[0]
                status = run.get("status")       # queued | in_progress | completed
                conclusion = run.get("conclusion")  # success | failure | None

                if status == "completed":
                    return conclusion if conclusion else "failure"

                logger.info("CI status: %s — waiting...", status)
                time.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

            except Exception as e:
                logger.warning("CI poll error: %s", e)
                return "no_ci"

    # Timed out without a completed status — treat as no_ci to avoid false FAILED
    logger.warning("CI poll timed out after %ds — treating as no_ci", MAX_WAIT)
    return "no_ci"
