import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import platform
from datetime import datetime, timedelta
from visualize import show_analysis_window
import database
import report_generator
import pandas as pd
try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

class StudyTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Study Time Logger")
        self.root.geometry("1000x800") # Larger size to show all UI elements

        database.init_db()

        # --- State Variables ---
        self.timer_running = False
        self.is_paused = False
        self.start_time = None
        self.elapsed_time = timedelta(0)
        self.after_id = None

        # --- Pomodoro State ---
        self.pomodoro_mode = tk.BooleanVar()
        self.pomodoro_state = None
        self.pomodoro_cycles = 0

        # --- UI Setup ---
        self.setup_styles()
        self.setup_ui()
        self.load_mock_exams()
        self.load_exam_goals()
        self.load_study_goals()
        self.load_study_history()
        self.update_progress_display()

    def setup_styles(self):
        os_name = platform.system()
        default_font_family = "Ubuntu" if os_name == "Linux" else ("Segoe UI" if os_name == "Windows" else "San Francisco")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=(default_font_family, 12))
        style.configure('TButton', font=(default_font_family, 12, 'bold'))
        style.configure('TLabel', font=(default_font_family, 12))
        style.configure('Status.TLabel', font=(default_font_family, 14, 'italic'))
        style.configure('Timer.TLabel', font=(default_font_family, 48))
        style.layout("Goal.TProgressbar",
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        style.configure("Goal.TProgressbar", thickness=20, background='green')
        style.configure("Treeview.Heading", font=(default_font_family, 12, 'bold'))
        style.configure("Achieved.TLabel", foreground="green")
        style.configure("NotAchieved.TLabel", foreground="red")

    def setup_ui(self):
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        timer_tab = ttk.Frame(notebook)
        study_history_tab = ttk.Frame(notebook)
        study_goals_tab = ttk.Frame(notebook)
        exam_goals_tab = ttk.Frame(notebook)
        mock_exam_tab = ttk.Frame(notebook)

        notebook.add(timer_tab, text='Timer')
        notebook.add(study_history_tab, text='Study History')
        notebook.add(study_goals_tab, text='Study Goals')
        notebook.add(exam_goals_tab, text='Exam Goals')
        notebook.add(mock_exam_tab, text='Mock Exams')

        self.setup_timer_tab(timer_tab)
        self.setup_study_history_tab(study_history_tab)
        self.setup_study_goals_tab(study_goals_tab)
        self.setup_exam_goals_tab(exam_goals_tab)
        self.setup_mock_exam_tab(mock_exam_tab)

    def setup_timer_tab(self, parent_tab):
        # This method now contains all the UI elements from the previous version
        pomodoro_frame = ttk.Frame(parent_tab)
        pomodoro_frame.pack(pady=5)
        self.pomodoro_check = ttk.Checkbutton(pomodoro_frame, text="Pomodoro Mode", variable=self.pomodoro_mode, command=self.toggle_pomodoro_mode)
        self.pomodoro_check.pack(side="left", padx=5)
        self.pomodoro_status_label = ttk.Label(pomodoro_frame, text="", style="Status.TLabel")
        self.pomodoro_status_label.pack(side="left", padx=5)

        self.goal_frame = ttk.LabelFrame(parent_tab, text="Daily Goal Progress", padding=10)
        self.goal_frame.pack(pady=5, padx=10, fill="x")
        self.goal_progress_label = ttk.Label(self.goal_frame, text="No goal set.")
        self.goal_progress_label.pack()
        self.goal_progressbar = ttk.Progressbar(self.goal_frame, orient="horizontal", length=300, mode="determinate", style="Goal.TProgressbar")
        self.goal_progressbar.pack(pady=5)

        self.subjects = ["Chemistry", "English", "Information", "Japanese", "Math", "Physics", "Social Studies"]
        self.selected_subject = tk.StringVar(value=self.subjects[0])
        self.selected_subject.trace_add("write", self.on_subject_change)
        self.subject_menu = ttk.OptionMenu(parent_tab, self.selected_subject, self.subjects[0], *self.subjects)
        self.subject_menu.pack(pady=5)

        self.timer_label = ttk.Label(parent_tab, text="00:00:00", style='Timer.TLabel', anchor="center")
        self.timer_label.pack(pady=10, fill="x")

        self.button_frame = ttk.Frame(parent_tab)
        self.button_frame.pack(pady=5)
        self.bottom_button_frame = ttk.Frame(parent_tab)
        self.bottom_button_frame.pack(pady=5)

        self.start_button = ttk.Button(self.button_frame, text="Start", command=self.start_timer, style='TButton')
        self.pause_button = ttk.Button(self.button_frame, text="Pause", command=self.pause_timer, style='TButton')
        self.resume_button = ttk.Button(self.button_frame, text="Resume", command=self.resume_timer, style='TButton')
        self.stop_button = ttk.Button(self.button_frame, text="Stop", command=self.stop_and_reset_all, style='TButton')
        self.save_button = ttk.Button(self.button_frame, text="Save", command=self.save_and_reset, style='TButton')
        self.discard_button = ttk.Button(self.button_frame, text="Discard", command=self.discard_and_reset, style='TButton')
        self.analysis_button = ttk.Button(self.bottom_button_frame, text="Analysis", command=self.open_analysis_window, style='TButton')
        self.report_button = ttk.Button(self.bottom_button_frame, text="Generate Report", command=self.generate_report_callback, style='TButton')
        
        self.reset_ui()

    def setup_study_goals_tab(self, parent_tab):
        # Main frame for this tab with vertical layout
        main_frame = ttk.Frame(parent_tab)
        main_frame.pack(fill="both", expand=True)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(main_frame, text="Set Study Time Goal", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")
        input_frame.columnconfigure(1, weight=1)

        # Goal Type
        self.study_goal_type = tk.StringVar(value="daily")
        ttk.Label(input_frame, text="Goal Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        goal_type_frame = ttk.Frame(input_frame)
        goal_type_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        daily_radio = ttk.Radiobutton(goal_type_frame, text="Daily", variable=self.study_goal_type, value="daily")
        daily_radio.pack(side="left", padx=(0, 10))
        weekly_radio = ttk.Radiobutton(goal_type_frame, text="Weekly", variable=self.study_goal_type, value="weekly")
        weekly_radio.pack(side="left")

        # Subject
        all_subjects = ["All"] + self.subjects
        self.study_goal_subject = tk.StringVar(value=all_subjects[0])
        ttk.Label(input_frame, text="Subject:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        subject_menu = ttk.OptionMenu(input_frame, self.study_goal_subject, all_subjects[0], *all_subjects)
        subject_menu.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Target Minutes
        ttk.Label(input_frame, text="Target (minutes):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.study_goal_minutes_entry = ttk.Entry(input_frame)
        self.study_goal_minutes_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Notes
        ttk.Label(input_frame, text="Notes:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.study_goal_notes_entry = ttk.Entry(input_frame)
        self.study_goal_notes_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        save_button = ttk.Button(input_frame, text="Set Goal", command=self.set_study_goal_callback)
        save_button.grid(row=4, column=0, columnspan=2, pady=10)

        # --- Treeview Frame ---
        tree_frame = ttk.LabelFrame(main_frame, text="Current Study Goals", padding=10)
        tree_frame.pack(pady=(0, 10), padx=10, fill="both", expand=True)

        self.study_goals_tree = ttk.Treeview(tree_frame, columns=("ID", "Type", "Subject", "Target", "Notes"), show="headings")
        self.study_goals_tree.heading("ID", text="ID")
        self.study_goals_tree.column("ID", width=0, stretch=tk.NO)
        self.study_goals_tree.heading("Type", text="Type")
        self.study_goals_tree.heading("Subject", text="Subject")
        self.study_goals_tree.heading("Target", text="Target (mins)")
        self.study_goals_tree.heading("Notes", text="Notes")
        self.study_goals_tree.column("Notes", width=250)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.study_goals_tree.yview)
        self.study_goals_tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.study_goals_tree.pack(side="left", fill="both", expand=True)

        # --- Buttons Frame ---
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=(0, 10), padx=10, fill="x")
        delete_button = ttk.Button(buttons_frame, text="Delete Goal", command=self.delete_study_goal_callback)
        delete_button.pack(side="right", padx=5)

    def setup_exam_goals_tab(self, parent_tab):
        # Main frame for this tab with vertical layout
        main_frame = ttk.Frame(parent_tab)
        main_frame.pack(fill="both", expand=True)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(main_frame, text="Set New Exam Goal", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Subject:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.goal_subject_var = tk.StringVar(value=self.subjects[0])
        self.goal_subject_menu = ttk.OptionMenu(input_frame, self.goal_subject_var, self.subjects[0], *self.subjects)
        self.goal_subject_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Exam Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.goal_exam_name_entry = ttk.Entry(input_frame)
        self.goal_exam_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Exam Date:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        if CALENDAR_AVAILABLE:
            self.goal_exam_date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                                 foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        else:
            self.goal_exam_date_entry = ttk.Entry(input_frame)
            self.goal_exam_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.goal_exam_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Target Score:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_score_entry = ttk.Entry(input_frame)
        self.goal_target_score_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Notes:").grid(row=4, column=0, padx=5, pady=5, sticky="nw")
        self.goal_notes_text = tk.Text(input_frame, height=3, width=40)
        self.goal_notes_text.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        save_button = ttk.Button(input_frame, text="Save Goal", command=self.add_exam_goal_callback)
        save_button.grid(row=5, column=0, columnspan=2, pady=10)

        # --- Treeview Frame ---
        tree_frame = ttk.LabelFrame(main_frame, text="Active Goals", padding=10)
        tree_frame.pack(pady=(0, 10), padx=10, fill="both", expand=True)

        self.goal_tree = ttk.Treeview(tree_frame, columns=("ID", "Date", "Subject", "Exam Name", "Target", "Status", "Notes"), show="headings")
        self.goal_tree.heading("ID", text="ID")
        self.goal_tree.heading("Date", text="Date")
        self.goal_tree.heading("Subject", text="Subject")
        self.goal_tree.heading("Exam Name", text="Exam Name")
        self.goal_tree.heading("Target", text="Target")
        self.goal_tree.heading("Status", text="Status")
        self.goal_tree.heading("Notes", text="Notes")

        self.goal_tree.column("ID", width=30, stretch=tk.NO)
        self.goal_tree.column("Date", width=100)
        self.goal_tree.column("Subject", width=120)
        self.goal_tree.column("Exam Name", width=150)
        self.goal_tree.column("Target", width=80, anchor="center")
        self.goal_tree.column("Status", width=100, anchor="center")
        self.goal_tree.column("Notes", width=150)

        self.goal_tree.tag_configure('Achieved', background='#d9ead3')
        self.goal_tree.tag_configure('Not Achieved', background='#f4cccc')

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.goal_tree.yview)
        self.goal_tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.goal_tree.pack(side="left", fill="both", expand=True)

        # --- Buttons Frame ---
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=(0, 10), padx=10, fill="x")

        achieved_button = ttk.Button(buttons_frame, text="Mark as Achieved", command=lambda: self.update_goal_status_callback("Achieved"))
        achieved_button.pack(side="left", padx=5)

        not_achieved_button = ttk.Button(buttons_frame, text="Mark as Not Achieved", command=lambda: self.update_goal_status_callback("Not Achieved"))
        not_achieved_button.pack(side="left", padx=5)

        delete_button = ttk.Button(buttons_frame, text="Delete Goal", command=self.delete_exam_goal_callback)
        delete_button.pack(side="right", padx=5)

    def setup_mock_exam_tab(self, parent_tab):
        # Input frame
        input_frame = ttk.LabelFrame(parent_tab, text="Enter Mock Exam Result", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")

        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

        ttk.Label(input_frame, text="Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        if CALENDAR_AVAILABLE:
            self.mock_date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                           foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        else:
            self.mock_date_entry = ttk.Entry(input_frame)
            self.mock_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.mock_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Subject:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.mock_selected_subject = tk.StringVar(value=self.subjects[0])
        self.mock_subject_menu = ttk.OptionMenu(input_frame, self.mock_selected_subject, self.subjects[0], *self.subjects)
        self.mock_subject_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Exam Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mock_exam_name_entry = ttk.Entry(input_frame)
        self.mock_exam_name_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Score:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.mock_score_entry = ttk.Entry(input_frame)
        self.mock_score_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Max Score:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.mock_max_score_entry = ttk.Entry(input_frame)
        self.mock_max_score_entry.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Deviation:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.mock_deviation_entry = ttk.Entry(input_frame)
        self.mock_deviation_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        save_button = ttk.Button(input_frame, text="Save Result", command=self.add_mock_exam_callback)
        save_button.grid(row=4, column=0, columnspan=4, pady=10)

        tree_frame = ttk.Frame(parent_tab)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        self.mock_tree = ttk.Treeview(tree_frame, columns=("ID", "Date", "Subject", "Exam Name", "Score", "Max Score", "Deviation"), show="headings")
        self.mock_tree.heading("ID", text="ID")
        self.mock_tree.heading("Date", text="Date")
        self.mock_tree.heading("Subject", text="Subject")
        self.mock_tree.heading("Exam Name", text="Exam Name")
        self.mock_tree.heading("Score", text="Score")
        self.mock_tree.heading("Max Score", text="Max Score")
        self.mock_tree.heading("Deviation", text="Deviation")

        self.mock_tree.column("ID", width=40, stretch=tk.NO)
        self.mock_tree.column("Date", width=100)
        self.mock_tree.column("Subject", width=100)
        self.mock_tree.column("Exam Name", width=150)
        self.mock_tree.column("Score", width=80)
        self.mock_tree.column("Max Score", width=80)
        self.mock_tree.column("Deviation", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.mock_tree.yview)
        self.mock_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.mock_tree.pack(side="left", fill="both", expand=True)

        buttons_frame = ttk.Frame(parent_tab)
        buttons_frame.pack(pady=5, padx=10, fill="x")
        delete_button = ttk.Button(buttons_frame, text="Delete Result", command=self.delete_mock_exam_callback)
        delete_button.pack(side="right", padx=5)

    def setup_study_history_tab(self, parent_tab):
        tree_frame = ttk.Frame(parent_tab)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.study_history_tree = ttk.Treeview(tree_frame, columns=("ID", "Date", "Subject", "Minutes"), show="headings")
        self.study_history_tree.heading("ID", text="ID")
        self.study_history_tree.column("ID", width=40, stretch=tk.NO)
        self.study_history_tree.heading("Date", text="Date")
        self.study_history_tree.column("Date", width=100)
        self.study_history_tree.heading("Subject", text="Subject")
        self.study_history_tree.column("Subject", width=150)
        self.study_history_tree.heading("Minutes", text="Minutes")
        self.study_history_tree.column("Minutes", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.study_history_tree.yview)
        self.study_history_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.study_history_tree.pack(side="left", fill="both", expand=True)

        buttons_frame = ttk.Frame(parent_tab)
        buttons_frame.pack(pady=5, padx=10, fill="x")
        delete_button = ttk.Button(buttons_frame, text="Delete Record", command=self.delete_study_history_callback)
        delete_button.pack(side="right", padx=5)

    def generate_report_callback(self):
        filename = report_generator.generate_weekly_report()
        if filename:
            messagebox.showinfo("Report Generated", f"Successfully generated report: {filename}")
        else:
            messagebox.showwarning("Report Error", "No data available for the last 7 days to generate a report.")

    # --- Mock Exam Methods ---
    def load_mock_exams(self):
        for item in self.mock_tree.get_children():
            self.mock_tree.delete(item)
        df = database.get_mock_exams()
        for index, row in df.iterrows():
            values = (
                row['id'],
                row['date'],
                row['subject'],
                row['exam_name'],
                '' if pd.isna(row['score']) else int(row['score']),
                '' if pd.isna(row['max_score']) else int(row['max_score']),
                '' if pd.isna(row['deviation_value']) else row['deviation_value']
            )
            self.mock_tree.insert("", "end", values=values, iid=row['id'])

    def add_mock_exam_callback(self):
        if CALENDAR_AVAILABLE and hasattr(self.mock_date_entry, 'get_date'):
            date = self.mock_date_entry.get_date().strftime('%Y-%m-%d')
        else:
            date = self.mock_date_entry.get()
        subject = self.mock_selected_subject.get()
        exam_name = self.mock_exam_name_entry.get()
        score = self.mock_score_entry.get()
        max_score = self.mock_max_score_entry.get()
        deviation = self.mock_deviation_entry.get()

        if not date or not subject or not exam_name:
            messagebox.showwarning("Input Error", "Date, Subject, and Exam Name are required.")
            return

        try:
            if score and not score.isdigit(): raise ValueError("Score must be a number.")
            if max_score and not max_score.isdigit(): raise ValueError("Max Score must be a number.")
            if deviation: float(deviation)
        except ValueError as e:
            messagebox.showwarning("Input Error", str(e))
            return

        database.add_mock_exam(date, subject, exam_name, score, max_score, deviation)
        
        self.mock_exam_name_entry.delete(0, tk.END)
        self.mock_score_entry.delete(0, tk.END)
        self.mock_max_score_entry.delete(0, tk.END)
        self.mock_deviation_entry.delete(0, tk.END)
        
        self.load_mock_exams()
        messagebox.showinfo("Success", "Mock exam result saved successfully.")

    def delete_mock_exam_callback(self):
        selected_item = self.mock_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a result to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected result?"):
            exam_id = int(selected_item)
            database.delete_mock_exam(exam_id)
            self.load_mock_exams()

    # --- Study History Methods ---
    def load_study_history(self):
        for item in self.study_history_tree.get_children():
            self.study_history_tree.delete(item)
        df = database.get_all_records()
        for index, row in df.iterrows():
            self.study_history_tree.insert("", "end", values=(row['id'], row['date'], row['subject'], row['minutes']), iid=row['id'])

    def delete_study_history_callback(self):
        selected_item = self.study_history_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a record to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected record?"):
            record_id = int(selected_item)
            database.delete_study_record(record_id)
            self.load_study_history()
            self.update_progress_display()

    # --- Exam Goal Methods ---
    def load_exam_goals(self):
        for item in self.goal_tree.get_children():
            self.goal_tree.delete(item)
        df = database.get_exam_goals()
        for index, row in df.iterrows():
            tags = (row['status'].replace(' ', ''),) # Create a tag from the status
            self.goal_tree.insert("", "end", values=(row['id'], row['exam_date'], row['subject'], row['exam_name'], row['target_score'], row['status'], row['notes']), iid=row['id'], tags=tags)

    def add_exam_goal_callback(self):
        subject = self.goal_subject_var.get()
        exam_name = self.goal_exam_name_entry.get()
        if CALENDAR_AVAILABLE and hasattr(self.goal_exam_date_entry, 'get_date'):
            exam_date = self.goal_exam_date_entry.get_date().strftime('%Y-%m-%d')
        else:
            exam_date = self.goal_exam_date_entry.get()
        target_score = self.goal_target_score_entry.get()
        notes = self.goal_notes_text.get("1.0", tk.END).strip()

        if not subject or not exam_name or not target_score:
            messagebox.showwarning("Input Error", "Subject, Exam Name, and Target Score are required.")
            return

        try:
            if not target_score.isdigit(): raise ValueError("Target Score must be a number.")
        except ValueError as e:
            messagebox.showwarning("Input Error", str(e))
            return

        database.add_exam_goal(subject, exam_name, exam_date, int(target_score), notes)

        self.goal_exam_name_entry.delete(0, tk.END)
        self.goal_exam_date_entry.delete(0, tk.END)
        self.goal_target_score_entry.delete(0, tk.END)
        self.goal_notes_text.delete("1.0", tk.END)

        self.load_exam_goals()
        messagebox.showinfo("Success", "Exam goal saved successfully.")

    def update_goal_status_callback(self, status):
        selected_item = self.goal_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to update.")
            return
        
        goal_id = int(selected_item)
        database.update_exam_goal_status(goal_id, status)
        self.load_exam_goals()

    def delete_exam_goal_callback(self):
        selected_item = self.goal_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected goal?"):
            goal_id = int(selected_item)
            database.delete_exam_goal(goal_id)
            self.load_exam_goals()

    # --- Study Goal Methods ---
    def load_study_goals(self):
        for item in self.study_goals_tree.get_children():
            self.study_goals_tree.delete(item)
        df = database.get_goals()
        for index, row in df.iterrows():
            self.study_goals_tree.insert("", "end", values=(row['id'], row['goal_type'].capitalize(), row['subject'], row['target_minutes'], row['notes']), iid=row['id'])

    def set_study_goal_callback(self):
        goal_type = self.study_goal_type.get()
        subject = self.study_goal_subject.get()
        minutes_str = self.study_goal_minutes_entry.get()
        notes = self.study_goal_notes_entry.get()

        if not minutes_str:
            messagebox.showwarning("Input Error", "Target minutes cannot be empty.")
            return
        try:
            minutes = int(minutes_str)
            if minutes <= 0:
                raise ValueError("Minutes must be a positive number.")
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid positive number for minutes.")
            return

        today = datetime.now().date()
        if goal_type == 'daily':
            start_date = today.strftime('%Y-%m-%d')
        else: # weekly
            start_date = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')

        database.set_goal(goal_type, subject, start_date, minutes, notes)
        self.study_goal_minutes_entry.delete(0, tk.END)
        self.study_goal_notes_entry.delete(0, tk.END)
        self.load_study_goals()
        self.update_progress_display()
        messagebox.showinfo("Success", "Study goal has been set successfully.")

    def delete_study_goal_callback(self):
        selected_item = self.study_goals_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected goal?"):
            goal_id = int(selected_item)
            database.delete_study_goal(goal_id)
            self.load_study_goals()
            self.update_progress_display()

    def on_subject_change(self, *args):
        self.update_progress_display()

    def reset_ui(self):
        if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None
        self.timer_running = False; self.is_paused = False; self.pomodoro_state = None
        
        for widget in self.button_frame.winfo_children(): widget.pack_forget()
        for widget in self.bottom_button_frame.winfo_children(): widget.pack_forget()

        self.start_button.config(text="Start Pomodoro" if self.pomodoro_mode.get() else "Start")
        self.start_button.pack(side="left", expand=True, padx=5)
        self.analysis_button.pack(side="left", expand=True, padx=5)
        self.report_button.pack(side="left", expand=True, padx=5)
        
        self.subject_menu.config(state="enabled")
        self.pomodoro_check.config(state="enabled")
        self.pomodoro_status_label.config(text="")
        self.timer_label.config(text="25:00" if self.pomodoro_mode.get() else "00:00:00")
        self.update_progress_display()

    def update_progress_display(self):
        subject = self.selected_subject.get()
        self.goal_frame.config(text=f"Daily Goal Progress ({subject})")
        today = datetime.now().date()
        target, progress = database.get_progress('daily', subject, today)

        if target is None:
            # Fallback to checking for an "All" subjects goal
            target, progress = database.get_progress('daily', 'All', today)
            if target is not None:
                self.goal_frame.config(text="Daily Goal Progress (All Subjects)")
            else:
                self.goal_progress_label.config(text=f'No daily goal set for "{subject}" or "All".')
                self.goal_progressbar['value'] = 0
                self.goal_progressbar['maximum'] = 100
                return

        self.goal_progress_label.config(text=f"Daily Goal: {progress} / {target} minutes")
        self.goal_progressbar['value'] = progress
        self.goal_progressbar['maximum'] = target

    def save_record(self, duration):
        minutes = int(duration.total_seconds() // 60)
        if minutes == 0:
            print("Study time was less than a minute, so it was not recorded.")
            return
        today_date = datetime.now().strftime('%Y-%m-%d')
        subject = self.selected_subject.get()
        database.add_record(today_date, subject, minutes)
        print(f"Record saved: {subject} - {minutes} minutes")
        self.update_progress_display()
        self.load_study_history()

    def toggle_pomodoro_mode(self):
        self.reset_ui()

    def start_timer(self):
        if self.pomodoro_mode.get():
            self.pomodoro_cycles = 0
            self.start_pomodoro_work_session()
        else:
            self.start_normal_timer()

    def start_normal_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.is_paused = False
            self.start_time = datetime.now()
            self.elapsed_time = timedelta(0)
            self.update_normal_timer()
            self.update_ui_for_running_timer()

    def update_normal_timer(self):
        if self.timer_running and not self.is_paused:
            current_elapsed = self.elapsed_time + (datetime.now() - self.start_time)
            formatted_time = str(current_elapsed).split('.')[0]
            self.timer_label.config(text=formatted_time)
            self.after_id = self.root.after(1000, self.update_normal_timer)

    def start_pomodoro_work_session(self):
        self.pomodoro_state = "Work"
        self.pomodoro_status_label.config(text=f"Work ({self.pomodoro_cycles + 1}/4)")
        self.run_pomodoro_timer(25 * 60)

    def start_pomodoro_break(self):
        self.pomodoro_cycles += 1
        if self.pomodoro_cycles % 4 == 0:
            self.pomodoro_state = "Long Break"
            self.pomodoro_status_label.config(text="Long Break")
            self.run_pomodoro_timer(15 * 60)
        else:
            self.pomodoro_state = "Short Break"
            self.pomodoro_status_label.config(text=f"Short Break ({self.pomodoro_cycles}/4)")
            self.run_pomodoro_timer(5 * 60)

    def run_pomodoro_timer(self, duration_seconds):
        self.timer_running = True
        self.end_time = datetime.now() + timedelta(seconds=duration_seconds)
        self.update_pomodoro_timer()
        self.update_ui_for_running_timer()

    def update_pomodoro_timer(self):
        if not self.timer_running: return
        remaining = self.end_time - datetime.now()
        if remaining.total_seconds() < 0:
            self.root.bell()
            if self.pomodoro_state == "Work":
                self.save_pomodoro_record()
                self.start_pomodoro_break()
            else: self.reset_ui()
            return
        formatted_time = f"{int(remaining.total_seconds() // 60):02d}:{int(remaining.total_seconds() % 60):02d}"
        self.timer_label.config(text=formatted_time)
        self.after_id = self.root.after(1000, self.update_pomodoro_timer)

    def pause_timer(self):
        if self.timer_running and not self.is_paused:
            self.is_paused = True; self.timer_running = False
            self.elapsed_time += datetime.now() - self.start_time
            if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None
            self.update_ui_for_paused_timer()

    def resume_timer(self):
        if not self.timer_running and self.is_paused:
            self.is_paused = False; self.timer_running = True
            self.start_time = datetime.now()
            self.update_normal_timer()
            self.update_ui_for_running_timer(is_resume=True)

    def stop_and_reset_all(self):
        if self.pomodoro_mode.get(): self.reset_ui()
        else:
            if self.timer_running or self.is_paused:
                self.timer_running = False
                if not self.is_paused: self.elapsed_time += datetime.now() - self.start_time
                if self.after_id: self.root.after_cancel(self.after_id)
                self.update_ui_for_stopped_timer()

    def save_and_reset(self):
        self.save_record(self.elapsed_time)
        self.reset_ui()

    def discard_and_reset(self):
        self.reset_ui()

    def save_pomodoro_record(self):
        self.save_record(timedelta(minutes=25))

    def update_ui_for_running_timer(self, is_resume=False):
        if not is_resume: self.start_button.pack_forget(); self.bottom_button_frame.pack_forget()
        self.resume_button.pack_forget()
        self.subject_menu.config(state="disabled")
        self.pomodoro_check.config(state="disabled")
        if not self.pomodoro_mode.get(): self.pause_button.pack(side="left", expand=True, padx=5)
        self.stop_button.pack(side="left", expand=True, padx=5)

    def update_ui_for_paused_timer(self):
        self.pause_button.pack_forget()
        self.resume_button.pack(side="left", expand=True, padx=5)

    def update_ui_for_stopped_timer(self):
        self.pause_button.pack_forget(); self.resume_button.pack_forget(); self.stop_button.pack_forget()
        self.save_button.pack(side="left", expand=True, padx=5)
        self.discard_button.pack(side="left", expand=True, padx=5)

    def open_analysis_window(self):
        show_analysis_window(self.root)


if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimerApp(root)
    root.mainloop()
