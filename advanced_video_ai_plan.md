# Advanced Video Generation AI Integration Plan

## 1. Goal
Integrate advanced AI video generation models (e.g., Runway Gen-2, Luma Dream Machine) to replace the static DALL-E 3 cover art with highly dynamic, audio-reactive music videos. This fulfills the outstanding roadmap task in Phase 3.

## 2. Architecture Additions
- **New Module (`src/video_generator.py`):**
  Create an abstraction layer `AdvancedVideoGenerator` that handles prompt formulation, API communication with the video provider (e.g., Luma API), and downloading the generated `.mp4` background.
- **Pipeline Integration (`main.py`):**
  If `use_advanced_video` is toggled true, the pipeline will skip the DALL-E image generation and instead call `AdvancedVideoGenerator.generate_video(art_prompt)`.
  The resulting background video will be passed to `VideoProducer` (`src/video_uploader.py`), which will overlay the audio, subtitles, and visualizers onto the moving background instead of a static image.

## 3. API/Frontend Changes
- **Backend (`api.py`):**
  Add a `use_advanced_video: bool = Form(False)` parameter to the `/api/v1/generate` endpoint.
- **Frontend (`FileUploader.tsx` & `Sidebar.tsx`):**
  Add a toggle to enable advanced AI video generation in the frontend UI.

## 4. Execution Steps
1. Create `src/video_generator.py` with the Luma Dream Machine / Runway API stubs.
2. Update the `MusicRemaker` or `ContentGenerator` to interface with the new video module.
3. Update `main.py` to route the pipeline correctly based on the new flag.
4. Update `api.py` and the React frontend to expose the toggle.
5. Update `ROADMAP.md` to reflect progress.
