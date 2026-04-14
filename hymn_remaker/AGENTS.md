# Instructions for Autonomous Agents
Welcome LLM. When operating within this repository:
1. **Always Read Context:** Begin by checking `VERSION.md`, `CHANGELOG.md`, `TODO.md`, and `ROADMAP.md` to establish current state.
2. **Versioning Protocol:** Always update `VERSION.md` on each run, adding a corresponding entry in `CHANGELOG.md` and explicitly mentioning the version bump in your git commit message.
3. **Commenting Requirement:** Any complex logic involving Threading, Web UI state, Audio Math (like `pydub` db ducking), or concurrent API limits MUST be commented with explanations detailing the *why*. Do not comment self-explanatory code.
4. **Testing Protocol:** Run `python -m pytest tests/` before committing.
5. **UI Protocol:** Use `frontend_verification_instructions` using Playwright whenever `app.py` is edited to visually ensure the layout does not break.
6. **Submodule Rules:** Automatically pull upstream changes from linked submodules and resolve conflicts defensively. Do not destroy the core feature pipeline when doing so.
