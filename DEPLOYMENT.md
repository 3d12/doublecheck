# Deployment

1. SSH into deployment environment
2. Create virtual environment
  > python3 -m venv .venv
3. Activate virtual environment
  > . .venv/bin/activate
4. Transfer wheel file to deployment environment
  - To build wheel file:
  > python -m build
5. Use pip to install (e.g. for v0.0.1)
  - If this is an upgrade, use pip uninstall to remove the old version first
  > pip install doublecheck-0.0.1-py3-none-any.whl
  - This will install all dependencies as well
6. If this is a fresh deployment (not an upgrade) then you will also want to init the db
  > flask --app doublecheck init-db
7. Remake config.py with a new secret key
  > echo "SECRET_KEY = '$(python -c "import secrets; print(secrets.token_hex())")'" > ./.venv/var/doublecheck-instance/config.py
8. Install WSGI interface if not already installed
  > pip install waitress
9. Use WSGI interface to serve the app
  > waitress-serve --call 'doublecheck:create_app'
10. Configure nginx if not already configured
  - Ensure that listening on port 80/443 is redirected to port 8080 internally
