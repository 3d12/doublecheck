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
        Blueprint, current_app, flash, g, redirect, render_template, request, url_for
        )
from markupsafe import Markup
from werkzeug.datastructures import FileStorage
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
            'SELECT p.id, p.title, p.body, p.created, p.author_id, u.username, f.id as game_id, f.file_contents'
            ' FROM post p '
            ' JOIN user u ON (p.author_id = u.id)'
            ' LEFT JOIN file f ON (p.id = f.post_id)'
            ' ORDER BY p.created DESC'
            ).fetchall()
    new_posts = [dict(e) for e in posts]

    # populate image and pgn data fields in posts, but only where an associated file exists
    for post in new_posts:
        if post['file_contents'] is None:
            continue
        pgn_data = chess.pgn.read_game(io.StringIO(str(post['file_contents'])))
        # the parser is VERY loose, even if the file looks nothing like a PGN it will
        #   still usually parse out at least one move of 1. --
        # so we don't have to worry about read_game returning None here, since it
        #   will only do that with an empty file and those are being filtered out upon
        #   insertion to the db
        post['svg_image'] = Markup(chess.svg.board(pgn_data.end().board(), size=350)) # pyright: ignore
        post['pgn_data'] = Markup(pgn_data.accept(chess.pgn.StringExporter(columns=40, headers=False, variations=False))) # pyright: ignore
        #post['pgn_event'] = pgn_data.headers['Event'] # pyright: ignore
        #post['pgn_date'] = pgn_data.headers['Date'] # pyright: ignore
        post['pgn_headers'] = pgn_data.headers # pyright: ignore

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

        # first validate the pgn file, if one was included
        if 'pgn_file' in request.files:
            error = check_pgn_for_errors(request.files['pgn_file'])

        if error is not None:
            flash(error)
        else:
            # first make the post, so we can use the post id in saving the file
            db = get_db()
            cursor = db.execute('INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)',
                       (title, body, g.user['id'])
                       )
            db.commit()
            # then insert the pgn data, if one exists (we know by now it's passed validation)
            if 'pgn_file' in request.files:
                post_id = cursor.lastrowid
                file = request.files['pgn_file']
                file_contents = file.stream.read()
                file_name = secure_filename(str(file.filename))
                db = get_db()
                db.execute('INSERT INTO file (uploader_id, post_id, file_name, file_contents) VALUES (?, ?, ?, ?)',
                           (g.user['id'], post_id, file_name, file_contents.decode("UTF-8"))
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

def check_pgn_for_errors(pgn: FileStorage):
    # first validate the pgn file, if one was included
    # file must have valid extension
    if not pgn.filename or '.' not in pgn.filename or pgn.filename.rsplit('.',1)[1].lower() not in current_app.config['ALLOWED_FILETYPES']:
        return "Invalid PGN: file extension invalid, must be .pgn or .txt"
    # file must contain data
    pgn_contents = pgn.stream.read()
    if pgn_contents == b'':
        return "Invalid PGN: empty file"
    else:
        # rewind the stream buffer so it can be read from again later
        pgn.stream.seek(0)
    # file must successfully parse as PGN
    pgn_stringio = io.StringIO(str(pgn_contents))
    game_tree = chess.pgn.read_game(pgn_stringio)
    # the only way game_tree.game can return None is if the input StringIO
    #   is empty, but we are already checking for empty file contents before this
    game = game_tree.game() # pyright: ignore
    if len(game.errors) > 0:
        return f"Invalid PGN: errors encountered while parsing: {str(game.errors)}"
    # the parser is VERY loose, even if the file looks nothing like a PGN it will
    #   still usually parse out at least one move of 1. --
    first_move = game.next()
    if first_move is None or str(first_move)[:5] == '1. --':
        return f"Invalid PGN, unable to parse first move: {str(pgn_contents)}"
    # all validations passed
    return None
