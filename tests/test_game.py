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
from doublecheck.db import get_db

def test_index(client):
    assert client.get('/game/').status_code == 404

def test_exists_required(client, app):
    # get max id so we know which one won't exist
    with app.app_context():
        db = get_db()
        max_id = db.execute('SELECT max(id) FROM file').fetchone()[0]
    invalid_file_id = max_id+1


    response = client.get(f'/game/{invalid_file_id}/view')
    assert response.status_code == 404
    assert b'does not exist' in response.data

def test_view(client):
    response = client.get('/game/1/view')
    assert response.status_code == 200
    assert b'1. e4 e5 2. d4 Nf6' in response.data

# don't parametrize this, because we need to hit the buttons in order
def test_view_buttons(client):
    response = client.post('/game/1/view', data={'nextMove': 'true'})
    assert response.status_code == 200
    assert b'Event' not in response.data
    response = client.post('/game/1/view', data={'prevMove': 'true'})
    assert response.status_code == 200
    assert b'Event' in response.data
    response = client.post('/game/1/view', data={'lastMove': 'true'})
    assert response.status_code == 200
    assert b'Nxe5' not in response.data
    response = client.post('/game/1/view', data={'firstMove': 'true'})
    assert response.status_code == 200
    assert b'Nxe5' in response.data
    response = client.post('/game/1/view', data={'nonExistentMove': 'true'})
    assert response.status_code == 200
    assert b'Nxe5' in response.data
