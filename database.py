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
        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL, -- 'daily' or 'weekly'
                subject TEXT NOT NULL,   -- Specific subject or 'All'
                target_minutes INTEGER NOT NULL,
                notes TEXT,
                UNIQUE(goal_type, subject)
            )
        """)
        # Add notes column to existing goals table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE goals ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
        # ToDo table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                is_done INTEGER NOT NULL DEFAULT 0
            )
        """)
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

def get_all_records():
    """Retrieves all study records and returns them as a pandas DataFrame."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT date, subject, minutes FROM study_log", conn)
    return df

def set_goal(goal_type, subject, target_minutes, notes):
    """Creates or updates a goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (goal_type, subject, target_minutes, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(goal_type, subject) DO UPDATE SET
            target_minutes = excluded.target_minutes,
            notes = excluded.notes;
        """, (goal_type, subject, target_minutes, notes))
        conn.commit()

def get_goals():
    """Retrieves all goals."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT goal_type, subject, target_minutes, notes FROM goals", conn)
    return df

def get_progress(goal_type, subject):
    """Calculates the progress for a given goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target_minutes FROM goals WHERE goal_type=? AND subject=?", (goal_type, subject))
        result = cursor.fetchone()
        if not result:
            return None, None # No goal set

        target_minutes = result[0]
        today = datetime.now().date()

        if goal_type == 'daily':
            start_date = today
        elif goal_type == 'weekly':
            start_date = today - timedelta(days=today.weekday())
        else:
            return target_minutes, 0 # Should not happen

        query_subject = "AND subject = ?" if subject != "All" else ""
        params = [str(start_date), str(today)]
        if subject != "All":
            params.append(subject)

        cursor.execute(f"""
            SELECT SUM(minutes) FROM study_log
            WHERE date BETWEEN ? AND ? {query_subject}
        """, params)
        
        progress_minutes = cursor.fetchone()[0]
        return target_minutes, progress_minutes or 0

# --- ToDo List Functions ---

def add_todo(task):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        conn.commit()

def get_todos():
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT id, task, is_done FROM todos", conn)
    return df

def update_todo_status(task_id, is_done):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE todos SET is_done = ? WHERE id = ?", (is_done, task_id))
        conn.commit()

def delete_todo(task_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE id = ?", (task_id,))
        conn.commit()

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