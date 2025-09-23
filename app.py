import os
from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import *; #this is giving errors right now. commenting it out until i figure that out,

#we might not need this one
from werkzeug.security import generate_password_hash, check_password_hash

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev', 
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