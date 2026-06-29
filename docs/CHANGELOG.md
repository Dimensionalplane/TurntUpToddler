# Changelog

All notable changes to this project will be documented in this file.

## [5.38.1] - 2026-06-29
### Added
- Implemented `InteractiveReviewModal.tsx` React component, re-enabling pipeline pausing and live metadata edits during generation.
- Integrated `InteractiveReviewModal` into `FileUploader.tsx`.

### Changed
- Expanded `ChildrenSongFinder` to dynamically scrape BitMidi, removing the limit of only 5 hardcoded public domain songs.
- Updated Next.js application frontend.
- Updated `Player.tsx` interface to accept `url` properly.
