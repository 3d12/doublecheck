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
        Blueprint, flash, g, redirect, render_template, request, url_for
        )
from werkzeug.exceptions import abort

from doublecheck.auth import login_required
from doublecheck.db import get_db

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
            'SELECT p.id, p.title, p.body, p.created, p.author_id, u.username'
            ' FROM post p JOIN user u ON (p.author_id = u.id)'
            ' ORDER BY created DESC'
            ).fetchall()
    return render_template('blog/index.html', posts=posts)

@bp.route('/create', methods=('GET','POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title', '')
        body = request.form.get('body', '')
        error = None

        if title == '':
            error = 'Title is required'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute('INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)',
                       (title, body, g.user['id'])
                       )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
            'SELECT p.id, p.title, p.body, p.created, p.author_id, u.username'
            ' FROM post p JOIN user u ON (p.author_id = u.id)'
            ' WHERE p.id = ?',
            (id,)
            ).fetchone()

    if post is None:
        abort(404, f"Post id {id} does not exist")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET','POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form.get('title', '')
        body = request.form.get('body', '')
        error = None

        if title == '':
            error = 'Title is required'
        
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                    'UPDATE post SET title = ?, body = ? WHERE id = ?',
                    (title, body, id)
                    )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

