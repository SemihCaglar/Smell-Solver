import sqlite3
import uuid

DB_PATH = "smellsolver.db"

def init_db():
    """Initialize the database and create tables if they do not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS installations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                installation_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT internal_id, github_repo_id, repo_full_name, installation_id 
        FROM repositories 
        WHERE internal_id = ?
    """, (internal_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "internal_id": row[0],
            "github_repo_id": row[1],
            "repo_full_name": row[2],
            "installation_id": row[3]
        }
    return None

