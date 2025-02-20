import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def calculate_per_lap_stats(data):
    """
    Calculate statistics for each lap.
    """
    lap_stats = []
    num_laps = len(data['breakout_times'])
    
    # Assume turn_end_times is provided in the data for each lap
    turn_end_times = data.get('turn_end_times', [0] * num_laps)
    
    for lap in range(num_laps):
        breakout_time = data['breakout_times'][lap]
        breakout_distance = data['breakout_distances'][lap]
        fifteen_time = data['fifteen_times'][lap]
        
        # Calculate underwater time
        if lap == 0:
            # First lap: underwater time is from start to breakout
            underwater_time = breakout_time
        else:
            # Subsequent laps: underwater time is from turn end to breakout
            underwater_time = breakout_time - turn_end_times[lap - 1]
        
        # Calculate underwater speed
        underwater_speed = breakout_distance / underwater_time if underwater_time > 0 else 0
        
        turn_time = data['turn_times'][lap] if 'turn_times' in data else 0
        lap_stats.append({
            "Lap": lap + 1,
            "Breakout Time": round(breakout_time, 2),
            "Breakout Distance": round(breakout_distance, 2),
            "15m Time": round(fifteen_time, 2),
            "Underwater Speed": round(underwater_speed, 2),
            "Turn Time": round(turn_time, 2)
        })
    
    return pd.DataFrame(lap_stats)

def calculate_overall_stats(lap_stats):
    """
    Calculate overall statistics across all laps.
    """
    overall_stats = {
        "Average Breakout Time": round(lap_stats["Breakout Time"].mean(), 2),
        "Average Breakout Distance": round(lap_stats["Breakout Distance"].mean(), 2),
        "Average 15m Time": round(lap_stats["15m Time"].mean(), 2),
        "Average Underwater Speed": round(lap_stats["Underwater Speed"].mean(), 2),
        "Average Turn Time": round(lap_stats["Turn Time"].mean(), 2)
    }
    
    return overall_stats

def generate_pdf_report(lap_stats, overall_stats, filepath):
    """
    Generate a PDF report with lap statistics and overall statistics.
    """
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Race Statistics Report")
    
    # Lap Statistics Table
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 100, "Per Lap Statistics:")
    
    lap_data = [lap_stats.columns.tolist()] + lap_stats.values.tolist()
    table = Table(lap_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 100, height - 300)
    
    # Overall Statistics
    c.drawString(100, height - 350, "Overall Statistics:")
    y_position = height - 370
    for stat, value in overall_stats.items():
        c.drawString(100, y_position, f"{stat}: {value:.2f}")
        y_position -= 20
    
    c.save()

def run(race_details, base_directory):
    """
    Generate a report based on race details and data in the specified directory.
    """
    # Construct the file path based on race details
    filename = f"{race_details['swimmer_name'].replace(' ', '_')}_{race_details['gender'].value}_{race_details['distance'].value}_{race_details['stroke'].value}.csv"
    filepath = os.path.join(base_directory, "stroke_and_turn", race_details['session'].value, filename)
    
    if not os.path.exists(filepath):
        print(f"No data found for {filename}.")
        return
    
    # Read the data from the CSV file
    data = pd.read_csv(filepath)
    
    # Calculate statistics
    lap_stats = calculate_per_lap_stats(data)
    overall_stats = calculate_overall_stats(lap_stats)
    
    # Generate PDF report
    pdf_filepath = os.path.join(base_directory, "reports", f"{filename.replace('.csv', '.pdf')}")
    os.makedirs(os.path.dirname(pdf_filepath), exist_ok=True)
    generate_pdf_report(lap_stats, overall_stats, pdf_filepath)
    
    print(f"Report generated: {pdf_filepath}")

def main():
    # Example data
    data = {
        "breakout_times": [1.2, 1.3, 1.1],
        "breakout_distances": [5.0, 5.2, 5.1],
        "fifteen_times": [5.5, 5.6, 5.4],
        "turn_times": [0.8, 0.9, 0.85],  # Example turn times
        "turn_end_times": [0.5, 1.0, 1.5]  # Example turn end times
    }
    
    lap_stats = calculate_per_lap_stats(data)
    overall_stats = calculate_overall_stats(lap_stats)
    generate_pdf_report(lap_stats, overall_stats, "race_statistics_report.pdf")

if __name__ == "__main__":
    main() 