from flask import Flask, g, render_template, url_for
from markupsafe import Markup
import sqlite3
from pathlib import Path
from collections import defaultdict
import re
import markdown

# --- Path Configuration ---
SITE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = SITE_ROOT / 'assets' / 'asset_index.db'
TEMPLATE_FOLDER = SITE_ROOT / 'templates'
NOTEBOOK_DIR = SITE_ROOT / 'assets' / 'data' / 'Hawk_Eye_Dev_Notebooks' / '01_Rap_Notebook'

app = Flask(__name__,
            static_folder=SITE_ROOT,
            static_url_path='',
            template_folder=TEMPLATE_FOLDER)

def format_title(text: str):
    """Converts a filename-safe string to a more readable title."""
    return re.sub(r'[_-]', ' ', text).title()

# --- Shared Data for Templates ---
@app.context_processor
def inject_notebooks():
    """Makes the list of notebooks available to all templates."""
    notebooks = []
    if NOTEBOOK_DIR.exists():
        for f in sorted(NOTEBOOK_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in ['.html', '.md']:
                notebooks.append({
                    'title': format_title(f.stem),
                    'key': f.stem
                })
    return dict(notebooks=notebooks)

# --- Database ---
def get_db():
    db = getattr(g, '_db', None)
    if db is None:
        if not DB_PATH.exists():
            return None
        db = g._db = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_db', None)
    if db is not None:
        db.close()

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/albums')
def albums_api():
    db = get_db()
    if not db:
        return "Database not found. Please run `tools/build_asset_index.py`.", 500
    
    cur = db.execute('SELECT key, sku, title, album, type, image_path FROM content ORDER BY album, title')
    rows = cur.fetchall()
    
    albums = defaultdict(lambda: {'items': [], 'image_path': ''})
    for row in rows:
        album_title = row['album']
        albums[album_title]['items'].append(dict(row))
        if not albums[album_title]['image_path'] and row['image_path']:
            albums[album_title]['image_path'] = url_for('static', filename='assets/' + row['image_path'])

    # Convert defaultdict to a list of dicts for JSON
    result = []
    for album_title, data in albums.items():
        result.append({
            'title': album_title,
            'image_path': data['image_path'],
            'items': data['items']
        })
    return result

@app.route('/content/<content_key>')
def content_page(content_key):
    db = get_db()
    if not db:
        return "Database not found.", 500

    cur = db.execute('SELECT * FROM content WHERE key = ?', (content_key,))
    row = cur.fetchone()
    if not row:
        return "Content not found", 404

    content_body = "No content available for this item."
    if row['lyrics_path']:
        content_file = SITE_ROOT / 'assets' / row['lyrics_path']
        if content_file.is_file():
            content_body = content_file.read_text(encoding='utf-8')

    audio_url = url_for('static', filename='assets/' + row['audio_path']) if row['audio_path'] else ''
    image_url = url_for('static', filename='assets/' + row['image_path']) if row['image_path'] else ''

    return render_template('content.html',
        title=row['title'],
        album=row['album'],
        type=row['type'],
        audio_url=audio_url,
        image_url=image_url,
        content=content_body
    )

@app.route('/notebook/<notebook_key>')
def notebook_page(notebook_key):
    """Renders a single notebook page from HTML or Markdown."""
    file_path_html = NOTEBOOK_DIR / f"{notebook_key}.html"
    file_path_md = NOTEBOOK_DIR / f"{notebook_key}.md"

    content = ""
    if file_path_html.exists():
        content = file_path_html.read_text(encoding='utf-8')
    elif file_path_md.exists():
        md_content = file_path_md.read_text(encoding='utf-8')
        content = markdown.markdown(md_content)
    else:
        return "Notebook not found", 404
    
    return render_template('notebook.html',
        title=format_title(notebook_key),
        content=Markup(content)
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)
