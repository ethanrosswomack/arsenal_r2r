#!/usr/bin/env python3
"""
tools/build_asset_index.py

Scans the `assets/tracks` directory for content (audio, text) and builds an
SQLite index.
"""
import argparse
import csv
import sqlite3
from pathlib import Path
import re

AUDIO_EXTS = {".mp3", ".m4a", ".ogg", ".wav", ".flac", ".aac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".lrc", ".md"}

def find_first_file_by_ext(directory: Path, extensions: set):
    """Find the first file in a directory matching a set of extensions."""
    for p in directory.iterdir():
        if p.is_file() and p.suffix.lower() in extensions:
            return p
    return None

def format_title(text: str):
    """Converts a filename-safe string to a more readable title."""
    return re.sub(r'[_-]', ' ', text).title()

def build_rows(assets_dir: Path):
    content_root = assets_dir / "tracks"
    if not content_root.exists():
        raise SystemExit(f"Content directory not found: `{content_root}`")

    rows = []
    for sku_dir in content_root.iterdir():
        if not sku_dir.is_dir():
            continue

        sku = sku_dir.name
        album_title = format_title(sku)
        album_image_file = find_first_file_by_ext(sku_dir, IMAGE_EXTS)

        all_files = list(sku_dir.iterdir())
        
        for file in all_files:
            if not file.is_file() or file.stem.startswith('.'):
                continue

            content_type = ""
            if file.suffix.lower() in AUDIO_EXTS:
                content_type = "track"
            elif file.suffix.lower() in TEXT_EXTS:
                has_matching_audio = any(f.stem == file.stem and f.suffix.lower() in AUDIO_EXTS for f in all_files)
                if has_matching_audio:
                    continue
                content_type = "commentary"
            else:
                continue

            key = f"{sku}-{file.stem}"
            title = format_title(file.stem)
            
            audio_path, lyrics_path = "", ""
            if content_type == "track":
                audio_path = file.relative_to(assets_dir).as_posix()
                # --- FIXED: More direct logic to find matching lyrics file ---
                for ext in TEXT_EXTS:
                    potential_lyrics_file = sku_dir / f"{file.stem}{ext}"
                    if potential_lyrics_file.is_file():
                        lyrics_path = potential_lyrics_file.relative_to(assets_dir).as_posix()
                        break 
            elif content_type == "commentary":
                lyrics_path = file.relative_to(assets_dir).as_posix()

            rows.append({
                "key": key,
                "sku": sku,
                "title": title,
                "album": album_title,
                "type": content_type,
                "audio_path": audio_path,
                "image_path": album_image_file.relative_to(assets_dir).as_posix() if album_image_file else "",
                "lyrics_path": lyrics_path,
            })

    return sorted(rows, key=lambda r: (r["album"], r["title"]))

def write_db(rows, db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        sku TEXT,
        title TEXT,
        album TEXT,
        type TEXT,
        audio_path TEXT,
        image_path TEXT,
        lyrics_path TEXT
    );
    """)
    cur.execute("DELETE FROM content;")
    cur.executemany(
        "INSERT INTO content (key, sku, title, album, type, audio_path, image_path, lyrics_path) VALUES (:key, :sku, :title, :album, :type, :audio_path, :image_path, :lyrics_path)",
        rows
    )
    conn.commit()
    conn.close()

def main():
    p = argparse.ArgumentParser(description="Build an asset index from the `assets/tracks` directory.")
    p.add_argument("--csv", action="store_true", help="Also write a CSV index file.")
    p.add_argument("--dry-run", action="store_true", help="Print rows instead of writing to the database.")
    args = p.parse_args()

    script_dir = Path(__file__).resolve().parent
    site_dir = script_dir.parent
    assets_dir = site_dir / "assets"

    OUT_DB = assets_dir / "asset_index.db"
    OUT_CSV = assets_dir / "asset_index.csv"

    rows = build_rows(assets_dir)
    
    if not rows:
        print("No content found in `assets/tracks`. Database not updated.")
        return

    if args.dry_run:
        for r in rows:
            print(r)
        print(f"\nFound {len(rows)} entries.")
        return

    write_db(rows, OUT_DB)
    print(f"Wrote `{OUT_DB}` with {len(rows)} rows.")
    if args.csv:
        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote `{OUT_CSV}`.")

if __name__ == "__main__":
    main()
