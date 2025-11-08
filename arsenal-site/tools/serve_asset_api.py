#!/usr/bin/env python3
"""
Simple Flask API to serve asset metadata from `asset_index.db`.

Place this in `arsenal-site/tools/serve_asset_api.py` and run from the repo root:

    python3 arsenal-site/tools/serve_asset_api.py

It will serve static files from `arsenal-site/assets` under /assets and the
API on http://127.0.0.1:5000.

Endpoints:
- GET /api/songs         -> list of songs (id/key/title)
- GET /api/song/<key>    -> metadata for a song key (audio_url, image_url, lyrics, title)

This is a minimal dev server for local testing only.
"""
from flask import Flask, jsonify, url_for, abort
import sqlite3
from pathlib import Path
import argparse

# locate assets dir relative to this file (tools/ -> arsenal-site)
script_dir = Path(__file__).resolve().parent
site_dir = script_dir.parent
if (site_dir / "assets").exists():
    assets_dir = (site_dir / "assets").resolve()
elif (site_dir / "static").exists():
    assets_dir = (site_dir / "static").resolve()
else:
    assets_dir = (site_dir / "assets").resolve()

DB_PATH = assets_dir / "asset_index.db"

# create Flask app that serves static files from assets_dir at /assets
app = Flask(__name__, static_folder=str(assets_dir), static_url_path='/assets')


def get_db_conn():
    if not DB_PATH.exists():
        raise RuntimeError(f"DB not found: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/songs')
def list_songs():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, key, title FROM songs ORDER BY title')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/song/<key>')
def song_by_key(key):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM songs WHERE key = ? COLLATE NOCASE', (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        abort(404)
    row = dict(row)

    # build URLs for audio/image (serve under /assets)
    audio_url = url_for('static', filename=row['audio_path']) if row.get('audio_path') else None
    image_url = url_for('static', filename=row['image_path']) if row.get('image_path') else None

    # read lyrics file content if present
    lyrics = None
    if row.get('lyrics_path'):
        lyrics_path = assets_dir / row['lyrics_path']
        if lyrics_path.exists():
            try:
                lyrics = lyrics_path.read_text(encoding='utf-8')
            except Exception:
                lyrics = None

    return jsonify({
        'id': row.get('id'),
        'key': row.get('key'),
        'title': row.get('title'),
        'audio_url': audio_url,
        'image_url': image_url,
        'lyrics': lyrics or ''
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=5000, type=int)
    args = parser.parse_args()
    print(f"Serving assets from: {assets_dir}")
    print(f"DB: {DB_PATH}")
    app.run(host=args.host, port=args.port, debug=True)
