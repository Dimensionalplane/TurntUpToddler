import os
import sys
import logging
import mido
import numpy as np

# Add the repo root to sys.path
sys.path.append(os.getcwd())

from pipeline.processing.sonic_vacuum import SonicVacuumProcessor
from pipeline.processing.symbolic_norm import SymbolicNormalizer
from pipeline.processing.house_quantizer import HouseStructuralQuantizer
from hymn_remaker.src.quality_evaluator import QualityEvaluator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("BatchValidator")

SAMPLE_MIDIS = [
    "hymn_remaker/input/Emmanuel.mid",
    "hymn_remaker/input/leyenda.mid",
    "hymn_remaker/input/Kumbayah.mid",
    "hymn_remaker/input/bach-cello-suite-no1-prelude.mid",
    "hymn_remaker/input/Hallelu, Hallelu.mid"
]

EDGE_CASE_MIDIS = [
    "hymn_remaker/input/empty.mid",
    "hymn_remaker/input/no_notes.mid"
]

OUTPUT_DIR = "output_test_batch"

def create_edge_cases():
    os.makedirs("hymn_remaker/input", exist_ok=True)
    # 1. Empty MIDI
    m1 = mido.MidiFile()
    m1.tracks.append(mido.MidiTrack())
    m1.save("hymn_remaker/input/empty.mid")

    # 2. MIDI with no note_on
    m2 = mido.MidiFile()
    t2 = mido.MidiTrack()
    t2.append(mido.MetaMessage('track_name', name='NoNotes'))
    t2.append(mido.Message('program_change', program=0, time=0))
    m2.tracks.append(t2)
    m2.save("hymn_remaker/input/no_notes.mid")

def validate_midi_structure(path):
    """Checks if MIDI has at least one track, correct tempo messages, and kick track."""
    try:
        if not os.path.exists(path):
            return False, "File not created"
        mid = mido.MidiFile(path)
        tracks = mid.tracks
        if len(tracks) == 0:
            return False, "No tracks found"

        has_kick = any("kick" in t.name.lower() for t in tracks)
        # Check if tempo is set
        has_tempo = any(msg.type == 'set_tempo' for t in tracks for msg in t)

        return True, f"Tracks: {len(tracks)}, Kick: {has_kick}, Tempo: {has_tempo}"
    except Exception as e:
        return False, str(e)

def run_batch():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    create_edge_cases()
    evaluator = QualityEvaluator()
    report = []

    for midi_path in SAMPLE_MIDIS + EDGE_CASE_MIDIS:
        if not os.path.exists(midi_path):
            logger.warning(f"File not found: {midi_path}")
            continue

        name = os.path.basename(midi_path)
        logger.info(f"Processing {name}...")

        # 1. Sonic Vacuum
        try:
            vacuum = SonicVacuumProcessor(midi_path)
            audio_path = os.path.join(OUTPUT_DIR, f"{name}_dry.wav")
            vacuum.render_dry_piano(audio_path)
            score = evaluator.evaluate(audio_path)
        except Exception as e:
            logger.error(f"SonicVacuum failed for {name}: {e}")
            score = 0.0

        # 2. Symbolic Normalizer
        try:
            norm = SymbolicNormalizer(midi_path)
            norm_path = os.path.join(OUTPUT_DIR, f"{name}_norm.mid")
            norm.normalize(norm_path)
        except Exception as e:
            logger.error(f"SymbolicNormalizer failed for {name}: {e}")

        # 3. House Quantizer
        try:
            quantizer = HouseStructuralQuantizer(midi_path)
            house_path = os.path.join(OUTPUT_DIR, f"{name}_house.mid")
            quantizer.quantize(house_path)
            valid, info = validate_midi_structure(house_path)
        except Exception as e:
            logger.error(f"HouseQuantizer failed for {name}: {e}")
            valid, info = False, str(e)

        report.append({
            "name": name,
            "quality_score": score,
            "house_valid": valid,
            "house_info": info
        })

    logger.info("Batch Validation Complete. Summary:")
    print(f"{'Name':<40} | {'Score':<6} | {'Valid':<5} | {'Info'}")
    print("-" * 80)
    for r in report:
        print(f"{r['name']:<40} | {r['quality_score']:<6} | {str(r['house_valid']):<5} | {r['house_info']}")

if __name__ == "__main__":
    run_batch()
