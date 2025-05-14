from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import database.database as database
import time

main_bp = Blueprint('main_routes', __name__) #TODO add template folder parameter

@main_bp.route('/', methods=['GET', 'POST'])
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
        return redirect(url_for('main.main_page'))

    repos = database.get_repositories_by_internal_ids(session.get("internal_repo_ids", []))
    return render_template("home/main.html", repositories=repos)

@main_bp.route('/install-success', methods=['GET'])
def install_success():
    time.sleep(2)
    installation_id = request.args.get("installation_id")
    if not installation_id:
        return "Installation ID missing in query parameters.", 400
    repo_list = database.get_repositories_by_installation(installation_id)
    internal_ids = [repo["internal_id"] for repo in repo_list]
    session["internal_repo_ids"] = internal_ids
    return render_template("home/install_success.html", installation_id=installation_id, repositories=repo_list)

@main_bp.route('/remove_repo', methods=['POST'])
def remove_repo():
    repo_id = request.form.get('repo_id')
    if not repo_id:
        flash("Repository ID is missing.", "danger")
        return redirect(url_for('main.main_page'))
    if 'internal_repo_ids' in session and repo_id in session['internal_repo_ids']:
        session['internal_repo_ids'].remove(repo_id)
        flash("Repository removed.", "success")
    else:
        flash("Repository not found in session.", "info")
    return redirect(url_for('main.main_page'))