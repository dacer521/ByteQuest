import os
import sqlite3
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import *;
from werkzeug.security import generate_password_hash, check_password_hash
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command
from user import User

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None) 
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or os.urandom(24),
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
        SQLALCHEMY_DATABASE_URI="sqlite:///db.sqlite",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # User session management setup
    login_manager = LoginManager()
    login_manager.init_app(app)

    client = WebApplicationClient(GOOGLE_CLIENT_ID)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    # Ensure the database is initialized manually via CLI
    app.cli.add_command(init_db_command)

    #TODO: should probably add error handling to this
    def get_google_provider_cfg():
        return requests.get(GOOGLE_DISCOVERY_URL).json();
    """These should only be essential routes"""
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return (
                "<p>Hello, {}! You're logged in! Email: {}</p>"
                "<div><p>Google Profile Picture:</p>"
                '<img src="{}" alt="Google profile pic"></img></div>'
                '<a class="button" href="/logout">Logout</a>'.format(
                    current_user.name, current_user.email, current_user.profile_pic
                )
            )
        else:
            return '<a class="button" href="/login">Google Login</a>'

            # return render_template("index.html") #TODO: UNCOMMENT AND TURN ABOVE INTO A TEMPLATE
    
    @app.route("/login")
    def login():
        # Find out what URL to hit for Google login
        google_provider_cfg = get_google_provider_cfg()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Use library to construct the request for Google login and provide
        # scopes that let you retrieve user's profile from Google
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=request.base_url + "/callback",
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    
    @app.route('/home')
    @login_required
    def hello():
        return 'Hello, World!'

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
