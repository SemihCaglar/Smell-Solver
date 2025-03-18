import time
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import config
from pyngrok import ngrok
import database.database as database
from utils import start_ngrok, get_jwt, get_installation_access_token
from github_event_handler import process_installation_event
from routes.main_routes import main_bp
from routes.github_routes import github_bp
from routes.repo_routes import repo_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize the SQLite database
database.init_db()

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(github_bp)
app.register_blueprint(repo_bp)

if __name__ == '__main__':
    public_url = start_ngrok()
    app.run(port=config.NGROK_PORT, debug=True, use_reloader=False)
