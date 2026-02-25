import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import *;
from werkzeug.security import generate_password_hash, check_password_hash
from oauthlib.oauth2 import WebApplicationClient
import requests
import RestrictedPython
from dotenv import load_dotenv
load_dotenv() # loads the .env file so os.getenv can find the variables
import codeEvaluator
import json

# Internal imports
from db import init_db_command, get_db
from user import User


#defines structure
ARTICLE_STRUCTURE = [
    {
        "unit": 1,
        "title": "Programming Basics",
        "lessons": [
            {"slug": "1a", "title": "What is programming?"},
            {"slug": "1b", "title": "What are variables?"},
            {"slug" : "1c", "title" : "What are print statements?"}
        ],
    },
    {
        "unit": 2,
        "title": "Data Types and Operators",
        "lessons": [
            {"slug": "2a", "title": "What are data types?"},
            {"slug": "2b", "title": "What are operators?"},
            {"slug": "2c", "title": "What are logical operators?"},
        ],
    },
    {
        "unit": 3,
        "title": "Conditionals",
        "lessons": [
            {"slug": "3a", "title": "What are conditionals?"},
            {"slug": "3b", "title": "What are elif and else statements?"},
            {"slug": "3c", "title": "What are match case statements?"},
        ],
    },
    {
        "unit": 4,
        "title": "Loops",
        "lessons": [
            {"slug": "4a", "title": "What are loops? Why use them?"},
            {"slug": "4b", "title": "What are nested loops?"},
            {"slug": "4c", "title": "What are while loops?"},
        ],
    },
    {
        "unit": 5,
        "title": "Lists",
        "lessons": [],
    },
    {
        "unit": 6,
        "title": "Functions",
        "lessons": [
            {"slug": "6a", "title": "What are functions?"},
            {"slug": "6b", "title": "What are functions as function arguments?"},
        ],
    },
    {
        "unit": 7,
        "title": "Outside Packages",
        "lessons": [],
    },
]

#sets up moving between articles so the in-between thingy works
def build_article_registry(structure):
    lookup = {}
    sequence = []
    nav = []
    for unit in structure:
        unit_entry = {
            "unit": unit["unit"],
            "title": unit["title"],
            "lessons": [],
        }
        for lesson in unit["lessons"]:
            meta = {
                "unit": unit["unit"],
                "unit_title": unit["title"],
                "slug": lesson["slug"],
                "title": lesson["title"],
                "template": lesson.get("template")
                or f"articles/{unit['unit']}/{lesson['slug']}.html",
            }
            unit_entry["lessons"].append(meta)
            sequence.append(meta)
            lookup[(meta["unit"], meta["slug"])] = meta
        nav.append(unit_entry)
    for idx, meta in enumerate(sequence):
        meta["index"] = idx
    return lookup, sequence, nav


ARTICLE_LOOKUP, ARTICLE_SEQUENCE, ARTICLE_NAV = build_article_registry(
    ARTICLE_STRUCTURE
)

def ensure_progress_schema():
    """Create the user progress table if it does not already exist."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id TEXT NOT NULL,
            unit INTEGER NOT NULL,
            lessons_read TEXT NOT NULL DEFAULT '[]',
            practice_completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, unit),
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        """
    )
    db.commit()

def unit_name_to_number(unit_name):
    if not unit_name:
        return None
    if unit_name.startswith("unit"):
        try:
            return int(unit_name.replace("unit", ""))
        except ValueError:
            return None
    return None

def get_unit_progress(user_id):
    """Fetch saved lesson/practice status for the user."""
    db = get_db()
    rows = db.execute(
        "SELECT unit, lessons_read, practice_completed FROM user_progress WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    progress = {}
    for row in rows:
        try:
            lessons = json.loads(row["lessons_read"] or "[]")
        except json.JSONDecodeError:
            lessons = []
        progress[row["unit"]] = {
            "lessons_read": lessons,
            "practice_completed": bool(row["practice_completed"]),
        }
    return progress

def record_lesson_read(user_id, unit, slug):
    """Mark a lesson as read for the user."""
    db = get_db()
    row = db.execute(
        "SELECT lessons_read FROM user_progress WHERE user_id = ? AND unit = ?",
        (user_id, unit),
    ).fetchone()
    if not row:
        db.execute(
            "INSERT INTO user_progress (user_id, unit, lessons_read, practice_completed) VALUES (?, ?, ?, 0)",
            (user_id, unit, json.dumps([slug])),
        )
    else:
        try:
            lessons = set(json.loads(row["lessons_read"] or "[]"))
        except json.JSONDecodeError:
            lessons = set()
        if slug not in lessons:
            lessons.add(slug)
            db.execute(
                "UPDATE user_progress SET lessons_read = ? WHERE user_id = ? AND unit = ?",
                (json.dumps(list(lessons)), user_id, unit),
            )
    db.commit()

def record_practice_completed(user_id, unit):
    """Persist that the user finished a unit's practice."""
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM user_progress WHERE user_id = ? AND unit = ?",
        (user_id, unit),
    ).fetchone()
    if not row:
        db.execute(
            "INSERT INTO user_progress (user_id, unit, lessons_read, practice_completed) VALUES (?, ?, '[]', 1)",
            (user_id, unit),
        )
    else:
        db.execute(
            "UPDATE user_progress SET practice_completed = 1 WHERE user_id = ? AND unit = ?",
            (user_id, unit),
        )
    db.commit()

def build_learning_state(user_id=None):
    """Return per-unit lock/unlock status for templates and route guards."""
    state = {"units": {}}
    progress_map = get_unit_progress(user_id) if user_id else {}
    chain_unlocked = True

    for unit in ARTICLE_STRUCTURE:
        unit_num = unit["unit"]
        lesson_slugs = [lesson["slug"] for lesson in unit["lessons"]]
        unit_progress = progress_map.get(unit_num, {})
        lessons_read = set(unit_progress.get("lessons_read", []))
        practice_completed = bool(unit_progress.get("practice_completed"))

        article_unlocked = chain_unlocked
        lessons_read_count = len(lessons_read.intersection(set(lesson_slugs)))
        all_lessons_read = article_unlocked and lessons_read_count >= len(lesson_slugs)
        practice_unlocked = (article_unlocked and all_lessons_read) or practice_completed

        state["units"][unit_num] = {
            "article_unlocked": article_unlocked,
            "practice_unlocked": practice_unlocked,
            "practice_completed": practice_completed,
            "lessons_read_count": lessons_read_count,
            "lessons_total": len(lesson_slugs),
        }

        # Next units unlock only after current practice is completed
        chain_unlocked = chain_unlocked and practice_completed

    return state

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

    @app.context_processor
    def inject_navigation():
        learning_state = (
            build_learning_state(current_user.id) if current_user.is_authenticated else build_learning_state(None)
        )
        return {
            "ARTICLE_NAV": ARTICLE_NAV,
            "LEARNING_STATE": learning_state,
        }
    
    login_manager.login_view = "index" #this makes it so when they try to access a page that needs a login, they are redirected to main page.

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    # ------------Ensure the database is initialized manually via CLI------------------------------
    # ------------Make sure that you are in the venv and run `flask init-db`-----------------------
    # ------------Ensure the database is initialized manually via CLI------------------------------
    app.cli.add_command(init_db_command)

    # Ensure the progress table exists
    with app.app_context():
        ensure_progress_schema()

    #TODO: should probably add error handling to this
    def get_google_provider_cfg():
        return requests.get(GOOGLE_DISCOVERY_URL).json();




    """These will not have article routes
    we will (try) to make those with templates and code."""




    @app.route('/')
    def index():
        return render_template(
            "index.html",
        )

    @app.route("/logingoogle")
    def logingoogle():
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
    
    @app.route("/logingoogle/callback")
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
    
   # In your practice route:
    @app.route("/practice/<unit_name>")
    @login_required
    def practice(unit_name):
        unit_number = unit_name_to_number(unit_name)
        learning_state = build_learning_state(current_user.id)
        unit_state = learning_state["units"].get(unit_number, {})
        if not unit_state.get("article_unlocked"):
            abort(403)
        if not unit_state.get("practice_unlocked"):
            abort(403)

        # Load the unit data to pass to template
        unit_data = codeEvaluator.get_unit_data(unit_name)
        if not unit_data:
            return "Unit not found", 404
        return render_template(
            "practice.html",
            unit_name=unit_name,
            unit_data=unit_data,
            learning_state=learning_state,
        )


    @app.route("/submit_code", methods=["POST"])
    @login_required
    def submit_code():
        unit_name = request.form.get("unit_name")
        unit_number = unit_name_to_number(unit_name) if unit_name else None
        code = request.form.get("code")

        learning_state = build_learning_state(current_user.id)
        unit_state = learning_state["units"].get(unit_number, {}) if unit_number else {}
        if not unit_state.get("practice_unlocked"):
            abort(403)

        result = codeEvaluator.evaluate_submission(unit_name, code)

        next_unit = None
        next_unit_first = None
        if unit_number is not None:
            for idx, unit in enumerate(ARTICLE_STRUCTURE):
                if unit["unit"] == unit_number and idx + 1 < len(ARTICLE_STRUCTURE):
                    next_unit = ARTICLE_STRUCTURE[idx + 1]
                    if next_unit.get("lessons"):
                        first_slug = next_unit["lessons"][0]["slug"]
                        next_unit_first = ARTICLE_LOOKUP.get((next_unit["unit"], first_slug))
                    break

        if result.get("success") and unit_number:
            record_practice_completed(current_user.id, unit_number)
        learning_state = build_learning_state(current_user.id)

        return render_template(
            "result.html",
            unit_name=unit_name,
            code=code,
            result=result,
            next_unit=next_unit,
            next_unit_first=next_unit_first,
            learning_state=learning_state,
        )

    @app.route("/articles/<int:unit>/<slug>")
    @login_required
    def article(unit, slug):
        article_meta = ARTICLE_LOOKUP.get((unit, slug))
        if not article_meta:
            abort(404)
        learning_state = build_learning_state(current_user.id)
        unit_state = learning_state["units"].get(unit, {})
        if not unit_state.get("article_unlocked"):
            abort(403)
        prev_article = (
            ARTICLE_SEQUENCE[article_meta["index"] - 1]
            if article_meta["index"] > 0
            else None
        )
        next_article = (
            ARTICLE_SEQUENCE[article_meta["index"] + 1]
            if article_meta["index"] < len(ARTICLE_SEQUENCE) - 1
            else None
        )
        if next_article:
            next_unit_state = learning_state["units"].get(next_article["unit"], {})
            if not next_unit_state.get("article_unlocked"):
                next_article = None

        # Mark lesson as read for gating purposes
        record_lesson_read(current_user.id, unit, slug)
        learning_state = build_learning_state(current_user.id)
        return render_template(
            article_meta["template"],
            current_article=article_meta,
            prev_article=prev_article,
            next_article=next_article,
            learning_state=learning_state,
        )

    

    return app


if __name__ == "__main__":
    app = create_app()
    #USE THIS IF TESTING LOCALLY (until we get a website with a certificate.)
    #This is only so we can test without annoying "this website is not secure errors", it's unencrypted
    #use "localhost:5000"
    app.run(host="0.0.0.0", port=5000)
    
