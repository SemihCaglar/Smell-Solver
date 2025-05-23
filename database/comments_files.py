import sqlite3
import json
from config import DB_PATH


def add_comment_smell(
    pr_id,
    file_path,
    commit_sha,
    line,
    side,
    smell_type,
    associated_code,
    comment_body,
    suggestion=None,
    github_comment_id=None,
    github_comment_url=None,
    is_smell=True,
    repair_enabled=True,
    status="Pending"
):
    """
    Insert a new comment smell into the comment_smells table,
    storing the associated code block. If `is_smell` is True,
    update the smell_summary and (if repair_enabled) increment
    the smell_count in the pull_requests table.
    Returns the ID of the new comment smell record.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Insert the new comment smell with associated code
        c.execute(
            """
            INSERT INTO comment_smells (
                pr_id,
                file_path,
                commit_sha,
                line,
                side,
                smell_type,
                associated_code,
                comment_body,
                suggestion,
                github_comment_id,
                github_comment_url,
                status,
                is_current,
                repair_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                pr_id,
                file_path,
                commit_sha,
                line,
                side,
                smell_type,
                associated_code,
                comment_body,
                suggestion,
                github_comment_id,
                github_comment_url,
                status,
                1 if repair_enabled else 0,
            )
        )
        conn.commit()
        smell_id = c.lastrowid

        # Only count real comment smells
        if is_smell:
            # Update smell_summary (increment total_smells)
            c.execute(
                """
                INSERT INTO smell_summary (pr_id, repo_internal_id, total_smells)
                VALUES (
                    ?,
                    (SELECT repo_internal_id FROM pull_requests WHERE id = ?),
                    1
                )
                ON CONFLICT(pr_id) DO UPDATE
                  SET total_smells = total_smells + 1
                """,
                (pr_id, pr_id)
            )
            conn.commit()

            # Optionally increment smell_count in pull_requests
            if repair_enabled:
                c.execute(
                    """
                    UPDATE pull_requests
                       SET smell_count = smell_count + 1,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = ?
                    """,
                    (pr_id,)
                )
                conn.commit()

    return smell_id


def archive_comment_smells_for_file(pr_id, file_path):
    """
    Archive comment smells for a specific file in a pull request
    by setting is_current = 0. Recalculates the PR's smell_count.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Archive the active smells for this file
        c.execute(
            """
            UPDATE comment_smells
               SET is_current = 0
             WHERE pr_id = ?
               AND file_path = ?
            """,
            (pr_id, file_path)
        )
        conn.commit()

        # Recalculate active smells count
        c.execute(
            """
            UPDATE pull_requests
               SET smell_count = (
                   SELECT COUNT(*)
                     FROM comment_smells
                    WHERE pr_id = ?
                      AND is_current = 1
                      AND repair_enabled = 1
               ),
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (pr_id, pr_id)
        )
        conn.commit()


def delete_comment_smells_for_file(pr_id, file_path):
    """
    Delete all comment smell records for a specific file in a PR.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM comment_smells WHERE pr_id = ? AND file_path = ?",
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
            INSERT INTO files (
                pr_id,
                repo_internal_id,
                file_path,
                blob_sha,
                status
            ) VALUES (?, ?, ?, ?, ?)
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

