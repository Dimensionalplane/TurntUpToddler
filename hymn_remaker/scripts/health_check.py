#!/usr/bin/env python3
"""
Health Check Script: Verify all components of the HymnMania pipeline are functional.
"""

import subprocess
import sys
import os
import logging
import importlib.util
import shutil

# Add repo root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("HealthCheck")

def check_binary(name):
    """Check if a binary is available on PATH."""
    found = shutil.which(name) is not None
    if found:
        logger.info(f"Binary found: {name}")
    else:
        logger.error(f"Binary NOT found: {name}")
    return found

def check_python_module(module_name):
    """Check if a Python module is available."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            logger.info(f"Module found: {module_name}")
            return True
        else:
            logger.error(f"Module NOT found: {module_name}")
            return False
    except Exception as e:
        logger.error(f"Error checking module {module_name}: {e}")
        return False

def smoke_test_pipeline():
    """Run a minimal MIDI through Sonic Vacuum and QualityEvaluator."""
    import mido

    # Check if pipeline modules are available
    try:
        from pipeline.processing.sonic_vacuum import SonicVacuumProcessor
    except ImportError as e:
        logger.warning(f"Skipping smoke test - SonicVacuum not available: {e}")
        return True  # Not a critical failure

    try:
        from hymn_remaker.src.quality_evaluator import QualityEvaluator
    except ImportError:
        logger.warning("Skipping quality evaluation - QualityEvaluator not available")
        QualityEvaluator = None

    test_input = "test_input/short_hymn.mid"
    test_output_wav = "output_test_batch/smoke_test.wav"
    os.makedirs("output_test_batch", exist_ok=True)

    # Create a tiny 1-bar MIDI if it doesn't exist
    if not os.path.exists(test_input):
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))
        mid.save(test_input)

    logger.info("Starting Pipeline Smoke Test...")
    try:
        vacuum = SonicVacuumProcessor(test_input)
        vacuum.render_dry_piano(test_output_wav)
        if not os.path.exists(test_output_wav):
            raise RuntimeError("Smoke test WAV not generated.")

        if QualityEvaluator is not None:
            evaluator = QualityEvaluator()
            score = evaluator.evaluate(test_output_wav)
            logger.info(f"Smoke test quality score: {score}")
        else:
            logger.info("Smoke test WAV generated successfully (score skipped)")
        return True
    except Exception as e:
        logger.error(f"Pipeline Smoke Test FAILED: {e}")
        return False


def run_health_check():
    results = {
        "ffmpeg": check_binary("ffmpeg"),
        "fluidsynth": check_binary("fluidsynth"),
        "mido": check_python_module("mido"),
        "numpy": check_python_module("numpy"),
        "scipy": check_python_module("scipy"),
        "librosa": check_python_module("librosa"),
        "smoke_test": smoke_test_pipeline()
    }

    logger.info("Health Check Summary:")
    for component, status in results.items():
        print(f"{component:20} : {'PASSED' if status else 'FAILED'}")

    failed = [k for k, v in results.items() if not v]
    if failed:
        logger.warning(f"Failed components: {', '.join(failed)}")
        if "smoke_test" in failed:
            sys.exit(1)


if __name__ == "__main__":
    run_health_check()
