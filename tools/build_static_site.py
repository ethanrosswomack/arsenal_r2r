#!/usr/bin/env python3
"""
Converts the Arsenal project into a fully static HTML website with media URLs
pointing to Cloudflare R2.
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
TEMPLATE_DIR = SITE_ROOT / "templates"

# --- R2 and URL Configuration ---
BASE_R2_URL = "https://r2.reincarnated2resist.com"
ALBUM_DIR_MAP = {
    "SG": "01_singles",
    "FD": "02_full-disclosure",
    "BAP": "03_behold-a-pale-horse",
    "M": "04_milabs",
    "SB": "05_shadow-banned",
    "ME": "06_malicious-ep",
}

AUDIO_EXTS = {".mp3", ".m4a", ".ogg", ".wav", ".flac", ".aac"}
TEXT_EXTS = {".txt", ".lrc", ".md"}

def format_title(text: str):
    """Converts a filename-safe string to a more readable title."""
    return re.sub(r'[_-]', ' ', text).title()

def build_song_data():
    """
    Scans the local assets directory to build a structured list of all songs,
    generating public R2 URLs for all media.
    """
    content_root = ASSETS_DIR / "tracks"
    if not content_root.exists():
        raise SystemExit(f"Content directory not found: `{content_root}`")

    all_songs = []
    for sku_dir in sorted(content_root.iterdir()):
        if not sku_dir.is_dir():
            continue

        # Expect dirs like HAWK-SG-01, HAWK-SB-03, etc.
        match = re.match(r"HAWK-([A-Z]+)-([0-9]+)$", sku_dir.name)
        if not match:
            print(f"[SKIP] Directory '{sku_dir.name}' does not match expected SKU pattern.")
            continue

        album_code, track_num_str = match.groups()
        sku = sku_dir.name
        album_r2_dir = ALBUM_DIR_MAP.get(album_code)

        if not album_r2_dir:
            print(f"[WARN] No R2 directory mapping for album code '{album_code}' in SKU '{sku}'.")
            continue

        # Find the audio file to determine the slug
        audio_files = list(sku_dir.glob("*.mp3"))
        if not audio_files:
            print(f"[WARN] No .mp3 file found in {sku_dir.name}")
            continue
        
        slug = audio_files[0].stem
        
        # Find the local lyrics file path for embedding content
        local_lyrics_path = ""
        for ext in TEXT_EXTS:
            potential_lyrics_file = sku_dir / f"{slug}{ext}"
            if potential_lyrics_file.is_file():
                local_lyrics_path = potential_lyrics_file.relative_to(ASSETS_DIR).as_posix()
                break

        all_songs.append({
            "key": sku,
            "sku": sku,
            "title": format_title(slug),
            "album": format_title(sku_dir.name),
            "type": "track",
            "audio_path": f"{BASE_R2_URL}/{album_r2_dir}/{sku}/{slug}.mp3",
            "image_path": f"{BASE_R2_URL}/{album_r2_dir}/{sku}/cover.png",
            "local_lyrics_path": local_lyrics_path, # Used only during build
        })

    # Group songs by album for the main JSON data file
    albums = defaultdict(lambda: {'items': [], 'image_path': ''})
    for song in sorted(all_songs, key=lambda s: s['title']):
        album_title = song['album']
        albums[album_title]['items'].append(song)
        if not albums[album_title]['image_path'] and song['image_path']:
            albums[album_title]['image_path'] = song['image_path']

    result = [{'title': title, **data} for title, data in albums.items()]
    return result, all_songs

def main():
    """Generates the static site."""
    print("Starting static site build...")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()
    
    # Copy only necessary static files (CSS, JS)
    # We no longer copy the entire assets folder, as media is on R2
    static_dest = DIST_DIR / "static"
    static_dest.mkdir()
    shutil.copy(ASSETS_DIR / "styles.css", static_dest)
    shutil.copy(ASSETS_DIR / "main.js", static_dest)
    print(f"Copied essential assets to: {static_dest.relative_to(SITE_ROOT)}")

    album_data, all_songs = build_song_data()
    
    # Write the main data file for the homepage
    api_dir = DIST_DIR / "api"
    api_dir.mkdir()
    with (api_dir / "data.json").open("w", encoding="utf-8") as f:
        json.dump(album_data, f, indent=2)
    print("Generated R2-powered song data at: api/data.json")

    # Generate individual song pages
    content_template = (TEMPLATE_DIR / "content.html").read_text(encoding="utf-8")
    nav_template = (TEMPLATE_DIR / "nav.html").read_text(encoding="utf-8")
    content_dir = DIST_DIR / "content"
    content_dir.mkdir()

    for song in all_songs:
        lyrics = "No lyrics available for this song."
        if song['local_lyrics_path']:
            lyrics_file = ASSETS_DIR / song['local_lyrics_path']
            if lyrics_file.exists():
                lyrics = f"<pre>{lyrics_file.read_text(encoding='utf-8')}</pre>"

        page_content = content_template.replace("{{ title }}", song['title'])
        page_content = page_content.replace("{{ content }}", lyrics)
        page_content = page_content.replace("{{ audio_url }}", song['audio_path'])
        page_content = page_content.replace("{{ image_url }}", song['image_path'])
        page_content = page_content.replace("{% include 'nav.html' %}", nav_template)

        output_path = content_dir / f"{song['key']}.html"
        output_path.write_text(page_content, encoding="utf-8")
    
    print(f"Generated {len(all_songs)} song pages with R2 URLs.")

    # Process and copy main index page
    index_template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    index_nav_template = nav_template.replace("../index.html", "index.html")
    index_content = index_template.replace("{% include 'nav.html' %}", index_nav_template)
    (DIST_DIR / "index.html").write_text(index_content, encoding="utf-8")
    print(f"Processed and copied index.html to: {DIST_DIR.relative_to(SITE_ROOT)}")

    print("\n✅ Static site build complete!")
    print(f"Output is in the `{DIST_DIR.relative_to(SITE_ROOT)}` directory.")

if __name__ == "__main__":
    main()
