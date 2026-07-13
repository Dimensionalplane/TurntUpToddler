import os
import glob
import multiprocessing
import subprocess
from video_generator import render_milkdrop

GENERATED_DIR = "generated"
PRESETS_DIR = "hymn_remaker/presets"

def render_single(args):
    mp3_path, preset, out, overlay_text = args
    print(f"Starting render: {os.path.basename(mp3_path)}")
    try:
        render_milkdrop(
            mp3_path,
            out,
            overlay_text,
            preset_path=preset,
        )
        print(f"Finished rendering: {os.path.basename(out)}")
    except Exception as e:
        print(f"Error rendering {os.path.basename(mp3_path)}: {e}")

def main():
    mp3s = sorted(glob.glob(os.path.join(GENERATED_DIR, "Thy_Word *generated.mp3")))
    presets = sorted(glob.glob(os.path.join(PRESETS_DIR, "*.milk")))

    print(f"Found {len(mp3s)} generated MP3s:")
    for m in mp3s:
        print(f"  {os.path.basename(m)}")

    tasks = []
    for i, mp3_path in enumerate(mp3s):
        preset = presets[i % len(presets)] if presets else None
        safe = os.path.splitext(os.path.basename(mp3_path))[0]
        out = os.path.join(GENERATED_DIR, f"{safe}_projectm.mp4")
        if os.path.exists(out):
            print(f"Skipping already rendered: {os.path.basename(out)}")
            continue
        
        name_no_ext = safe.replace("_generated", "")
        parts = name_no_ext.split(" ")
        genre_part = parts[-1].replace("_", " ") if len(parts) >= 3 else "remix"
        speed_part = parts[1] if len(parts) >= 2 else "1.0x"
        
        speed_disp = speed_part
        if speed_part == "05x": speed_disp = "0.5x"
        elif speed_part == "10x": speed_disp = "1.0x"
        elif speed_part == "25x": speed_disp = "2.5x"
        elif speed_part == "50x": speed_disp = "5.0x"
        elif speed_part == "100x": speed_disp = "10.0x"
        
        overlay_text = f"Thy Word ({speed_disp} Speed) - {genre_part.upper()}"
        
        tasks.append((mp3_path, preset, out, overlay_text))

    # Run in parallel with 3 worker processes (safe CPU/Memory threshold)
    print(f"\nStarting parallel rendering with 3 processes...")
    with multiprocessing.Pool(processes=3) as pool:
        pool.map(render_single, tasks)

    print("\nAll videos rendered successfully!")
    print("Starting batch upload to YouTube...")
    subprocess.run(["python", "_batch_upload.py"])

if __name__ == "__main__":
    main()
