# services/database_service.py
import sqlite3
from services.db import DB_PATH

class DatabaseService:
    """Service class for database operations used by plugins."""
    
    def get_resume_by_id(self, resume_id: int):
        """
        Fetch a resume by ID from the database.
        Uses processed_text if available, falls back to text.
        
        Args:
            resume_id: The ID of the resume to fetch (int, not str)
            
        Returns:
            dict with 'id', 'name', 'text' or None if not found
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, processed_text, text 
            FROM resumes 
            WHERE id = ?
        """, (resume_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Use processed_text if available, otherwise fall back to text
        text_content = row[2] if row[2] else row[3]
        
        return {
            'id': row[0],
            'name': row[1],
            'text': text_content
        }
    
    def get_job_by_id(self, job_id: int):
        """
        Fetch a job by ID from the database.
        Uses processed_description if available, falls back to description.

        Args:
            job_id: The ID of the job to fetch (int, not str)

        Returns:
            dict with 'id', 'title', 'company', 'location', 'link', 'description'
            or None if not found
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, company, location, link, processed_description, description 
            FROM jobs 
            WHERE id = ?
        """, (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        description_content = row[5] if row[5] else row[6]
        
        return {
            'id': row[0],
            'title': row[1],
            'company': row[2],
            'location': row[3],
            'link': row[4],
            'description': description_content
        }
    
    def get_all_jobs(self):
        """
        Fetch all jobs from the database.
        Uses processed_description if available, falls back to description.
        
        Returns:
            list of dict with job information
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, company, location, link, processed_description, description 
            FROM jobs
        """)
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            # Use processed_description if available, otherwise fall back to description
            description_content = row[5] if row[5] else row[6]
            
            jobs.append({
                'id': row[0],
                'title': row[1],
                'company': row[2],
                'location': row[3],
                'link': row[4],
                'description': description_content
            })
        
        return jobs
    
    def list_all_resumes(self):
        """
        List all resumes in the database.
        
        Returns:
            list of dict with 'id' and 'name'
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, created_at 
            FROM resumes 
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        resumes = []
        for row in rows:
            resumes.append({
                'id': row[0],
                'name': row[1],
                'created_at': row[2]
            })
        
        return resumes
    
    def get_most_recent_resume(self):
        """
        Get the most recently created resume.
        Uses processed_text if available, falls back to text.
        
        Returns:
            dict with resume info or None
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, processed_text, text 
            FROM resumes 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Use processed_text if available, otherwise fall back to text
        text_content = row[2] if row[2] else row[3]
        
        return {
            'id': row[0],
            'name': row[1],
            'text': text_content
        }
    
    def save_match(self, resume_id: int, job_id: int, score: float, reason: str, confidence: float = 0.5, detailed_analysis: str = None):
        """
        Save or update a match in the database.
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            score: Match score (0-100)
            reason: Reason for the match
            confidence: Confidence score (0.0-1.0)
            detailed_analysis: Optional JSON string with detailed analysis
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO resume_job_matches (resume_id, job_id, score, confidence, reason, detailed_analysis)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(resume_id, job_id) DO UPDATE SET
                score = excluded.score,
                confidence = excluded.confidence,
                reason = excluded.reason,
                detailed_analysis = excluded.detailed_analysis,
                matched_at = CURRENT_TIMESTAMP
        """, (resume_id, job_id, score, confidence, reason, detailed_analysis))
        
        conn.commit()
        conn.close()