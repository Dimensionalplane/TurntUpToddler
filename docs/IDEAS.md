# Ideas & Brainstorming

*   **Vocal Separation Pre-processing**: If the input is audio instead of MIDI, use Spleeter to extract the melody before feeding to MusicGen.
*   **Genre-Specific Prompt Engineering**: Dynamically adjust the DALL-E 3 prompt based on the musical style selected (e.g., Deep House gets neon club visuals, Acoustic Folk gets warm sunlight imagery).
*   **Multi-Voice Choir**: Instead of a single TTS voice, generate 3-4 different ElevenLabs voices and pan them left/right to create an artificial choir for religious hymns.
*   **Beat-Synced Visuals**: Use librosa to detect beat transients in the remade audio, and pulse the DALL-E image scale in FFmpeg to the beat.
