import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hymn_name TEXT,
                style TEXT,
                video_path TEXT,
                audio_path TEXT,
                metadata_path TEXT,
                date_created TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")

def add_history(hymn_name, style, video_path, audio_path, metadata_path):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (hymn_name, style, video_path, audio_path, metadata_path, date_created)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (hymn_name, style, video_path, audio_path, metadata_path, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to add to history: {e}")

def get_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT hymn_name, style, video_path, audio_path, metadata_path, date_created FROM history ORDER BY date_created DESC')
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "hymn_name": row[0],
                "style": row[1],
                "video_path": row[2],
                "audio_path": row[3],
                "metadata_path": row[4],
                "date_created": row[5]
            } for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        return []
