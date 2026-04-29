# Universal LLM Agent Instructions

This document serves as the foundational rulebook for any Large Language Model (LLM) agent (e.g., Claude, GPT, Gemini, Jules, Copilot) interacting with and developing this repository.

## 1. Session Start Protocol
- **Audit Documentation:** Always enter a deep planning mode before making any code changes. Use memory tools, read this rule documentation, and learn the repo structure. Read `VISION.md`, `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, `MEMORY.md`, `DEPLOY.md`, `PROJECT_STRUCTURE.md` and `HANDOFF.md`.
- **Inventory Submodules:** Map the full directory structure and inventory all packages/submodules before any implementation work.
- **Clarification:** Ask clarifying questions using `request_user_input` or `message_user` to verify assumptions and gain absolute certainty on the requirements before using the `set_plan` tool.

## 2. Development Guidelines
- **Chunk Tasks:** Break large requirement lists into small, independent, committable units to avoid overload.
- **Git Operations:** Regularly `git pull`, `commit`, and `push` between implementing each major feature. Intelligently merge feature branches into main, update submodules, and merge upstream changes without losing functionality or causing regressions.
- **Autonomy & Momentum:** Do not stop the party. If you can complete a feature, commit/push, and proceed to the next feature autonomously, do so. Correct errors found along the way and continue researching.
- **Code Quality:** Comment code in depth (what, why, how, optimizations, bugs), but leave self-explanatory code bare.
- **Idempotency:** When implementing generative features, cache responses (e.g. DALL-E MD5 hashing) and respect CLI flags like `--skip-render` to avoid duplicate API charges.

## 3. Documentation Requirements
- Maintain extensive project documentation in the `/docs` directory including `VISION.md`, `ROADMAP.md`, `TODO.md`, `IDEAS.md`, `DEPLOY.md`, `MEMORY.md`, `CHANGELOG.md`, `PROJECT_STRUCTURE.md`.
- Ensure there is an `AGENTS.md` (and related `CLAUDE.md`, `GEMINI.md`, `GPT.md` etc) containing these exact rules at the project root.
- Document inputs and decisions in extreme detail in `HANDOFF.md` before finishing a session.

## 4. Versioning Protocol
- Track a single global version number in the root `VERSION` file and log the history in `docs/CHANGELOG.md`.
- Display the version number prominently in the UI.
- Every build should have a new version number.
- Always reference version bumps in `git commit` messages.

## 5. End of Session Protocol
- Use memory tools to update internal state.
- Update all rule documentation to match any new paradigms learned during the session.
- Update project documentation in comprehensive detail.
- Commit and push changes.

## 6. Project Specific Architecture Rules
- Do not add heavy ML blocking calls into `app.py`. The Streamlit UI must remain a fast gateway. Route ML tasks to the RabbitMQ `renderer` microservice.
