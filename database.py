
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
                UNIQUE(goal_type, subject)
            )
        """)
        # ToDo table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                is_done INTEGER NOT NULL DEFAULT 0
            )
        """)
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

def set_goal(goal_type, subject, target_minutes):
    """Creates or updates a goal."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (goal_type, subject, target_minutes)
            VALUES (?, ?, ?)
            ON CONFLICT(goal_type, subject) DO UPDATE SET
            target_minutes = excluded.target_minutes;
        """, (goal_type, subject, target_minutes))
        conn.commit()

def get_goals():
    """Retrieves all goals."""
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT goal_type, subject, target_minutes FROM goals", conn)
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

