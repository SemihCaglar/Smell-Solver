import sqlite3
import json
import json

DB_PATH = "smellsolver.db"

def add_comment_smell(pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column, smell_type, original_comment, suggested_fix, status="Pending"):
    """
    Insert a new comment smell into the comment_smells table and update the smell_summary table.
    Returns the ID of the new comment smell record.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO comment_smells 
            (pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column, smell_type, original_comment, suggested_fix, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column, smell_type, original_comment, suggested_fix, status)
        )
        conn.commit()
        smell_id = c.lastrowid

        # Update smell_summary table: increment if exists; otherwise, insert a new record.
        c.execute(
            """
            INSERT INTO smell_summary (pr_id, repo_internal_id, total_smells)
            VALUES (?, (SELECT repo_internal_id FROM pull_requests WHERE id = ?), 1)
            ON CONFLICT(pr_id) DO UPDATE SET total_smells = total_smells + 1
            """,
            (pr_id, pr_id)
        )
        conn.commit()

    return smell_id

def delete_comment_smells_for_file(pr_id, file_path):
    """
    Delete any existing comment smells for a specific file in a pull request.
    Useful when re-processing a file to remove outdated comments.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            DELETE FROM comment_smells WHERE pr_id = ? AND file_path = ?
            """,
            (pr_id, file_path)
        )
        conn.commit()

def add_file_record(pr_id, repo_internal_id, file_path, blob_sha, status):
    """
    Insert a new record for a file with its metadata.
    Returns the ID of the new file record.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO files (pr_id, repo_internal_id, file_path, blob_sha, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pr_id, repo_internal_id, file_path, blob_sha, status)
        )
        conn.commit()
        return c.lastrowid

def update_file_record(file_id, blob_sha=None, status=None):
    """
    Update the file record's blob_sha and/or status.
    Also updates the updated_at timestamp.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        fields = []
        params = []
        if blob_sha is not None:
            fields.append("blob_sha = ?")
            params.append(blob_sha)
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if not fields:
            return
        params.append(file_id)
        query = f"UPDATE files SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        c.execute(query, params)
        conn.commit()

def update_repo_settings(repo_internal_id, create_issues, enabled_smells):
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
            INSERT INTO repo_settings (repo_internal_id, create_issues, enabled_smells)
            VALUES (?, ?, ?)
            ON CONFLICT(repo_internal_id) DO UPDATE SET
                create_issues = excluded.create_issues,
                enabled_smells = excluded.enabled_smells
            """,
            (repo_internal_id, 1 if create_issues else 0, settings_json)
        )
        conn.commit()
