#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Document - AI Developer Workflow for documentation

Usage:
  uv run adw_document.py <issue-number> [adw-id]

Workflow:
1. Fetch GitHub issue details (if not in state)
2. Generate/update documentation using AI
3. Post documentation results to issue
4. Create commit with documentation changes
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
AGENT_DOCUMENTER = "documenter"


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
            "  Standalone: uv run adw_document.py <issue-number> [adw-id]",
            "  Chained: ... | uv run adw_document.py",
            "Examples:",
            "  uv run adw_document.py 123",
            "  uv run adw_document.py 123 abc12345",
            "  echo '{\"issue_number\": \"123\"}' | uv run adw_document.py",
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


def run_documentation(adw_id: str, issue_number: str, logger: logging.Logger) -> dict:
    """Run documentation generation using the /document command."""
    logger.info("Generating documentation...")

    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_DOCUMENTER, "📝 Starting documentation generation...")
    )

    doc_template_request = AgentTemplateRequest(
        agent_name=AGENT_DOCUMENTER,
        slash_command="/document",
        args=[],
        adw_id=adw_id,
        model="sonnet",
    )

    logger.debug(
        f"doc_template_request: {doc_template_request.model_dump_json(indent=2, by_alias=True)}"
    )

    doc_response = execute_template(doc_template_request)

    logger.debug(
        f"doc_response: {doc_response.model_dump_json(indent=2, by_alias=True)}"
    )

    if not doc_response.success:
        logger.error(f"Documentation generation failed: {doc_response.output}")
        make_issue_comment(
            issue_number,
            format_issue_message(
                adw_id, AGENT_DOCUMENTER, f"❌ Documentation generation failed: {doc_response.output}"
            )
        )
        return None

    # Parse documentation results
    try:
        doc_results = parse_json(doc_response.output, dict)
        logger.info(f"Documentation generated: {doc_results.get('summary', 'No summary')}")
        return doc_results
    except Exception as e:
        logger.error(f"Error parsing documentation results: {e}")
        return None


def format_documentation_comment(doc_results: dict) -> str:
    """Format documentation results for GitHub issue comment."""
    if not doc_results:
        return "❌ No documentation results available"

    summary = doc_results.get("summary", "No summary provided")
    files_updated = doc_results.get("files_updated", [])
    new_files = doc_results.get("new_files_created", [])
    coverage = doc_results.get("documentation_coverage", {})

    comment_parts = [
        "## 📚 Documentation Results",
        "",
        f"### Summary",
        summary,
        ""
    ]

    if files_updated:
        comment_parts.append("### 📝 Files Updated")
        comment_parts.append("")
        for file_info in files_updated:
            file_name = file_info.get("file", "unknown")
            changes = file_info.get("changes", "No details")
            sections = file_info.get("sections_added", [])

            comment_parts.append(f"**{file_name}**")
            comment_parts.append(f"- {changes}")
            if sections:
                comment_parts.append(f"- Sections added: {', '.join(sections)}")
            comment_parts.append("")

    if new_files:
        comment_parts.append("### ✨ New Files Created")
        comment_parts.append("")
        for file_info in new_files:
            file_name = file_info.get("file", "unknown")
            purpose = file_info.get("purpose", "No description")
            comment_parts.append(f"**{file_name}**")
            comment_parts.append(f"- {purpose}")
            comment_parts.append("")

    if coverage:
        funcs_documented = coverage.get("functions_documented", 0)
        total_funcs = coverage.get("total_functions", 0)
        percentage = coverage.get("coverage_percentage", 0)

        comment_parts.append("### 📊 Documentation Coverage")
        comment_parts.append("")
        comment_parts.append(f"- Functions documented: {funcs_documented}/{total_funcs}")
        comment_parts.append(f"- Coverage: {percentage}%")
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
    temp_logger = setup_logger(arg_adw_id, "adw_document") if arg_adw_id else None
    adw_id = ensure_adw_id(issue_number, arg_adw_id, temp_logger)

    # Load the state that was created/found by ensure_adw_id
    state = ADWState.load(adw_id, temp_logger)

    # Set up logger with ADW ID
    logger = setup_logger(adw_id, "adw_document")
    logger.info(f"ADW Document starting - ID: {adw_id}, Issue: {issue_number}")

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
        issue_number, format_issue_message(adw_id, "ops", "✅ Starting documentation generation")
    )

    # Run documentation generation
    doc_results = run_documentation(adw_id, issue_number, logger)

    if not doc_results:
        logger.error("Documentation generation failed")
        sys.exit(1)

    # Format and post documentation results
    doc_comment = format_documentation_comment(doc_results)
    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_DOCUMENTER, f"📊 Documentation Complete:\n\n{doc_comment}")
    )

    logger.info("Documentation generation completed successfully")

    # Commit the documentation changes
    logger.info("\n=== Committing documentation ===")
    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, AGENT_DOCUMENTER, "✅ Committing documentation"),
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
        state.save("adw_document")

    commit_msg, error = create_commit(AGENT_DOCUMENTER, issue, issue_class, adw_id, logger)

    if error:
        logger.error(f"Error committing documentation: {error}")
        make_issue_comment(
            issue_number,
            format_issue_message(
                adw_id, AGENT_DOCUMENTER, f"❌ Error committing documentation: {error}"
            ),
        )
    else:
        logger.info(f"Documentation committed: {commit_msg}")

    # Finalize git operations (push and create/update PR)
    logger.info("\n=== Finalizing git operations ===")
    finalize_git_operations(state, logger)

    # Update state
    state.save("adw_document")

    # Output state for chaining
    state.to_stdout()

    logger.info(f"Documentation completed successfully for issue #{issue_number}")
    make_issue_comment(
        issue_number,
        format_issue_message(adw_id, "ops", "✅ Documentation completed"),
    )


if __name__ == "__main__":
    main()
