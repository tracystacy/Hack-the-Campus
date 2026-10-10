import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, send_from_directory
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'greenpulse.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app = Flask(__name__)
# Keep secret key stable during development so restarts don't invalidate sessions
app.secret_key = os.environ.get('GREENPULSE_SECRET', 'greenpulse-dev-secret-key-maseno-2026')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

MISSIONS = [
    ('Campus Cleanup', 'Collect and safely dispose of litter in a shared campus or neighbourhood space.', 'Cleanup', 30, '🧹'),
    ('Waste Sorting Hero', 'Separate recyclable materials (paper, plastics, cans) from general waste.', 'Recycling', 20, '♻️'),
    ('Plastic-Free Day', 'Avoid single-use plastic and choose reusable bottles, cups, and bags.', 'Plastic reduction', 15, '🌱'),
    ('Plant for Tomorrow', 'Plant or care for a tree or native plant in a green space.', 'Tree care', 35, '🌳'),
]

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS missions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          description TEXT NOT NULL,
          category TEXT NOT NULL,
          points INTEGER NOT NULL,
          emoji TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submissions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          mission_id INTEGER NOT NULL,
          details TEXT NOT NULL,
          location TEXT,
          quantity REAL,
          unit TEXT,
          photo TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL,
          reviewed_at TEXT,
          reviewed_by INTEGER,
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(mission_id) REFERENCES missions(id),
          FOREIGN KEY(reviewed_by) REFERENCES users(id)
        );
        ''')
        if db.execute('SELECT COUNT(*) FROM missions').fetchone()[0] == 0:
            db.executemany(
                'INSERT INTO missions(title, description, category, points, emoji) VALUES (?, ?, ?, ?, ?)',
                MISSIONS
            )
        admin = db.execute('SELECT id FROM users WHERE email=?', ('admin@greenpulse.local',)).fetchone()
        if not admin:
            db.execute(
                'INSERT INTO users(name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                ('GreenPulse Admin', 'admin@greenpulse.local', generate_password_hash('GreenPulse2026!'), 'admin', datetime.now().isoformat(timespec='minutes'))
            )

init_db()

def current_user():
    if 'user_id' not in session:
        return None
    with connect() as db:
        return db.execute('SELECT id, name, email, role FROM users WHERE id=?', (session['user_id'],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user['role'] != 'admin':
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_user():
    return {'logged_in_user': current_user()}

@app.route('/')
def home():
    with connect() as db:
        stats = {
            'actions': db.execute("SELECT COUNT(*) FROM submissions WHERE status='approved'").fetchone()[0],
            'people': db.execute('SELECT COUNT(*) FROM users WHERE role="user"').fetchone()[0],
            'waste': db.execute("SELECT COALESCE(SUM(quantity), 0) FROM submissions WHERE status='approved' AND lower(unit) IN ('kg','kgs','kilograms')").fetchone()[0],
            'trees': db.execute("SELECT COALESCE(SUM(CASE WHEN lower(s.unit)='trees' AND s.quantity > 0 THEN s.quantity ELSE 1 END), 0) FROM submissions s JOIN missions m ON s.mission_id=m.id WHERE s.status='approved' AND (lower(m.category) LIKE '%tree%' OR lower(s.unit)='trees')").fetchone()[0]
        }
        missions = db.execute('SELECT * FROM missions ORDER BY id LIMIT 4').fetchall()
        leaders = db.execute('''
            SELECT u.name, COALESCE(SUM(m.points), 0) AS points
            FROM users u
            JOIN submissions s ON s.user_id = u.id AND s.status = 'approved'
            JOIN missions m ON m.id = s.mission_id
            WHERE u.role = 'user'
            GROUP BY u.id
            HAVING points > 0
            ORDER BY points DESC, u.name
            LIMIT 5
        ''').fetchall()
    return render_template('home.html', stats=stats, missions=missions, leaders=leaders)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()[:80]
        email = request.form.get('email', '').strip().lower()[:160]
        password = request.form.get('password', '')
        if not name or '@' not in email or len(password) < 8:
            flash('Enter your name, a valid email address and a password of at least 8 characters.', 'error')
        else:
            try:
                with connect() as db:
                    cur = db.execute(
                        'INSERT INTO users(name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                        (name, email, generate_password_hash(password), 'user', datetime.now().isoformat(timespec='minutes'))
                    )
                    session['user_id'] = cur.lastrowid
                flash('Welcome to GreenPulse! Your account is ready.', 'success')
                return redirect(url_for('missions'))
            except sqlite3.IntegrityError:
                flash('An account with that email already exists. Please log in.', 'error')
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            flash('You are now logged in.', 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(url_for('admin') if user['role'] == 'admin' else url_for('missions'))
        flash('Incorrect email or password.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/missions')
def missions():
    with connect() as db:
        items = db.execute('SELECT * FROM missions ORDER BY id').fetchall()
        mine = set()
        user = current_user()
        if user:
            mine = {
                r['mission_id']
                for r in db.execute('SELECT DISTINCT mission_id FROM submissions WHERE user_id=?', (user['id'],)).fetchall()
            }
    return render_template('missions.html', missions=items, submitted_missions=mine)

@app.route('/submit/<int:mission_id>', methods=['GET', 'POST'])
@login_required
def submit(mission_id):
    with connect() as db:
        mission = db.execute('SELECT * FROM missions WHERE id=?', (mission_id,)).fetchone()
    if not mission:
        abort(404)
    if request.method == 'POST':
        details = request.form.get('details', '').strip()[:1000]
        location = request.form.get('location', '').strip()[:160]
        unit = request.form.get('unit', '').strip()[:20]
        try:
            quantity = float(request.form.get('quantity') or 0)
        except ValueError:
            quantity = 0
        quantity = max(0, min(quantity, 1000000))
        photo_name = None
        photo = request.files.get('photo')

        if not details:
            flash('Please describe the action you completed.', 'error')
            return render_template('submit.html', mission=mission)

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash('Photo must be JPG, JPEG, PNG, or WEBP format.', 'error')
                return render_template('submit.html', mission=mission)
            clean_name = secure_filename(photo.filename) or 'evidence.jpg'
            photo_name = secrets.token_hex(8) + '_' + clean_name[:100]
            photo.save(os.path.join(UPLOAD_DIR, photo_name))

        with connect() as db:
            db.execute(
                '''INSERT INTO submissions(user_id, mission_id, details, location, quantity, unit, photo, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (session['user_id'], mission_id, details, location, quantity, unit, photo_name, 'pending', datetime.now().isoformat(timespec='minutes'))
            )
        flash('Action submitted for review! Points will be awarded once verified by an admin.', 'success')
        return redirect(url_for('my_actions'))

    return render_template('submit.html', mission=mission)

@app.route('/my-actions')
@login_required
def my_actions():
    with connect() as db:
        items = db.execute('''
            SELECT s.*, m.title, m.emoji, m.points
            FROM submissions s
            JOIN missions m ON m.id = s.mission_id
            WHERE s.user_id = ?
            ORDER BY s.id DESC
        ''', (session['user_id'],)).fetchall()
        points = db.execute('''
            SELECT COALESCE(SUM(m.points), 0)
            FROM submissions s
            JOIN missions m ON m.id = s.mission_id
            WHERE s.user_id = ? AND s.status = 'approved'
        ''', (session['user_id'],)).fetchone()[0]
    return render_template('my_actions.html', submissions=items, points=points)

@app.route('/leaderboard')
def leaderboard():
    with connect() as db:
        leaders = db.execute('''
            SELECT u.name, COALESCE(SUM(m.points), 0) AS points, COUNT(s.id) AS actions
            FROM users u
            JOIN submissions s ON s.user_id = u.id AND s.status = 'approved'
            JOIN missions m ON m.id = s.mission_id
            WHERE u.role = 'user'
            GROUP BY u.id
            HAVING points > 0
            ORDER BY points DESC, actions DESC, u.name
        ''').fetchall()
    return render_template('leaderboard.html', leaders=leaders)

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    user = current_user()
    if user['role'] == 'admin':
        return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)
    with connect() as db:
        owned = db.execute('SELECT id FROM submissions WHERE photo=? AND user_id=?', (filename, user['id'])).fetchone()
        if owned:
            return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)
    abort(403)

@app.route('/admin')
@admin_required
def admin():
    with connect() as db:
        pending = db.execute('''
            SELECT s.*, u.name AS user_name, u.email, m.title, m.emoji, m.points
            FROM submissions s
            JOIN users u ON u.id = s.user_id
            JOIN missions m ON m.id = s.mission_id
            WHERE s.status = 'pending'
            ORDER BY s.id ASC
        ''').fetchall()
        recent = db.execute('''
            SELECT s.*, u.name AS user_name, m.title, m.emoji, m.points
            FROM submissions s
            JOIN users u ON u.id = s.user_id
            JOIN missions m ON m.id = s.mission_id
            WHERE s.status != 'pending'
            ORDER BY s.id DESC
            LIMIT 10
        ''').fetchall()
        missions_list = db.execute('''
            SELECT m.*, COUNT(s.id) AS submission_count
            FROM missions m
            LEFT JOIN submissions s ON s.mission_id = m.id
            GROUP BY m.id
            ORDER BY m.id DESC
        ''').fetchall()
        stats = {
            'pending': len(pending),
            'approved': db.execute("SELECT COUNT(*) FROM submissions WHERE status='approved'").fetchone()[0],
            'rejected': db.execute("SELECT COUNT(*) FROM submissions WHERE status='rejected'").fetchone()[0],
            'missions': len(missions_list)
        }
    return render_template('admin.html', pending=pending, recent=recent, missions=missions_list, stats=stats)

@app.route('/admin/review/<int:submission_id>', methods=['POST'])
@admin_required
def review(submission_id):
    decision = request.form.get('decision')
    if decision not in ('approved', 'rejected'):
        abort(400)
    with connect() as db:
        row = db.execute('SELECT status FROM submissions WHERE id=?', (submission_id,)).fetchone()
        if not row:
            abort(404)
        if row['status'] == 'pending':
            db.execute(
                'UPDATE submissions SET status=?, reviewed_at=?, reviewed_by=? WHERE id=? AND status=?',
                (decision, datetime.now().isoformat(timespec='minutes'), session['user_id'], submission_id, 'pending')
            )
    flash(f'Submission {decision}. Verified community stats updated.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/missions/add', methods=['POST'])
@admin_required
def add_mission():
    title = request.form.get('title', '').strip()[:100]
    description = request.form.get('description', '').strip()[:1000]
    category = request.form.get('category', '').strip()[:50]
    emoji = request.form.get('emoji', '🌱').strip()[:10] or '🌱'
    try:
        points = int(request.form.get('points', 0))
    except (ValueError, TypeError):
        points = 0

    if not title or len(title) < 3:
        flash('Please provide a descriptive mission title (at least 3 characters).', 'error')
        return redirect(url_for('admin') + '#add-mission')
    if not description or len(description) < 8:
        flash('Please provide clear instructions for the mission (at least 8 characters).', 'error')
        return redirect(url_for('admin') + '#add-mission')
    if not category:
        flash('Please choose or enter a category for the mission.', 'error')
        return redirect(url_for('admin') + '#add-mission')
    if points <= 0 or points > 1000:
        flash('Points must be a positive number between 1 and 1,000.', 'error')
        return redirect(url_for('admin') + '#add-mission')

    with connect() as db:
        db.execute(
            'INSERT INTO missions (title, description, category, points, emoji) VALUES (?, ?, ?, ?, ?)',
            (title, description, category, points, emoji)
        )
    flash(f'Success! New mission "{title}" {emoji} ({points} pts) is now live for all members.', 'success')
    return redirect(url_for('admin') + '#missions')

@app.route('/admin/missions/<int:mission_id>/edit', methods=['POST'])
@admin_required
def edit_mission(mission_id):
    title = request.form.get('title', '').strip()[:100]
    description = request.form.get('description', '').strip()[:1000]
    category = request.form.get('category', '').strip()[:50]
    emoji = request.form.get('emoji', '🌱').strip()[:10] or '🌱'
    try:
        points = int(request.form.get('points', 0))
    except (ValueError, TypeError):
        points = 0

    if not title or not description or not category or points <= 0 or points > 1000:
        flash('All mission fields are required and points must be between 1 and 1,000.', 'error')
        return redirect(url_for('admin') + '#missions')

    with connect() as db:
        existing = db.execute('SELECT id FROM missions WHERE id=?', (mission_id,)).fetchone()
        if not existing:
            abort(404)
        db.execute(
            'UPDATE missions SET title=?, description=?, category=?, points=?, emoji=? WHERE id=?',
            (title, description, category, points, emoji, mission_id)
        )
    flash(f'Mission "{title}" updated successfully!', 'success')
    return redirect(url_for('admin') + '#missions')

@app.route('/admin/missions/<int:mission_id>/delete', methods=['POST'])
@admin_required
def delete_mission(mission_id):
    with connect() as db:
        mission = db.execute('SELECT * FROM missions WHERE id=?', (mission_id,)).fetchone()
        if not mission:
            abort(404)
        sub_count = db.execute('SELECT COUNT(*) FROM submissions WHERE mission_id=?', (mission_id,)).fetchone()[0]
        if sub_count > 0:
            flash(f'Cannot delete "{mission["title"]}" because {sub_count} member submission(s) are linked to it. You can edit the mission instead.', 'error')
            return redirect(url_for('admin') + '#missions')
        db.execute('DELETE FROM missions WHERE id=?', (mission_id,))
    flash(f'Mission "{mission["title"]}" has been removed.', 'info')
    return redirect(url_for('admin') + '#missions')

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Admin access or permission is required for that page.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='The requested page or resource could not be found.'), 404

@app.errorhandler(413)
def too_large(e):
    flash('That file is too large. Please upload an image under 4 MB.', 'error')
    return redirect(request.referrer or url_for('missions'))

if __name__ == '__main__':
    print('\n========================================')
    print('  GreenPulse is running!')
    print('  Website:    http://127.0.0.1:5000')
    print('  Demo Admin: admin@greenpulse.local')
    print('  Password:   GreenPulse2026!')
    print('========================================\n')
    app.run(debug=True)
