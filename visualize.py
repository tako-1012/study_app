
import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database

def show_analysis_window(root):
    analysis_window = tk.Toplevel(root)
    analysis_window.title("Analysis")
    analysis_window.geometry("800x600")

    df = database.get_all_records()

    if df.empty:
        ttk.Label(analysis_window, text="No data to analyze.").pack(pady=20)
        return

    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Pie chart for study time per subject
    subject_summary = df.groupby('subject')['minutes'].sum()
    ax1.pie(subject_summary, labels=subject_summary.index, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Study Time by Subject')

    # Bar chart for daily study time
    date_summary = df.groupby('date')['minutes'].sum()
    date_summary.plot(kind='bar', ax=ax2)
    ax2.set_title('Daily Study Time')
    ax2.set_ylabel('Minutes')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    # Embed the plots into the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=analysis_window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Add a close button
    close_button = ttk.Button(analysis_window, text="Close", command=analysis_window.destroy)
    close_button.pack(side=tk.BOTTOM, pady=10)
