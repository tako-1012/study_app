
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import platform
from datetime import datetime, timedelta
from visualize import show_analysis_window
from goals_ui import GoalWindow
import database
import report_generator

class StudyTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Study Time Logger")
        self.root.geometry("500x450") # Adjusted for tabs

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
        self.load_todos()
        self.update_progress_display()

    def setup_styles(self):
        os_name = platform.system()
        default_font_family = "Ubuntu" if os_name == "Linux" else ("Segoe UI" if os_name == "Windows" else "San Francisco")
        self.strikethrough_font = font.Font(family=default_font_family, size=12, overstrike=True)
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

    def setup_ui(self):
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        timer_tab = ttk.Frame(notebook)
        todo_tab = ttk.Frame(notebook)

        notebook.add(timer_tab, text='Timer')
        notebook.add(todo_tab, text='ToDo List')

        self.setup_timer_tab(timer_tab)
        self.setup_todo_tab(todo_tab)

    def setup_timer_tab(self, parent_tab):
        # This method now contains all the UI elements from the previous version
        pomodoro_frame = ttk.Frame(parent_tab)
        pomodoro_frame.pack(pady=5)
        self.pomodoro_check = ttk.Checkbutton(pomodoro_frame, text="Pomodoro Mode", variable=self.pomodoro_mode, command=self.toggle_pomodoro_mode)
        self.pomodoro_check.pack(side="left", padx=5)
        self.pomodoro_status_label = ttk.Label(pomodoro_frame, text="", style="Status.TLabel")
        self.pomodoro_status_label.pack(side="left", padx=5)

        goal_frame = ttk.LabelFrame(parent_tab, text="Daily Goal Progress (All Subjects)", padding=10)
        goal_frame.pack(pady=5, padx=10, fill="x")
        self.goal_progress_label = ttk.Label(goal_frame, text="No goal set.")
        self.goal_progress_label.pack()
        self.goal_progressbar = ttk.Progressbar(goal_frame, orient="horizontal", length=300, mode="determinate", style="Goal.TProgressbar")
        self.goal_progressbar.pack(pady=5)

        self.subjects = ["Chemistry", "English", "Information", "Japanese", "Math", "Physics", "Social Studies"]
        self.selected_subject = tk.StringVar(value=self.subjects[0])
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
        self.goals_button = ttk.Button(self.bottom_button_frame, text="Goals", command=self.open_goals_window, style='TButton')
        self.report_button = ttk.Button(self.bottom_button_frame, text="Generate Report", command=self.generate_report_callback, style='TButton')
        
        self.reset_ui()

    def setup_todo_tab(self, parent_tab):
        # Input frame
        input_frame = ttk.Frame(parent_tab, padding=5)
        input_frame.pack(fill="x")
        self.todo_entry = ttk.Entry(input_frame, width=40)
        self.todo_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        add_button = ttk.Button(input_frame, text="Add Task", command=self.add_todo_callback)
        add_button.pack(side="left")

        # Treeview to display tasks
        self.todo_tree = ttk.Treeview(parent_tab, columns=("ID", "Task"), show="headings", selectmode="browse")
        self.todo_tree.heading("ID", text="ID")
        self.todo_tree.heading("Task", text="Task")
        self.todo_tree.column("ID", width=40, stretch=tk.NO)
        self.todo_tree.pack(pady=5, padx=5, fill="both", expand=True)
        self.todo_tree.tag_configure('done', font=self.strikethrough_font, foreground='gray')

        # ToDo buttons frame
        todo_button_frame = ttk.Frame(parent_tab, padding=5)
        todo_button_frame.pack(fill="x")
        toggle_done_button = ttk.Button(todo_button_frame, text="Toggle Done", command=self.toggle_todo_status_callback)
        toggle_done_button.pack(side="left", padx=5)
        delete_button = ttk.Button(todo_button_frame, text="Delete Task", command=self.delete_todo_callback)
        delete_button.pack(side="left", padx=5)

    def generate_report_callback(self):
        filename = report_generator.generate_weekly_report()
        if filename:
            messagebox.showinfo("Report Generated", f"Successfully generated report: {filename}")
        else:
            messagebox.showwarning("Report Error", "No data available for the last 7 days to generate a report.")

    # --- ToDo Methods ---
    def load_todos(self):
        for item in self.todo_tree.get_children():
            self.todo_tree.delete(item)
        df = database.get_todos()
        for index, row in df.iterrows():
            tags = ('done',) if row['is_done'] else ()
            self.todo_tree.insert("", "end", values=(row['id'], row['task']), tags=tags, iid=row['id'])

    def add_todo_callback(self):
        task = self.todo_entry.get()
        if task:
            database.add_todo(task)
            self.todo_entry.delete(0, tk.END)
            self.load_todos()
        else:
            messagebox.showwarning("Input Error", "Task cannot be empty.")

    def toggle_todo_status_callback(self):
        selected_item = self.todo_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a task to mark as done/undone.")
            return
        
        task_id = int(selected_item)
        current_tags = self.todo_tree.item(selected_item, 'tags')
        new_status = 0 if 'done' in current_tags else 1
        database.update_todo_status(task_id, new_status)
        self.load_todos()

    def delete_todo_callback(self):
        selected_item = self.todo_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a task to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected task?"):
            task_id = int(selected_item)
            database.delete_todo(task_id)
            self.load_todos()

    # ... (All other methods from the previous version are pasted here) ...
    def reset_ui(self):
        if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None
        self.timer_running = False; self.is_paused = False; self.pomodoro_state = None
        
        for widget in self.button_frame.winfo_children(): widget.pack_forget()
        for widget in self.bottom_button_frame.winfo_children(): widget.pack_forget()

        self.start_button.config(text="Start Pomodoro" if self.pomodoro_mode.get() else "Start")
        self.start_button.pack(side="left", expand=True, padx=5)
        self.goals_button.pack(side="left", expand=True, padx=5)
        self.analysis_button.pack(side="left", expand=True, padx=5)
        self.report_button.pack(side="left", expand=True, padx=5)
        
        self.subject_menu.config(state="enabled")
        self.pomodoro_check.config(state="enabled")
        self.pomodoro_status_label.config(text="")
        self.timer_label.config(text="25:00" if self.pomodoro_mode.get() else "00:00:00")
        self.update_progress_display()

    def open_goals_window(self):
        goal_window = GoalWindow(self.root, self.subjects)
        goal_window.transient(self.root)
        goal_window.wait_window()
        self.update_progress_display()

    def update_progress_display(self):
        target, progress = database.get_progress('daily', 'All')
        if target is not None:
            self.goal_progress_label.config(text=f"Daily Goal: {progress} / {target} minutes")
            self.goal_progressbar['value'] = progress
            self.goal_progressbar['maximum'] = target
        else:
            self.goal_progress_label.config(text="No daily goal set for \"All Subjects\".")
            self.goal_progressbar['value'] = 0
            self.goal_progressbar['maximum'] = 100

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
