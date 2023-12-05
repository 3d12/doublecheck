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
        Blueprint, app, current_app, flash, g, redirect, render_template, request, session, url_for
        )
from markupsafe import Markup
from werkzeug.exceptions import abort

from doublecheck.db import get_db

import chess.pgn, chess.svg
import io

bp = Blueprint('game', __name__, url_prefix='/game')

@bp.route('/', methods=('GET','POST'))
def index():
    abort(404)

def get_file_by_id(id):
    file = get_db().execute(
            'SELECT f.* from file f'
            ' where f.id = ?',
            (id,)
            ).fetchone()
    
    if file is None:
        abort(404, f"File with game id {id} does not exist")

    return file

@bp.route('/<int:game_id>/view', methods=('GET','POST'))
def view(game_id):
    session_game_view_id = session.get('game_view_id')
    if session_game_view_id is None or session_game_view_id != game_id:
        file = get_file_by_id(game_id)
        session['game_view_file_contents'] = str(file['file_contents'])
        session['game_view_id'] = game_id
        session['game_view_ply'] = 0

    # we don't have to worry about read_game returning None here, since it
    #   will only do that with an empty file and those are being filtered
    #   out upon insertion to the db
    # so, we can ignore pyright warning us about it possibly being None
    game = chess.pgn.read_game(io.StringIO(session.get('game_view_file_contents')))
    game_ply = session.get('game_view_ply',0)

    if game_ply > 0:
        for _ in range(game_ply, 0, -1):
            game = game.next() # pyright: ignore

    if request.method == 'POST':
        if request.form.get('nextMove') is not None and not game.is_end(): # pyright: ignore
            game = game.next() # pyright: ignore
        elif request.form.get('prevMove') is not None and game_ply > 0:
            game = game.parent # pyright: ignore
        elif request.form.get('firstMove') is not None and game_ply > 0:
            game = game.game() # pyright: ignore
        elif request.form.get('lastMove') is not None and not game.is_end(): # pyright: ignore
            game = game.end() # pyright: ignore
        session['game_view_ply'] = game.ply() # pyright: ignore

    game_image = Markup(chess.svg.board(game.board(), size=350)) # pyright: ignore

    return render_template('game/view.html', game=game, game_image=game_image)
