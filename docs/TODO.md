# TODO - HYMN REMAKER

## IMMEDIATE TASKS (v1.39.0+)
- [x] Integrate Dynamic AI Video generation in pipeline.
- [x] Update FFmpeg logic for looped video backgrounds.
- [x] Expose `use_dynamic_video` in API and Frontend.
- [x] Optimize Sora/Runway prompt engineering for better loop points.
- [x] Implement video-specific caching in Redis.

## BUG FIXES
- [ ] Fix race condition in Job Status polling when RabbitMQ is under high load.
- [ ] Improve sanitization for non-alphanumeric lyric characters in SRT generation.

## FEATURES
- [x] Add "Style Presets" dropdown in Frontend for common genre combinations.
- [x] Support for 4K video rendering (currently 1080p).
- [x] Expand Radio Service to support YouTube Live RTMP.
