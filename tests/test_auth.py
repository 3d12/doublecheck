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
import pytest
from flask import current_app, g, session
from doublecheck.db import get_db
from doublecheck.auth import Roles

@pytest.mark.parametrize(('create_first_user_as_admin', 'registration_enabled'), (
    (True, True),
    (True, False),
    (False, True),
    (False, False)
    ))
def test_first_registration(app_with_no_data, create_first_user_as_admin, registration_enabled):
    # load a version of the app which has no data in the db
    client = app_with_no_data.test_client()
    with app_with_no_data.app_context():
        current_app.config['CREATE_FIRST_USER_AS_ADMIN'] = create_first_user_as_admin
        current_app.config['REGISTRATION_ENABLED'] = registration_enabled
        # make sure register link appears on index, but only if
        #   registration is enabled or the first user should be
        #   set up as admin
        if current_app.config['CREATE_FIRST_USER_AS_ADMIN'] or current_app.config['REGISTRATION_ENABLED']:
            response = client.get('/')
            assert b'href="/auth/register"' in response.data
            # register new user
            response = client.post(
                    '/auth/register',
                    data={'username': 'firstuser', 'password': 'admin'}
                    )
            assert response.headers['Location'] == '/auth/login'
            # make sure register link no longer appears on index, but only if
            #   registration is supposed to be disabled
            if not current_app.config['REGISTRATION_ENABLED']:
                response = client.get('/')
                assert b'href="/auth/register"' not in response.data
            # login as new user
            response = client.post(
                    '/auth/login',
                    data={'username': 'firstuser', 'password': 'admin'}
                    )
            assert response.headers['Location'] == '/'
            # make sure admin link appears on index, but only if
            #   that first user should have been set up as admin
            if current_app.config['CREATE_FIRST_USER_AS_ADMIN']:
                response = client.get('/')
                assert b'href="/admin/"' in response.data
                # and validate db has correct value for role
                user_data = get_db().execute('SELECT * FROM user WHERE username = ?', ('firstuser',)).fetchone()
                assert user_data['role'] == Roles.ADMIN.value

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

def test_login_as_deactivated_user(auth, app):
    # stage account id 2 as deactivated
    with app.app_context():
        db = get_db()
        db.execute('UPDATE user SET active = 0, deactivated_on = current_timestamp WHERE id = 2')
        db.commit()

    # attempt to login
    response = auth.login('other', 'other')
    print(response.data)
    assert b'Deactivated account' in response.data
