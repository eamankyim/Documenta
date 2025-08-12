from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from pdf_to_webpage import PDFToHTMLConverter
import uuid
import json
from datetime import datetime, timedelta
import re
import secrets
from models import db, User, Project, Token, ResetToken

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///splitter.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CONVERSION_ENABLED = False  # Disable PDF extraction/conversion; use as formatting tool only

# Initialize database
db.init_app(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
# --- Database-based user store ---
def _load_users():
    users = {}
    for user in User.query.all():
        users[user.email] = {
            'name': user.name,
            'email': user.email,
            'password_hash': user.password_hash,
            'created_at': user.created_at.isoformat(),
            'plan': user.plan,
            'plan_updated_at': user.plan_updated_at.isoformat() if user.plan_updated_at else None
        }
    return users

def _save_users(users):
    # This function is kept for compatibility but now uses database
    pass

def _valid_email(email: str) -> bool:
    return bool(email) and re.match(r'^\S+@\S+\.\S+$', email)

def _current_user_email():
    return session.get('user_email')

def _is_authenticated() -> bool:
    return bool(_current_user_email())

def _get_user_plan() -> str:
    """Get the current user's plan"""
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

# Password reset functionality
def _load_reset_tokens():
    tokens = {}
    for reset_token in ResetToken.query.all():
        if reset_token.expires > datetime.utcnow():
            tokens[reset_token.email] = {
                'token': reset_token.token,
                'expires': reset_token.expires.isoformat()
            }
    return tokens

def _save_reset_tokens(tokens):
    # This function is kept for compatibility but now uses database
    pass

def _create_reset_token(email):
    """Create a password reset token for an email"""
    # Clean up expired tokens
    ResetToken.query.filter(ResetToken.expires < datetime.utcnow()).delete()
    db.session.commit()
    
    # Generate new token
    reset_token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=24)
    
    # Remove existing token for this email
    ResetToken.query.filter_by(email=email).delete()
    
    # Create new token
    new_reset_token = ResetToken(
        email=email,
        token=reset_token,
        expires=expires
    )
    db.session.add(new_reset_token)
    db.session.commit()
    
    return reset_token

def _verify_reset_token(email, token):
    """Verify a password reset token"""
    reset_token = ResetToken.query.filter_by(email=email, token=token).first()
    if not reset_token:
        return False
    
    if datetime.utcnow() > reset_token.expires:
        # Token expired, remove it
        db.session.delete(reset_token)
        db.session.commit()
        return False
    
    return True

def _clear_reset_token(email):
    """Clear a password reset token after use"""
    ResetToken.query.filter_by(email=email).delete()
    db.session.commit()


# Database-based token store
def _load_tokens():
    tokens = {}
    for token_obj in Token.query.all():
        tokens[token_obj.unique_id] = token_obj.token
    return tokens

def _save_tokens(tokens):
    # This function is kept for compatibility but now uses database
    pass

def _get_or_create_token(unique_id):
    token_obj = Token.query.filter_by(unique_id=unique_id).first()
    if not token_obj:
        tok = uuid.uuid4().hex
        token_obj = Token(unique_id=unique_id, token=tok)
        db.session.add(token_obj)
        db.session.commit()
        return tok
    return token_obj.token

def _verify_token(unique_id, provided):
    token_obj = Token.query.filter_by(unique_id=unique_id).first()
    if not token_obj:
        return False
    return token_obj.token == provided

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

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/upgrade-plan', methods=['POST'])
def upgrade_plan():
    if not _is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    plan = data.get('plan')
    
    if plan not in ['Pro', 'Enterprise']:
        return jsonify({'error': 'Invalid plan'}), 400
    
    email = _current_user_email()
    user = User.query.filter_by(email=email).first()
    
    if user:
        user.plan = plan
        user.plan_updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'plan': plan,
            'message': f'Successfully upgraded to {plan} plan!'
        })
    
    return jsonify({'error': 'User not found'}), 404

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
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if not error and existing_user:
            error = 'An account with that email already exists'
        if error:
            return render_template('signup.html', error=error, name=name, email=email)
        
        # Create new user
        new_user = User(
            name=name,
            email=email,
            plan='Free'
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        session['user_email'] = email
        return redirect(url_for('pricing'))
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
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
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Create reset token
            reset_token = _create_reset_token(email)
            # In a real app, you would send this via email
            # For now, we'll just show it (NOT recommended for production)
            flash(f'Password reset token: {reset_token}', 'info')
            return render_template('forgot_password.html', 
                                message='If an account with that email exists, a reset link has been sent.',
                                email=email)
        else:
            # Don't reveal if email exists or not
            return render_template('forgot_password.html', 
                                message='If an account with that email exists, a reset link has been sent.')
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm')
        
        if not email or not new_password or not confirm_password:
            flash('All fields are required', 'error')
        elif new_password != confirm_password:
            flash('Passwords do not match', 'error')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters', 'error')
        elif not _verify_reset_token(email, token):
            flash('Invalid or expired reset token', 'error')
        else:
            # Update password
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                _clear_reset_token(email)
                flash('Password updated successfully! You can now sign in.', 'success')
                return redirect(url_for('signin'))
            else:
                flash('Account not found', 'error')
    
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
            
            # Read the converted HTML content
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract title from HTML
            title = filename.replace('.pdf', '')
            import re
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = re.sub(r'\s+', ' ', title_match.group(1)).strip()
            
            # Store project in database
            project = Project(
                unique_id=unique_id,
                filename=f"{unique_id}_converted.html",
                title=title,
                content=html_content,
                size=len(html_content)
            )
            db.session.add(project)
            db.session.commit()
            
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
    project = Project.query.filter_by(unique_id=unique_id).first()
    
    if not project:
        return "Project not found", 404
    
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
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    
    if not project:
        return "Project not found", 404
    
    # Enforce token for editing
    token = request.args.get('token')
    if not _verify_token(unique_id, token):
        return "Forbidden: missing or invalid edit token", 403
    
    return render_template('editor.html', unique_id=unique_id)

@app.route('/api/content/<unique_id>')
def get_content(unique_id):
    project = Project.query.filter_by(unique_id=unique_id).first()
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    return jsonify({'content': project.content})

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
    
    if not content:
        return jsonify({'error': 'No content provided'}), 400
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    project.content = content
    project.size = len(content)
    project.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

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
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    if not project:
        return "Project not found", 404
    
    # Create a temporary file for download
    import tempfile
    import os
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
    temp_file.write(project.content)
    temp_file.close()
    
    try:
        return send_file(temp_file.name, as_attachment=True, download_name=project.filename)
    finally:
        # Clean up temporary file
        os.unlink(temp_file.name)

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
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    try:
        # Delete associated token
        Token.query.filter_by(unique_id=unique_id).delete()
        # Delete project
        db.session.delete(project)
        db.session.commit()
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
    
    # Minimal editable document with a main-content wrapper expected by the editor
    default_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Untitled Document</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2c3e50; }
        .main-content { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .document-header { border-bottom: 1px solid #e0e0e0; margin-bottom: 20px; }
        .main-title { font-size: 22px; font-weight: 600; }
        p { line-height: 1.7; margin: 12px 0; }
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

    # Create project in database
    project = Project(
        unique_id=unique_id,
        filename=f"{unique_id}_converted.html",
        title="Untitled Document",
        content=default_html,
        size=len(default_html)
    )
    db.session.add(project)
    db.session.commit()

    # create edit token
    _get_or_create_token(unique_id)
    return redirect(url_for('edit_converted', unique_id=unique_id, token=_get_or_create_token(unique_id)))

@app.route('/new-named', methods=['GET', 'POST'])
def new_named_document():
    # Require authentication to create
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Check if user can create projects (not Free plan)
    if not _can_create_projects():
        flash('Free plan users cannot create new projects. Please upgrade to Pro or Enterprise to create projects.', 'error')
        return redirect(url_for('pricing'))
    
    if request.method == 'POST':
        project_name = request.form.get('project_name', '').strip()
        if not project_name:
            flash('Project name is required', 'error')
            return render_template('new_project.html')
        
        """Create a new named document and redirect to the editor."""
        unique_id = str(uuid.uuid4())
        
        # Create document with custom title
        default_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
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
            <h1 class="main-title">{project_name}</h1>
        </header>
        <section>
            <p>Start typing here...</p>
        </section>
    </main>
</body>
</html>'''

        # Create project in database
        project = Project(
            unique_id=unique_id,
            filename=f"{unique_id}_converted.html",
            title=project_name,
            content=default_html,
            size=len(default_html)
        )
        db.session.add(project)
        db.session.commit()

        # Create edit token
        _get_or_create_token(unique_id)
        return redirect(url_for('edit_converted', unique_id=unique_id, token=_get_or_create_token(unique_id)))
    
    return render_template('new_project.html')

@app.route('/api/list_outputs')
def list_outputs():
    # Require authentication to list user documents (basic gating)
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    # Get projects from database
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    
    documents = []
    for project in projects:
        documents.append({
            'unique_id': project.unique_id,
            'filename': project.filename,
            'modified': project.updated_at.isoformat(),
            'size': project.size,
            'title': project.title or 'Untitled Document',
        })

    return jsonify({'documents': documents})

@app.route('/api/token/<unique_id>')
def get_token(unique_id):
    # Require authentication to obtain edit/download token
    auth_resp = _require_auth()
    if auth_resp:
        return auth_resp
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
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
    
    project = Project.query.filter_by(unique_id=unique_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    try:
        # Update project title in database
        project.title = new_name
        
        # Update content with new title
        content = project.content
        
        # Update <title> tag
        import re
        content = re.sub(r'<title>.*?</title>', f'<title>{new_name}</title>', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Update main title in h1
        content = re.sub(r'<h1[^>]*class=["\"][^"\"]*main-title[^"\"]*["\"][^>]*>.*?</h1>', 
                        f'<h1 class="main-title">{new_name}</h1>', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Update project content and size
        project.content = content
        project.size = len(content)
        project.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Project renamed to "{new_name}"'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to rename project: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 