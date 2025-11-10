#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Review - AI Developer Workflow for code review

Usage:
  uv run adw_review.py <issue-number> [adw-id]

Workflow:
1. Fetch GitHub issue details (if not in state)
2. Review code changes using AI
3. Post review results to issue
4. Create commit with review results
5. Push and update PR

Environment Requirements:
- CLAUDE_CODE_PATH: Path to Claude CLI
- ANTHROPIC_API_KEY: (Optional) Anthropic API key - if not provided, will use Claude CLI subscription
- GITHUB_PAT: (Optional) GitHub Personal Access Token - only if using a different account than 'gh auth login'
"""

import json
import subprocess
import sys
import os
import logging
from typing import Tuple, Optional
from dotenv import load_dotenv
from adw_modules.data_types import (
    AgentTemplateRequest,
    GitHubIssue,
    IssueClassSlashCommand,
)
from adw_modules.agent import execute_template
from adw_modules.github import (
    extract_repo_path,
    fetch_issue,
    make_issue_comment,
    get_repo_url,
)
from adw_modules.utils import make_adw_id, setup_logger, parse_json
from adw_modules.state import ADWState
from adw_modules.git_ops import commit_changes, finalize_git_operations
from adw_modules.workflow_ops import format_issue_message, create_commit, ensure_adw_id, classify_issue

# Agent name constant
AGENT_REVIEWER = "code_reviewer"


def check_env_vars(logger: Optional[logging.Logger] = None) -> None:
    """Check that all required environment variables are set."""
    required_vars = [
        "CLAUDE_CODE_PATH",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        error_msg = "Error: Missing required environment variables:"
        if logger:
            logger.error(error_msg)
            for var in missing_vars:
                logger.error(f"  - {var}")
        else:
            print(error_msg, file=sys.stderr)
            for var in missing_vars:
                print(f"  - {var}", file=sys.stderr)
        sys.exit(1)


def parse_args(
    state: Optional[ADWState] = None,
    logger: Optional[logging.Logger] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Parse command line arguments.
    Returns (issue_number, adw_id) where both may be None."""
    # If we have state from stdin, we might not need issue number from args
    if state:
        if len(sys.argv) >= 2:
            return sys.argv[1], None
        else:
            return None, None

    # Standalone mode - need at least issue number
    if len(sys.argv) < 2:
        usage_msg = [
            "Usage:",
            "  Standalone: uv run adw_review.py <issue-number> [adw-id]",
            "  Chained: ... | uv run adw_review.py",
            "Examples:",
            "  uv run adw_review.py 123",
            "  uv run adw_review.py 123 abc12345",
            "  echo '{\"issue_number\": \"123\"}' | uv run adw_review.py",
        ]
        if logger:
            for msg in usage_msg:
                logger.error(msg)
        else:
            for msg in usage_msg:
                print(msg)
        sys.exit(1)

    issue_number = sys.argv[1]
    adw_id = sys.argv[2] if len(sys.argv) > 2 else None

    return issue_number, adw_id


def run_code_review(adw_id: str, issue_number: str, logger: logging.Logger) -> dict:
    """Run code review using the /review command."""
    logger.info("Running code review...")

    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_REVIEWER, "🔍 Starting code review...")
    )

    review_template_request = AgentTemplateRequest(
        agent_name=AGENT_REVIEWER,
        slash_command="/review",
        args=[],
        adw_id=adw_id,
        model="sonnet",
    )

    logger.debug(
        f"review_template_request: {review_template_request.model_dump_json(indent=2, by_alias=True)}"
    )

    review_response = execute_template(review_template_request)

    logger.debug(
        f"review_response: {review_response.model_dump_json(indent=2, by_alias=True)}"
    )

    if not review_response.success:
        logger.error(f"Code review failed: {review_response.output}")
        make_issue_comment(
            issue_number,
            format_issue_message(
                adw_id, AGENT_REVIEWER, f"❌ Code review failed: {review_response.output}"
            )
        )
        return None

    # Parse review results
    try:
        review_results = parse_json(review_response.output, dict)
        logger.info(f"Review completed: {review_results.get('overall_assessment', 'unknown')}")
        return review_results
    except Exception as e:
        logger.error(f"Error parsing review results: {e}")
        return None


def format_review_comment(review_results: dict) -> str:
    """Format review results for GitHub issue comment."""
    if not review_results:
        return "❌ No review results available"

    assessment = review_results.get("overall_assessment", "unknown")
    summary = review_results.get("summary", "No summary provided")
    strengths = review_results.get("strengths", [])
    issues = review_results.get("issues", [])
    recommendations = review_results.get("recommendations", [])

    # Map assessment to emoji
    assessment_emoji = {
        "pass": "✅",
        "pass_with_comments": "⚠️",
        "needs_changes": "❌"
    }.get(assessment, "❓")

    comment_parts = [
        f"## {assessment_emoji} Code Review Results",
        f"",
        f"**Overall Assessment:** {assessment.upper().replace('_', ' ')}",
        f"",
        f"### Summary",
        summary,
        f""
    ]

    if strengths:
        comment_parts.append("### ✅ Strengths")
        comment_parts.append("")
        for strength in strengths:
            comment_parts.append(f"- {strength}")
        comment_parts.append("")

    if issues:
        # Group by severity
        critical = [i for i in issues if i.get("severity") == "critical"]
        major = [i for i in issues if i.get("severity") == "major"]
        minor = [i for i in issues if i.get("severity") == "minor"]
        suggestions = [i for i in issues if i.get("severity") == "suggestion"]

        for severity_name, severity_issues in [
            ("Critical Issues", critical),
            ("Major Issues", major),
            ("Minor Issues", minor),
            ("Suggestions", suggestions)
        ]:
            if severity_issues:
                emoji = {"Critical Issues": "🚨", "Major Issues": "⚠️", "Minor Issues": "ℹ️", "Suggestions": "💡"}
                comment_parts.append(f"### {emoji.get(severity_name, '')} {severity_name}")
                comment_parts.append("")
                for issue in severity_issues:
                    file = issue.get("file", "unknown")
                    line = issue.get("line", "")
                    issue_desc = issue.get("issue", "No description")
                    suggestion = issue.get("suggestion", "")
                    category = issue.get("category", "general")

                    if line:
                        comment_parts.append(f"**{file}:{line}** ({category})")
                    else:
                        comment_parts.append(f"**{file}** ({category})")
                    comment_parts.append(f"- Issue: {issue_desc}")
                    if suggestion:
                        comment_parts.append(f"- Fix: {suggestion}")
                    comment_parts.append("")

    if recommendations:
        comment_parts.append("### 📋 Recommendations")
        comment_parts.append("")
        for rec in recommendations:
            comment_parts.append(f"- {rec}")
        comment_parts.append("")

    return "\n".join(comment_parts)


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    arg_issue_number, arg_adw_id = parse_args(None)

    # Initialize state and issue number
    issue_number = arg_issue_number

    # Ensure we have an issue number
    if not issue_number:
        print("Error: No issue number provided", file=sys.stderr)
        sys.exit(1)

    # Ensure ADW ID exists with initialized state
    temp_logger = setup_logger(arg_adw_id, "adw_review") if arg_adw_id else None
    adw_id = ensure_adw_id(issue_number, arg_adw_id, temp_logger)

    # Load the state that was created/found by ensure_adw_id
    state = ADWState.load(adw_id, temp_logger)

    # Set up logger with ADW ID
    logger = setup_logger(adw_id, "adw_review")
    logger.info(f"ADW Review starting - ID: {adw_id}, Issue: {issue_number}")

    # Validate environment (now with logger)
    check_env_vars(logger)

    # Get repo information from git remote
    try:
        github_repo_url: str = get_repo_url()
        repo_path: str = extract_repo_path(github_repo_url)
    except ValueError as e:
        logger.error(f"Error getting repository URL: {e}")
        sys.exit(1)

    # Handle branch - checkout existing branch from state
    branch_name = state.get("branch_name")
    if branch_name:
        result = subprocess.run(["git", "checkout", branch_name], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to checkout branch {branch_name}: {result.stderr}")
            make_issue_comment(
                issue_number,
                format_issue_message(adw_id, "ops", f"❌ Failed to checkout branch {branch_name}")
            )
            sys.exit(1)
        logger.info(f"Checked out existing branch: {branch_name}")
    else:
        logger.warning("No branch in state, using current branch")

    make_issue_comment(
        issue_number, format_issue_message(adw_id, "ops", "✅ Starting code review")
    )

    # Run code review
    review_results = run_code_review(adw_id, issue_number, logger)

    if not review_results:
        logger.error("Code review failed")
        sys.exit(1)

    # Format and post review results
    review_comment = format_review_comment(review_results)
    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_REVIEWER, f"📊 Review Complete:\n\n{review_comment}")
    )

    logger.info("Code review completed successfully")

    # Commit the review results
    logger.info("\n=== Committing review results ===")
    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_REVIEWER, "✅ Committing review results"),
    )

    # Fetch issue details
    issue = fetch_issue(issue_number, repo_path)

    # Get issue classification
    issue_class = state.get("issue_class")
    if not issue_class:
        issue_class, error = classify_issue(issue, adw_id, logger)
        if error:
            logger.warning(f"Error classifying issue: {error}, defaulting to /chore")
            issue_class = "/chore"
        state.update(issue_class=issue_class)
        state.save("adw_review")

    commit_msg, error = create_commit(AGENT_REVIEWER, issue, issue_class, adw_id, logger)

    if error:
        logger.error(f"Error committing review results: {error}")
        make_issue_comment(
            issue_number,
            format_issue_message(
                adw_id, AGENT_REVIEWER, f"❌ Error committing review results: {error}"
            ),
        )
    else:
        logger.info(f"Review results committed: {commit_msg}")

    # Finalize git operations (push and create/update PR)
    logger.info("\n=== Finalizing git operations ===")
    finalize_git_operations(state, logger)

    # Update state
    state.save("adw_review")

    # Output state for chaining
    state.to_stdout()

    # Determine exit code based on review assessment
    assessment = review_results.get("overall_assessment", "unknown")
    if assessment == "needs_changes":
        logger.info(f"Code review completed with changes needed for issue #{issue_number}")
        make_issue_comment(
            issue_number,
            format_issue_message(adw_id, "ops", "❌ Code review requires changes"),
        )
        sys.exit(1)
    else:
        logger.info(f"Code review completed successfully for issue #{issue_number}")
        make_issue_comment(
            issue_number,
            format_issue_message(adw_id, "ops", f"✅ Code review passed: {assessment}"),
        )


if __name__ == "__main__":
    main()
