import sqlite3
from config import DB_PATH

def add_or_update_pull_request(
    repo_internal_id: str,
    pr_number: int,
    title: str,
    status: str,
    created_at: str,
) -> int:
    """
    Insert a new pull_request row or update the existing one.
    Returns the local `id` (PR PK) for use in other tables.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Upsert the PR row
        c.execute("""
            INSERT INTO pull_requests
              (repo_internal_id, pr_number, title, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(repo_internal_id, pr_number) DO UPDATE
              SET title      = excluded.title,
                  status     = excluded.status,
                  updated_at = CURRENT_TIMESTAMP
        """, (repo_internal_id, pr_number, title, status, created_at))
        conn.commit()

        # Fetch its internal PK
        c.execute("""
            SELECT id
              FROM pull_requests
             WHERE repo_internal_id = ?
               AND pr_number        = ?
        """, (repo_internal_id, pr_number))
        pr_id, = c.fetchone()
    return pr_id
