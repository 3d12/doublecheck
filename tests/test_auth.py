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
import pytest
from flask import g, session
from doublecheck.db import get_db

def test_register(client, app):
    # make sure registration is enabled via config
    with app.app_context():
        app.config['REGISTRATION_ENABLED'] = True
    assert client.get('/auth/register').status_code == 200
    response = client.post(
            '/auth/register', data={'username': 'a', 'password': 'a'}
            )
    assert response.headers['Location'] == '/auth/login'

    with app.app_context():
        assert get_db().execute(
                "SELECT * FROM user WHERE username = 'a'",
                ).fetchone() is not None

@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('', '', b'Username is required'),
    ('a', '', b'Password is required'),
    ('test', 'test', b'already registered')
    ))
def test_tegister_validate_input(client, username, password, message, app):
    # make sure registration is enabled via config
    with app.app_context():
        app.config['REGISTRATION_ENABLED'] = True
    response = client.post(
            '/auth/register',
            data={'username': username, 'password': password}
            )
    assert message in response.data

def test_login(client, auth):
    assert client.get('/auth/login').status_code == 200
    response = auth.login()
    assert response.headers['Location'] == '/'

    with client:
        client.get('/')
        assert session['user_id'] == 1
        assert g.user['username'] == 'test'

@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('a', 'test', b'Invalid username'),
    ('test', 'a', b'Invalid password'),
    ))
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data

def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert 'user_id' not in session
