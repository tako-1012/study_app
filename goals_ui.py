
import tkinter as tk
from tkinter import ttk, messagebox
import database

class GoalWindow(tk.Toplevel):
    def __init__(self, parent, subjects):
        super().__init__(parent)
        self.title("Manage Goals")
        self.geometry("500x400")

        self.subjects = ["All"] + subjects

        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Goal Creation Frame ---
        create_frame = ttk.LabelFrame(main_frame, text="Set a New Goal", padding="10")
        create_frame.pack(fill="x", pady=5)

        ttk.Label(create_frame, text="Goal Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.goal_type_var = tk.StringVar(value="Daily")
        goal_type_combo = ttk.Combobox(create_frame, textvariable=self.goal_type_var, values=["Daily", "Weekly"], state="readonly")
        goal_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(create_frame, text="Subject:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.subject_var = tk.StringVar(value=self.subjects[0])
        subject_combo = ttk.Combobox(create_frame, textvariable=self.subject_var, values=self.subjects, state="readonly")
        subject_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(create_frame, text="Target (minutes):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.target_var = tk.StringVar()
        target_entry = ttk.Entry(create_frame, textvariable=self.target_var)
        target_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        set_button = ttk.Button(create_frame, text="Set Goal", command=self.set_goal_callback)
        set_button.grid(row=3, column=0, columnspan=2, pady=10)

        create_frame.columnconfigure(1, weight=1)

        # --- Existing Goals Frame ---
        list_frame = ttk.LabelFrame(main_frame, text="Current Goals", padding="10")
        list_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(list_frame, columns=("Type", "Subject", "Target"), show="headings")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Subject", text="Subject")
        self.tree.heading("Target", text="Target (mins)")
        self.tree.pack(fill="both", expand=True)

        self.load_goals()

    def set_goal_callback(self):
        goal_type = self.goal_type_var.get()
        subject = self.subject_var.get()
        target_str = self.target_var.get()

        if not target_str.isdigit():
            messagebox.showerror("Invalid Input", "Target must be a number (in minutes).")
            return

        target_minutes = int(target_str)
        database.set_goal(goal_type.lower(), subject, target_minutes)
        messagebox.showinfo("Success", "Goal has been set!")
        self.target_var.set("")
        self.load_goals()

    def load_goals(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load from database
        goals_df = database.get_goals()
        for index, row in goals_df.iterrows():
            self.tree.insert("", "end", values=(row['goal_type'].capitalize(), row['subject'], row['target_minutes']))
