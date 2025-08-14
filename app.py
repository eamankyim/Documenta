from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from pdf_to_webpage import PDFToHTMLConverter
import uuid
import json
from datetime import datetime, timedelta, timezone
import re
import secrets
from models import db, User, Project, Token, ResetToken
from config import config

# Create Flask app
app = Flask(__name__)

# Configure the app based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Initialize database
db.init_app(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
CONVERSION_ENABLED = False  # Disable PDF extraction/conversion; use as formatting tool only

# --- Database-based user management ---
def _valid_email(email: str) -> bool:
    return bool(email) and re.match(r'^\S+@\S+\.\S+$', email)

def _current_user_email():
    return session.get('user_email')

def _is_authenticated() -> bool:
    return bool(_current_user_email())

def _get_user_plan() -> str:
    """Get the current user's plan from database"""
    if not _is_authenticated():
        return None
    email = _current_user_email()
    user = User.query.filter_by(email=email).first()
    return user.plan if user else 'Free'

def _can_create_projects() -> bool:
    """Check if current user can create projects (not Free plan)"""
    plan = _get_user_plan()
    return plan != 'Free'

def _require_auth():
    if not _is_authenticated():
        return redirect(url_for('signin', next=request.path))
    return None

# Database-based token management
def _get_or_create_token(unique_id):
    """Get or create token for a project from database"""
    token_record = Token.query.filter_by(unique_id=unique_id).first()
    if not token_record:
        tok = uuid.uuid4().hex
        token_record = Token(unique_id=unique_id, token=tok)
        db.session.add(token_record)
        db.session.commit()
        return tok
    return token_record.token

def _verify_token(unique_id, provided):
    """Verify token for a project from database"""
    token_record = Token.query.filter_by(unique_id=unique_id).first()
    return bool(token_record) and token_record.token == provided

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Marketing main page
    return render_template('website_home.html')

@app.route('/projects')
def projects():
    # Auth-adaptive projects page
    return render_template('index.html')

@app.route('/site')
def site_home():
    return render_template('website_home.html')

# Removed duplicate pricing and upgrade-plan routes

# --- Auth routes ---
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''
        error = None
        
        if not name or not email or not password:
            error = 'All fields are required'
        elif not _valid_email(email):
            error = 'Invalid email address'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters'
        elif password != confirm:
            error = 'Passwords do not match'
        
        # Check if user already exists in database
        existing_user = User.query.filter_by(email=email).first()
        if not error and existing_user:
            error = 'An account with that email already exists'
        
        if error:
            return render_template('signup.html', error=error, name=name, email=email)
        
        # Create new user in database
        user = User(
            name=name,
            email=email,
            plan='Free'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        session['user_email'] = email
        return redirect(url_for('pricing'))
    
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        
        # Get user from database
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return render_template('signin.html', error='Invalid email or password', email=email)
        
        session['user_email'] = email
        next_url = request.args.get('next')
        return redirect(next_url or url_for('projects'))
    
    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signin'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        # Check if user exists in database
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires = datetime.now(timezone.utc) + timedelta(hours=24)
            
            # Save reset token to database
            reset_token = ResetToken(
                email=email,
                token=token,
                expires=expires
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # In a real app, you'd send an email here
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
        else:
            # Don't reveal if email exists or not
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
        
        return redirect(url_for('signin'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Find valid reset token
    reset_token = ResetToken.query.filter_by(token=token).first()
    
    if not reset_token or reset_token.expires < datetime.now(timezone.utc):
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('signin'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        else:
            # Update user password
            user = User.query.filter_by(email=reset_token.email).first()
            if user:
                user.set_password(password)
                db.session.commit()
                
                # Delete used reset token
                db.session.delete(reset_token)
                db.session.commit()
                
                flash('Password updated successfully. Please sign in with your new password.', 'success')
                return redirect(url_for('signin'))
            else:
                flash('User not found.', 'error')
    
    return render_template('reset_password.html', token=token)

@app.route('/api/me')
def api_me():
    email = _current_user_email()
    user = User.query.filter_by(email=email).first() if email else None
    
    return jsonify({
        'authenticated': bool(user),
        'email': email,
        'name': user.name if user else None,
        'plan': user.plan if user else 'Free',
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if user can create projects (not Free plan)
    if not _can_create_projects():
        return jsonify({'error': 'Free plan users cannot upload files. Please upgrade to Pro or Enterprise to upload files.'}), 403
    
    if not CONVERSION_ENABLED:
        return jsonify({'error': 'PDF conversion is currently disabled. Use New Document or Open existing.'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
    
    try:
        # Generate unique ID for the project
        unique_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
        file.save(file_path)
        
        # Convert PDF to HTML
        converter = PDFToHTMLConverter(file_path, os.path.join(app.config['OUTPUT_FOLDER'], f"{unique_id}_converted.html"))
        converter.generate_html()
        
        # Read the generated HTML content
        output_filename = f"{unique_id}_converted.html"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Save project to database
        project = Project(
            unique_id=unique_id,
            filename=output_filename,
            title=filename.replace('.pdf', ''),
            content=html_content,
            size=len(html_content)
        )
        
        # Associate with current user if authenticated
        if _is_authenticated():
            user = User.query.filter_by(email=_current_user_email()).first()
            if user:
                project.user_id = user.id
        
        db.session.add(project)
        db.session.commit()
        
        # Clean up uploaded file
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'unique_id': unique_id,
            'filename': output_filename,
            'message': 'File uploaded and converted successfully!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/view/<unique_id>')
def view_converted(unique_id):
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    return render_template('viewer.html', unique_id=unique_id)

@app.route('/edit/<unique_id>')
def edit_converted(unique_id):
    # Require authentication to edit
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can edit projects (not Free plan)
    if not _can_create_projects():
        flash('Free plan users cannot edit projects. Please upgrade to Pro or Enterprise to edit projects.', 'error')
        return redirect(url_for('pricing'))
    
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    # Enforce token for editing
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return "Forbidden: missing or invalid edit token", 403
    
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
    # Require authentication to save
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can edit projects (not Free plan)
    if not _can_create_projects():
        return jsonify({'error': 'Free plan users cannot edit projects. Please upgrade to Pro or Enterprise to edit projects.'}), 403
    
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.get_json()
    content = data.get('content')
    project_name = data.get('project_name', '').strip()
    
    if not content:
        return jsonify({'error': 'No content provided'}), 400
    
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    # If this is the first save and no project name is provided, ask for one
    if not project_name:
        return jsonify({
            'needs_name': True,
            'message': 'Please provide a project name for your first save'
        }), 400
    
    # Update the HTML content with the project name
    content = re.sub(r'<title>.*?</title>', f'<title>{project_name}</title>', content, flags=re.IGNORECASE | re.DOTALL)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'success': True, 'message': f'Project "{project_name}" saved successfully!'})

@app.route('/download/<unique_id>')
def download_file(unique_id):
    # Require authentication to download
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can download projects (not Free plan)
    if not _can_create_projects():
        flash('Free plan users cannot download projects. Please upgrade to Pro or Enterprise to download projects.', 'error')
        return redirect(url_for('pricing'))
    
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return "Forbidden: missing or invalid token", 403
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return "File not found", 404
    
    return send_file(html_path, as_attachment=True, download_name=html_file)

@app.route('/api/delete/<unique_id>', methods=['DELETE'])
def delete_file(unique_id):
    # Require authentication to delete
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can edit projects (not Free plan)
    if not _can_create_projects():
        return jsonify({'error': 'Free plan users cannot delete projects. Please upgrade to Pro or Enterprise to delete projects.'}), 403
    
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return jsonify({'error': 'Forbidden'}), 403
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    if not os.path.exists(html_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        os.remove(html_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/new')
def new_document():
    # Require authentication to create
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can create projects (not Free plan)
    if not _can_create_projects():
        flash('Free plan users cannot create new projects. Please upgrade to Pro or Enterprise to create projects.', 'error')
        return redirect(url_for('pricing'))
    
    """Create a new blank document and redirect to the editor."""
    unique_id = str(uuid.uuid4())
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)

    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    # Minimal editable document with a main-content wrapper expected by the editor
    default_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Project</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2c3e50; }
        .main-content { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        p { line-height: 1.7; margin: 12px 0; }
    </style>
    </head>
<body>
    <div class="main-content">
        <p>Start typing here...</p>
    </div>
</body>
</html>'''

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(default_html)

    # create edit token
    _get_or_create_token(unique_id)
    return redirect(url_for('edit_converted', unique_id=unique_id, token=_get_or_create_token(unique_id)))

@app.route('/api/list_outputs')
def list_outputs():
    # Require authentication to list user documents (basic gating)
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
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
            
            # Extract title preview from <title> tag only
            title = None
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content_head = f.read(200000)
                m = re.search(r'<title>(.*?)</title>', content_head, re.IGNORECASE | re.DOTALL)
                if m:
                    title = re.sub(r'\s+', ' ', m.group(1)).strip()
        
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

@app.route('/api/token/<unique_id>')
def get_token(unique_id):
    # Require authentication to obtain edit/download token
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    if not os.path.exists(html_path):
        return jsonify({'error': 'File not found'}), 404
    tok = _get_or_create_token(unique_id)
    return jsonify({'token': tok})

@app.route('/api/rename/<unique_id>', methods=['POST'])
def rename_project(unique_id):
    # Require authentication to rename
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can edit projects (not Free plan)
    if not _can_create_projects():
        return jsonify({'error': 'Free plan users cannot rename projects. Please upgrade to Pro or Enterprise to rename projects.'}), 403
    
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.get_json()
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({'error': 'Project name is required'}), 400
    
    html_file = f"{unique_id}_converted.html"
    html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_file)
    
    if not os.path.exists(html_path):
        return jsonify({'error': 'Project not found'}), 404
    
    try:
        # Read current content
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update title in HTML
        
        # Update <title> tag only (for browser tab and metadata)
        content = re.sub(r'<title>.*?</title>', f'<title>{new_name}</title>', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Write updated content
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': f'Project renamed to "{new_name}"'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to rename project: {str(e)}'}), 500

# New database-based routes
@app.route('/project/<unique_id>')
def view_project(unique_id):
    """View a project from the database"""
    # Get project from database
    project = Project.query.filter_by(unique_id=unique_id).first()
    
    if not project:
        return "Project not found", 404
    
    # Check if token is required
    token = request.args.get('token')
    if token and not _verify_token(unique_id, token):
        return "Invalid token", 403
    
    return project.content

@app.route('/api/projects')
def api_projects():
    """Get projects for the current user from database"""
    if not _is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    user = User.query.filter_by(email=_current_user_email()).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user's projects from database
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.created_at.desc()).all()
    
    project_list = []
    for project in projects:
        project_list.append({
            'id': project.id,
            'unique_id': project.unique_id,
            'filename': project.filename,
            'title': project.title,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'size': project.size
        })
    
    return jsonify(project_list)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/upgrade/<plan>')
def upgrade_plan(plan):
    if not _is_authenticated():
        return redirect(url_for('signin'))
    
    if plan not in ['Pro', 'Enterprise']:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('pricing'))
    
    # Update user plan in database
    user = User.query.filter_by(email=_current_user_email()).first()
    if user:
        user.plan = plan
        user.plan_updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        flash(f'Successfully upgraded to {plan} plan!', 'success')
    else:
        flash('User not found.', 'error')
    
    return redirect(url_for('pricing'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    try:
        print("=" * 50)
        print("STARTING FLASK APPLICATION")
        print("=" * 50)
        
        # Create database tables if they don't exist
        print("Initializing database...")
        with app.app_context():
            db.create_all()
        print("Database initialized successfully!")
        
        # Use PORT environment variable for Render deployment
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting Flask app on port {port}")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"Debug mode: {os.environ.get('FLASK_DEBUG', 'False')}")
        print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
        print("=" * 50)
        print("APP IS STARTING - THIS SHOULD STAY RUNNING")
        print("=" * 50)
        
        app.run(debug=False, host='0.0.0.0', port=port)
        
    except Exception as e:
        print(f"ERROR starting app: {e}")
        import traceback
        traceback.print_exc()
        raise
