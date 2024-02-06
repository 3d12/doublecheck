#Doublecheck - A web-based chess game database.
#Copyright (C) 2023 Nick Edner

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published
#by the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.

#You should have received a copy of the GNU Affero General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.
import functools

from flask import (
        Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
        )
from werkzeug.security import check_password_hash, generate_password_hash

from doublecheck.db import get_db

from enum import Enum

class Roles(Enum):
    NONE = 1
    VIEWER = 2
    USER = 3
    MEMBER = 4
    MODERATOR = 5
    ADMIN = 6

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET','POST'))
def register():
    # If config is set up to create first user as admin,
    #   we should first confirm this config by checking the
    #   db state
    create_first_user_as_admin = current_app.config.get('CREATE_FIRST_USER_AS_ADMIN', False)
    if create_first_user_as_admin:
        db = get_db()
        result = db.execute('SELECT count(id) as user_count FROM user').fetchone()
        if result['user_count'] != 0:
            current_app.config['CREATE_FIRST_USER_AS_ADMIN'] = False
            create_first_user_as_admin = False

    # If registration is not enabled, redirect to the index
    registration_enabled = current_app.config.get('REGISTRATION_ENABLED', False)
    if not create_first_user_as_admin and not registration_enabled:
        error = 'Registration is currently disabled'
        flash(error)
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        db = get_db()
        error = None

        if username == '':
            error = 'Username is required'
        elif password == '':
            error = 'Password is required'

        if error is None:
            try:
                new_user_role = Roles.ADMIN.value if create_first_user_as_admin else Roles.USER.value
                db.execute('INSERT INTO user (username, password, role) VALUES (?, ?, ?)',
                           (username, generate_password_hash(password), new_user_role)
                           )
                db.commit()
            except db.IntegrityError:
                error = f'User {username} is already registered'
            else:
                if create_first_user_as_admin:
                    current_app.config['CREATE_FIRST_USER_AS_ADMIN'] = False
                return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET','POST'))
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['password'], password):
            error = 'Invalid password'
        elif user['active'] == 0:
            error = 'Deactivated account'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
    
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user['role'] != Roles.ADMIN.value:
            return redirect(url_for('index'))

        return view(**kwargs)
    return wrapped_view
