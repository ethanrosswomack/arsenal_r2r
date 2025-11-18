#!/usr/bin/env python3
"""
Converts the Arsenal project into a fully static HTML website.

This script reads all content from the `assets` directory, generates individual
HTML pages for each song, and creates a JSON file to power the homepage. The
output is a complete, self-contained website in the `dist` folder, ready for
deployment on any static hosting service.
"""
import json
import shutil
from pathlib import Path
import re
from collections import defaultdict

# --- Configuration ---
SITE_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = SITE_ROOT / "dist"
ASSETS_DIR = SITE_ROOT / "assets"
STATIC_DIR = DIST_DIR / "static"
TEMPLATE_DIR = SITE_ROOT / "templates"

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

def build_song_data():
    """
    Scans the assets directory to build a structured list of all songs and albums.
    """
    content_root = ASSETS_DIR / "tracks"
    if not content_root.exists():
        raise SystemExit(f"Content directory not found: `{content_root}`")

    all_songs = []
    for sku_dir in content_root.iterdir():
        if not sku_dir.is_dir():
            continue

        sku = sku_dir.name
        album_title = format_title(sku)
        album_image_file = find_first_file_by_ext(sku_dir, IMAGE_EXTS)

        for file in sku_dir.iterdir():
            if file.is_file() and file.suffix.lower() in AUDIO_EXTS:
                key = f"{sku}-{file.stem}"
                title = format_title(file.stem)
                
                lyrics_path = ""
                for ext in TEXT_EXTS:
                    potential_lyrics_file = sku_dir / f"{file.stem}{ext}"
                    if potential_lyrics_file.is_file():
                        lyrics_path = potential_lyrics_file.relative_to(ASSETS_DIR).as_posix()
                        break
                
                all_songs.append({
                    "key": key,
                    "sku": sku,
                    "title": title,
                    "album": album_title,
                    "type": "track",
                    "audio_path": file.relative_to(ASSETS_DIR).as_posix(),
                    "image_path": album_image_file.relative_to(ASSETS_DIR).as_posix() if album_image_file else "",
                    "lyrics_path": lyrics_path,
                })

    # Group songs by album
    albums = defaultdict(lambda: {'items': [], 'image_path': ''})
    for song in sorted(all_songs, key=lambda s: s['title']):
        album_title = song['album']
        albums[album_title]['items'].append(song)
        if not albums[album_title]['image_path'] and song['image_path']:
            albums[album_title]['image_path'] = f"static/{song['image_path']}"

    # Convert to a list of dicts for JSON
    result = []
    for album_title, data in albums.items():
        result.append({
            'title': album_title,
            'image_path': data['image_path'],
            'items': data['items']
        })
    return result

def main():
    """Generates the static site."""
    print("Starting static site build...")

    # 1. Clean and recreate the output directory
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()
    print(f"Created clean output directory: {DIST_DIR}")

    # 2. Copy static assets (CSS, JS, images, audio)
    shutil.copytree(ASSETS_DIR, STATIC_DIR)
    print(f"Copied assets to: {STATIC_DIR}")

    # 3. Build the song data and write it to a JSON file
    song_data = build_song_data()
    api_dir = DIST_DIR / "api"
    api_dir.mkdir()
    with (api_dir / "data.json").open("w", encoding="utf-8") as f:
        json.dump(song_data, f, indent=2)
    print("Generated song data at: api/data.json")

    # 4. Generate individual song pages
    content_template = (TEMPLATE_DIR / "content.html").read_text(encoding="utf-8")
    nav_template = (TEMPLATE_DIR / "nav.html").read_text(encoding="utf-8")
    content_dir = DIST_DIR / "content"
    content_dir.mkdir()

    all_songs = [song for album in song_data for song in album['items']]

    for song in all_songs:
        lyrics = "No lyrics available for this song."
        if song['lyrics_path']:
            lyrics_file = ASSETS_DIR / song['lyrics_path']
            if lyrics_file.exists():
                lyrics = lyrics_file.read_text(encoding='utf-8')

        # Replace placeholders in the template
        page_content = content_template.replace("{{ title }}", song['title'])
        page_content = page_content.replace("{{ content }}", f"<pre>{lyrics}</pre>")
        page_content = page_content.replace("{{ audio_url }}", f"../static/{song['audio_path']}")
        page_content = page_content.replace("{{ image_url }}", f"../static/{song['image_path']}")
        page_content = page_content.replace("{% include 'nav.html' %}", nav_template)

        # Write the final HTML file
        output_path = content_dir / f"{song['key']}.html"
        output_path.write_text(page_content, encoding="utf-8")
    
    print(f"Generated {len(all_songs)} song pages in: {content_dir.relative_to(SITE_ROOT)}")

    # 5. Process and copy main HTML pages
    index_template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    index_nav_template = (TEMPLATE_DIR / "nav.html").read_text(encoding="utf-8").replace("../index.html", "index.html")
    index_content = index_template.replace("{% include 'nav.html' %}", index_nav_template)
    (DIST_DIR / "index.html").write_text(index_content, encoding="utf-8")
    
    print(f"Copied main HTML pages to: {DIST_DIR.relative_to(SITE_ROOT)}")


    print("\\n✅ Static site build complete!")
    print(f"Output is in the `{DIST_DIR.relative_to(SITE_ROOT)}` directory.")

if __name__ == "__main__":
    main()
