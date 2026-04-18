# Ideas & Brainstorms

This document captures creative expansions, "blue sky" thinking, and potential pivot directions for the Hymn Remaker project.

## Audio & Music Generation
- **Genre Shifting UI:** Allow the user to select the output genre in Streamlit. Instead of hardcoding "Deep House" into the MusicGen prompt, provide options for "Synthwave", "Lo-Fi Hip Hop", "Orchestral Epic", or "Trap".
- **Stem Separation:** After Replicate generates the remix, use an AI stem separator (like `spleeter` or `demucs`) to split the track into vocals, drums, bass, and other. This would allow the orchestrator to duck *only* the melodic instruments when the TTS vocal is playing, keeping the drum groove perfectly intact.
- **Dynamic Tempo Matching:** Analyze the BPM of the original MIDI file using `librosa`. Feed that exact BPM into the Replicate MusicGen prompt to ensure the output remix strictly adheres to the original tempo, avoiding awkward stretching during the mixdown phase.

## Visuals & Video
- **Audio-Reactive Avatars:** Instead of static cover art, integrate a lightweight 2D vtuber or audio-reactive visualizer (using a library like `vispy` or OpenGL) that pulses and animates to the beat of the generated track.
- **Theme Consistency:** Use the OpenAI API to extract keywords from the lyrics. Feed those keywords back into DALL-E 3 with a persistent "style seed" so that all videos generated in a specific session share a cohesive visual aesthetic (e.g., "stained glass window style", "cyberpunk neon style").

## Infrastructure & Distribution
- **"Infinite Stream" Mode (Live DJ):** Implement an Icecast server or HLS stream. As the daemon processes new hymns, it dynamically crossfades them into a continuous 24/7 internet radio broadcast.
- **Automated Social Distribution:** Extend `video_uploader.py` beyond YouTube. Integrate the TikTok and Instagram Graph APIs to automatically publish the extracted shorts directly to those platforms.
