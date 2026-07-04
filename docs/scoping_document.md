# Scoping Document: Next Roadmap Item

## Current Context
With the successful forward-merge of the Kids Mode and tooltips branch, the frontend is currently a robust multi-page application with functional WebSockets, `InteractiveReviewModal` UI hooks, and `ChildrenSongFinder` scraping.

Looking at `IDEAS.md` and `ROADMAP.md`, several items remain. The prompt has requested scoping the next highest priority roadmap item.

## Highest Priority Candidates

**1. Suno.ai / Udio TTS Integration (Singing Synthesis)**
*   **Description:** Currently, the pipeline relies on ElevenLabs for text-to-speech, which produces spoken-word or choral recitations that are time-stretched to fit the instrumental. The logical next step for a *music* pipeline is integrating true AI singing models like Suno.ai or Udio.
*   **Feasibility:** High.
*   **Value:** High. This transforms the final output from a "spoken poem over music" to a "fully produced song."

**2. Docker/Container Optimization & Microservices**
*   **Description:** Shrink the runtime container. Currently, the multi-stage build is bloated by heavy ML dependencies (PyTorch, OpenCV for `oemer`, `demucs`).
*   **Feasibility:** Involves significant devops work.
*   **Value:** High (Operational). Reduces deployment costs, improves startup times.

## Recommendation for Next Iteration
**Docker Optimization & ML Service Isolation** is the most pressing architectural need based on the `HANDOFF.md` instructions. With the RabbitMQ cluster rendering endpoints already merged into the FastAPI backend (`/api/v1/editor/cluster`), the groundwork for asynchronous, distributed ML workers is laid.

*Next Action:* Begin isolating heavy ML dependencies into a separate `worker.Dockerfile` and updating `docker-compose.yml` to spin up lightweight API containers and dedicated GPU-enabled worker nodes.
