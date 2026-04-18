# Project Memory

## Observations
- The project relies heavily on `ffmpeg` and `fluidsynth` being installed at the system level.
- Streamlit concurrency requires `add_script_run_ctx` for background thread UI updates.
- Deep House remakes are the core aesthetic.
- The pipeline architecture utilizes several external APIs (OpenAI, Replicate, ElevenLabs), requiring careful idempotency controls (`--skip-render`, caching) to avoid excessive API costs during testing.

## Preferences
- The user desires extreme detail in documentation and robust logging.
- Autonomous momentum is highly encouraged ("Don't stop the party!!!").
- Version numbers should be stored centrally (e.g., `VERSION` file) and not hardcoded into the Python source.
- Code should be commented extensively, explaining the "why", while self-evident code is left bare.
