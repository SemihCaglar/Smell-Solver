import sqlite3
import uuid

DB_PATH = "smellsolver.db"

def init_db():
    """Initialize the database and create tables if they do not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # 1. installations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS installations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                installation_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 2. repositories table
        c.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_id TEXT UNIQUE,
                github_repo_id TEXT,
                repo_full_name TEXT,
                installation_id TEXT,
                UNIQUE(github_repo_id, installation_id)
            )
        """)
        # 3. pull_requests table (basic metadata)
        c.execute("""
            CREATE TABLE IF NOT EXISTS pull_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_internal_id TEXT,
                pr_number INTEGER,
                title TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        # 4. comment_smells table
        c.execute("""
            CREATE TABLE IF NOT EXISTS comment_smells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_id INTEGER,
                file_path TEXT,
                blob_sha TEXT,
                line_number INTEGER,
                smell_type TEXT CHECK (smell_type IN (
                    'Vague Comment', 
                    'Misleading Comment', 
                    'Obvious Comment', 
                    'Beautification', 
                    'Commented-Out Code', 
                    'Attribution', 
                    'Too Much Information', 
                    'Non-Local Comment', 
                    'No Comment', 
                    'Task Comment'
                )),
                original_comment TEXT,
                suggested_fix TEXT,
                status TEXT CHECK (status IN ('Accepted', 'Rejected', 'Pending')),
                FOREIGN KEY (pr_id) REFERENCES pull_requests (id)
            )
        """)
        # 5. repo_settings table
        c.execute("""
            CREATE TABLE IF NOT EXISTS repo_settings (
                repo_internal_id TEXT PRIMARY KEY,
                create_issues BOOLEAN DEFAULT 1,
                enabled_smells TEXT,  -- JSON string listing enabled smell types
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        # 6. smell_summary table
        c.execute("""
            CREATE TABLE IF NOT EXISTS smell_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_internal_id TEXT,
                file_path TEXT,
                total_smells INTEGER DEFAULT 0,
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id),
                UNIQUE(repo_internal_id, file_path)
            )
        """)
        conn.commit()

def add_installation(installation_id):
    """Add an installation record (if not already present)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO installations (installation_id) VALUES (?)", (installation_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        # The installation already exists.
        pass

def remove_installation(installation_id):
    """Remove the installation and its associated repositories from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM repositories WHERE installation_id = ?", (installation_id,))
        c.execute("DELETE FROM installations WHERE installation_id = ?", (installation_id,))
        conn.commit()

def add_repository(installation_id, github_repo_id, repo_full_name):
    """
    Generate a random internal ID for the repository and add a repository record.
    Returns the generated internal ID.
    """
    internal_id = str(uuid.uuid4())
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO repositories (internal_id, github_repo_id, repo_full_name, installation_id)
                VALUES (?, ?, ?, ?)
            """, (internal_id, github_repo_id, repo_full_name, installation_id))
            conn.commit()
    except sqlite3.IntegrityError:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT internal_id FROM repositories 
                WHERE github_repo_id = ? AND installation_id = ?
            """, (github_repo_id, installation_id))
            row = c.fetchone()
            if row:
                internal_id = row[0]
    return internal_id

def get_repositories_by_internal_ids(internal_ids):
    """Retrieve repository details for all repositories whose internal_id is in the provided list."""
    if not internal_ids:
        return []
    placeholders = ','.join('?' for _ in internal_ids)
    query = f"""
        SELECT internal_id, github_repo_id, repo_full_name, installation_id 
        FROM repositories 
        WHERE internal_id IN ({placeholders})
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, internal_ids)
        rows = c.fetchall()
    return [
        {"internal_id": row[0], "github_repo_id": row[1], "repo_full_name": row[2], "installation_id": row[3]}
        for row in rows
    ]

def get_repositories_by_installation(installation_id):
    """Retrieve all repositories linked to a given installation."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT internal_id, github_repo_id, repo_full_name 
            FROM repositories 
            WHERE installation_id = ?
        """, (installation_id,))
        rows = c.fetchall()
    return [{"internal_id": row[0], "github_repo_id": row[1], "repo_full_name": row[2]} for row in rows]

def get_repository_by_id(repo_id):
    """Retrieve a repository by its internal ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT internal_id, github_repo_id, repo_full_name, installation_id 
            FROM repositories 
            WHERE internal_id = ?
        """, (repo_id,))
        row = c.fetchone()
    if row:
        return {"internal_id": row[0], "github_repo_id": row[1], "repo_full_name": row[2], "installation_id": row[3]}
    return None

def get_repository_by_internal_id(internal_id):
    """Retrieve a repository record by its internal_id."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT internal_id, github_repo_id, repo_full_name, installation_id 
            FROM repositories 
            WHERE internal_id = ?
        """, (internal_id,))
        row = c.fetchone()
    if row:
        return {
            "internal_id": row[0],
            "github_repo_id": row[1],
            "repo_full_name": row[2],
            "installation_id": row[3]
        }
    return None

# (Additional functions for pull_requests, comment_smells, repo_settings, and smell_summary
# would be implemented similarly when needed.)
