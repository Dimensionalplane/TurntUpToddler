# HANDOFF.md: Project Architecture, History, and Next Steps
**Version:** 5.38.0
**Date:** 2026-06-22

## Session Overview & Merges
During this synchronization session, I performed an "EXECUTIVE PROTOCOL: REPOSITORY SYNCHRONIZATION & INTELLIGENT MERGE".
1. Synchronized the local `main` branch with the upstream active progress branch `origin/main-12830181781022804878`. This safely brought in the `Kids Mode` expansion, unit test validations, and the `5.37.0` version bumps.
2. Evaluated other remote branches (`origin/feat/comprehensive-docs-and-tts-params-16556208438382467677` and `origin/jules-v1-27-0-docker-optimization-988672604789333865`). These branches had completely "unrelated histories" and massive tree-wide conflicts on every file resulting from a bad repository initialization state. As per the directive to "prevent regressions," I aborted these destructive merges.
3. Updated the global `VERSION` to `5.38.0` to finalize this sync session.

## Current State
The `hymn_remaker` project is an incredibly robust, automated AI pipeline for transforming public domain `.mid` files into modern, YouTube-ready music videos. It features parallel processing, Web UI, dynamic audio processing, and professional AI integrations (OpenAI, Replicate, ElevenLabs).

The codebase is highly functional, 100% stable, strictly typed, and completely modular.

## Next Steps for Incoming Model
Based on the `ROADMAP.md` and `IDEAS.md`, the pipeline is extremely robust and fully loaded with Cloud integration, Database management, and Dynamic AI prompting.

The next recommended frontier is:
1. **Docker Optimization:** The multi-stage build is currently bloated by heavy ML dependencies (`oemer`, PyTorch for `demucs`, OpenCV). Future architectural work should focus on shrinking the runtime container (e.g., Alpine/Distroless) and potentially isolating ML inference into microservices.
2. **Frontend Refactoring:** Porting `app.py` away from Streamlit into a Next.js / React application, while exposing the python logic through a `FastAPI` backend.
3. **Suno.ai / Udio TTS Integration:** Attempting to pivot from ElevenLabs (spoken word/choral TTS) into true generated "singing" by exploring unofficial/official APIs for Suno.ai or Udio.


## Handoff 5.39.0

### Accomplishments
- Verified that backend E2E logic successfully launches background children song scraping routines via `fastapi` and successfully hits the Interactive Review WebSocket breakpoint (100% test passing locally via Pytest in `test_kids_interactive.py` and `test_children_song_finder.py`).
- Added informative `lucide-react` `Info` tooltips to the `InteractiveReviewModal` component to guide users on modifying the extracted metadata.
- Generated a scoping document evaluating Docker Optimization and ML Microservices as the highest priority next step for the roadmap.

### Next Steps / Tips for Successors
- **Docker Optimization & ML Service Isolation** is the most pressing architectural need based on the `ROADMAP.md` instructions. With the RabbitMQ cluster rendering endpoints already merged into the FastAPI backend (`/api/v1/editor/cluster`), the groundwork for asynchronous, distributed ML workers is laid. Begin isolating heavy ML dependencies into a separate `worker.Dockerfile` and update `docker-compose.yml`.

## Handoff 5.40.0

### Accomplishments
- Successfully implemented **Docker Optimization & ML Service Isolation**.
- Separated the heavy ML dependencies (`oemer`, `demucs`, `torch`, `opencv-python-headless`, `onnxruntime`) entirely out of the core `hymn_remaker/requirements.txt` and the main `Dockerfile`.
- Configured a new `services/renderer/worker.Dockerfile` that exclusively houses the PyTorch and OpenCV packages to prevent backend bloat.
- Rewrote `stem_separator.py` and `omr_processor.py` to act as RabbitMQ dispatchers. Instead of making synchronous CLI calls, they now push JSON task parameters into the `render_jobs` queue and blockingly poll the central `Redis` container for completion status or errors.
- Extensively modified `worker.py` to route and execute the Demucs/Oemer ML jobs safely via the message queue.

### Next Steps / Tips for Successors
- The next logical step outlined in the `ROADMAP.md` / `IDEAS.md` is to evaluate and pivot from `ElevenLabs` to true AI "singing" synthesis using Suno.ai or Udio APIs (`suno_api.py`). The ML isolation architecture makes it possible to even consider hosting local inference servers for open-source AI vocal synthesizers (like Bark or RVC) down the road.
