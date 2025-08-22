
from fpdf import FPDF
from datetime import datetime, timedelta
import database
import matplotlib.pyplot as plt
import os
import pandas as pd

CHART_FILE = "weekly_chart.png"

def generate_weekly_report():
    """Generates a PDF report for the last 7 days of study and returns the filename."""
    
    # 1. Get Data
    today = datetime.now().date()
    last_week_start = today - timedelta(days=6)
    all_records = database.get_all_records()
    
    # Convert date column to datetime objects for filtering
    all_records['date'] = pd.to_datetime(all_records['date']).dt.date
    weekly_df = all_records[(all_records['date'] >= last_week_start) & (all_records['date'] <= today)]

    if weekly_df.empty:
        return None # No data to report

    # 2. Generate Chart
    subject_summary = weekly_df.groupby('subject')['minutes'].sum()
    fig, ax = plt.subplots()
    ax.pie(subject_summary, labels=subject_summary.index, autopct='%1.1f%%', startangle=90)
    ax.set_title('Study Time by Subject')
    plt.savefig(CHART_FILE)
    plt.close(fig)

    # 3. Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    
    # Header
    pdf.cell(0, 10, "Weekly Study Report", 0, 1, 'C')
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"{last_week_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}", 0, 1, 'C')
    pdf.ln(10)

    # Summary Section
    total_minutes = weekly_df['minutes'].sum()
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60
    target_minutes, _ = database.get_progress('weekly', 'All')

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Summary", 0, 1)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Total Study Time: {total_hours} hours, {remaining_minutes} minutes", 0, 1)
    if target_minutes:
        progress_percent = (total_minutes / target_minutes) * 100 if target_minutes > 0 else 100
        pdf.cell(0, 8, f"Weekly Goal (All Subjects): {target_minutes} minutes", 0, 1)
        pdf.cell(0, 8, f"Progress: {progress_percent:.2f}%", 0, 1)
    pdf.ln(10)

    # Chart
    pdf.image(CHART_FILE, x=pdf.get_x(), y=pdf.get_y(), w=pdf.w / 2)
    pdf.ln(pdf.w / 2 * 0.75 + 10) # Move down past the image

    # Detailed Log Table
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Detailed Log", 0, 1)
    pdf.set_font("helvetica", "B", 10)
    
    col_width = pdf.w / 3
    pdf.cell(col_width, 8, "Date", 1)
    pdf.cell(col_width, 8, "Subject", 1)
    pdf.cell(col_width, 8, "Minutes", 1)
    pdf.ln()

    pdf.set_font("helvetica", "", 10)
    for index, row in weekly_df.iterrows():
        pdf.cell(col_width, 8, str(row['date']), 1)
        pdf.cell(col_width, 8, row['subject'], 1)
        pdf.cell(col_width, 8, str(row['minutes']), 1)
        pdf.ln()

    # 4. Save PDF & Cleanup
    report_filename = f"Weekly_Report_{today.strftime('%Y-%m-%d')}.pdf"
    pdf.output(report_filename)
    os.remove(CHART_FILE)
    
    return report_filename
