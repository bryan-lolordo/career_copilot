import re
import sqlite3
from semantic_kernel.functions import kernel_function
from services.db import DB_PATH

class JobPreprocessorPlugin:

    # 🔹 Option 1: Bulk preprocessor (run once or to refresh all)
    @kernel_function(description="Preprocess all jobs and save simplified descriptions for reuse")
    async def preprocess_all_jobs(self, context):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ Ensure processed_description column exists
        cur.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cur.fetchall()]
        if "processed_description" not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN processed_description TEXT")

        # ✅ Get all unprocessed jobs
        cur.execute("SELECT id, title, company, description FROM jobs WHERE processed_description IS NULL OR processed_description=''")
        jobs = cur.fetchall()

        if not jobs:
            conn.close()
            return "✅ All jobs are already processed."

        summary = []
        for job_id, title, company, description in jobs:
            processed, sections = self._extract_text_sections(description)
            cur.execute("UPDATE jobs SET processed_description=? WHERE id=?", (processed, job_id))

            summary.append({
                "id": job_id,
                "title": title,
                "company": company,
                "sections_found": len(sections),
                "first_3_sections": sections[:3],
            })

        conn.commit()
        conn.close()

        # Build readable summary
        readable_summary = "\n\n".join([
            f"💼 {r['title']} at {r['company']} (ID {r['id']})\n"
            f"• Sections found: {r['sections_found']}\n"
            f"• Sample sections:\n  - " + "\n  - ".join(r['first_3_sections'])
            for r in summary
        ])

        return f"✅ Processed {len(summary)} job(s).\n\n🔍 Summary:\n{readable_summary}"

    # 🔹 Option 2: Single preprocessor (runtime fallback)
    @kernel_function(description="Preprocess one job if not already processed")
    async def preprocess_job(self, context, job_description: str, job_id: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ Ensure processed_description column exists
        cur.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cur.fetchall()]
        if "processed_description" not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN processed_description TEXT")

        # ✅ Skip if already processed
        cur.execute("SELECT processed_description FROM jobs WHERE id=?", (job_id,))
        existing = cur.fetchone()
        if existing and existing[0]:
            conn.close()
            return f"⚡ Job {job_id} already processed."

        processed, sections = self._extract_text_sections(job_description)
        cur.execute("UPDATE jobs SET processed_description=? WHERE id=?", (processed, job_id))
        conn.commit()
        conn.close()

        return (
            f"✅ Processed job {job_id} and saved to database.\n"
            f"• Sections found: {len(sections)}\n"
            f"• Sample sections:\n  - " + "\n  - ".join(sections[:3])
        )

    # 🧠 Shared helper (used by both)
    def _extract_text_sections(self, text: str):
        # Split into sentences or bullet points
        bullets = re.findall(r"•\s*(.+)", text)
        if not bullets:
            bullets = re.split(r"[\.\n]\s+", text.strip())
        cleaned = "\n".join(b.strip() for b in bullets if len(b.strip()) > 3)
        return cleaned, bullets
