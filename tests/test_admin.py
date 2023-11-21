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
