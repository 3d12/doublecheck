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
from flask import (
        current_app, Blueprint, flash, g, redirect, render_template, request, url_for
        )
from doublecheck.auth import login_required, admin_required

from enum import Enum, auto

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
