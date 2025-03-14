from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import config
from pyngrok import ngrok
import database.database as database
from utils import start_ngrok, get_jwt, get_installation_access_token
from github_event_handler import process_installation_event

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure random key

# Simulated repository "database" for manual additions (for backward compatibility)
repository_db = {
    "c4d2e6b8-1a7f-4f92-a9b1-1234567890ab": {"name": "Example Repo 1", "owner": "admin1"},
    "d8f3a4c2-5b6e-7d8f-9a0b-0987654321cd": {"name": "Example Repo 2", "owner": "admin2"}
}

# TODO: for the adding, use actual database.

# Initialize the SQLite database
database.init_db()

@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'POST':
        repo_id = request.form.get('repository_id')
        if repo_id in repository_db:
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

    if "internal_repo_ids" in session and session["internal_repo_ids"]:
        repos = database.get_repositories_by_internal_ids(session["internal_repo_ids"])
    else:
        repo_ids = session.get('repos', [])
        repos = [repository_db[rid] for rid in repo_ids if rid in repository_db]
    return render_template("main.html", repositories=repos)

@app.route('/github-app-event', methods=['POST'])
def github_event_handler():
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    payload = request.json

    print(f"🔔 Received GitHub event: {event_type}")

    if event_type == "installation":
        return process_installation_event(payload)

    return jsonify({"message": "Event received"}), 200

@app.route('/install-success', methods=['GET'])
def install_success():
    installation_id = request.args.get("installation_id")
    if not installation_id:
        return "Installation ID missing in query parameters.", 400

    repo_list = database.get_repositories_by_installation(installation_id)
    internal_ids = [repo["internal_id"] for repo in repo_list]
    session["internal_repo_ids"] = internal_ids

    return render_template("install_success.html", installation_id=installation_id, repositories=repo_list)

@app.route('/remove_repo', methods=['POST'])
def remove_repo():
    """Remove a repository from the session (dashboard) only."""
    repo_id = request.form.get('repo_id')
    if not repo_id:
        flash("Repository ID not provided.", "danger")
        return redirect(url_for('main_page'))
    
    # Try removing from internal_repo_ids first, then fallback to manual repos.
    if "internal_repo_ids" in session and repo_id in session["internal_repo_ids"]:
        session["internal_repo_ids"].remove(repo_id)
        flash("Repository removed from dashboard.", "success")
    elif "repos" in session and repo_id in session["repos"]:
        session["repos"].remove(repo_id)
        flash("Repository removed from dashboard.", "success")
    else:
        flash("Repository not found in session.", "warning")
    
    return redirect(url_for('main_page'))


if __name__ == '__main__':
    public_url = start_ngrok()  # Start the ngrok tunnel
    print(f"🌍 GitHub Event URL: {public_url}/github-app-event")
    print(f"🔄 Post-Installation Redirect URL: {public_url}/install-success")
    app.run(port=config.NGROK_PORT, debug=True, use_reloader=False)
