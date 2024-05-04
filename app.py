from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from functools import wraps  # Import wraps for decorator
from peewee import *
from forms import NoteForm
from flask_paginate import Pagination, get_page_args

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

db = SqliteDatabase('notes.db')

login_manager = LoginManager()
login_manager.init_app(app)

# Define models
class BaseModel(Model):
    class Meta:
        database = db

class Category(BaseModel):
    name = CharField()

class User(UserMixin, BaseModel):
    id = AutoField(primary_key=True)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(unique=True)

class Note(BaseModel):
    title = CharField()
    content = TextField()
    category = ForeignKeyField(Category, backref='notes')
    user = ForeignKeyField(User, backref='notes')

    @classmethod
    def get_or_404(cls, *args, **kwargs):
        obj = cls.get_or_none(*args, **kwargs)
        if obj is None:
            abort(404)
        return obj


# Create tables if they don't exist
db.connect()
db.create_tables([Category, User, Note])

@app.before_request
def require_login():
    if not current_user.is_authenticated and request.endpoint != 'login' and request.endpoint != 'register':
        return redirect(url_for('login'))


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
        notes_query = Note.select().where(Note.user == current_user)
        total = notes_query.count()
        pagination_notes = notes_query.offset(offset).limit(per_page)
        pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')
        return render_template('index.html', notes=pagination_notes, page=page, per_page=per_page, pagination=pagination)
    else:
        flash('Please log in to view your notes', 'warning')
        return redirect(url_for('login'))

@app.route('/add_note', methods=['GET', 'POST'])
@login_required
def add_note():
    form = NoteForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data
        category_name = form.category.data

        category, _ = Category.get_or_create(name=category_name)
        note = Note.create(title=title, content=content, category=category, user=current_user)

        flash('Note added successfully', 'success')
        return redirect(url_for('index'))
    return render_template('add_note.html', form=form)

def owns_note(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        note_id = kwargs.get('note_id')
        note = Note.get_or_none(Note.id == note_id)
        if note is None:
            abort(404)
        if note.user != current_user:
            flash("You don't have permission to access this note.", 'error')
            return redirect(url_for('index'))  # Redirect to a safe location
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
@owns_note
def edit_note(note_id):
    note = Note.get_or_none(Note.id == note_id)

    if note is None:
        abort(404)

    if request.method == 'POST':
        note.title = request.form['title']
        note.content = request.form['content']
        note.category = Category.get_or_create(name=request.form['category'])[0]
        note.save()

        flash('Note updated successfully', 'success')
        return redirect(url_for('index'))

    return render_template('edit_note.html', note=note)
    

@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
@owns_note
def delete_note(note_id):
    note = Note.get_or_404(Note.id == note_id)
    if note is None:
        abort(404)

    note.delete_instance()

    flash('Note deleted successfully', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists in the database
        user = User.get_or_none(User.username == username)
        if user:
            if user.password == password:
                login_user(user)
                return redirect(url_for('index'))  # Redirect to the add notes section
            else:
                flash('Invalid password', 'error')
        else:
            flash('User not found. Please register if you do not have an account.', 'error')
            return redirect(url_for('register'))  # Redirect to the registration page

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username already exists in the database
        if User.select().where(User.username == username).exists():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))

        # Check if the email already exists in the database
        if User.select().where(User.email == email).exists():
            flash('Email already exists. Please use a different one.', 'error')
            return redirect(url_for('register'))

        # Create a new user
        user = User(username=username, email=email, password=password)
        user.save()

        # Redirect to the login page after successful registration
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.before_request
def before_request():
    if not db.is_closed():
        db.close()
    db.connect()  # Connect to the database before each request

@app.teardown_request
def teardown_request(exception):
    db.close()  # Close the database connection after each request

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
