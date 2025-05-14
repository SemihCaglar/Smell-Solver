from flask import Blueprint, json, render_template, request, flash, redirect, url_for
import sqlite3
from config import DB_PATH
import database.installations_repositories as repo_db
import database.database as database
from collections import defaultdict

repo_bp = Blueprint('repo_routes', __name__, template_folder='../templates/repository')

@repo_bp.route('/r/<repo_id>', methods=['GET'])
def repo_dashboard(repo_id):
    """
    Repository Dashboard: shows real metrics and PR list for a given repository.
    """
    # 1) Fetch repository record
    repo = repo_db.get_repository_by_internal_id(repo_id)
    if not repo:
        flash("Repository not found.", "danger")
        return redirect(url_for('main_routes.main_page'))

    # 2) Open a DB connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 3) total_prs
    c.execute("""
      SELECT COUNT(*) 
        FROM pull_requests 
       WHERE repo_internal_id = ?
    """, (repo_id,))
    total_prs = c.fetchone()[0]

    # 4) total_smells (only active + repair_enabled)
    c.execute("""
      SELECT COUNT(*) 
        FROM comment_smells cs
        JOIN pull_requests pr ON cs.pr_id = pr.id
       WHERE pr.repo_internal_id = ?
         AND cs.is_current = 1
         AND cs.repair_enabled = 1
    """, (repo_id,))
    total_smells = c.fetchone()[0]

    # 5) most_common_smell
    c.execute("""
      SELECT cs.smell_type, COUNT(*) AS cnt
        FROM comment_smells cs
        JOIN pull_requests pr ON cs.pr_id = pr.id
       WHERE pr.repo_internal_id = ?
         AND cs.is_current = 1
       GROUP BY cs.smell_type
       ORDER BY cnt DESC
       LIMIT 1
    """, (repo_id,))
    row = c.fetchone()
    most_common_smell = row['smell_type'] if row else None

    stats = {
        "total_prs": total_prs,
        "total_smells": total_smells,
        "most_common_smell": most_common_smell or "—"
    }

    # 6) PR list (with date from created_at)
    c.execute("""
      SELECT pr_number, title, smell_count, created_at, status
        FROM pull_requests
       WHERE repo_internal_id = ?
       ORDER BY created_at DESC
    """, (repo_id,))
    pr_list = []
    for r in c.fetchall():
        pr_list.append({
            "pr_number":    r["pr_number"],
            "title":        r["title"],
            "smell_count":  r["smell_count"],
            "date":         r["created_at"][:10],
            "url":          f"https://github.com/{repo['repo_full_name']}/pull/{r['pr_number']}",
            "status":       r["status"],
        })

    # 7) Smell‐reports time series
    c.execute("""
      SELECT cs.created_at, cs.smell_type
        FROM comment_smells cs
        JOIN pull_requests pr ON cs.pr_id = pr.id
       WHERE pr.repo_internal_id = ?
       ORDER BY cs.created_at DESC
    """, (repo_id,))
    smell_reports = [
        {"date": r["created_at"][:10], "smell_type": r["smell_type"]}
        for r in c.fetchall()
    ]
    smell_reports_json = json.dumps(smell_reports)

    conn.close()

    return render_template(
        "repo_page.html",
        repo=repo,
        stats=stats,
        pr_list=pr_list,
        smell_reports_json=smell_reports_json
    )

@repo_bp.route('/r/<repo_id>/pr/<int:pr_number>', methods=['GET'])
def pr_analysis(repo_id, pr_number):
    """
    PR Analysis Page: detailed breakdown for a specific pull request,
    pulling real comment‐smell data.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1) Find the PR ID & metadata
    c.execute("""
      SELECT
        id,
        title,
        smell_count,
        status,
        created_at,
        updated_at
      FROM pull_requests
      WHERE repo_internal_id = ?
      AND pr_number = ?
    """, (repo_id, pr_number))
    pr = c.fetchone()
    if not pr:
        flash(f"PR #{pr_number} not found.", "warning")
        conn.close()
        return redirect(url_for('repo_routes.repo_dashboard', repo_id=repo_id))

    # 2) Fetch all active comment‐smells for this PR, including the GitHub link
    c.execute("""
    SELECT
        id                    AS comment_id,
        file_path             AS file,
        line,
        smell_type,
        associated_code       AS code_block,
        comment_body          AS original,
        suggestion,
        status,
        github_comment_url    AS url
    FROM comment_smells
    WHERE pr_id = ?
        AND is_current = 1
        AND repair_enabled = 1
    ORDER BY file_path, line
    """, (pr["id"],))

    smell_details = []
    for r in c.fetchall():
        smell_details.append({
            "comment_id": r["comment_id"],
            "file":       r["file"],
            "line":       r["line"],
            "smell_type": r["smell_type"],
            "original":   r["original"],
            "suggested":  r["suggestion"],
            "code_block": r["code_block"],
            "status":     r["status"],
            "url":        r["url"]
        })

    # # update file randomly
    # files = ["folder1/file1.java", "folder1/file2.java", "file3.java", "file4.java", "folder2/file1.java"]
    # #iterate over the smell_details and update the file randomly
    # for i in range(len(smell_details)):
    #     smell_details[i]["file"] = files[i % len(files)]    
    
    conn.close()
    file_groups = defaultdict(list)
    for s in smell_details:
        file_groups[s["file"]].append(s)

    return render_template(
        "pr_analysis.html",
        repo_id=repo_id,
        pr_details={
            "pr_number":    pr_number,
            "title":        pr["title"],
            "status":       pr["status"],
            "created_at":   pr["created_at"],
            "updated_at":   pr["updated_at"],
            "smell_count":  pr["smell_count"],
            "smell_details": smell_details,
        },
        file_groups=file_groups,
    )

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
        double_iteration  = request.form.get('double_iteration') == 'on'
        
        # Update the settings in the database
        database.update_repo_settings(repo_id, create_issues, enabled_smells, double_iteration)
        
        flash("Settings updated.", "success")
        return redirect(url_for('repo_routes.repo_settings', repo_id=repo_id))
    
    # For GET: load current settings.
    # Retrieve settings from the database.
    # If not found, use default dummy settings.

    current_settings = {
        "create_issues": True,
        "enabled_smells": ["Misleading", "Obvious", "Commented out code", "Irrelevant", "Task", "Too much info", "Beautification", "Nonlocal info", "Vague"],
        "double_iteration": False
    }
    # Try to fetch settings from the repo_settings table.
    settings_row = None
    import sqlite3
    try:
        with sqlite3.connect(database.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT create_issues, enabled_smells, double_iteration
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
        current_settings['double_iteration'] = bool(settings_row[2])
    
    return render_template("repo_settings.html", repo_id=repo_id, settings=current_settings)