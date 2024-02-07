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
from datetime import datetime, timezone
from doublecheck.db import get_db

def test_index(client, auth):
    response = client.get('/')
    assert b'Log In' in response.data
    assert b'href="/admin/"' not in response.data

    auth.login(username='admin', password='b')
    response = client.get('/')
    assert b'href="/admin/"' in response.data
    assert b'Log Out' in response.data

def test_admin_index(client, auth):
    auth.login(username='admin', password='b')
    response = client.get('/admin/')
    assert b'Control Panel' in response.data
    assert b'REGISTRATION_ENABLED' in response.data

def test_admin_index_insufficient_permissions(client, auth):
    # normal user has no access
    auth.login()
    response = client.get('/admin/')
    assert response.headers['Location'] == '/'

    # not logged in has no access
    auth.logout()
    response = client.get('/admin/')
    assert response.headers['Location'] == '/'

def test_admin_config_update(client, auth, app):
    # login and enable config via post to control panel
    auth.login(username='admin', password='b')
    response = client.post(
            '/admin/',
            data={'REGISTRATION_ENABLED': 'True'}
            )
    assert response.headers['Location'] == '/'
    auth.logout()
    response = client.get(response.headers['Location'])
    assert b'href="/auth/register"' in response.data

    # make sure config is now on
    with app.app_context():
        assert app.config['REGISTRATION_ENABLED'] == True

def test_config_registration_disabled(client, app):
    # make sure config is off
    with app.app_context():
        if app.config['REGISTRATION_ENABLED'] == True:
            app.config['REGISTRATION_ENABLED'] = False

    # attempt to GET page
    response = client.get('/auth/register')
    assert response.headers['Location'] == '/'
    response = client.get(response.headers['Location'])
    assert b'Registration is currently disabled' in response.data

    # attempt to POST to page
    response = client.post(
            '/auth/register',
            data={'username':'newuser','password':'newpassword'})
    assert response.headers['Location'] == '/'
    response = client.get(response.headers['Location'])
    assert b'Registration is currently disabled' in response.data

def test_user_cp(client, auth, app):
    # login and view user cp
    auth.login(username='admin', password='b')
    response = client.get('/admin/user_cp')
    assert response.status_code == 200
    assert b'<h1>User Control Panel</h1>' in response.data

    # verify that all the usernames in the database appear in the page
    with app.app_context():
        users = get_db().execute('SELECT * from user;').fetchall()
    for user in users:
        assert user['username'].encode(encoding='utf-8') in response.data

    # test misc post request, should be handled gracefully
    response = client.post(
            '/admin/user_cp',
            data={'testkey': 'testvalue'}
            )
    assert response.status_code == 200
    assert b'POST received' in response.data
    

    # ensure logged out and non-admin users can't view the page
    auth.logout()
    response = client.get('/admin/user_cp')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    auth.login()
    response = client.get('/admin/user_cp')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

def test_deactivate_user(client, auth, app):
    # login and verify the correct button appears on the user_cp page
    auth.login(username='admin', password='b')
    response = client.get('/admin/user_cp')
    assert b'<button name="deactivate" value="2">' in response.data
    # post request to deactivate account
    response = client.post(
            '/admin/user_cp',
            data={'deactivate': '2'}
            )
    assert response.status_code == 302
    assert response.headers['Location'] == '/admin/user_cp'
    # validate deactivation
    # capture current time to compare to deactivated time
    #   (round to nearest second because sqlite current_timestamp only
    #   captures to the second)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with app.app_context():
        user_status = get_db().execute(
                'SELECT id, active, deactivated'
                ' FROM user'
                ' WHERE id = 2',
                ).fetchone()
        assert user_status['active'] == 0
        # add tzinfo to db data so direct equality comparison will work
        assert user_status['deactivated'].replace(tzinfo=timezone.utc) == now

    # confirm that we cannot deactivate our own user via user cp
    # first check for lack of button
    response = client.get('/admin/user_cp')
    assert b'<button name="deactivate" value="3">' not in response.data
    # send the deactivation request anyway
    response = client.post(
            '/admin/user_cp',
            data={'deactivate': '3'}
            )
    assert response.status_code == 302
    assert response.headers['Location'] == '/admin/user_cp'
    response = client.get(response.headers['Location'])
    # check for error message
    assert b'cannot deactivate your own account here' in response.data
    # make sure the deactivation did not actually happen
    with app.app_context():
        user_status = get_db().execute(
                'SELECT id, active, deactivated'
                ' FROM user'
                ' WHERE id = 3',
                ).fetchone()
        assert user_status['active'] == 1
        assert user_status['deactivated'] == None

def test_activate_user(client, auth, app):
    # stage account id 2 as deactivated
    with app.app_context():
        db = get_db()
        db.execute('UPDATE user SET active = 0, deactivated = current_timestamp WHERE id = 2')
        db.commit()

    # login and verify the correct button appears on the user_cp page
    auth.login(username='admin', password='b')
    response = client.get('/admin/user_cp')
    assert b'<button name="activate" value="2">' in response.data
    # post request to activate account
    response = client.post(
            '/admin/user_cp',
            data={'activate': '2'}
            )
    assert response.status_code == 302
    assert response.headers['Location'] == '/admin/user_cp'

    # validate activation
    with app.app_context():
        user_status = get_db().execute(
                'SELECT id, active, deactivated'
                ' FROM user'
                ' WHERE id = 2',
                ).fetchone()
        assert user_status['active'] == 1
        assert user_status['deactivated'] == None
