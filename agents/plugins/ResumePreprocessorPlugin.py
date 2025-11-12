import re
import sqlite3
from semantic_kernel.functions import kernel_function
from services.db import DB_PATH

class ResumePreprocessorPlugin:

    # 🔹 Option 1: Bulk preprocessor (run once to initialize or refresh)
    @kernel_function(description="Preprocess all resumes, save structured text, and display summary details")
    async def preprocess_all_resumes(self, context):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ Ensure processed_text column exists
        cur.execute("PRAGMA table_info(resumes)")
        columns = [col[1] for col in cur.fetchall()]
        if "processed_text" not in columns:
            cur.execute("ALTER TABLE resumes ADD COLUMN processed_text TEXT")

        # ✅ Fetch all unprocessed resumes
        cur.execute("SELECT id, name, text FROM resumes WHERE processed_text IS NULL OR processed_text=''")
        resumes = cur.fetchall()

        if not resumes:
            conn.close()
            return "✅ All resumes are already processed."

        summary = []
        for resume_id, name, text in resumes:
            processed, bullets = self._extract_text_sections(text)
            cur.execute("UPDATE resumes SET processed_text=? WHERE id=?", (processed, resume_id))

            # Collect diagnostics
            summary.append({
                "id": resume_id,
                "name": name,
                "total_lines": len(text.splitlines()),
                "sections_found": len(bullets),
                "first_3_sections": bullets[:3],
            })

        conn.commit()
        conn.close()

        # Build readable summary
        readable_summary = "\n\n".join([
            f"📄 {r['name']} (ID {r['id']})\n"
            f"• Total lines: {r['total_lines']}\n"
            f"• Sections found: {r['sections_found']}\n"
            f"• Sample sections:\n  - " + "\n  - ".join(r['first_3_sections'])
            for r in summary
        ])

        return f"✅ Processed {len(summary)} resume(s).\n\n🔍 Summary:\n{readable_summary}"

    # 🔹 Option 2: Single preprocessor (runtime fallback)
    @kernel_function(description="Preprocess a single resume if not already processed")
    async def preprocess_resume(self, context, resume_text: str, resume_id: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ Ensure processed_text column exists
        cur.execute("PRAGMA table_info(resumes)")
        columns = [col[1] for col in cur.fetchall()]
        if "processed_text" not in columns:
            cur.execute("ALTER TABLE resumes ADD COLUMN processed_text TEXT")

        # ✅ Check if it's already processed
        cur.execute("SELECT processed_text FROM resumes WHERE id=?", (resume_id,))
        existing = cur.fetchone()
        if existing and existing[0]:
            conn.close()
            return f"⚡ Résumé {resume_id} already processed."

        processed, bullets = self._extract_text_sections(resume_text)
        cur.execute("UPDATE resumes SET processed_text=? WHERE id=?", (processed, resume_id))
        conn.commit()
        conn.close()

        return (
            f"✅ Processed résumé {resume_id} and saved to database.\n"
            f"• Sections found: {len(bullets)}\n"
            f"• Sample sections:\n  - " + "\n  - ".join(bullets[:3])
        )

    # 🧠 Shared helper for both methods
    def _extract_text_sections(self, text: str):
        # Try bullet format first
        bullets = re.findall(r"•\s*(.+)", text)
        if not bullets:
            # Fallback to splitting by sentence
            bullets = re.split(r"\.\s+", text.strip())
        cleaned = "\n".join(b.strip() for b in bullets if len(b.strip()) > 3)
        return cleaned, bullets
