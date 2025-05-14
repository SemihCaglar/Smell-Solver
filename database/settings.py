import sqlite3
from config import DB_PATH
import json

def get_repo_settings(repo_internal_id):
    """
    Fetch repo settings, with sensible defaults.
    Returns dict: { create_issues: bool, enabled_smells: list, double_iteration: bool }
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT create_issues, enabled_smells, double_iteration
              FROM repo_settings
             WHERE repo_internal_id = ?
        """, (repo_internal_id,))
        row = c.fetchone()

    if not row:
        return {
            "create_issues": True,
            "enabled_smells": [],
            "double_iteration": False
        }

    create_issues, enabled_json, double_it = row
    return {
        "create_issues": bool(create_issues),
        "enabled_smells": json.loads(enabled_json),
        "double_iteration": bool(double_it)
    }

def update_repo_settings(repo_internal_id, create_issues, enabled_smells, double_iteration=False):
    """
    Update the repository settings for a given repository.
    'create_issues' is a boolean.
    'enabled_smells' is a list of strings.
    """
    settings_json = json.dumps(enabled_smells)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO repo_settings (
                repo_internal_id,
                create_issues,
                enabled_smells,
                double_iteration
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(repo_internal_id) DO UPDATE SET
              create_issues = excluded.create_issues,
              enabled_smells = excluded.enabled_smells,
              double_iteration = excluded.double_iteration
            """,
            (repo_internal_id, 1 if create_issues else 0, settings_json, 1 if double_iteration else 0)
        )
        conn.commit()