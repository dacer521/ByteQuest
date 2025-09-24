import os
import sqlite3
from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import *; #this is giving errors right now. commenting it out until i figure that out,

#we might not need this one
from werkzeug.security import generate_password_hash, check_password_hash

from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command
from user import User

# Configuration
"""Important to note we are not storing client_secret here. ID is technically fine but, still,
for these, you can open CMD prompt and do:
set GOOGLE_CLIENT_(secret or id)=whatever_the_keys_are
"""
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None) 
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup (for the google logon)
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from the db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or os.urandom(24), #makes sure it's always encrypted even if secret key isn't set as an environmental variable 
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
        SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite",
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

###################################################################################################################################################
    """These should only be essential routes. We will deal with articles' routes using code to do it automatically"""

    # Root route
    @app.route('/')
    def index():
        return render_template("index.html")

    # Example route
    @app.route('/home')
    #login_required makes it so they need to be logged in, in this case have a linked email. we wil use this for pretty much everywhere except login.
    @login_required
    def hello():
        return 'Hello, World!'
    

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)