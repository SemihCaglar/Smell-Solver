from flask import Blueprint, render_template, request, flash, redirect, url_for
import database.database as database

repo_bp = Blueprint('repo_routes', __name__, template_folder='../templates/repository')

@repo_bp.route('/r/<repo_id>', methods=['GET'])
def repo_dashboard(repo_id):
    """
    Repository Dashboard: Shows repository statistics and a PR list via tabs.
    For now, you can provide dummy data or call functions to get real metrics.
    """
    # Example: Fetch repository details and dummy dashboard data
    repo = database.get_repository_by_internal_id(repo_id)
    if not repo:
        flash("Repository not found.", "danger")
        return redirect(url_for('main_routes.main_page'))
    
    # Dummy data for demonstration; replace with actual queries
    stats = {
        "total_prs": 10,
        "total_smells": 25,
        "most_common_smell": "Vague"
    }
    pr_list = [
        {"pr_number": 101, "title": "Fix bug in login", "smell_count": 3, "date": "2023-09-01"},
        {"pr_number": 102, "title": "Improve UI", "smell_count": 2, "date": "2023-09-02"}
    ]
    
    return render_template("repo_page.html", repo=repo, stats=stats, pr_list=pr_list)

@repo_bp.route('/r/<repo_id>/pr/<int:pr_number>', methods=['GET'])
def pr_analysis(repo_id, pr_number):
    """
    PR Analysis Page: Detailed breakdown for a specific pull request.
    """
    # Dummy data; replace with real PR analysis query
    pr_details = {
        "pr_number": pr_number,
        "title": "Example PR Title",
        "smell_details": [
            {"file": "app.py", "line": 42, "smell_type": "Vague", "original": "# unclear comment", "suggested": "# improved comment", "status": "Pending"}
        ]
    }
    return render_template("pr_analysis.html", repo_id=repo_id, pr_details=pr_details)

@repo_bp.route('/r/<repo_id>/settings', methods=['GET', 'POST'])
def repo_settings(repo_id):
    """
    Repository Settings Page: Allow configuring detection preferences.
    """
    # For GET: load current settings (dummy or from a function)
    # For POST: update settings in the database.
    if request.method == 'POST':
        # Process submitted settings form data
        # e.g., request.form.get('create_issues'), request.form.getlist('enabled_smells')
        flash("Settings updated.", "success")
        return redirect(url_for('repo_routes.repo_settings', repo_id=repo_id))
    
    # Dummy settings data; replace with real data retrieval.
    settings = {
        "create_issues": True,
        "enabled_smells": ["Vague", "Misleading", "Obvious"]
    }
    return render_template("repo_settings.html", repo_id=repo_id, settings=settings)
