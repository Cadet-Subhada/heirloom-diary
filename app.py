from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'heirloomsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

FAMILY_CODE = "2026"


# =======================
# Models
# =======================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    date = db.Column(db.Date)
    scratched = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =======================
# Routes
# =======================

@app.route('/')
def home():
    return redirect(url_for('cover'))


@app.route('/cover')
def cover():
    return render_template('cover.html')


@app.route('/unlock', methods=['POST'])
def unlock():
    entered_code = request.form.get('code')

    if entered_code == FAMILY_CODE:
        session['cover_unlocked'] = True
        return redirect(url_for('login'))
    else:
        return redirect(url_for('cover'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not session.get('cover_unlocked'):
        return redirect(url_for('cover'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('diary'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])

        new_user = User(
            username=request.form['username'],
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cover_unlocked', None)
    return redirect(url_for('cover'))


# =======================
# Diary Route
# =======================

@app.route('/diary', methods=['GET', 'POST'])
@login_required
def diary():

    selected_date_str = request.args.get('date')

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        selected_date = date.today()

    # Save new entry (always create new)
    if request.method == 'POST':
        new_entry = Entry(
            content=request.form['content'],
            date=selected_date,
            user_id=current_user.id
        )
        db.session.add(new_entry)
        db.session.commit()

        return redirect(url_for('diary', date=selected_date))

    # Get ALL entries for that date
    entries = Entry.query.filter_by(
        date=selected_date
    ).order_by(Entry.id.asc()).all()

    min_date = date(2026, 1, 1)
    max_date = date(2026, 12, 31)

    previous_date = selected_date - timedelta(days=1) if selected_date > min_date else None
    next_date = selected_date + timedelta(days=1) if selected_date < max_date else None

    formatted_date = selected_date.strftime("%d-%m-%Y, %A")
    formatted_day = selected_date.strftime("%A")

    return render_template(
        'diary.html',
        entries=entries,
        selected_date=selected_date,
        formatted_date=formatted_date,
        formatted_day=formatted_day,
        previous_date=previous_date,
        next_date=next_date,
        today=date.today(),
        username=current_user.username
    )

# =======================
# Scratch Toggle
# =======================

@app.route('/scratch/<int:entry_id>')
@login_required
def scratch(entry_id):

    entry = Entry.query.get_or_404(entry_id)

    # Only allow scratching your own entries
    if entry.user_id != current_user.id:
        return redirect(url_for('diary', date=entry.date))

    # Permanent scratch (no undo)
    if not entry.scratched:
        entry.scratched = True
        db.session.commit()

    return redirect(url_for('diary', date=entry.date))

# =======================
# Run App
# =======================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
