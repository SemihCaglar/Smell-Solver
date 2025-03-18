from flask import Blueprint, render_template
import database.database as database

repo_bp = Blueprint('repo', __name__)

def repo_page(repo_id):
    repo = database.get_repository_by_id(repo_id)
    return render_template("repository/repo_page.html", repo=repo)

@repo_bp.route('/r/<repo_id>', methods=['GET'])
def repo_details(repo_id):
    repo = database.get_repository_by_id(repo_id)
    if not repo:
        return "Repository not found.", 404
    return repo_page(repo_id)
