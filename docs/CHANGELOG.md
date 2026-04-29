# Changelog

All notable changes to this project will be documented in this file.

## [1.25.1] - Current
### Added
- **Exhaustive Documentation Pivot**: Massively expanded `VISION.md`, `ROADMAP.md`, `TODO.md`, `IDEAS.md`, `MEMORY.md`, and `HANDOFF.md` to capture the new microservices architecture and absolute autonomous generation goals.
- **Universal LLM Agent Rules**: Prepared rollout of universal instruction sets (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `GPT.md`, `copilot-instructions.md`) to standardize documentation, versioning, and feature progression across all future AI agent sessions.
- **Project Structure Documentation**: Added tracking for dependencies, libraries, and architecture structure.

## [1.25.0] - Previous
### Added
- **Microservice Architecture Pivot**: Decoupled the monolithic Streamlit script into a highly scalable, distributed microservice architecture.
- **RabbitMQ Integration**: Established a message broker using `pika` to orchestrate jobs between the UI and backend ML processes.
- **Renderer Worker Daemon**: Built the `services/renderer` headless daemon to asynchronously consume rendering tasks.
- **Docker Compose Orchestration**: Introduced `docker-compose.yml` defining the `web`, `rabbitmq`, and `renderer` cluster environment.

## [1.24.0] - Previous
- **WebRTC Foundation**: Integrated `streamlit-webrtc` into `app.py` for future low-latency interactive DJ previewing.

*(Previous changelog entries truncated for brevity)*
