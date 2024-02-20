#Doublecheck - A web-based chess game database.
#Copyright (C) 2024 Nick Edner

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
from flask import (
        abort, current_app, Blueprint, flash, g, redirect, render_template, request, url_for
        )
from doublecheck.auth import Roles, admin_required
from doublecheck.db import get_db

from werkzeug.security import generate_password_hash

from enum import Enum, auto
import datetime

class CONFIG_OPTIONS(Enum):
    REGISTRATION_ENABLED = auto()

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/', methods=('GET','POST'))
@admin_required
def index():
    if request.method == 'POST':
        config_values = {e.name: True if request.form[e.name] == 'True' else False for e in CONFIG_OPTIONS}
        flash(str(config_values)) # DEBUG
        for config_value in config_values:
            current_app.config[config_value] = config_values[config_value]
        return redirect(url_for('index'))

    return render_template('admin/index.html', config_options=CONFIG_OPTIONS, current_app=current_app)

@bp.route('/user_cp', methods=('GET','POST'))
@admin_required
def user_cp():
    db = get_db()

    if request.method == 'POST':
        # Check action: Deactivate user
        deactivate_id = request.form.get('deactivate')
        if deactivate_id is not None:
            # make sure we cannot deactivate our own account here
            if int(deactivate_id) != int(g.user['id']):
                user_deactivate = db.execute(
                        'UPDATE user'
                        ' SET active = 0,'
                        '   deactivated_on = current_timestamp'
                        ' WHERE id = ?',
                        (deactivate_id,)
                        )
                db.commit()
                flash(f'deactivate user {deactivate_id}, result: {user_deactivate}')
            else: 
                flash(f'cannot deactivate your own account here')
            return redirect(url_for('admin.user_cp'))
        # Check action: Activate user
        activate_id = request.form.get('activate')
        if activate_id is not None:
            user_activate = db.execute(
                    'UPDATE user'
                    ' SET active = 1,'
                    '   deactivated_on = null'
                    ' WHERE id = ?',
                    (activate_id,)
                    )
            db.commit()
            flash(f'activate user {activate_id}, result: {user_activate}')
            return redirect(url_for('admin.user_cp'))
        else:
            flash(f'POST received, request.form = {str(request.form)}')

    # GET request: populate list of users into template
    users = db.execute('SELECT id, member_number, username, display_name, role, created, last_login, active, deactivated_on FROM user ORDER BY role DESC, id ASC')
    users = [dict(e) for e in users]
    rolename_list = [e.title() for e in list(Roles.__members__)]
    for user in users:
        # This is where we could apply the current user's timezone offset (from
        #   preferences) to the datetimes retrieved from the db
        # No idea why pyright thinks user['created'] is a str here,
        #   it's a datetime.datetime
        #print((user['created']-datetime.timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')) # pyright: ignore
        user['rolename'] = rolename_list[int(user['role'])-1]
        # Change None to blank string for all columns in each record
        for key in user.keys():
            if user[key] is None:
                user[key] = ''
    return render_template('admin/user_cp.html', users=users)

@bp.route('/user_edit/<int:id>', methods=('GET','POST'))
@admin_required
def user_edit(id):
    db = get_db()

    if request.method == "POST":
        # TODO: Replace this with a data model
        attributes = ['username', 'password', 'confirm_new_password', 'role', 'created', 'active', 'deactivated_on', 'display_name', 'member_number', 'last_login', 'timezone']
        full_query_str = ''
        query_str = ''
        query_vars = []
        for attribute_str in attributes:
            if attribute_str in ['confirm_new_password']:
                continue
            attribute = request.form.get(attribute_str)
            if attribute is not None:
                # Replace blank strings with None so sqlite3
                #   will use null
                if attribute == '':
                    attribute = None
                # Password cannot be the default text, and
                #   must match confirmation
                elif attribute_str == 'password':
                    if attribute == 'example_password_characters':
                        continue
                    if attribute != request.form.get('confirm_new_password'):
                        flash("Password must match confirmation")
                        return redirect(url_for('admin.user_edit', id=id))
                    attribute = generate_password_hash(attribute)
                # Convert role from string (e.g. 'Roles.USER') to
                #   int via Enum
                elif attribute_str == 'role':
                    attribute = Roles[attribute.split('.')[-1]].value
                query_str += f', {attribute_str} = ?'
                query_vars.append(attribute)
        if query_str != '':
            # Remove leading comma + space
            query_str = query_str[2:]
            full_query_str = f'UPDATE user SET {query_str} WHERE id = {id}'
        db.execute(full_query_str, query_vars)
        db.commit()
        return redirect(url_for('admin.user_cp'))

    user_data = db.execute(
            'SELECT *'
            ' FROM user'
            ' WHERE id = ?',
            (id,)
            ).fetchone()
    if user_data is None:
        return abort(404)
    user_params = {}
    for key in user_data.keys():
        value = user_data[key]
        # Censor user's password
        if key == 'password':
            value = 'example_password_characters'
            user_params[key] = {'title': str(key).title().replace('_',' '), 'value': value}
            user_params['confirm_new_password'] = {'title': 'Confirm New Password', 'value': ''}
        # Remove id field
        elif key == 'id':
            continue
        # Remove 'None'
        else:
            value = value if value is not None else ''
        user_params[key] = {'title': str(key).title().replace('_',' '), 'value': value}
    return render_template('admin/user_edit.html', user_params=user_params)

@bp.route('/user_add', methods=('GET','POST'))
@admin_required
def user_add():
    db = get_db()

    # TODO: Replace this with a data model
    attributes = ['username', 'password', 'role', 'display_name', 'member_number', 'timezone']

    if request.method == 'POST':
        full_query_str = ''
        query_str = ''
        query_cols = ''
        query_vars = []
        for attribute_str in attributes:
            attribute = request.form.get(attribute_str)
            if attribute is not None:
                # Replace blank strings with None so sqlite3
                #   will use null
                if attribute == '':
                    attribute = None
                # Generate hash for password
                elif attribute_str == 'password':
                    attribute = generate_password_hash(attribute)
                # Convert role from string (e.g. 'Roles.USER') to
                #   int via Enum
                elif attribute_str == 'role':
                    attribute = Roles[attribute.split('.')[-1]].value
                query_str += ', ?'
                query_cols += f', {attribute_str}'
                query_vars.append(attribute)
        if query_str != '':
            # Remove leading comma + space
            query_str = query_str[2:]
            query_cols = query_cols[2:]
            # Surround with parens
            query_str = f'({query_str})'
            query_cols = f'({query_cols})'
            full_query_str = f'INSERT INTO user {query_cols} VALUES {query_str}'
        db.execute(full_query_str, query_vars)
        db.commit()
        return redirect(url_for('admin.user_cp'))

    user_params = {}
    for attribute_str in attributes:
        user_params[attribute_str] = {'title': str(attribute_str).title().replace('_',' '), 'value': ''}
    return render_template('admin/user_add.html', user_params=user_params)
