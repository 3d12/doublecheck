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

import os

from flask import Flask

from werkzeug.middleware.proxy_fix import ProxyFix

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
            SECRET_KEY='dev',
            DATABASE=os.path.join(app.instance_path, 'doublecheck.sqlite'),
            # Registration is disabled by default, can be enabled via admin control panel
            REGISTRATION_ENABLED=False,
            # First user created will have admin role by default
            CREATE_FIRST_USER_AS_ADMIN=True,
            # Max content length controls the allowed size of uploaded files, defaults to 16MB
            MAX_CONTENT_LENGTH=16*1000*1000,
            # Allowed filetypes for upload, defaults to .txt and .pgn
            ALLOWED_FILETYPES=['txt','pgn']
            )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # inject the config into the app context for access via jinja templates
    @app.context_processor
    def inject_config():
        return dict(app_config=app.config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, world!'

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)
    # inject auth roles into app context for access via jinja templates
    @app.context_processor
    def inject_roles():
        return dict(roles=auth.Roles)

    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')

    from . import admin
    app.register_blueprint(admin.bp)

    from . import game
    app.register_blueprint(game.bp)

    # apply proxyfix to support nginx proxy in front of the app
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app
