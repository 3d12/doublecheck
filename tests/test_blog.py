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
import os
import tempfile
import pytest
from doublecheck.db import get_db

def test_index(client, auth):
    response = client.get('/')
    assert b'Log In' in response.data

    auth.login()
    response = client.get('/')
    assert b'Log Out' in response.data
    assert b'test title' in response.data
    assert b'by test on 2018-01-01' in response.data
    assert b'test\nbody' in response.data
    assert b'href="/1/update"' in response.data
    assert b'<svg' in response.data
    assert b'href="/game/1/view"' in response.data

@pytest.mark.parametrize('path', (
    '/create',
    '/1/update',
    '/1/delete'
    ))
def test_login_required(client, path):
    response = client.post(path)
    assert response.headers['Location'] == '/auth/login'

def test_author_required(app, client, auth):
    # change the post author to another user
    with app.app_context():
        db = get_db()
        db.execute("UPDATE post SET author_id = 2 WHERE id = 1")
        db.commit()

    auth.login()
    # current user can't modify other user's posts
    assert client.post('/1/update').status_code == 403
    assert client.post('/1/delete').status_code == 403
    # current user doesn't see edit link
    assert b'href="/1/update"' not in client.get('/').data

def test_exists_required(client, auth, app):
    # get max id so we know which one won't exist
    with app.app_context():
        db = get_db()
        max_id = db.execute('SELECT max(id) FROM post').fetchone()[0]
    invalid_post_id = max_id+1

    auth.login()
    # first try update
    path = f'/{invalid_post_id}/update'
    assert client.post(path).status_code == 404
    # next try delete
    path = f'/{invalid_post_id}/delete'
    assert client.post(path).status_code == 404

def test_create(client, auth, app):
    # get count before insert
    with app.app_context():
        db = get_db()
        starting_count = db.execute('SELECT count(id) FROM post').fetchone()[0]

    auth.login()
    assert client.get('/create').status_code == 200
    client.post('/create', data={'title': 'created', 'body': ''})

    # get count after insert
    with app.app_context():
        db = get_db()
        ending_count = db.execute('SELECT count(id) FROM post').fetchone()[0]
        assert ending_count == starting_count+1

@pytest.mark.parametrize(('pgn_suffix', 'pgn_contents'), (
    ('valid.pgn', b'[Event "test event 2"]\n[Site "test site 2"]\n[Date "2023.10.17"]\n[Round "4"]\n[White "foo"]\n[Black "bar"]\n[Result "0-1"]\n\n1. e4 e5 2. d4 Nf6 3. Nc3 Nc6 4. d5 Nd4 5. Nf3 c5 6. Nxe5 Bd6 7. Bf4 O-O { test comment } 8. Nxf7 Rxf7 0-1'),
    ('valid.txt', b'[Event "test event 2"]\n[Site "test site 2"]\n[Date "2023.10.17"]\n[Round "4"]\n[White "foo"]\n[Black "bar"]\n[Result "0-1"]\n\n1. e4 e5 2. d4 Nf6 3. Nc3 Nc6 4. d5 Nd4 5. Nf3 c5 6. Nxe5 Bd6 7. Bf4 O-O { test comment } 8. Nxf7 Rxf7 0-1')
    ))
def test_create_with_pgn(client, auth, app, pgn_suffix, pgn_contents):
    # save max_file_id for comparison later
    with app.app_context():
        db = get_db()
        max_file_id = db.execute('SELECT max(id) FROM file').fetchone()[0]

    # create file
    pgn_fd, pgn_path = tempfile.mkstemp(suffix=pgn_suffix)
    os.write(pgn_fd, pgn_contents)
    os.close(pgn_fd)

    # create new post with file attached
    auth.login()
    assert client.get('/create').status_code == 200
    with open(pgn_path, 'rb') as f:
        response = client.post('/create',
                    data={'title': 'test with pgn', 'body': 'test body with pgn', 'pgn_file': f}
                    )
    assert response.headers['Location'] == '/'
    os.unlink(pgn_path)

    # check to make sure file got inserted to db
    with app.app_context():
        db = get_db()
        file = db.execute('SELECT * FROM file WHERE id = ?', (max_file_id+1,)).fetchone()
        assert pgn_suffix in file['file_name']
        assert pgn_contents.decode(encoding='utf-8') in file['file_contents']

@pytest.mark.parametrize(('pgn_suffix', 'pgn_contents', 'error'), (
    ('not_a_pgn.png', b'[Event "test event 2"]\n[Site "test site 2"]\n[Date "2023.10.17"]\n[Round "4"]\n[White "foo"]\n[Black "bar"]\n[Result "0-1"]\n\n1. e4 e5 2. d4 Nf6 3. Nc3 Nc6 4. d5 Nd4 5. Nf3 c5 6. Nxe5 Bd6 7. Bf4 O-O { test comment } 8. Nxf7 Rxf7 0-1', b'must be .pgn'),
    ('empty.pgn', b'', b'empty file'),
    ('newline.pgn', b'\n', b'unable to parse first move'),
    ('lyrics.pgn', b'Liberty, energy, dignity, and breakfast tea', b'unable to parse first move'),
    ('pgn_with_errors.pgn', b'[Event "test event 3"]\n[Site "test site 3"]\n[Date "2023.10.17"]\n[Round "4"]\n[White "foo"]\n[Black "bar"]\n[Result "0-1"]\n\n1. e4 e5 2. d4 Nf6 3. Qxf7 Nc6 4. d5 Nd4 5. Nf3 c5 6. Nxe5 Bd6 7. Bf4 O-O { test comment } 8. Nxf7 Rxf7 0-1', b'errors encountered while parsing')
    ))
def test_create_with_bad_pgn(client, auth, pgn_suffix, pgn_contents, error):
    # create file
    pgn_fd, pgn_path = tempfile.mkstemp(suffix=pgn_suffix)
    os.write(pgn_fd, pgn_contents)
    os.close(pgn_fd)

    # create new post with file attached
    auth.login()
    assert client.get('/create').status_code == 200
    with open(pgn_path, 'rb') as f:
        response = client.post('/create',
                    data={'title': 'test with bad pgn', 'body': 'test body with bad pgn', 'pgn_file': f}
                    )
    assert error in response.data
    os.unlink(pgn_path)

def test_update(client, auth, app):
    auth.login()
    assert client.get('/1/update').status_code == 200
    client.post('/1/update', data={'title': 'updated', 'body': ''})

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post['title'] == 'updated'

@pytest.mark.parametrize('path', (
    '/create',
    '/1/update'
    ))
def test_create_update_validate(client, auth, path):
    auth.login()
    response = client.post(path, data={'title': '', 'body': ''})
    assert b'Title is required' in response.data

def test_delete(client, auth, app):
    auth.login()
    response = client.post('/1/delete')
    assert response.headers['Location'] == '/'

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post is None
