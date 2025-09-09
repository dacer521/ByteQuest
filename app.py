import os
from flask import Flask, render_template, url_for

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev', 
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Context processor for template variables
    @app.context_processor
    def inject_brand():
        return {
            "SITE_NAME": "ByteQuest",
            "LOGO_URL": url_for("static", filename="images/logo.png")
        }

    # Root route
    @app.route('/')
    def index():
        return render_template("index.html")

    # Example route
    # @app.route('/hello')
    # def hello():
    #     return 'Hello, World!'

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5005, debug=True)