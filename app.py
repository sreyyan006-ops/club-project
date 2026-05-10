from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import csv, io, os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///clubs.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Settings(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    signups_live = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)

class Club(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    max_cap     = db.Column(db.Integer, default=30)
    current_cap = db.Column(db.Integer, default=0)

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    name       = db.Column(db.String(120), nullable=False)
    role       = db.Column(db.String(10), default='student')
    choice1    = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=True)
    choice2    = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=True)
    assigned   = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=True)
    flagged    = db.Column(db.Boolean, default=False)
    choice1_club  = db.relationship('Club', foreign_keys=[choice1])
    choice2_club  = db.relationship('Club', foreign_keys=[choice2])
    assigned_club = db.relationship('Club', foreign_keys=[assigned])

def get_settings():
    s = Settings.query.first()
    if not s:
        s = Settings(); db.session.add(s); db.session.commit()
    return s

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    clubs    = Club.query.all()
    students = User.query.filter_by(role='student').count()
    spots    = sum(max(c.max_cap - c.current_cap, 0) for c in clubs)
    return render_template('index.html', clubs=clubs, students=students, spots=spots)

@app.route('/clubs')
def clubs():
    return render_template('clubs.html', clubs=Club.query.all())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '').strip()
        user = User.query.filter(
            (User.username == identifier) | (User.student_id == identifier)
        ).first()
        if user and check_password_hash(user.password, password):
            session['user_id']   = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            return redirect(url_for('admin_dashboard') if user.role == 'admin' else url_for('student_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name, student_id = request.form.get('name','').strip(), request.form.get('student_id','').strip()
        username, password = request.form.get('username','').strip(), request.form.get('password','').strip()
        if not all([name, student_id, username, password]):
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        if User.query.filter((User.username==username)|(User.student_id==student_id)).first():
            flash('Username or Student ID already exists.', 'error')
            return render_template('signup.html')
        db.session.add(User(name=name, student_id=student_id, username=username, password=generate_password_hash(password)))
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def student_dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'admin': return redirect(url_for('admin_dashboard'))
    settings = get_settings()
    clubs = Club.query.all()
    return render_template('student_dashboard.html', user=user, settings=settings, clubs=clubs,
        assigned_club=Club.query.get(user.assigned) if user.assigned else None,
        c1=Club.query.get(user.choice1) if user.choice1 else None,
        c2=Club.query.get(user.choice2) if user.choice2 else None)

@app.route('/submit_choices', methods=['POST'])
@login_required
def submit_choices():
    user = User.query.get(session['user_id'])
    settings = get_settings()
    if not settings.signups_live:
        flash('Sign-ups are not open right now.', 'error')
        return redirect(url_for('student_dashboard'))
    if user.choice1:
        flash('You have already submitted your choices.', 'error')
        return redirect(url_for('student_dashboard'))
    c1, c2 = request.form.get('choice1', type=int), request.form.get('choice2', type=int)
    if not c1 or not c2 or c1 == c2:
        flash('Please select two different clubs.', 'error')
        return redirect(url_for('student_dashboard'))
    user.choice1, user.choice2 = c1, c2
    db.session.commit()
    flash('Choices submitted successfully!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    settings = get_settings()
    students = User.query.filter_by(role='student').all()
    clubs    = Club.query.all()
    return render_template('admin_dashboard.html', settings=settings, students=students, clubs=clubs,
        submitted=sum(1 for s in students if s.choice1),
        assigned=sum(1 for s in students if s.assigned),
        flagged=sum(1 for s in students if s.flagged))

@app.route('/admin/toggle_signups', methods=['POST'])
@admin_required
def toggle_signups():
    s = get_settings(); s.signups_live = not s.signups_live; db.session.commit()
    flash(f"Sign-ups {'opened' if s.signups_live else 'closed'}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_publish', methods=['POST'])
@admin_required
def toggle_publish():
    s = get_settings(); s.is_published = not s.is_published; db.session.commit()
    flash(f"Results {'published to students' if s.is_published else 'unpublished'}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/smart_assign', methods=['POST'])
@admin_required
def smart_assign():
    for club in Club.query.all(): club.current_cap = 0
    for student in User.query.filter_by(role='student').all():
        student.assigned = None; student.flagged = False
    db.session.commit()
    ok = bad = 0
    for student in User.query.filter_by(role='student').filter(User.choice1 != None).all():
        c1, c2 = Club.query.get(student.choice1), Club.query.get(student.choice2)
        if c1 and c1.current_cap < c1.max_cap:
            student.assigned = c1.id; c1.current_cap += 1; ok += 1
        elif c2 and c2.current_cap < c2.max_cap:
            student.assigned = c2.id; c2.current_cap += 1; ok += 1
        else:
            student.flagged = True; bad += 1
    db.session.commit()
    flash(f'Smart assign complete: {ok} assigned, {bad} flagged for review.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export_csv')
@admin_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID','Name','Choice 1','Choice 2','Assigned Club','Status'])
    for s in User.query.filter_by(role='student').all():
        writer.writerow([
            s.student_id, s.name,
            Club.query.get(s.choice1).name if s.choice1 else '',
            Club.query.get(s.choice2).name if s.choice2 else '',
            Club.query.get(s.assigned).name if s.assigned else '',
            'Review needed' if s.flagged else 'Assigned' if s.assigned else 'Submitted' if s.choice1 else 'Pending'
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=Masterlist.csv'})

@app.route('/admin/add_club', methods=['POST'])
@admin_required
def add_club():
    name = request.form.get('name','').strip()
    max_cap = request.form.get('max_cap', 30, type=int)
    if name:
        db.session.add(Club(name=name, max_cap=max_cap)); db.session.commit()
        flash(f'Club "{name}" added.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_club/<int:club_id>', methods=['POST'])
@admin_required
def delete_club(club_id):
    club = Club.query.get_or_404(club_id)
    db.session.delete(club); db.session.commit()
    flash(f'Club "{club.name}" deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

def seed_data():
    if not User.query.filter_by(role='admin').first():
        db.session.add(User(student_id='ADM001', username='admin',
            password=generate_password_hash('admin123'), name='Mrs. S', role='admin'))
    if Club.query.count() == 0:
        for name, cap in [('Song & Music',30),('Running Club',30),('Dance',25),
                          ('Ski Club',20),('Badminton',36),('Art & Design',28)]:
            db.session.add(Club(name=name, max_cap=cap))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True)
