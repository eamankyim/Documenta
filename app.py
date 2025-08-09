from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
from werkzeug.utils import secure_filename
from pdf_to_webpage import PDFToHTMLConverter
import uuid
import json
from datetime import datetime
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
CONVERSION_ENABLED = False  # Disable PDF extraction/conversion; use as formatting tool only

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if not CONVERSION_ENABLED:
        return jsonify({'error': 'PDF conversion is currently disabled. Use New Document or Open existing.'}), 400
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{unique_id}_converted.html")
        
        # Save uploaded file
        file.save(pdf_path)
        
        try:
            # Convert PDF to HTML
            converter = PDFToHTMLConverter(pdf_path, output_path)
            converter.generate_html()
            
            return jsonify({
                'success': True,
                'unique_id': unique_id,
                'original_filename': filename,
                'html_file': f"{unique_id}_converted.html"
            })
        except Exception as e:
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/view/<unique_id>')
def view_converted(unique_id):
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    return render_template('viewer.html', unique_id=unique_id)

@app.route('/edit/<unique_id>')
def edit_converted(unique_id):
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    return render_template('editor.html', unique_id=unique_id)

@app.route('/api/content/<unique_id>')
def get_content(unique_id):
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return jsonify({'error': 'File not found'}), 404
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({'content': content})

@app.route('/api/save/<unique_id>', methods=['POST'])
def save_content(unique_id):
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'No content provided'}), 400
    
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'success': True})

@app.route('/download/<unique_id>')
def download_file(unique_id):
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    return send_file(html_path, as_attachment=True, download_name=html_file)

@app.route('/new')
def new_document():
    """Create a new blank document and redirect to the editor."""
    unique_id = str(uuid.uuid4())
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)

    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    # Minimal editable document with a main-content wrapper expected by the editor
    default_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Untitled Document</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2c3e50; }}
        .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .document-header {{ border-bottom: 1px solid #e0e0e0; margin-bottom: 20px; }}
        .main-title {{ font-size: 22px; font-weight: 600; }}
        p {{ line-height: 1.7; margin: 12px 0; }}
    </style>
    </head>
<body>
    <main class="main-content">
        <header class="document-header">
            <h1 class="main-title">Untitled Document</h1>
        </header>
        <section>
            <p>Start typing here...</p>
        </section>
    </main>
</body>
</html>'''

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(default_html)

    return redirect(url_for('edit_converted', unique_id=unique_id))

@app.route('/api/list_outputs')
def list_outputs():
    outputs_dir = app.config['OUTPUT_FOLDER']
    if not os.path.exists(outputs_dir):
        return jsonify({'documents': []})

    documents = []
    for name in os.listdir(outputs_dir):
        if not name.endswith('_converted.html'):
            continue
        unique_id = name.split('_')[0]
        full_path = os.path.join(outputs_dir, name)
        try:
            mtime = os.path.getmtime(full_path)
            modified = datetime.fromtimestamp(mtime).isoformat()
            size = os.path.getsize(full_path)
            # Extract title preview
            title = None
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content_head = f.read(200000)
                m = re.search(r'<title>(.*?)</title>', content_head, re.IGNORECASE | re.DOTALL)
                if m:
                    title = re.sub(r'\s+', ' ', m.group(1)).strip()
                if not title:
                    m2 = re.search(r'<h1[^>]*class=["\"][^"\"]*main-title[^"\"]*["\"][^>]*>(.*?)</h1>', content_head, re.IGNORECASE | re.DOTALL)
                    if m2:
                        title = re.sub(r'<[^>]+>', '', m2.group(1))
                        title = re.sub(r'\s+', ' ', title).strip()
        
        except Exception:
            modified = None
            size = None
            title = None
        documents.append({
            'unique_id': unique_id,
            'filename': name,
            'modified': modified,
            'size': size,
            'title': title or 'Untitled Document',
        })

    # Sort by most recent first
    documents.sort(key=lambda d: d.get('modified') or '', reverse=True)
    return jsonify({'documents': documents})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 