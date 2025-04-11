import sqlite3
import json
import json

DP_PATH = "smellsolver.db"

def add_comment_smell(pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column,
                      smell_type, original_comment, suggested_fix, repair_enabled, status="Pending"):
    """
    Insert a new comment smell into the comment_smells table, update the smell_summary table,
    and (if repair is enabled) increment the smell_count in the corresponding pull request.
    Returns the ID of the new comment smell record.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Insert the new comment smell with repair_enabled flag.
        c.execute("""
            INSERT INTO comment_smells 
            (pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column, smell_type,
             original_comment, suggested_fix, status, is_current, repair_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (pr_id, file_path, blob_sha, start_line, end_line, start_column, end_column,
              smell_type, original_comment, suggested_fix, status, repair_enabled))
        conn.commit()
        smell_id = c.lastrowid

        # Update smell_summary table (incrementing total_smells regardless of repair settings).
        c.execute("""
            INSERT INTO smell_summary (pr_id, repo_internal_id, total_smells)
            VALUES (?, (SELECT repo_internal_id FROM pull_requests WHERE id = ?), 1)
            ON CONFLICT(pr_id) DO UPDATE SET total_smells = total_smells + 1
        """, (pr_id, pr_id))
        conn.commit()

        # Increment smell_count in pull_requests only if repair_enabled is true.
        if repair_enabled:
            c.execute("""
                UPDATE pull_requests 
                SET smell_count = smell_count + 1, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (pr_id,))
            conn.commit()

    return smell_id

def archive_comment_smells_for_file(pr_id, repo_internal_id, file_path):
    """
    Archive comment smells for a specific file in a pull request by setting is_current = 0.
    Also recalculates the pull request's smell_count (only counting active smells with repair_enabled = 1).
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Archive the smells.
        c.execute("""
            UPDATE comment_smells
            SET is_current = 0
            WHERE pr_id = ?
              AND file_path = ?
              AND EXISTS (
                  SELECT 1 FROM pull_requests
                  WHERE pull_requests.id = comment_smells.pr_id
                    AND pull_requests.repo_internal_id = ?
              )
        """, (pr_id, file_path, repo_internal_id))
        conn.commit()

        # Recalculate active (is_current = 1 and repair_enabled = 1) smells for this pull request and update smell_count.
        c.execute("""
            UPDATE pull_requests
            SET smell_count = (
                SELECT COUNT(*) FROM comment_smells 
                WHERE pr_id = ? AND is_current = 1 AND repair_enabled = 1
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (pr_id, pr_id))
        conn.commit()

def delete_comment_smells_for_file(pr_id, file_path):
    """
    (Optional) If you need a deletion method for specific purposes.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            DELETE FROM comment_smells 
            WHERE pr_id = ? AND file_path = ?
        """, (pr_id, file_path))
        conn.commit()

def add_file_record(pr_id, repo_internal_id, file_path, blob_sha, status):
    """
    Insert a new record for a file with its metadata.
    Returns the ID of the new file record.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO files (pr_id, repo_internal_id, file_path, blob_sha, status)
            VALUES (?, ?, ?, ?, ?)
        """, (pr_id, repo_internal_id, file_path, blob_sha, status))
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
        c.execute("""
            INSERT INTO repo_settings (repo_internal_id, create_issues, enabled_smells)
            VALUES (?, ?, ?)
            ON CONFLICT(repo_internal_id) DO UPDATE SET
                create_issues = excluded.create_issues,
                enabled_smells = excluded.enabled_smells
        """, (repo_internal_id, 1 if create_issues else 0, settings_json))
        conn.commit()