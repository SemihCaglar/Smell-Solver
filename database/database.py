#!/usr/bin/env python
import sqlite3
from database.installations_repositories import *
from database.comments_files import *

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
        # 3. pull_requests table (basic metadata with smell_count)
        c.execute("""
            CREATE TABLE IF NOT EXISTS pull_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_internal_id TEXT,
                pr_number INTEGER,
                title TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                smell_count INTEGER DEFAULT 0,
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        # 4. comment_smells table with extended location details, blob_sha, is_current flag, and repair_enabled flag
        c.execute("""
            CREATE TABLE IF NOT EXISTS comment_smells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_id INTEGER,
                file_path TEXT,
                blob_sha TEXT,
                start_line INTEGER,
                end_line INTEGER,
                start_column INTEGER,
                end_column INTEGER,
                smell_type TEXT CHECK (smell_type IN (
                    'Vague', 
                    'Misleading', 
                    'Obvious', 
                    'Beautification', 
                    'Commented-Out Code', 
                    'Attribution', 
                    'Too Much Information', 
                    'Non-Local', 
                    'No Comment', 
                    'Task'
                )),
                original_comment TEXT,
                suggested_fix TEXT,
                status TEXT CHECK (status IN ('Accepted', 'Rejected', 'Pending')),
                is_current BOOLEAN DEFAULT 1,
                repair_enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (pr_id) REFERENCES pull_requests (id)
            )
        """)
        # 5. repo_settings table
        c.execute("""
            CREATE TABLE IF NOT EXISTS repo_settings (
                repo_internal_id TEXT PRIMARY KEY,
                create_issues BOOLEAN DEFAULT 1,
                enabled_smells TEXT,
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        # 6. smell_summary table
        c.execute("""
            CREATE TABLE IF NOT EXISTS smell_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_id INTEGER UNIQUE,
                repo_internal_id TEXT,
                total_smells INTEGER DEFAULT 0,
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        # 7. files table for storing file metadata including blob_sha (without file content)
        c.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_id INTEGER,
                repo_internal_id TEXT,
                file_path TEXT,
                blob_sha TEXT,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pr_id) REFERENCES pull_requests (id),
                FOREIGN KEY (repo_internal_id) REFERENCES repositories (internal_id)
            )
        """)
        conn.commit()