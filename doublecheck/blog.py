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
        Blueprint, current_app, flash, g, redirect, render_template, request, url_for
        )
from markupsafe import Markup
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from doublecheck.auth import login_required
from doublecheck.db import get_db

import chess.pgn, chess.svg
import io

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    # If config is set up to create first user as admin,
    #   we should first confirm this config by checking the
    #   db state
    create_first_user_as_admin = current_app.config.get('CREATE_FIRST_USER_AS_ADMIN', False)
    if create_first_user_as_admin:
        db = get_db()
        result = db.execute('SELECT count(id) as user_count FROM user').fetchone()
        if result['user_count'] != 0:
            current_app.config['CREATE_FIRST_USER_AS_ADMIN'] = False

    db = get_db()
    posts = db.execute(
            'SELECT p.id, p.title, p.body, p.created, p.author_id, u.username, f.file_contents'
            ' FROM post p '
            ' JOIN user u ON (p.author_id = u.id)'
            ' JOIN file f ON (p.id = f.post_id)'
            ' ORDER BY p.created DESC'
            ).fetchall()
    new_posts = [dict(e) for e in posts]
    for post in new_posts:
        pgn_data = chess.pgn.read_game(io.StringIO(str(post['file_contents'])))
        if pgn_data is None:
            continue
        post['svg_image'] = Markup(chess.svg.board(pgn_data.end().board(), size=350))
        post['pgn_data'] = Markup(pgn_data.accept(chess.pgn.StringExporter(columns=40, headers=False, variations=False)))
    return render_template('blog/index.html', posts=new_posts)

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
            # first make the post, so we can use the post id in saving the file
            db = get_db()
            cursor = db.execute('INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)',
                       (title, body, g.user['id'])
                       )
            db.commit()
            if 'pgn_file' in request.files:
                file = request.files['pgn_file']
                if file and '.' in file.filename and file.filename.rsplit('.',1)[1].lower() in current_app.config['ALLOWED_FILETYPES']: # pyright: ignore
                    # TODO: Validate that the file contains actual PGN data, even though it matches the correct
                    #   extension this doesn't mean it's automatically valid
                    file_contents = str(file.read())
                    pgn_data = io.StringIO(file_contents)
                    game_tree = chess.pgn.read_game(pgn_data)
                    if game_tree is None:
                        flash(str(f"Invalid PGN: {file_contents}"))
                        return redirect(url_for('blog.index'))
                    post_id = cursor.lastrowid
                    file_name = secure_filename(file.filename) # pyright: ignore
                    db = get_db()
                    db.execute('INSERT INTO file (uploader_id, post_id, file_name, file_contents) VALUES (?, ?, ?, ?)',
                               (g.user['id'], post_id, file_name, file_contents)
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

