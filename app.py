from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'heirloomsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

# 🔐 FAMILY STRAP CODE (change this only here)
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
    date = db.Column(db.String(20))
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


@app.route('/diary', methods=['GET', 'POST'])
@login_required
def diary():
    today = date.today().strftime("%Y-%m-%d")

    if request.method == 'POST':
        new_entry = Entry(
            content=request.form['content'],
            date=today,
            user_id=current_user.id
        )
        db.session.add(new_entry)
        db.session.commit()

    selected_month = request.args.get('month')
    all_entries = Entry.query.order_by(Entry.date.desc()).all()

    if selected_month:
        filtered_entries = []
        for entry in all_entries:
            entry_month = datetime.strptime(entry.date, "%Y-%m-%d").month
            if entry_month == int(selected_month):
                filtered_entries.append(entry)
        entries = filtered_entries
    else:
        entries = all_entries

    return render_template(
        'diary.html',
        entries=entries,
        today=today,
        username=current_user.username
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cover_unlocked', None)
    return redirect(url_for('cover'))


# =======================
# Run App
# =======================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
