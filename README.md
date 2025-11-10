# ADW Showcase: Simple To-Do CLI

> A minimal demonstration of **Agent-Driven Workflow (ADW)** - an AI-powered software development automation system.

## What is ADW?

**ADW (Agent-Driven Workflow)** is an intelligent automation system that transforms GitHub issues into working code through AI agents. It integrates GitHub with Claude Code CLI to automatically:

1. **PLAN** - Classify the issue, create a branch, and generate an implementation plan
2. **BUILD** - Implement the solution based on the plan
3. **TEST** - Run comprehensive tests with automatic failure resolution
4. **REVIEW** - Perform code review checking for quality, security, and performance
5. **DOCUMENT** - Generate comprehensive documentation including README updates and docstrings

Think of it as a **fully automated developer** that can take requirements and turn them into tested, reviewed, and documented production-ready code with pull requests.

## What This Showcase Demonstrates

This repository contains a **minimal To-Do CLI application** that demonstrates the complete ADW workflow:

- **Empty starting point** - The `todo/cli.py` starts with just comments
- **Real issue** - A GitHub issue describes what needs to be built
- **Automated development** - ADW classifies, plans, implements, tests, reviews, and documents the solution
- **Generated PR** - Complete with implementation, tests, code review, and documentation

### The Workflow in Action

```
GitHub Issue Created
        ↓
ADW Classifies: "feature"
        ↓
Generates Branch: "feat-issue-1-adw-abc12345-todo-commands"
        ↓
Creates Plan: specs/issue-1-adw-abc12345-sdlc_planner-todo-commands.md
        ↓
Implements Code: todo/cli.py (add, list, remove functions)
        ↓
Writes Tests: tests/test_todo.py (comprehensive test suite)
        ↓
Runs Tests: Automatically fixes failures up to 4 times
        ↓
Reviews Code: Checks quality, security, performance
        ↓
Generates Docs: Updates README and adds docstrings
        ↓
Creates Pull Request: Production-ready!
```

## Prerequisites

Before running the demo, ensure you have:

1. **Claude Code CLI** - [Installation guide](https://docs.claude.com)
   ```bash
   # Verify installation
   claude --version
   ```

2. **GitHub CLI** - [Installation guide](https://cli.github.com/)
   ```bash
   # Install and authenticate
   gh auth login
   ```

3. **Python 3.11+** with `uv` package manager
   ```bash
   # Install uv
   pip install uv
   ```

4. **Git** - For version control operations

## Setup

### 1. Clone this repository
```bash
git clone https://github.com/YOUR_USERNAME/adw-showcase-todo.git
cd adw-showcase-todo
```

### 2. Configure environment variables
```bash
# Copy the sample environment file
cp .env.sample .env

# Edit .env if needed (default values usually work)
# CLAUDE_CODE_PATH=claude  # Path to Claude CLI
```

### 3. Install dependencies
```bash
uv sync
```

## Running the Demo

### Option 1: Complete 5-Phase Workflow (Recommended)

Run the complete PLAN → BUILD → TEST → REVIEW → DOCUMENT workflow:

```bash
# First, create a GitHub issue using the provided template
gh issue create --title "Implement add and list commands for To-Do CLI" \
                --body-file DEMO_ISSUE.md

# Note the issue number (e.g., #1)

# Run the full 5-phase ADW workflow
uv run adws/adw_plan_build_test_review_document.py <issue-number>
```

**What happens:**
1. **PLAN**: ADW fetches and classifies the issue, creates branch, generates implementation plan
2. **BUILD**: Implements the To-Do CLI with add/list/remove commands
3. **TEST**: Writes and runs comprehensive tests (with automatic failure resolution)
4. **REVIEW**: Performs code review checking quality, security, and performance
5. **DOCUMENT**: Generates comprehensive documentation and docstrings
6. Creates a production-ready pull request

### Option 1b: 3-Phase Workflow (Faster)

Run just PLAN → BUILD → TEST (without review and documentation):

```bash
# Run the 3-phase workflow
uv run adws/adw_plan_build_test.py <issue-number>
```

### Option 2: Step-by-Step Workflow

Run each phase individually to see the process:

```bash
# Step 1: PLAN phase
uv run adws/adw_plan.py <issue-number>
# Output: Creates branch, generates plan, pushes to GitHub

# Step 2: BUILD phase
uv run adws/adw_build.py <issue-number> <adw-id>
# Output: Implements code, pushes changes

# Step 3: TEST phase
uv run adws/adw_test.py <issue-number>
# Output: Runs tests, auto-fixes failures, posts results

# Step 4: REVIEW phase
uv run adws/adw_review.py <issue-number>
# Output: Performs code review, posts findings, commits results

# Step 5: DOCUMENT phase
uv run adws/adw_document.py <issue-number>
# Output: Generates documentation, updates README, commits changes
```

### Option 3: Automated Triggers

ADW can automatically process issues:

**Webhook (Real-time):**
```bash
# Start webhook server
uv run adws/adw_triggers/trigger_webhook.py

# In another terminal, expose it (requires ngrok or similar)
./scripts/expose_webhook.sh
```

**Cron (Polling every 20s):**
```bash
uv run adws/adw_triggers/trigger_cron.py
```

Trigger by:
- Creating a new issue (automatic)
- Commenting "adw" on any issue

## Expected Output

### File Structure After ADW Runs

```
adw-showcase-todo/
├── todo/
│   └── cli.py              # ✅ Fully implemented with add/list/remove
├── tests/
│   └── test_todo.py        # ✅ Comprehensive test suite
├── specs/
│   └── issue-1-adw-abc12345-sdlc_planner-todo-commands.md  # Implementation plan
├── agents/
│   └── abc12345/           # ADW execution logs and state
│       ├── adw_state.json
│       ├── sdlc_planner/
│       ├── sdlc_implementor/
│       └── test_runner/
└── todos.json              # Created by the CLI at runtime
```

### Generated Pull Request

The PR will include:
- **Branch**: `feat-issue-1-adw-abc12345-todo-commands`
- **Commits**:
  - Plan commit with implementation spec
  - Implementation commit with working code
  - Test commit with results
- **Description**: AI-generated summary of changes
- **Attribution**: "Generated with Claude Code"

### Example To-Do CLI Usage

After ADW completes, the CLI will work like this:

```bash
# Add a todo
todo add "Buy groceries"
todo add "Write documentation"

# List all todos
todo list
# Output:
# 1. Buy groceries
# 2. Write documentation

# Remove a todo
todo remove 1

# List again
todo list
# Output:
# 1. Write documentation
```

## Understanding ADW Components

### Slash Commands (.claude/commands/)
Pre-defined prompts for AI agents:
- `/classify_issue` - Determines if issue is bug/feature/chore
- `/chore`, `/bug`, `/feature` - Generate implementation plans
- `/implement` - Execute the plan
- `/test` - Run test suite
- `/resolve_failed_test` - Auto-fix test failures

### ADW Modules (adws/adw_modules/)
- `agent.py` - Claude Code CLI integration
- `workflow_ops.py` - Core business logic (classify, plan, implement)
- `git_ops.py` - Git operations (branch, commit, push)
- `github.py` - GitHub API operations
- `state.py` - Persistent workflow state management
- `data_types.py` - Type-safe data models

### Workflow Scripts (adws/)
- `adw_plan.py` - Planning phase
- `adw_build.py` - Implementation phase
- `adw_test.py` - Testing phase
- `adw_plan_build.py` - Combined plan + build
- `adw_plan_build_test.py` - Full workflow

### Triggers (adws/adw_triggers/)
- `trigger_webhook.py` - Real-time GitHub webhook processing
- `trigger_cron.py` - Polling-based automation

## Advanced Features

### Automatic Test Resolution
If tests fail, ADW automatically:
1. Analyzes the failure
2. Generates a fix using `/resolve_failed_test`
3. Re-runs tests
4. Repeats up to 4 times

### State Management
Each workflow gets a unique 8-character ID (e.g., `abc12345`) that tracks:
- Issue number
- Branch name
- Plan file location
- Issue classification
- Current phase

This enables:
- Resuming interrupted workflows
- Chaining phases together
- Debugging and auditing

### Workflow Tracking
All ADW operations are tracked:
- **Issue comments**: Progress updates with ADW ID
- **Execution logs**: `agents/{adw-id}/adw_{phase}/execution.log`
- **Agent outputs**: `agents/{adw-id}/{agent-name}/raw_output.jsonl`
- **Git commits**: Include ADW ID for traceability

## Customization

### Adding Your Own Slash Commands
Create new commands in `.claude/commands/`:

```markdown
# .claude/commands/my_command.md
Your custom prompt here...
```

### Modifying Workflow Phases
Edit the workflow scripts in `adws/` to:
- Add new phases (e.g., documentation, deployment)
- Change agent behaviors
- Customize commit messages
- Adjust retry logic

### Extending Issue Classification
Modify `classify_issue` slash command to support:
- Custom issue types beyond bug/feature/chore
- Priority levels
- Complexity estimation

## Troubleshooting

### Claude Code not found
```bash
# Set explicit path in .env
CLAUDE_CODE_PATH=/path/to/claude
```

### GitHub authentication issues
```bash
# Re-authenticate
gh auth login
gh auth status
```

### Tests not running
```bash
# Install test dependencies
uv sync

# Run tests manually
uv run pytest tests/
```

### Workflow state errors
```bash
# Clean up state
rm -rf agents/
```

## What's Next?

After running this demo, you can:

1. **Create your own issues** - Test ADW with different requirements
2. **Modify the workflow** - Add new phases or customize existing ones
3. **Integrate into your project** - Copy ADW to your own repository
4. **Scale up** - Use with more complex applications

## Architecture Diagram

```
┌─────────────────┐
│  GitHub Issue   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           ADW Orchestrator              │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │   PLAN   │─▶│  BUILD   │─▶│  TEST  ││
│  └──────────┘  └──────────┘  └────────┘│
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│        Claude Code CLI Agents           │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ sdlc_planner │  │ sdlc_implementor │ │
│  └──────────────┘  └──────────────────┘ │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ test_runner  │  │  test_resolver   │ │
│  └──────────────┘  └──────────────────┘ │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│         Git + GitHub                    │
│  • Branch creation                      │
│  • Commits                              │
│  • Pull requests                        │
│  • Issue comments                       │
└─────────────────────────────────────────┘
```

## Contributing

This is a showcase project demonstrating ADW capabilities. For the full ADW implementation, see the main repository.

## License

MIT License - See LICENSE file for details

## Learn More

- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [ADW Main Repository](#) <!-- Link to your main ADW repo -->

---

**Built with ADW** - Demonstrating the future of AI-powered software development
