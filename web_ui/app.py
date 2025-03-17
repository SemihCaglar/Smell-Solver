import time
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import config
from pyngrok import ngrok
import database.database as database
from utils import start_ngrok, get_jwt, get_installation_access_token
from github_event_handler import process_installation_event

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize the SQLite database
database.init_db()

@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'POST':
        repo_id = request.form.get('repository_id')
        repo = database.get_repository_by_id(repo_id)
        if repo:
            if 'internal_repo_ids' not in session:
                session['internal_repo_ids'] = []
            if repo_id not in session['internal_repo_ids']:
                session['internal_repo_ids'].append(repo_id)
                flash("Repository '{}' added.".format(repo['repo_full_name']), "success")
            else:
                flash("Repository already added.", "info")
        else:
            flash("Invalid repository ID.", "danger")
        return redirect(url_for('main_page'))

    repos = database.get_repositories_by_internal_ids(session.get("internal_repo_ids", []))
    return render_template("home/main.html", repositories=repos)

@app.route('/github-app-event', methods=['POST'])
def github_app_event():
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    payload = request.json
    print("Received GitHub event:", event_type)
    if event_type == "installation":
        return process_installation_event(payload)
    #TODO: Handle other event types such as pull_request
    return jsonify({"message": "Event received"}), 200

@app.route('/install-success', methods=['GET'])
def install_success():
    time.sleep(2)
    installation_id = request.args.get("installation_id")
    if not installation_id:
        return "Installation ID missing in query parameters.", 400
    repo_list = database.get_repositories_by_installation(installation_id)
    internal_ids = [repo["internal_id"] for repo in repo_list]
    session["internal_repo_ids"] = internal_ids
    return render_template("home/install_success.html", installation_id=installation_id, repositories=repo_list)

@app.route('/remove_repo', methods=['POST'])
def remove_repo():
    repo_id = request.form.get('repo_id')
    if not repo_id:
        flash("Repository ID is missing.", "danger")
        return redirect(url_for('main_page'))
    if 'internal_repo_ids' in session and repo_id in session['internal_repo_ids']:
        session['internal_repo_ids'].remove(repo_id)
        flash("Repository removed.", "success")
    else:
        flash("Repository not found in session.", "info")
    return redirect(url_for('main_page'))

def repo_page(repo_id): # TODO 
    repo = database.get_repository_by_id(repo_id)
    
    return render_template("repository/repo_page.html", repo=repo)

@app.route('/r/<repo_id>', methods=['GET'])
def repo_details(repo_id):
    repo = database.get_repository_by_id(repo_id)
    if not repo:
        return "Repository not found.", 404
    return repo_page(repo_id)

if __name__ == '__main__':
    public_url = start_ngrok()
    app.run(port=config.NGROK_PORT, debug=True, use_reloader=False)
