"""
Migration script to add job_fit_score column to existing resumes table.
Run this once to update your existing database.
"""

import sqlite3
import os

# Get database path
DB_NAME = os.path.join(os.path.dirname(__file__), "database.db")

def migrate():
    """Add job_fit_score column to resumes table if it doesn't exist"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("PRAGMA table_info(resumes)")
        columns = [column[1] for column in cur.fetchall()]
        
        if 'job_fit_score' not in columns:
            print("Adding job_fit_score column to resumes table...")
            
            # Add the column with default value 0
            cur.execute("""
                ALTER TABLE resumes
                ADD COLUMN job_fit_score INTEGER DEFAULT 0
            """)
            
            conn.commit()
            print("✅ Migration successful! job_fit_score column added.")
        else:
            print("✅ job_fit_score column already exists. No migration needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    print("Starting database migration...")
    migrate()
    print("Migration complete!")
