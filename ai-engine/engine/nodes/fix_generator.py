# ai-engine/engine/nodes/fix_generator.py

import os
import logging
from collections import defaultdict
from langchain_core.messages import HumanMessage, SystemMessage

from engine.state import AgentState, Failure, Fix, FixStatus, BugType
from engine.config import llm, format_commit_message
from engine.nodes.utils import emit
from engine.nodes.fix_strategies import apply_rule_based_fix

logger = logging.getLogger(__name__)

# ── Module-level cache for fix results ────────────────────
# Key: (file_path, normalized_error_description)
# Value: fixed_code string
# Cache scope: per process lifetime (reset on restart)
_FIX_CACHE: dict[tuple[str, str], str] = {}

SYSTEM_PROMPT = """You are an expert software engineer specializing in automated code repair.
Your job is to fix code bugs precisely and minimally.

Rules:
- Return ONLY the fixed code for the specific file — no explanations, no markdown, no code fences
- Make the smallest possible change that fixes the bug
- Never introduce new bugs or change unrelated code
- Preserve the original code style, indentation, and structure
- If you cannot fix it, return the original code unchanged
"""

BATCH_SYSTEM_PROMPT = """You are an expert software engineer specializing in automated code repair.
Your job is to fix ALL the listed bugs in the file precisely and minimally.

Rules:
- Return ONLY the fixed code for the entire file — no explanations, no markdown, no code fences
- Fix ALL the listed bugs in a single response
- Make the smallest possible changes that fix all bugs
- Never introduce new bugs or change unrelated code
- Preserve the original code style, indentation, and structure
- If you cannot fix a bug, leave that part of the code unchanged
"""


def fix_generator(state: AgentState) -> dict:
    """
    Node 6: Generate fixes for all classified failures using the configured LLM.

    Optimizations:
    - Uses current_iteration_failures so we only fix issues found THIS iteration
    - Early stopping: Skip if tests already pass AND there are no static failures
    - Batching: Group multiple errors in same file into one LLM call
    - Caching: Skip LLM call if same error was fixed before
    - Full language support: works on any language the LLM understands
    """
    emit(state, "node_start", "fix", iteration=state["current_iteration"])

    # ── Use per-iteration failures to avoid re-fixing already-fixed issues ──
    failures: list[Failure] = (
        state.get("current_iteration_failures")
        or state.get("failures", [])
    )

    # ── Early stopping: tests already pass AND no static failures ────────────
    if state.get("test_passed", False) and not failures:
        logger.info("Tests already passing and no static failures — skipping fix generation")
        emit(state, "node_end", "fix", fixes_count=0, skipped="tests_passed")
        return {"fixes": [], "current_iteration_fixes": []}

    repo_path = state["repo_local_path"]
    primary_language = state.get("primary_language", "unknown")
    fixes: list[Fix] = []

    if not failures:
        logger.info("No failures to fix in this iteration")
        emit(state, "node_end", "fix", fixes_count=0, failures_count=0)
        return {"fixes": fixes, "current_iteration_fixes": []}

    # ── Group failures by file for batching ───────────────
    failures_by_file: dict[str, list[Failure]] = defaultdict(list)
    for failure in failures:
        failures_by_file[failure.file].append(failure)

    logger.info(
        "Iteration %d: fixing %d failures in %d files (language: %s)",
        state.get("current_iteration", 1),
        len(failures),
        len(failures_by_file),
        primary_language,
    )

    for file_path, file_failures in failures_by_file.items():
        if len(file_failures) == 1:
            fix = _generate_fix_with_cache(file_failures[0], repo_path, primary_language)
            fixes.append(fix)
        else:
            batch_fixes = _generate_batch_fix(file_failures, repo_path, primary_language)
            fixes.extend(batch_fixes)

        emit(state, "node_end", "fix",
             files_processed=len([f for f in fixes if f.status == FixStatus.FIXED]),
             fixes_count=len(fixes),
             failures_count=len(failures))

    applied = len([f for f in fixes if f.status == FixStatus.FIXED])
    failed  = len([f for f in fixes if f.status == FixStatus.FAILED])
    skipped = len([f for f in fixes if f.status == FixStatus.SKIPPED])
    logger.info(
        "Fix generation done: applied=%d failed=%d skipped=%d",
        applied, failed, skipped,
    )
    return {"fixes": fixes, "current_iteration_fixes": fixes}


def _normalize_error(description: str) -> str:
    """Normalize error description for cache key consistency."""
    return description.strip().lower()


def _generate_fix_with_cache(failure: Failure, repo_path: str, language: str = "") -> Fix:
    """Generate fix with caching to avoid redundant LLM calls."""
    cache_key = (failure.file, _normalize_error(failure.description))
    
    if cache_key in _FIX_CACHE:
        logger.info("Cache hit for %s: %s", failure.file, failure.description[:50])
        fixed_code = _FIX_CACHE[cache_key]
        return _apply_cached_fix(failure, repo_path, fixed_code)
    
    fix = _generate_fix(failure, repo_path, language)
    
    if fix.status == FixStatus.FIXED and fix.after_snippet:
        _FIX_CACHE[cache_key] = fix.after_snippet
    
    return fix


def _apply_cached_fix(failure: Failure, repo_path: str, fixed_code: str) -> Fix:
    """Apply a cached fix to the file."""
    abs_path = os.path.join(repo_path, failure.file)
    
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()

        logger.info("Applied cached fix to: %s", abs_path)

        # Store full fixed code — patch_applier writes it to disk
        return Fix(
            file=failure.file,
            line=failure.line,
            bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file,
                failure.line, failure.description
            ),
            status=FixStatus.FIXED,
            before_snippet=original_code[:500],
            after_snippet=fixed_code,
        )
    except Exception as e:
        logger.error("Failed to apply cached fix to %s: %s", abs_path, e)
        return Fix(
            file=failure.file, line=failure.line, bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file, failure.line, str(e)
            ),
            status=FixStatus.FAILED,
        )


def _generate_batch_fix(failures: list[Failure], repo_path: str, language: str = "") -> list[Fix]:
    """Generate fixes for multiple errors in the same file with a single LLM call."""
    if not failures:
        return []
    
    file_path = failures[0].file
    abs_path = os.path.join(repo_path, file_path)
    
    # Validate file exists
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        logger.warning("File not found or is directory for batch fix: %s", abs_path)
        return [
            Fix(
                file=f.file, line=f.line, bug_type=f.bug_type,
                commit_message=format_commit_message(
                    f.bug_type.value, f.file, f.line, f.description
                ),
                status=FixStatus.FAILED,
            )
            for f in failures
        ]
    
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()
    except Exception as e:
        logger.error("Cannot read file for batch fix %s: %s", abs_path, e)
        return [
            Fix(
                file=f.file, line=f.line, bug_type=f.bug_type,
                commit_message=format_commit_message(
                    f.bug_type.value, f.file, f.line, str(e)
                ),
                status=FixStatus.FAILED,
            )
            for f in failures
        ]
    
    # Build batched prompt
    prompt = _build_batch_prompt(failures, original_code, language)
    
    try:
        logger.info("Making batched LLM call for %d errors in %s", len(failures), file_path)
        response = llm.invoke([
            SystemMessage(content=BATCH_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        fixed_code = response.content.strip()
        
        # Strip markdown fences if model adds them
        if fixed_code.startswith("```"):
            lines = fixed_code.splitlines()
            fixed_code = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )
        
        if fixed_code == original_code or not fixed_code:
            logger.info("No changes from batch LLM fix for %s — trying rule-based fallback", file_path)
            # Try rule-based fix for each failure individually
            result_fixes = []
            current_code = original_code
            for f in failures:
                rule_fixed = apply_rule_based_fix(current_code, f.bug_type, f.description)
                if rule_fixed != current_code:
                    current_code = rule_fixed
                    result_fixes.append(Fix(
                        file=f.file, line=f.line, bug_type=f.bug_type,
                        commit_message=format_commit_message(
                            f.bug_type.value, f.file, f.line, f.description
                        ),
                        status=FixStatus.FIXED,
                        before_snippet=original_code[:500],
                        after_snippet=rule_fixed[:500],
                    ))
                else:
                    result_fixes.append(Fix(
                        file=f.file, line=f.line, bug_type=f.bug_type,
                        commit_message=format_commit_message(
                            f.bug_type.value, f.file, f.line, f.description
                        ),
                        status=FixStatus.SKIPPED,
                        before_snippet=original_code[:500],
                        after_snippet=original_code[:500],
                    ))
            # Only the first FIXED fix carries the full accumulated code for patch_applier.
            # All subsequent FIXED fixes become SKIPPED (one write per file).
            found_first = False
            for fix in result_fixes:
                if fix.status == FixStatus.FIXED:
                    if not found_first:
                        fix.after_snippet = current_code  # full accumulated fixed content
                        found_first = True
                    else:
                        fix.status = FixStatus.SKIPPED
                        fix.after_snippet = ""
            return result_fixes
        
        logger.info("Batch LLM fix generated for: %s", abs_path)

        # Create Fix objects — first failure carries the full fixed code for patch_applier to write,
        # subsequent failures for the same file are marked SKIPPED (file written once)
        result = []
        for i, f in enumerate(failures):
            result.append(Fix(
                file=f.file,
                line=f.line,
                bug_type=f.bug_type,
                commit_message=format_commit_message(
                    f.bug_type.value, f.file, f.line, f.description
                ),
                status=FixStatus.FIXED if i == 0 else FixStatus.SKIPPED,
                before_snippet=original_code[:500],
                after_snippet=fixed_code if i == 0 else "",
            ))
        return result
        
    except Exception as e:
        logger.error("Batch LLM fix generation failed for %s: %s", file_path, e)
        return [
            Fix(
                file=f.file, line=f.line, bug_type=f.bug_type,
                commit_message=format_commit_message(
                    f.bug_type.value, f.file, f.line, str(e)
                ),
                status=FixStatus.FAILED,
            )
            for f in failures
        ]


def _build_batch_prompt(failures: list[Failure], original_code: str, language: str = "") -> str:
    """Build a prompt for fixing multiple errors in one file."""
    file_path  = failures[0].file
    lang_hint  = f" ({language}" + " source file)" if language else ""
    error_list = "\n".join([
        f"  {i+1}. Line {f.line}: {f.bug_type.value} - {f.description}"
        for i, f in enumerate(failures)
    ])

    return f"""Fix ALL of the following {len(failures)} errors in this{lang_hint} file:

File: {file_path}

Errors to fix:
{error_list}

Current file content:
{original_code}

Return ONLY the complete fixed file content with ALL errors fixed. No explanations, no markdown fences."""

def _generate_fix(failure: Failure, repo_path: str, language: str = "") -> Fix:
    abs_path = os.path.join(repo_path, failure.file)

    # ── guard: must be a file not a directory ─────────────
    if not failure.file or not failure.file.strip():
        logger.warning("Empty file path in failure — skipping")
        return Fix(
            file=failure.file or "",
            line=failure.line,
            bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file or "",
                failure.line, failure.description
            ),
            status=FixStatus.SKIPPED,
        )

    if not os.path.exists(abs_path):
        logger.warning("File not found for fix: %s", abs_path)
        return Fix(
            file=failure.file,
            line=failure.line,
            bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file,
                failure.line, failure.description
            ),
            status=FixStatus.FAILED,
        )

    # ── guard: must not be a directory ────────────────────
    if os.path.isdir(abs_path):
        logger.warning("Path is a directory, not a file — skipping: %s", abs_path)
        return Fix(
            file=failure.file,
            line=failure.line,
            bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file,
                failure.line, failure.description
            ),
            status=FixStatus.SKIPPED,
        )

    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()
    except Exception as e:
        logger.error("Cannot read file %s: %s", abs_path, e)
        return Fix(
            file=failure.file, line=failure.line, bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file, failure.line, str(e)
            ),
            status=FixStatus.FAILED,
        )

    prompt = _build_prompt(failure, original_code, language)

    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        fixed_code = response.content.strip()

        # Strip markdown fences if model adds them anyway
        if fixed_code.startswith("```"):
            lines = fixed_code.splitlines()
            fixed_code = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )

        if fixed_code == original_code or not fixed_code:
            logger.info("No change from LLM for %s:%d — trying rule-based fallback", failure.file, failure.line)
            # ── Rule-based fallback ─────────────────────────────
            rule_fixed = apply_rule_based_fix(original_code, failure.bug_type, failure.description)
            if rule_fixed != original_code:
                logger.info("Rule-based fix generated for: %s", abs_path)
                return Fix(
                    file=failure.file, line=failure.line, bug_type=failure.bug_type,
                    commit_message=format_commit_message(
                        failure.bug_type.value, failure.file,
                        failure.line, failure.description
                    ),
                    status=FixStatus.FIXED,
                    before_snippet=original_code[:500],
                    after_snippet=rule_fixed,
                )

            return Fix(
                file=failure.file, line=failure.line, bug_type=failure.bug_type,
                commit_message=format_commit_message(
                    failure.bug_type.value, failure.file,
                    failure.line, failure.description
                ),
                status=FixStatus.SKIPPED,
                before_snippet=original_code[:500],
                after_snippet=fixed_code[:500],
            )

        commit_msg = format_commit_message(
            failure.bug_type.value, failure.file,
            failure.line, failure.description
        )

        # Store full fixed code — patch_applier is responsible for writing it to disk
        return Fix(
            file=failure.file,
            line=failure.line,
            bug_type=failure.bug_type,
            commit_message=commit_msg,
            status=FixStatus.FIXED,
            before_snippet=original_code[:500],
            after_snippet=fixed_code,
        )

    except Exception as e:
        logger.error("LLM fix generation failed for %s: %s", failure.file, e)
        return Fix(
            file=failure.file, line=failure.line, bug_type=failure.bug_type,
            commit_message=format_commit_message(
                failure.bug_type.value, failure.file, failure.line, str(e)
            ),
            status=FixStatus.FAILED,
        )


def _build_prompt(failure: Failure, original_code: str, language: str = "") -> str:
    lang_hint = f" {language}" if language else ""
    return f"""Fix the following {failure.bug_type.value} error in this{lang_hint} file:

File: {failure.file}
Line: {failure.line}
Error: {failure.description}

Current file content:
{original_code}

Return ONLY the complete fixed file content. No explanations, no markdown fences."""
