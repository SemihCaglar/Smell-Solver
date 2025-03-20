from flask import Blueprint, json, render_template, request, flash, redirect, url_for
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
        {"pr_number": 101, "title": "Fix bug in login", "smell_count": 3, "date": "2021-09-01"},
        {"pr_number": 102, "title": "Improve UI", "smell_count": 2, "date": "2021-09-02"},
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
    Processes form submission to update settings in the database.
    """
    # For POST: update settings in the database.
    if request.method == 'POST':
        # Retrieve form data
        create_issues = request.form.get('create_issues') == 'on'
        enabled_smells = request.form.getlist('enabled_smells')
        
        # Update the settings in the database
        database.update_repo_settings(repo_id, create_issues, enabled_smells)
        
        flash("Settings updated.", "success")
        return redirect(url_for('repo_routes.repo_settings', repo_id=repo_id))
    
    # For GET: load current settings.
    # Retrieve settings from the database.
    # If not found, use default dummy settings.
    current_settings = {
        "create_issues": True,
        "enabled_smells": ["Vague", "Misleading", "Obvious"]
    }
    # Try to fetch settings from the repo_settings table.
    settings_row = None
    import sqlite3
    try:
        with sqlite3.connect(database.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT create_issues, enabled_smells
                FROM repo_settings
                WHERE repo_internal_id = ?
            """, (repo_id,))
            settings_row = c.fetchone()
    except Exception as e:
        print("Error fetching repo settings:", e)
    
    if settings_row:
        current_settings['create_issues'] = bool(settings_row[0])
        try:
            current_settings['enabled_smells'] = json.loads(settings_row[1])
        except Exception:
            current_settings['enabled_smells'] = []
    
    return render_template("repo_settings.html", repo_id=repo_id, settings=current_settings)