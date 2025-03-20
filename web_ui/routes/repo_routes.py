from flask import Blueprint, json, render_template, request, flash, redirect, url_for
import database.database as database
import random
import datetime

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
        "total_prs": 30,
        "total_smells": 100,
        "most_common_smell": "Vague"
    }
    # New dummy PR list with 30 random entries.
    base_date = datetime.date(2025, 1, 1)
    pr_list = []
    for i in range(30):
        pr_list.append({
            "pr_number": 100 + i,
            "title": f"Dummy PR {i+1}",
            "smell_count": random.randint(1, 10),
            "date": (base_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        })
    
    smell_reports = [
        { "date": "2024-05-12", "smell_type": "Vague" },
        { "date": "2023-11-20", "smell_type": "No Comment" },
        { "date": "2023-04-24", "smell_type": "Vague" },
        { "date": "2024-03-15", "smell_type": "Misleading" },
        { "date": "2023-11-21", "smell_type": "Task" },
        { "date": "2024-05-27", "smell_type": "Task" },
        { "date": "2024-09-03", "smell_type": "Misleading" },
        { "date": "2024-03-05", "smell_type": "Task" },
        { "date": "2024-01-13", "smell_type": "Obvious" },
        { "date": "2024-06-26", "smell_type": "Beautification" },
        { "date": "2023-02-01", "smell_type": "Beautification" },
        { "date": "2023-08-01", "smell_type": "Attribution" },
        { "date": "2023-12-28", "smell_type": "Beautification" },
        { "date": "2024-11-03", "smell_type": "Too Much Information" },
        { "date": "2023-09-27", "smell_type": "Beautification" },
        { "date": "2025-02-02", "smell_type": "Obvious" },
        { "date": "2023-01-06", "smell_type": "No Comment" },
        { "date": "2023-10-06", "smell_type": "Misleading" },
        { "date": "2023-08-02", "smell_type": "Beautification" },
        { "date": "2023-01-06", "smell_type": "Beautification" },
        { "date": "2023-06-11", "smell_type": "Misleading" },
        { "date": "2024-04-07", "smell_type": "No Comment" },
        { "date": "2025-03-16", "smell_type": "Too Much Information" },
        { "date": "2023-12-22", "smell_type": "Vague" },
        { "date": "2024-10-08", "smell_type": "Vague" },
        { "date": "2024-12-14", "smell_type": "Task" },
        { "date": "2023-09-26", "smell_type": "Commented-Out Code" },
        { "date": "2024-01-21", "smell_type": "Obvious" },
        { "date": "2024-07-28", "smell_type": "Misleading" },
        { "date": "2023-07-13", "smell_type": "Commented-Out Code" },
        { "date": "2025-01-14", "smell_type": "Obvious" },
        { "date": "2024-11-28", "smell_type": "Task" },
        { "date": "2024-08-26", "smell_type": "Beautification" },
        { "date": "2023-03-09", "smell_type": "Beautification" },
        { "date": "2024-07-24", "smell_type": "Non-Local" },
        { "date": "2024-05-04", "smell_type": "Commented-Out Code" },
        { "date": "2024-09-08", "smell_type": "No Comment" },
        { "date": "2024-06-22", "smell_type": "Commented-Out Code" },
        { "date": "2025-01-11", "smell_type": "Beautification" },
        { "date": "2024-06-09", "smell_type": "Non-Local" },
        { "date": "2024-10-15", "smell_type": "Obvious" },
        { "date": "2023-11-21", "smell_type": "Task" },
        { "date": "2023-02-11", "smell_type": "Non-Local" },
        { "date": "2024-02-26", "smell_type": "Vague" },
        { "date": "2024-03-14", "smell_type": "Obvious" },
        { "date": "2024-04-14", "smell_type": "Too Much Information" },
        { "date": "2024-08-01", "smell_type": "Attribution" },
        { "date": "2024-01-02", "smell_type": "Non-Local" },
        { "date": "2023-08-03", "smell_type": "Task" },
        { "date": "2024-12-10", "smell_type": "Task" },
        { "date": "2024-09-04", "smell_type": "Commented-Out Code" },
        { "date": "2024-04-06", "smell_type": "Task" },
        { "date": "2025-02-08", "smell_type": "Misleading" },
        { "date": "2025-03-14", "smell_type": "Beautification" },
        { "date": "2023-12-27", "smell_type": "Task" },
        { "date": "2024-08-26", "smell_type": "Beautification" },
        { "date": "2023-09-24", "smell_type": "Commented-Out Code" },
        { "date": "2024-06-08", "smell_type": "Vague" },
        { "date": "2023-03-19", "smell_type": "No Comment" },
        { "date": "2024-05-12", "smell_type": "Too Much Information" },
        { "date": "2024-03-14", "smell_type": "Non-Local" },
        { "date": "2023-11-30", "smell_type": "Attribution" },
        { "date": "2024-05-16", "smell_type": "Too Much Information" },
        { "date": "2023-07-30", "smell_type": "Beautification" },
        { "date": "2023-10-31", "smell_type": "Too Much Information" },
        { "date": "2025-01-31", "smell_type": "Misleading" },
        { "date": "2024-06-19", "smell_type": "Attribution" },
        { "date": "2024-04-30", "smell_type": "Too Much Information" },
        { "date": "2023-01-24", "smell_type": "Non-Local" },
        { "date": "2024-12-26", "smell_type": "Commented-Out Code" },
        { "date": "2025-01-09", "smell_type": "Too Much Information" },
        { "date": "2023-12-13", "smell_type": "Task" },
        { "date": "2023-05-14", "smell_type": "Obvious" },
        { "date": "2025-03-18", "smell_type": "Vague" },
        { "date": "2024-12-23", "smell_type": "Non-Local" },
        { "date": "2024-08-08", "smell_type": "Misleading" },
        { "date": "2025-02-18", "smell_type": "Non-Local" },
        { "date": "2023-11-06", "smell_type": "Obvious" },
        { "date": "2023-06-17", "smell_type": "Non-Local" },
        { "date": "2023-08-16", "smell_type": "Beautification" },
        { "date": "2023-06-20", "smell_type": "Attribution" },
        { "date": "2023-03-11", "smell_type": "Attribution" },
        { "date": "2025-01-20", "smell_type": "Commented-Out Code" },
        { "date": "2023-03-18", "smell_type": "Beautification" },
        { "date": "2023-07-24", "smell_type": "Too Much Information" },
        { "date": "2024-10-20", "smell_type": "Obvious" },
        { "date": "2024-02-25", "smell_type": "Vague" },
        { "date": "2023-09-27", "smell_type": "Attribution" },
        { "date": "2024-12-03", "smell_type": "Non-Local" },
        { "date": "2024-09-26", "smell_type": "Attribution" },
        { "date": "2023-06-20", "smell_type": "Misleading" },
        { "date": "2025-01-14", "smell_type": "Non-Local" },
        { "date": "2024-09-22", "smell_type": "Commented-Out Code" },
        { "date": "2024-11-30", "smell_type": "Too Much Information" }
    ]
    smell_reports_json = json.dumps(smell_reports)
    
    return render_template("repo_page.html", repo=repo, stats=stats, pr_list=pr_list, smell_reports_json=smell_reports_json)

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
        "enabled_smells": ["Vague", "Misleading", "Obvious", "Beautification", "Commented-Out Code", "Attribution", "Too Much Information", "Non-Local", "No Comment", "Task"]
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