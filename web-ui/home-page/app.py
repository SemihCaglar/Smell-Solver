from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import uuid
from pyngrok import ngrok
import config
import json
import os
import requests
import time
import jwt  # PyJWT for GitHub App JWT generation
from database.database import init_db, add_installation, add_repository, get_repositories_by_installation

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure random key

# Simulated repository "database" for manual additions (for backward compatibility)
repository_db = {
    "c4d2e6b8-1a7f-4f92-a9b1-1234567890ab": {"name": "Example Repo 1", "owner": "admin1"},
    "d8f3a4c2-5b6e-7d8f-9a0b-0987654321cd": {"name": "Example Repo 2", "owner": "admin2"}
}

# Initialize the SQLite database
init_db()

def start_ngrok():
    """Start an ngrok tunnel with a reserved subdomain using pyngrok."""
    ngrok.set_auth_token(config.NGROK_TOKEN)
    if not ngrok.get_tunnels():
        public_url = ngrok.connect(config.NGROK_PORT, "http", subdomain=config.NGROK_SUBDOMAIN).public_url
        print(f"✅ ngrok tunnel started: {public_url}")
    return ngrok.get_tunnels()[0].public_url

@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'POST':
        # User enters a repository ID in the form.
        repo_id = request.form.get('repository_id')
        if repo_id in repository_db:
            # Use session storage to keep track of repositories the user has added.
            if 'repos' not in session:
                session['repos'] = []
            if repo_id not in session['repos']:
                session['repos'].append(repo_id)
                flash(f"Repository '{repository_db[repo_id]['name']}' added.", "success")
            else:
                flash("Repository already added.", "info")
        else:
            flash("Invalid repository ID.", "danger")
        return redirect(url_for('main_page'))

    # Retrieve repository details from the session for display.
    repo_ids = session.get('repos', [])
    repos = [repository_db[rid] for rid in repo_ids if rid in repository_db]
    return render_template("main.html", repositories=repos)

@app.route('/github-event', methods=['POST'])
def github_event_handler():
    """Handles GitHub App webhook events."""
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    payload = request.json

    print(f"🔔 Received GitHub event: {event_type}")

    if event_type == "installation":
        return process_installation_event(payload)

    return jsonify({"message": "Event received"}), 200

def process_installation_event(payload):
    """Processes GitHub App installation events and stores data in the database."""
    installation_id = str(payload["installation"]["id"])
    repositories = payload.get("repositories", [])

    # Save the installation in the database.
    add_installation(installation_id)

    repo_list = []
    for repo in repositories:
        repo_full_name = repo["full_name"]
        repo_id = str(repo["id"])
        # Save repository details in the database.
        add_repository(installation_id, repo_id, repo_full_name)
        repo_list.append({"repo_id": repo_id, "repo_name": repo_full_name})
        print(f"✅ App installed on {repo_full_name} (Repo ID: {repo_id}, Installation ID: {installation_id})")

    # Store installation ID in session (optional)
    session["installation_id"] = installation_id

    return jsonify({
        "message": "Installation successful",
        "installation_id": installation_id,
        "repositories": repo_list
    }), 200

# JWT and installation token functions (if you need them later)
def get_jwt():
    """Generates a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10 minutes expiration
        "iss": config.GITHUB_APP_ID
    }
    token = jwt.encode(payload, config.GITHUB_PRIVATE_KEY, algorithm="RS256")
    return token

def get_installation_access_token(installation_id):
    """Obtains an installation access token using the installation ID."""
    jwt_token = get_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        token = response.json()["token"]
        return token
    else:
        print("Error obtaining installation token:", response.json())
        return None

@app.route('/install-success', methods=['GET'])
def install_success():
    """
    Displays the repositories for the given installation.
    GitHub redirects the admin with a URL like:
    https://yourdomain/install-success?installation_id=62575426&setup_action=install
    """
    installation_id = request.args.get("installation_id")
    if not installation_id:
        return "Installation ID missing in query parameters.", 400

    # Get repositories from the database for this installation.
    repo_list = get_repositories_by_installation(installation_id)

    return render_template("install_success.html", installation_id=installation_id, repositories=repo_list)

if __name__ == '__main__':
    public_url = start_ngrok()  # Start the ngrok tunnel
    print(f"🌍 GitHub Event URL: {public_url}/github-event")
    print(f"🔄 Post-Installation Redirect URL: {public_url}/install-success")
    app.run(port=config.NGROK_PORT, debug=True, use_reloader=False)
