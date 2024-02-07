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
        current_app, Blueprint, flash, g, redirect, render_template, request, url_for
        )
from doublecheck.auth import Roles, admin_required
from doublecheck.db import get_db

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
                        '   deactivated = current_timestamp'
                        ' WHERE id = ?',
                        (deactivate_id)
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
                    '   deactivated = null'
                    ' WHERE id = ?',
                    (activate_id)
                    )
            db.commit()
            flash(f'activate user {activate_id}, result: {user_activate}')
            return redirect(url_for('admin.user_cp'))
        else:
            flash(f'POST received, request.form = {str(request.form)}')

    # GET request: populate list of users into template
    users = db.execute('SELECT id, member_number, username, display_name, role, created, last_login, active, deactivated FROM user ORDER BY role DESC, id ASC')
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
