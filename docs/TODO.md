# TODO - HYMN REMAKER

## IMMEDIATE TASKS (v1.39.0+)
- [x] Integrate Dynamic AI Video generation in pipeline (v1.40.0).
- [x] Update FFmpeg logic for looped video backgrounds (v1.40.0).
- [x] Expose `use_dynamic_video` in API and Frontend (v1.40.0).
- [x] Optimize Sora/Runway prompt engineering for better loop points (v1.43.0).
- [x] Implement video-specific caching in Redis (v1.44.0).

## BUG FIXES
- [x] Fix race condition in Job Status polling when RabbitMQ is under high load (v1.50.0).
- [x] Improve sanitization for non-alphanumeric lyric characters in SRT generation (NFKD) (v1.44.0).
- [x] Fix hardcoded frontend API URLs (v1.46.0).

## FEATURES
- [x] Add "Style Presets" dropdown in Frontend for common genre combinations (v1.42.0).
- [x] Support for 4K video rendering (v1.43.0).
- [x] Expand Radio Service to support YouTube Live RTMP (v1.45.0).
- [x] Multi-Channel Webhook Notifier (v1.46.0).
- [x] Implement "Style-Transfer" logic in OMRProcessor (v1.47.0).
- [x] Intelligent MIDI Analysis & Style Auto-Detection (v1.48.0).
- [x] Granular Subtitle & Visual Customization (v1.49.0).
- [ ] Live Collaborative Editing in Review loop.
