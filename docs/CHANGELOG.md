# Changelog

All notable changes to this project will be documented in this file.

## [1.26.0] - Current
### Added
- **Multi-Voice Spatial Expansion via PyRubberband**: Upgraded the ElevenLabs choral harmony algorithm. By replacing crude framerate shifting with high-fidelity `pyrubberband` pitch-shifting, parallel vocal tracks are now perfectly pitch-shifted (+4 and +7 semitones) without altering their temporal duration. This results in significantly clearer, crisper multi-part harmonies.

## [1.25.1] - Previous
### Added
- **Redis Render Polling System**: Connected the Streamlit UI to a Redis state store to actively poll and reflect the status of tasks queued in the RabbitMQ render cluster.
- **Headless Worker Microservice**: Added `worker.py` daemon capable of pulling from RabbitMQ and updating Redis.
- **Exhaustive Documentation Pivot**: Massively expanded `VISION.md`, `ROADMAP.md`, `TODO.md`, `LIBRARIES.md`, and `HANDOFF.md` to capture the new microservices architecture and absolute autonomous generation goals.
- **Universal LLM Agent Rules**: Prepared rollout of universal instruction sets (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `GPT.md`, `copilot-instructions.md`) to standardize documentation, versioning, and feature progression across all future AI agent sessions.
