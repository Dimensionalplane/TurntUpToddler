"""Multi-voice vocal harmonization for hip-hop acapellas using ElevenLabs.

Pipeline:
1. Take an isolated vocal stem (WAV)
2. Detect pitch & timing via basic-pitch
3. Generate 2-3 harmonized voice parts using ElevenLabs voice cloning/TTS
4. Align everything to a 145 BPM grid
5. Export layered WAV stems + MIDI for Ableton OSC assembly

Harmony intervals (hip-hop style):
  - Voice 1: Original (lead vocal)
  - Voice 2: Major 3rd below (or perfect 5th below for bass-heavy parts)
  - Voice 3: Octave above (high harmony / ad-lib)
  - Voice 4 (optional): Unison double (thickened lead)
"""

import os
import json
import logging
import tempfile
import subprocess
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────
DEFAULT_BPM = 145
HARMONY_INTERVALS = {
    "low_harmony": -4,  # major 3rd below (in semitones)
    "sub_harmony": -7,  # perfect 5th below
    "high_harmony": 12,  # octave above
    "unison_double": 0,  # same pitch, different voice
}
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_VOICE_STABILITY = 0.35
DEFAULT_VOICE_SIMILARITY = 0.75


class VocalHarmonizer:
    """Generate harmonized vocal parts from an isolated vocal stem."""

    def __init__(self, api_key: Optional[str] = None, bpm: int = DEFAULT_BPM):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self.bpm = bpm
        self.beat_duration = 60.0 / bpm  # seconds per beat

        if not self.api_key:
            logger.warning(
                "ELEVENLABS_API_KEY not set. "
                "Will fall back to internal pitch-shift synthesis."
            )

        self._session = None

    @property
    def session(self):
        if self._session is None:
            import requests

            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key,
                }
            )
        return self._session

    # ── Step 1: Pitch & timing detection ────────────────────────────────

    def detect_pitch_and_timing(self, vocal_path: str) -> dict:
        """Analyze vocal stem using basic-pitch.

        Returns a dict with:
          - notes: list of {pitch, start_beat, duration_beats, velocity}
          - bpm: detected BPM (or self.bpm)
          - key: detected key (if available)
        """
        logger.info(f"Harmonizer: Detecting pitch & timing from {vocal_path}...")

        out_dir = tempfile.mkdtemp(prefix="vocal_analysis_")
        base = os.path.splitext(os.path.basename(vocal_path))[0]
        midi_out = os.path.join(out_dir, f"{base}_basic_pitch.mid")
        csv_out = os.path.join(out_dir, f"{base}_basic_pitch.csv")

        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            creationflags = 0

        try:
            subprocess.run(
                [
                    "basic-pitch",
                    "--save-midi",
                    "--save-model-outputs",
                    out_dir,
                    vocal_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=creationflags,
            )
        except FileNotFoundError:
            logger.warning("basic-pitch CLI not found. Falling back to librosa + pYIN.")
            return self._detect_pitch_librosa(vocal_path)
        except subprocess.TimeoutExpired:
            logger.warning("basic-pitch timed out. Falling back.")
            return self._detect_pitch_librosa(vocal_path)

        notes = []
        if os.path.exists(csv_out):
            notes = self._parse_basic_pitch_csv(csv_out, midi_out)
        elif os.path.exists(midi_out):
            notes = self._parse_midi_notes(midi_out)
        else:
            logger.warning("No basic-pitch output found. Falling back.")
            return self._detect_pitch_librosa(vocal_path)

        return {
            "notes": notes,
            "bpm": self.bpm,
            "key": self._estimate_key(notes),
        }

    def _parse_basic_pitch_csv(self, csv_path: str, midi_path: str) -> list:
        """Parse basic-pitch CSV output into structured notes."""
        import csv

        notes = []
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pitch = int(float(row.get("pitch", 0)))
                    start_time = float(row.get("start_time", 0))
                    duration = float(row.get("duration", 0))
                    velocity = int(float(row.get("velocity", 80)))
                    start_beat = start_time / self.beat_duration
                    dur_beats = duration / self.beat_duration
                    notes.append(
                        {
                            "pitch": pitch,
                            "start_beat": round(start_beat, 3),
                            "duration_beats": round(max(dur_beats, 0.25), 3),
                            "velocity": velocity,
                            "start_time": start_time,
                            "duration": duration,
                        }
                    )
                except (ValueError, KeyError):
                    continue
        if not notes:
            return self._parse_midi_notes(midi_path)
        return notes

    def _parse_midi_notes(self, midi_path: str) -> list:
        """Extract note events from a MIDI file."""
        try:
            import mido
        except ImportError:
            logger.error("mido not installed; cannot parse MIDI.")
            return []

        notes = []
        mid = mido.MidiFile(midi_path)
        current_time = 0.0
        pending = {}

        for msg in mid:
            current_time += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                pending[(msg.note, msg.channel)] = (current_time, msg.velocity)
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                key = (msg.note, msg.channel)
                if key in pending:
                    start, vel = pending.pop(key)
                    duration = max(0.05, current_time - start)
                    start_beat = start / self.beat_duration
                    dur_beats = duration / self.beat_duration
                    notes.append(
                        {
                            "pitch": msg.note,
                            "start_beat": round(start_beat, 3),
                            "duration_beats": round(max(dur_beats, 0.25), 3),
                            "velocity": vel,
                            "start_time": start,
                            "duration": duration,
                        }
                    )
        return sorted(notes, key=lambda n: n["start_beat"])

    def _detect_pitch_librosa(self, vocal_path: str) -> dict:
        """Fallback pitch detection using librosa + pYIN."""
        try:
            import librosa
        except ImportError:
            logger.error("librosa not installed; cannot detect pitch.")
            return {"notes": [], "bpm": self.bpm, "key": "C"}

        logger.info("Harmonizer: Using librosa pYIN fallback...")
        y, sr = librosa.load(vocal_path, sr=22050)
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"), sr=sr
        )

        times = librosa.times_like(f0, sr=sr)
        notes = []
        note_start = None
        current_pitch = 0

        for i, (freq, voiced) in enumerate(zip(f0, voiced_flag)):
            if voiced and freq > 0:
                midi_pitch = int(round(12 * np.log2(freq / 440.0) + 69))
                if note_start is None:
                    note_start = times[i]
                    current_pitch = midi_pitch
                elif abs(midi_pitch - current_pitch) > 1:
                    duration = times[i] - note_start
                    start_beat = note_start / self.beat_duration
                    dur_beats = duration / self.beat_duration
                    notes.append(
                        {
                            "pitch": current_pitch,
                            "start_beat": round(start_beat, 3),
                            "duration_beats": round(max(dur_beats, 0.25), 3),
                            "velocity": 90,
                            "start_time": note_start,
                            "duration": duration,
                        }
                    )
                    note_start = times[i]
                    current_pitch = midi_pitch
            elif note_start is not None:
                duration = times[i] - note_start
                start_beat = note_start / self.beat_duration
                dur_beats = duration / self.beat_duration
                notes.append(
                    {
                        "pitch": current_pitch,
                        "start_beat": round(start_beat, 3),
                        "duration_beats": round(max(dur_beats, 0.25), 3),
                        "velocity": 90,
                        "start_time": note_start,
                        "duration": duration,
                    }
                )
                note_start = None

        return {"notes": notes, "bpm": self.bpm, "key": self._estimate_key(notes)}

    def _estimate_key(self, notes: list) -> str:
        """Rough key estimate from note distribution."""
        if not notes:
            return "C"
        pitches = [n["pitch"] % 12 for n in notes]
        if not pitches:
            return "C"
        from collections import Counter

        chroma = Counter(pitches)
        root = chroma.most_common(1)[0][0]
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return note_names[root]

    # ── Step 2: Harmony generation ──────────────────────────────────────

    def generate_harmonies(self, analysis: dict) -> dict:
        """Generate harmonized voice parts from pitch analysis.

        Returns a dict mapping voice names to lists of notes:
          - "lead": original melody
          - "low_harmony": major 3rd below
          - "sub_harmony": perfect 5th below
          - "high_harmony": octave above
          - "unison_double": same pitch (thickened lead)
        """
        notes = analysis.get("notes", [])
        if not notes:
            logger.warning("No notes to harmonize!")
            return {"lead": []}

        logger.info(f"Harmonizer: Generating harmonies from {len(notes)} notes...")

        harmonies = {
            "lead": notes,
            "low_harmony": self._transpose_notes(
                notes, HARMONY_INTERVALS["low_harmony"]
            ),
            "sub_harmony": self._transpose_notes(
                notes, HARMONY_INTERVALS["sub_harmony"]
            ),
            "high_harmony": self._transpose_notes(
                notes, HARMONY_INTERVALS["high_harmony"]
            ),
            "unison_double": self._transpose_notes(
                notes, HARMONY_INTERVALS["unison_double"]
            ),
        }

        for voice in harmonies:
            harmonies[voice] = self._clamp_pitches(harmonies[voice], 36, 96)

        # Groove offsets for humanized feel
        harmonies["low_harmony"] = self._apply_groove_offset(
            harmonies["low_harmony"], offset_beats=0.03
        )
        harmonies["high_harmony"] = self._apply_groove_offset(
            harmonies["high_harmony"], offset_beats=-0.02
        )

        # Sub-harmony only on strong beats (1 & 3)
        harmonies["sub_harmony"] = self._filter_strong_beats(
            harmonies["sub_harmony"], beats_per_measure=4
        )

        logger.info(
            f"Harmonizer: Generated {sum(len(v) for v in harmonies.values())} "
            f"harmony notes across {len(harmonies)} voices."
        )
        return harmonies

    def _transpose_notes(self, notes: list, semitones: int) -> list:
        result = []
        for n in notes:
            new_note = dict(n)
            new_pitch = n["pitch"] + semitones
            new_note["pitch"] = max(0, min(127, new_pitch))
            result.append(new_note)
        return result

    def _clamp_pitches(self, notes: list, min_pitch: int, max_pitch: int) -> list:
        return [n for n in notes if min_pitch <= n["pitch"] <= max_pitch]

    def _apply_groove_offset(self, notes: list, offset_beats: float) -> list:
        result = []
        for n in notes:
            new_note = dict(n)
            new_note["start_beat"] = max(0, n["start_beat"] + offset_beats)
            result.append(new_note)
        return result

    def _filter_strong_beats(self, notes: list, beats_per_measure: int = 4) -> list:
        result = []
        for n in notes:
            beat_in_measure = n["start_beat"] % beats_per_measure
            if beat_in_measure < 0.5 or abs(beat_in_measure - 2) < 0.5:
                result.append(n)
        return result

    # ── Step 3: ElevenLabs voice rendering ─────────────────────────────

    def list_voices(self) -> list:
        """Fetch available ElevenLabs voices."""
        if not self.api_key:
            return []
        try:
            resp = self.session.get(f"{ELEVENLABS_API_URL}/voices")
            if resp.status_code == 200:
                return resp.json().get("voices", [])
            logger.warning(f"ElevenLabs /voices error: {resp.status_code}")
            return []
        except Exception as e:
            logger.error(f"ElevenLabs /voices failed: {e}")
            return []

    def clone_voice(self, name: str, audio_paths: list[str]) -> Optional[str]:
        """Clone a voice from audio samples via ElevenLabs."""
        if not self.api_key:
            return None

        logger.info(
            f"Harmonizer: Cloning voice '{name}' from {len(audio_paths)} samples..."
        )
        url = f"{ELEVENLABS_API_URL}/voices/add"

        files = []
        for ap in audio_paths:
            if os.path.exists(ap):
                files.append(
                    ("files", (os.path.basename(ap), open(ap, "rb"), "audio/wav"))
                )

        if not files:
            logger.error("No valid audio files for voice cloning.")
            return None

        data = {
            "name": name,
            "labels": json.dumps({"use_case": "music", "source": "hymn_remaker"}),
        }

        try:
            resp = self.session.post(url, data=data, files=files)
            for _, fobj in files:
                fobj[1].close()
            if resp.status_code == 200:
                voice_id = resp.json().get("voice_id")
                logger.info(f"Voice cloned: {voice_id}")
                return voice_id
            logger.warning(
                f"Voice cloning failed: {resp.status_code} {resp.text[:200]}"
            )
            return None
        except Exception as e:
            logger.error(f"Voice cloning error: {e}")
            return None

    def generate_voice_part(
        self,
        voice_id: str,
        lyrics_text: str,
        pitch_shift: int = 0,
        output_path: str = "harmony_part.wav",
    ) -> Optional[str]:
        """Generate a vocal part using ElevenLabs TTS with optional pitch shift."""
        if not self.api_key:
            return self._pitch_shift_stem(None, pitch_shift, output_path)

        logger.info(f"Harmonizer: Generating voice part (shift={pitch_shift})...")

        url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
        payload = {
            "text": lyrics_text,
            "model_id": DEFAULT_MODEL,
            "voice_settings": {
                "stability": DEFAULT_VOICE_STABILITY,
                "similarity_boost": DEFAULT_VOICE_SIMILARITY,
            },
        }

        try:
            resp = self.session.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"TTS failed: {resp.status_code} {resp.text[:200]}")
                return self._pitch_shift_stem(None, pitch_shift, output_path)

            raw_path = output_path.replace(".wav", "_raw.mp3")
            with open(raw_path, "wb") as f:
                f.write(resp.content)

            ffmpeg = self._find_ffmpeg()
            subprocess.run(
                [ffmpeg, "-y", "-i", raw_path, "-ar", "44100", output_path],
                capture_output=True,
                timeout=30,
            )
            os.unlink(raw_path)

            if pitch_shift != 0:
                return self._pitch_shift_stem(output_path, pitch_shift, output_path)
            return output_path

        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return self._pitch_shift_stem(None, pitch_shift, output_path)

    def _pitch_shift_stem(
        self, input_path: Optional[str], semitones: int, output_path: str
    ) -> Optional[str]:
        """Pitch-shift an audio file using ffmpeg's rubberband."""
        if semitones == 0 and input_path and os.path.exists(input_path):
            return input_path

        ffmpeg = self._find_ffmpeg()
        if not input_path or not os.path.exists(input_path):
            freq = 440.0 * (2 ** (semitones / 12.0))
            cmd = [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"aevalsrc=sin(2*PI*{freq:.1f}*t):d=1:c=stereo",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            return output_path

        factor = 2 ** (semitones / 12.0)
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            input_path,
            "-af",
            f"rubberband=pitch={factor:.6f}",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            return output_path
        except Exception as e:
            logger.error(f"Pitch shift failed: {e}")
            return input_path

    def _find_ffmpeg(self) -> str:
        local_ffmpeg = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "bin", "ffmpeg.exe"
        )
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        return "ffmpeg"

    # ── Step 4: Render harmony stems ────────────────────────────────────

    def render_harmony_stems(
        self,
        analysis: dict,
        harmonies: dict,
        output_dir: str,
        lyrics_path: Optional[str] = None,
    ) -> dict:
        """Render each harmony voice as a WAV stem.

        Uses ElevenLabs TTS when API key is available, otherwise synthesizes
        internally with formant-filtered sine waves.
        """
        os.makedirs(output_dir, exist_ok=True)
        stems = {}

        lyrics_text = ""
        if lyrics_path and os.path.exists(lyrics_path):
            with open(lyrics_path) as f:
                lyrics_text = f.read()
        elif analysis.get("notes"):
            lyrics_text = self._generate_placeholder_lyrics(analysis["notes"])
        else:
            lyrics_text = ("La la la la la la la " * 16).strip()

        voices_to_render = {
            "lead": 0,
            "low_harmony": HARMONY_INTERVALS["low_harmony"],
            "sub_harmony": HARMONY_INTERVALS["sub_harmony"],
            "high_harmony": HARMONY_INTERVALS["high_harmony"],
            "unison_double": HARMONY_INTERVALS["unison_double"],
        }

        voice_id = None
        if self.api_key:
            existing_voices = self.list_voices()
            if existing_voices:
                for v in existing_voices:
                    if "hymn" in v.get("name", "").lower():
                        voice_id = v["voice_id"]
                        break
                if not voice_id:
                    voice_id = existing_voices[0]["voice_id"]
                logger.info(f"Using ElevenLabs voice: {voice_id}")

        for voice_name, semitone_shift in voices_to_render.items():
            stem_path = os.path.join(output_dir, f"{voice_name}.wav")

            if self.api_key and voice_id:
                result = self.generate_voice_part(
                    voice_id=voice_id,
                    lyrics_text=lyrics_text,
                    pitch_shift=semitone_shift,
                    output_path=stem_path,
                )
                if result:
                    stems[voice_name] = result
                    continue

            logger.info(
                f"Harmonizer: Synthesizing {voice_name} (shift={semitone_shift})..."
            )
            result = self._synthesize_from_notes(
                harmonies.get(voice_name, []),
                semitone_shift,
                sr=44100,
                output_path=stem_path,
            )
            if result:
                stems[voice_name] = result

        return stems

    def _generate_placeholder_lyrics(self, notes: list) -> str:
        syllables = [
            "La",
            "Lo",
            "Li",
            "Le",
            "Lu",
            "Ya",
            "Yo",
            "Yi",
            "Ye",
            "Yu",
            "Ah",
            "Oh",
            "Eh",
            "EE",
            "Oo",
        ]
        words = []
        phrases = []
        for i, note in enumerate(notes):
            syl = syllables[i % len(syllables)]
            words.append(syl)
            if len(words) >= 4:
                phrases.append(" ".join(words))
                words = []
        if words:
            phrases.append(" ".join(words))
        return "\n".join(phrases)

    def _synthesize_from_notes(
        self, notes: list, semitone_shift: int, sr: int, output_path: str
    ) -> Optional[str]:
        """Synthesize audio from note events using formant-filtered sine waves."""
        if not notes:
            return None

        total_beats = max(n["start_beat"] + n["duration_beats"] for n in notes)
        total_samples = int(total_beats * self.beat_duration * sr) + sr
        audio = np.zeros(total_samples, dtype=np.float64)

        for note in notes:
            pitch = note["pitch"] + semitone_shift
            if pitch < 24 or pitch > 96:
                continue

            freq = 440.0 * (2 ** ((pitch - 69) / 12.0))
            start_sample = int(note["start_beat"] * self.beat_duration * sr)
            duration_samples = int(note["duration_beats"] * self.beat_duration * sr)
            duration_samples = max(duration_samples, int(0.05 * sr))
            end_sample = min(start_sample + duration_samples, total_samples)
            n_samples = end_sample - start_sample

            if n_samples <= 0:
                continue

            t = np.arange(n_samples, dtype=np.float64) / sr

            fundamental = np.sin(2 * np.pi * freq * t)
            harmonic2 = np.sin(2 * np.pi * freq * 2 * t) * 0.3
            harmonic3 = np.sin(2 * np.pi * freq * 3 * t) * 0.1
            harmonic4 = np.sin(2 * np.pi * freq * 4 * t) * 0.05

            signal = fundamental + harmonic2 + harmonic3 + harmonic4

            velocity_norm = note.get("velocity", 80) / 127.0
            signal *= velocity_norm * 0.3

            fade_len = min(n_samples // 16, int(0.01 * sr))
            if fade_len > 0:
                signal[:fade_len] *= np.linspace(0, 1, fade_len)
                signal[-fade_len:] *= np.linspace(1, 0, fade_len)

            audio[start_sample:end_sample] += signal

        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.95

        reverb_tail = np.exp(-np.linspace(0, 5, int(0.3 * sr))) * 0.1
        wet = np.convolve(audio, reverb_tail, mode="full")[: len(audio)]
        audio = audio * 0.8 + wet * 0.2

        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.95

        stereo = np.column_stack([audio, audio]).astype(np.float32)
        sf.write(output_path, stereo, sr)
        logger.info(
            f"  Synthesized: {output_path} ({os.path.getsize(output_path) / 1024:.0f}KB)"
        )
        return output_path

    # ── Step 5: BPM grid alignment ─────────────────────────────────────

    def quantize_to_grid(self, notes: list, grid_unit: float = 0.25) -> list:
        """Snap note start times and durations to the nearest grid unit."""
        result = []
        for n in notes:
            q = dict(n)
            snapped_start = round(n["start_beat"] / grid_unit) * grid_unit
            q["start_beat"] = max(0, snapped_start)
            snapped_dur = max(
                grid_unit, round(n["duration_beats"] / grid_unit) * grid_unit
            )
            q["duration_beats"] = snapped_dur
            result.append(q)
        return result

    def export_midi(
        self, harmonies: dict, output_path: str, track_names: Optional[list[str]] = None
    ):
        """Export harmonized voices to a multi-track MIDI file."""
        try:
            import mido
        except ImportError:
            logger.error("mido not installed; cannot export MIDI.")
            return

        if track_names is None:
            track_names = list(harmonies.keys())

        mid = mido.MidiFile()
        for voice_name in track_names:
            notes = harmonies.get(voice_name, [])
            if not notes:
                continue

            track = mido.MidiTrack()
            track.append(mido.MetaMessage("track_name", name=voice_name, time=0))
            track.append(
                mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm), time=0)
            )

            prev_time = 0.0
            for n in sorted(notes, key=lambda x: x["start_beat"]):
                start_sec = n["start_beat"] * self.beat_duration
                dur_sec = n["duration_beats"] * self.beat_duration

                delta = int((start_sec - prev_time) * 480)
                if delta < 0:
                    delta = 0

                track.append(
                    mido.Message(
                        "note_on",
                        note=n["pitch"],
                        velocity=n.get("velocity", 80),
                        time=delta,
                    )
                )
                dur_ticks = max(1, int(dur_sec * 480))
                track.append(
                    mido.Message(
                        "note_off", note=n["pitch"], velocity=0, time=dur_ticks
                    )
                )
                prev_time = start_sec + dur_sec

            mid.tracks.append(track)

        mid.save(output_path)
        logger.info(f"Exported MIDI: {output_path} ({len(mid.tracks)} tracks)")

    # ── Full pipeline ──────────────────────────────────────────────────

    def run_pipeline(
        self,
        vocal_path: str,
        output_dir: str,
        lyrics_path: Optional[str] = None,
    ) -> dict:
        """Run the full vocal harmonization pipeline.

        Args:
            vocal_path: Path to isolated vocal stem WAV.
            output_dir: Output directory for stems and MIDI.
            lyrics_path: Optional path to lyrics text for TTS.

        Returns:
            Dict with "analysis", "harmonies", "stems", "midi_path".
        """
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Harmonizer Pipeline: {vocal_path}")
        logger.info(f"{'=' * 60}")

        analysis = self.detect_pitch_and_timing(vocal_path)
        logger.info(
            f"  Detected {len(analysis['notes'])} notes, "
            f"key={analysis['key']}, bpm={analysis['bpm']}"
        )

        harmonies = self.generate_harmonies(analysis)
        logger.info(f"  Generated {len(harmonies)} harmony voices")

        grid_unit = 0.25
        for voice_name in harmonies:
            harmonies[voice_name] = self.quantize_to_grid(
                harmonies[voice_name], grid_unit=grid_unit
            )

        stems = self.render_harmony_stems(
            analysis, harmonies, output_dir, lyrics_path=lyrics_path
        )
        logger.info(f"  Rendered {len(stems)} audio stems")

        midi_path = os.path.join(output_dir, "harmony_full.mid")
        self.export_midi(harmonies, midi_path)
        logger.info(f"  Exported MIDI: {midi_path}")

        result = {
            "analysis": analysis,
            "harmonies": harmonies,
            "stems": stems,
            "midi_path": midi_path,
        }
        logger.info(f"{'=' * 60}\n")
        return result
