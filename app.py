import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import *;
from werkzeug.security import generate_password_hash, check_password_hash
from oauthlib.oauth2 import WebApplicationClient
import requests
import json

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




    """These will not have article routes
    we will (try) to make those with templates and code."""




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
            #scopes can be found here https://developers.google.com/identity/protocols/oauth2/scopes#google-sign-in
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    
    @app.route("/login/callback")
    def callback():
        #Gets auth code google sent
        code = request.args.get("code");
        #Find URL to hit to get tokens, allowing us to ask things in behalf of user
        google_provider_cfg = get_google_provider_cfg()
        token_endpoint = google_provider_cfg["token_endpoint"]
        #Prepare and send a token request
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            redirect_url=request.base_url,
            code=code
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET),
        )
        #Parse tokens
        client.parse_request_body_response(json.dumps(token_response.json()))
        
        #now we have tokens, we can hit the Google URL that gives us user profile info
        #like their pfp and email
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri,headers=headers,data=body)
        
        #make sure user is verified by google (we verify their email through Google)
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json().get("sub")
            users_email = userinfo_response.json().get("email")
            picture = userinfo_response.json().get("picture")
            users_name = userinfo_response.json().get("given_name")
        else:
            return "User email not available or not verified by Google", 400
        
        #FINALLY, create the user in the database using info provided by Google.
        user = User(id_=unique_id,name=users_name,email=users_email,profile_pic=picture)
        #add user to db if they aren't already in it
        if not User.get(unique_id):
            User.create(unique_id,users_name,users_email,picture)
        
        #log user in then send them to home page
        login_user(user)
        return redirect(url_for("index"))
    
    @app.route('/home')
    @login_required
    def hello():
        return 'Hello, World!'
    
    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))
    return app

if __name__ == "__main__":
    app = create_app()
    #USE THIS IF TESTING LOCALLY (until we get a website with a certificate.)
    #ssl_context="adhoc"
    app.run(host="0.0.0.0", port=5000, debug=True,ssl_context="adhoc")
