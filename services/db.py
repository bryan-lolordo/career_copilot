# services/db.py
import sqlite3
import os

DB_PATH = os.path.join("data", "career_copilot.db")

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Create the database and all tables if they don't exist."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            link TEXT,
            description TEXT,
            embedding TEXT,
            search_query TEXT,
            search_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Résumés table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            path TEXT,
            word_count INTEGER,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Resume-Job Matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            reason TEXT,
            detailed_analysis TEXT,
            confidence REAL DEFAULT 0.5,
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(resume_id, job_id)
        )
    """)

    # Add confidence column if it doesn't exist (migration)
    try:
        cursor.execute("""
            ALTER TABLE resume_job_matches 
            ADD COLUMN confidence REAL DEFAULT 0.5
        """)
        print("✅ Added confidence column to resume_job_matches")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()
    
    # Run migrations for existing databases
    _migrate_database()


def _migrate_database():
    """Apply database migrations for existing databases."""
    add_created_at_to_jobs()
    add_detailed_analysis_column()


def add_created_at_to_jobs():
    """Migration: Add created_at timestamp to jobs table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "created_at" not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("✅ Migration: Added created_at column to jobs table")
        
        # Update existing NULL timestamps
        cursor.execute("UPDATE jobs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        print(f"✅ Updated {cursor.rowcount} jobs with current timestamp")
    
    conn.commit()
    conn.close()


def add_detailed_analysis_column():
    """Migration: Add detailed_analysis column to resume_job_matches table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(resume_job_matches)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "detailed_analysis" not in columns:
        cursor.execute("ALTER TABLE resume_job_matches ADD COLUMN detailed_analysis TEXT")
        print("✅ Migration: Added detailed_analysis column to resume_job_matches table")
    
    conn.commit()
    conn.close()


# ============================================================================
# JOB FUNCTIONS
# ============================================================================

def save_jobs(jobs, query, location):
    """
    Save job results into the database without duplicates.
    
    Args:
        jobs: List of job dictionaries to save
        query: The search query used to find these jobs
        location: The location used in the search
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for job in jobs:
        # Check if job already exists
        cursor.execute(
            "SELECT id FROM jobs WHERE title=? AND company=? AND location=?",
            (job.get("title"), job.get("company"), job.get("location")),
        )
        if cursor.fetchone():
            continue

        # Insert new job
        cursor.execute("""
            INSERT INTO jobs (title, company, location, link, description, search_query, search_location, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("link"),
            job.get("description") or "",
            query,
            location
        ))

    conn.commit()  
    conn.close()


def save_job(title, company, location, description, link):
    """
    Save a single job to the database.
    
    Args:
        title: Job title
        company: Company name
        location: Job location
        description: Job description
        link: Application link
    """
    save_jobs([{
        'title': title,
        'company': company,
        'location': location,
        'description': description,
        'link': link
    }], query="", location="")


def get_job_by_id(job_id: int):
    """
    Get a job by its ID.
    
    Args:
        job_id: The ID of the job
    
    Returns:
        Dictionary with job details or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, company, location, link, description, created_at
        FROM jobs
        WHERE id = ?
    """, (job_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'title': row[1],
            'company': row[2],
            'location': row[3],
            'link': row[4],
            'description': row[5],
            'created_at': row[6]
        }
    return None


# ============================================================================
# RESUME FUNCTIONS
# ============================================================================

def save_resume(name, path, text):
    """
    Save parsed résumé text and metadata to the database.
    
    Args:
        name: Display name for the resume
        path: Original file path
        text: Extracted text content
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    word_count = len(text.split())
    cursor.execute("""
        INSERT INTO resumes (name, path, word_count, text)
        VALUES (?, ?, ?, ?)
    """, (name, path, word_count, text))
    conn.commit()
    conn.close()


def delete_resume(resume_id):
    """
    Delete a résumé record by ID.
    
    Args:
        resume_id: The ID of the resume to delete
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    conn.commit()
    conn.close()


def get_resume_by_id(resume_id: int):
    """
    Get a resume by its ID.
    
    Args:
        resume_id: The ID of the resume
    
    Returns:
        Dictionary with resume details or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, text, word_count, created_at
        FROM resumes
        WHERE id = ?
    """, (resume_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'name': row[1],
            'text': row[2],
            'word_count': row[3],
            'created_at': row[4]
        }
    return None


# ============================================================================
# RESUME-JOB MATCH FUNCTIONS
# ============================================================================

def save_job_match(resume_id: int, job_id: int, score: int, reason: str, confidence: float = 0.5, detailed_analysis: str = None):
    """
    Save or update a job match result with optional detailed analysis.
    
    If a match already exists for this resume-job pair, it will be updated
    with the new score, reason, and detailed analysis.
    
    Args:
        resume_id: ID of the resume
        job_id: ID of the job
        score: Match score (0-100)
        reason: Explanation for the match score
        confidence: Confidence score (0.0-1.0)
        detailed_analysis: Optional JSON string with detailed match breakdown
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Use INSERT OR REPLACE to update if match already exists
    cursor.execute("""
        INSERT OR REPLACE INTO resume_job_matches 
        (resume_id, job_id, score, confidence, reason, detailed_analysis)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (resume_id, job_id, score, confidence, reason, detailed_analysis))
    
    conn.commit()
    conn.close()


def get_match_by_ids(resume_id: int, job_id: int):
    """
    Get a specific match result by resume and job IDs.
    
    Args:
        resume_id: ID of the resume
        job_id: ID of the job
    
    Returns:
        Dictionary with match details including detailed_analysis, or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.id,
            m.resume_id,
            m.job_id,
            m.score,
            m.reason,
            m.detailed_analysis,
            m.matched_at,
            m.confidence,
            r.name as resume_name,
            j.title,
            j.company,
            j.location,
            j.link,
            j.description
        FROM resume_job_matches m
        JOIN resumes r ON m.resume_id = r.id
        JOIN jobs j ON m.job_id = j.id
        WHERE m.resume_id = ? AND m.job_id = ?
    """, (resume_id, job_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'resume_id': row[1],
            'job_id': row[2],
            'score': row[3],
            'reason': row[4],
            'detailed_analysis': row[5],
            'matched_at': row[6],
            'confidence': row[7] if row[7] is not None else 0.5,
            'resume_name': row[8],
            'job_title': row[9],
            'company': row[10],
            'location': row[11],
            'link': row[12],
            'description': row[13]
        }
    return None


def get_matches_for_resume(resume_id: int):
    """
    Get all match results for a resume, ordered by score (highest first).
    
    Args:
        resume_id: ID of the resume
    
    Returns:
        List of tuples containing match and job details
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.score,
            m.reason,
            m.matched_at,
            m.detailed_analysis,
            j.id as job_id,
            j.title,
            j.company,
            j.location,
            j.link,
            j.description
        FROM resume_job_matches m
        JOIN jobs j ON m.job_id = j.id
        WHERE m.resume_id = ?
        ORDER BY m.score DESC, m.matched_at DESC
    """, (resume_id,))
    
    matches = cursor.fetchall()
    conn.close()
    
    return matches


def has_matches_for_resume(resume_id: int) -> bool:
    """
    Check if a resume has any stored match results.
    
    Args:
        resume_id: ID of the resume
    
    Returns:
        True if matches exist, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM resume_job_matches WHERE resume_id = ?",
        (resume_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0


def clear_matches_for_resume(resume_id: int) -> int:
    """
    Clear all match results for a resume (useful for re-matching).
    
    Args:
        resume_id: ID of the resume
    
    Returns:
        Number of matches deleted
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resume_job_matches WHERE resume_id = ?", (resume_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted


def get_match_stats_for_resume(resume_id: int) -> dict:
    """
    Get statistics about matches for a resume.
    
    Args:
        resume_id: ID of the resume
    
    Returns:
        Dictionary with stats: total_matches, avg_score, top_score, last_matched
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(score) as avg_score,
            MAX(score) as top_score,
            MAX(matched_at) as last_matched
        FROM resume_job_matches
        WHERE resume_id = ?
    """, (resume_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        return {
            'total_matches': row[0],
            'avg_score': round(row[1], 1) if row[1] else 0,
            'top_score': row[2] if row[2] else 0,
            'last_matched': row[3]
        }
    else:
        return {
            'total_matches': 0,
            'avg_score': 0,
            'top_score': 0,
            'last_matched': None
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_db_connection():
    """
    Get a database connection.
    
    Returns:
        sqlite3.Connection object
    """
    return sqlite3.connect(DB_PATH)