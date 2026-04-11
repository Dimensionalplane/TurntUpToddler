# TODO

## High Priority
- [x] Implement robust documentation structure across `docs/`.
- [x] Modify `hymn_remaker/app.py` to display the global version number in the sidebar.
- [x] Modify `hymn_remaker/app.py` to allow user selection of ElevenLabs Voice ID and Model.
- [x] Update `process_single_midi` in `main.py` to accept and pass the Voice ID and Model parameters.

## Medium Priority
- [x] Improve error handling and retry logic around FFmpeg subtitle burning.
- [x] Add caching for DALL-E 3 image generation so re-running the same pipeline doesn't burn credits.
- [x] Add a progress bar specifically for the YouTube upload chunking process.

## Low Priority / Polish
- [ ] Clean up temporary files more aggressively if a pipeline step fails mid-way.
- [ ] Add unit tests specifically mocking the ElevenLabs API responses.
