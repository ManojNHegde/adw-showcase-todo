#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Complete Workflow - AI Developer Workflow for the full SDLC

Usage: uv run adw_plan_build_test_review_document.py <issue-number> [adw-id]

This script runs the complete ADW pipeline with all 5 phases:
1. adw_plan.py - Planning phase
2. adw_build.py - Implementation phase
3. adw_test.py - Testing phase
4. adw_review.py - Code review phase
5. adw_document.py - Documentation phase

The scripts are chained together via persistent state (adw_state.json).
Each phase builds on the previous phase's work.
"""

import subprocess
import sys
import os

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.workflow_ops import ensure_adw_id


def run_phase(phase_name: str, script_path: str, issue_number: str, adw_id: str, extra_args: list = None) -> bool:
    """
    Run a single ADW phase.

    Args:
        phase_name: Name of the phase for display
        script_path: Path to the phase script
        issue_number: GitHub issue number
        adw_id: ADW workflow ID
        extra_args: Additional arguments to pass to the script

    Returns:
        True if successful, False otherwise
    """
    cmd = ["uv", "run", script_path, issue_number, adw_id]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"PHASE: {phase_name}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ {phase_name} phase failed with exit code {result.returncode}")
        return False

    print(f"\n✅ {phase_name} phase completed successfully")
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run adw_plan_build_test_review_document.py <issue-number> [adw-id]")
        print("\nThis runs the complete ADW workflow:")
        print("  1. PLAN - Generate implementation plan")
        print("  2. BUILD - Implement the solution")
        print("  3. TEST - Run comprehensive tests")
        print("  4. REVIEW - Perform code review")
        print("  5. DOCUMENT - Generate documentation")
        sys.exit(1)

    issue_number = sys.argv[1]
    adw_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure ADW ID exists with initialized state
    adw_id = ensure_adw_id(issue_number, adw_id)
    print(f"{'='*60}")
    print(f"ADW Complete Workflow")
    print(f"{'='*60}")
    print(f"Issue Number: #{issue_number}")
    print(f"ADW ID: {adw_id}")
    print(f"{'='*60}\n")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define phases
    phases = [
        ("PLAN", os.path.join(script_dir, "adw_plan.py"), []),
        ("BUILD", os.path.join(script_dir, "adw_build.py"), []),
        ("TEST", os.path.join(script_dir, "adw_test.py"), ["--skip-e2e"]),  # Skip E2E for simpler showcase
        ("REVIEW", os.path.join(script_dir, "adw_review.py"), []),
        ("DOCUMENT", os.path.join(script_dir, "adw_document.py"), []),
    ]

    # Run each phase sequentially
    for phase_name, script_path, extra_args in phases:
        success = run_phase(phase_name, script_path, issue_number, adw_id, extra_args)
        if not success:
            print(f"\n{'='*60}")
            print(f"❌ Workflow stopped at {phase_name} phase")
            print(f"{'='*60}")
            sys.exit(1)

    # All phases completed successfully
    print(f"\n{'='*60}")
    print(f"✅ COMPLETE WORKFLOW FINISHED SUCCESSFULLY")
    print(f"{'='*60}")
    print(f"Issue: #{issue_number}")
    print(f"ADW ID: {adw_id}")
    print(f"\nAll 5 phases completed:")
    print(f"  ✅ PLAN - Implementation plan created")
    print(f"  ✅ BUILD - Solution implemented")
    print(f"  ✅ TEST - Tests passed")
    print(f"  ✅ REVIEW - Code reviewed")
    print(f"  ✅ DOCUMENT - Documentation generated")
    print(f"\nCheck your GitHub PR for the complete implementation!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
