# Agent Instructions

This document provides high-level guidelines for AI agents working within the Omni-Workspace.

## Global Directives
*   All agents MUST read and adhere to `docs/UNIVERSAL_LLM_INSTRUCTIONS.md` before performing any tasks.
*   **Version Management**: Always increment the version string stored in the `VERSION` and `docs/VERSION.md` files upon feature completion. The version must be mirrored precisely in `docs/CHANGELOG.md`.
*   **Commit Formatting**: Reference the version bump clearly in your commit messages.
*   **Documentation Maintenance**: Ensure `VISION.md`, `ROADMAP.md`, `TODO.md`, `IDEAS.md`, `DEPLOY.md`, `MEMORY.md`, and `CHANGELOG.md` accurately reflect the current state of the project after any significant changes.
*   **Handoff**: Detail exactly what was done and provide an analysis of the next steps in `docs/HANDOFF.md` before completing a session.
