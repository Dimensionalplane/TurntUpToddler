# Frontend Refactoring Implementation Plan

## 1. Goal
Migrate the existing Streamlit frontend (`hymn_remaker/app.py`) to a modern React/Next.js stack while keeping the Python AI pipeline robustly decoupled via a FastAPI backend (`hymn_remaker/api.py`).

## 2. Directory Structure
Create a new directory at the project root for the frontend:
```text
/frontend
  /public
  /src
    /app              (Next.js App Router)
      layout.tsx
      page.tsx        (Automated Pipeline Dashboard)
      /editor         (Hymn Editor Tab)
        page.tsx
      /history        (Generation History Tab)
        page.tsx
    /components       (Reusable UI elements)
      /Sidebar.tsx
      /FileUploader.tsx
      /Player.tsx
      /MetadataEditor.tsx
      /RadioStreamer.tsx
    /lib              (API Client & Utils)
      api.ts          (Axios wrappers for FastAPI)
  package.json
  next.config.js
```

## 3. Backend API Updates (FastAPI)
The existing FastAPI backend needs expansion to handle Streamlit-exclusive features:
1. **Interactive Review Endpoint:** Streamlit pauses the script execution natively for `interactive_mode`. We need a split flow:
   - `POST /api/v1/generate/init`: Uploads file, extracts metadata, and pauses. Returns metadata.
   - `POST /api/v1/generate/resume`: Accepts modified metadata from the frontend and resumes AI generation.
2. **Hymn Editor APIs:**
   - `POST /api/v1/editor/preview`: Render and return audio.
   - `POST /api/v1/editor/metadata`: Extract metadata from `.mxl`.
3. **Radio Streamer APIs:**
   - `POST /api/v1/radio/start`: Start the RTMP stream.
   - `POST /api/v1/radio/stop`: Stop stream.
   - `POST /api/v1/radio/skip`: Skip track.
   - `GET /api/v1/radio/status`: Get current playing track.
4. **WebSocket/SSE for Progress Logging:**
   - Streamlit easily injects `progress_bars[file_path].progress(prog)`. FastAPI needs to expose a WebSocket or Server-Sent Events (SSE) endpoint to stream progress logs (`process_single_midi` status updates) in real-time to the React UI.

## 4. Frontend Component Mapping
- **Sidebar (Streamlit `st.sidebar`):** Global settings context (Styles, TTS, Options, Visualizer).
- **Tab 1: Pipeline (Streamlit `st.tabs[0]`):** Drag-and-drop area. Status list.
- **Tab 2: Editor (Streamlit `st.tabs[1]`):** Dedicated page for manual `.mid` testing and `.mxl` extraction.

## 5. Execution Steps
1. Bootstrap Next.js project: `npx create-next-app@latest frontend --typescript --tailwind --eslint --app`.
2. Expand `api.py` endpoints and test with Swagger UI (`/docs`).
3. Build the core React Layout and Sidebar components.
4. Build the API client in React to connect to FastAPI.
5. Implement the main Dashboard and File Uploading.
6. Implement WebSocket for live progress bars.
7. Implement the Editor tab.
8. Update Docker Compose to build and run the Next.js container alongside the FastAPI container.
9. Deprecate and remove `app.py`.
