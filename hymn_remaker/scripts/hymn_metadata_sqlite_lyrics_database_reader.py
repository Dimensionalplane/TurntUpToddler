import os
import sys
import sqlite3
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "..", "hymn_remaker", "hymn_database.db")

def query_metadata(midi_name):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        return None, None

    hymn_base = os.path.splitext(os.path.basename(midi_name))[0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try multiple query variants
    cursor.execute(
        "SELECT lyrics, author FROM hymns WHERE filename = ? OR original_filename = ? OR filename LIKE ? OR original_filename LIKE ?",
        (midi_name, midi_name, f"%{hymn_base}%", f"%{hymn_base}%")
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0], row[1]
    return None, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi", required=True)
    args = parser.parse_args()
    lyrics, author = query_metadata(args.midi)
    print(f"Lyrics: {str(lyrics)[:100]}...")
    print(f"Author: {author}")

if __name__ == "__main__":
    main()
