<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0 (initial population)

Modified principles: N/A (first fill of template)

Added sections:
  - I. Multi-Agent Orchestration
  - II. API-First Backend
  - III. Incremental & Recoverable Execution
  - IV. Observability & Export
  - V. Simplicity & YAGNI
  - Runtime Constraints
  - Development Workflow

Removed sections: None (template placeholders replaced)

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check section already present; gates align
  ✅ .specify/templates/spec-template.md — Functional requirements format compatible
  ✅ .specify/templates/tasks-template.md — Phase structure compatible; observability & export tasks apply
  ⚠ .specify/templates/agent-file-template.md — Not reviewed; no constitution refs expected
  ⚠ .specify/templates/checklist-template.md — Not reviewed; no constitution refs expected

Follow-up TODOs:
  - TODO(RATIFICATION_DATE): Exact project start date uncertain; set to earliest known commit era (2025-Q4).
    Update when confirmed.
  - TODO(COMMANDS_DIR): .specify/templates/commands/ directory is empty; no command files to update.
-->

# AI Playlet Agent Constitution

## Core Principles

### I. Multi-Agent Orchestration

The system MUST be structured as a coordinated multi-agent pipeline: a **Planner** produces the
story outline, **Role agents** embody characters, a **Director** injects runtime instructions, and
a **Supervisor** observes without interfering unless triggered. Each agent has a single, well-defined
responsibility and MUST NOT conflate concerns from another agent's domain.

**Rationale**: Short-drama generation requires coherent narrative continuity across turns. Clean agent
separation enables independent testing, hot-patching of individual agents, and traceable attribution
of each story beat.

### II. API-First Backend

All functionality MUST be exposed through a versioned REST API (FastAPI). No feature is considered
"done" until it has a corresponding HTTP endpoint. The frontend (plain HTML/CSS/JS) MUST consume
only documented API endpoints — it MUST NOT contain business logic that duplicates backend state.

**Rationale**: Separation of concerns keeps the browser client thin and ensures the system can be
driven by CLI, tests, or third-party integrations without re-implementing logic.

### III. Incremental & Recoverable Execution

Session execution MUST support pause, resume, rollback, and director-inject operations at any turn
boundary. The `planned` mode MUST gate episode start behind outline approval. The `free` mode MUST
produce a minimum viable planner output via deterministic rules — never silently fail to a blank
state.

**Rationale**: LLM generation is non-deterministic and expensive. Users MUST be able to course-correct
mid-session without restarting, preserving invested context and computation.

### IV. Observability & Export

Every session MUST produce an exportable transcript (台本). Structured logging MUST go to
`log/server/`. The frontend MUST surface model/API configuration errors at startup via a blocking
setup modal before any generation is attempted. Endpoints MUST return actionable error messages
(not silent 500s) when configuration is missing.

**Rationale**: Creators need a deliverable artifact, and operators need diagnosable logs. Opaque
failures waste user time and hide integration bugs.

### V. Simplicity & YAGNI

New code MUST start as the simplest thing that satisfies the current requirement. Abstractions are
introduced only when a concrete second use-case exists. No speculative frameworks, no
organizational-only modules, no feature flags for single-path code paths.

**Rationale**: The codebase has already undergone significant refactors. Further complexity without
immediate justification increases maintenance burden and slows iteration.

## Runtime Constraints

- **Language/Runtime**: Python 3.11; FastAPI + Uvicorn; plain HTML/CSS/JS frontend.
- **Model interface**: OpenAI-compatible SDK (`openai` Python package). Model credentials MUST be
  supplied via `.env` (`base_url`, `api_key`, `model`). The system MUST NOT hard-code model names
  or URLs.
- **No framework coupling**: The runtime engine (`runtime/`) MUST NOT import frontend modules, and
  frontend JS MUST NOT share Python-specific schemas. Communication is JSON over HTTP only.
- **Testing**: `pytest` for backend. Tests MUST exercise real session state where practical; mock
  only external LLM calls.
- **Port**: Default `8013`. MUST be configurable via environment variable.

## Development Workflow

- All new features begin with a spec under `specs/###-feature-name/`.
- Backend routes are added in `backend/app_factory.py`; new runtime behaviors go in `runtime/`.
- Frontend changes MUST be verified in-browser against the dev server before marking complete.
- Commits MUST be atomic and reference the relevant feature or fix.
- PRs MUST verify compliance with all five Core Principles before merge.
- Breaking changes to the session API MUST increment the route version or provide a migration note
  in the PR description.

## Governance

This constitution supersedes informal conventions and verbal agreements. Amendments require:
1. A written rationale explaining which principle is affected and why the change is necessary.
2. Approval from at least one other active contributor (or the project owner if solo).
3. A migration plan if existing code violates the amended principle.

**Versioning policy**:
- MAJOR: Principle removal, redefinition, or governance restructure.
- MINOR: New principle or materially expanded guidance added.
- PATCH: Clarifications, wording fixes, non-semantic edits.

**Compliance review**: Every PR description MUST include a "Constitution Check" confirming no
principles are violated, or explicitly justifying any deviation in the Complexity Tracking section
of the plan.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm project start date | **Last Amended**: 2026-04-16
