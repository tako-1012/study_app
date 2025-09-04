import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_FILE = "study_log.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Study log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL
            )
        """)
        # Goals table - new schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL, -- 'daily' or 'weekly'
                subject TEXT NOT NULL,   -- Specific subject or 'All'
                start_date TEXT NOT NULL, -- Date for daily, or start of week for weekly
                target_minutes INTEGER NOT NULL,
                notes TEXT,
                UNIQUE(goal_type, subject, start_date)
            )
        """)
        try:
            cursor.execute("ALTER TABLE goals ADD COLUMN start_date TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
        # Mock Exams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subject TEXT NOT NULL,
                exam_name TEXT NOT NULL,
                score INTEGER,
                max_score INTEGER,
                deviation_value REAL
            )
        """)
        # Exam Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_exam_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                exam_name TEXT NOT NULL,
                target_score INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                notes TEXT
            )
        """)
        # Add exam_date column to existing table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE mock_exam_goals ADD COLUMN exam_date TEXT")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
        conn.commit()

def add_record(date, subject, minutes):
    """Adds a new study record to the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO study_log (date, subject, minutes) VALUES (?, ?, ?)", 
                       (date, subject, minutes))
        conn.commit()

def delete_study_record(record_id):
    """Deletes a study record."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM study_log WHERE id = ?", (record_id,))
        conn.commit()

def get_all_records():
    """Retrieves all study records and returns them as a pandas DataFrame."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT id, date, subject, minutes FROM study_log", conn)
    return df

def set_goal(goal_type, subject, start_date, target_minutes, notes):
    """Creates or updates a goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (goal_type, subject, start_date, target_minutes, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(goal_type, subject, start_date) DO UPDATE SET
            target_minutes = excluded.target_minutes,
            notes = excluded.notes;
        """, (goal_type, subject, start_date, target_minutes, notes))
        conn.commit()

def get_goals():
    """Retrieves all goals."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT id, goal_type, subject, start_date, target_minutes, notes FROM goals ORDER BY start_date DESC", conn)
    return df

def delete_study_goal(goal_id):
    """Deletes a study goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()

def get_progress(goal_type, subject, for_date):
    """Calculates the progress for a given goal for a specific date."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        if goal_type == 'daily':
            start_of_period = for_date.strftime('%Y-%m-%d')
            end_of_period = start_of_period
        elif goal_type == 'weekly':
            start_of_period_dt = for_date - timedelta(days=for_date.weekday())
            start_of_period = start_of_period_dt.strftime('%Y-%m-%d')
            end_of_period_dt = start_of_period_dt + timedelta(days=6)
            end_of_period = end_of_period_dt.strftime('%Y-%m-%d')
        else:
            return None, 0

        # Find the goal for the period
        cursor.execute("""
            SELECT target_minutes FROM goals
            WHERE goal_type=? AND subject=? AND start_date=?
        """, (goal_type, subject, start_of_period))
        result = cursor.fetchone()

        if not result:
            return None, None # No goal set

        target_minutes = result[0]

        # Calculate progress for the period
        query_subject = "AND subject = ?" if subject != "All" else ""
        params = [start_of_period, end_of_period]
        if subject != "All":
            params.append(subject)

        cursor.execute(f"""
            SELECT SUM(minutes) FROM study_log
            WHERE date BETWEEN ? AND ? {query_subject}
        """, params)
        
        progress_minutes = cursor.fetchone()[0]
        return target_minutes, progress_minutes or 0

# --- Mock Exam Functions ---

def add_mock_exam(date, subject, exam_name, score, max_score, deviation_value):
    """Adds a new mock exam record to the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Convert empty strings to None for numeric fields
        score = int(score) if score else None
        max_score = int(max_score) if max_score else None
        deviation_value = float(deviation_value) if deviation_value else None
        cursor.execute("""
            INSERT INTO mock_exams (date, subject, exam_name, score, max_score, deviation_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, subject, exam_name, score, max_score, deviation_value))
        conn.commit()

def get_mock_exams():
    """Retrieves all mock exam records and returns them as a pandas DataFrame."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT id, date, subject, exam_name, score, max_score, deviation_value FROM mock_exams ORDER BY date DESC", conn)
    return df

def delete_mock_exam(exam_id):
    """Deletes a mock exam record."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mock_exams WHERE id = ?", (exam_id,))
        conn.commit()

# --- Exam Goal Functions ---

def add_exam_goal(subject, exam_name, exam_date, target_score, notes):
    """Adds a new exam goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mock_exam_goals (subject, exam_name, exam_date, target_score, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (subject, exam_name, exam_date, target_score, notes))
        conn.commit()

def get_exam_goals():
    """Retrieves all exam goals."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT id, subject, exam_name, exam_date, target_score, status, notes FROM mock_exam_goals ORDER BY exam_date", conn)
    return df

def update_exam_goal_status(goal_id, status):
    """Updates the status of an exam goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE mock_exam_goals SET status = ? WHERE id = ?", (status, goal_id))
        conn.commit()

def delete_exam_goal(goal_id):
    """Deletes an exam goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mock_exam_goals WHERE id = ?", (goal_id,))
        conn.commit()