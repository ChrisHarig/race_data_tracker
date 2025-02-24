import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, PageBreak, Spacer

def calculate_per_lap_stats(data, race_details):
    """
    Calculate statistics for each lap from the event data and breakout/fifteen data.
    """
    stroke = race_details['stroke']
    distance = race_details['distance']
    lap_stats = []
    
    # Get the events from stroke_and_turn data
    events = data.get('events', [])  # List of {type, time} dictionaries
    
    # Get breakout/fifteen data if available
    breakout_data = data.get('breakout_times', None)
    breakout_distances = data.get('breakout_distances', None)
    fifteen_times = data.get('fifteen_times', None)
    
    # Find all turn_end events to determine laps (these mark the end of each lap)
    lap_markers = [0.0]  # Start with 0 for first lap
    
    if stroke in ["breaststroke", "butterfly"]:
        # For breast/fly, use turn_start events
        lap_markers.extend([e['time'] for e in events if e['type'] == 'turn_start'])
    elif stroke == "im":
        # For IM, pattern depends on distance
        if distance == "200":
            # 200 IM: turn_start (fly, back) -> turn_end (breast) -> turn_start (free)
            turn_events = [(e['time'], e['type']) for e in events if e['type'] in ['turn_start', 'turn_end']]
            turn_events.sort(key=lambda x: x[0])  # Sort by time
            
            # First 2 turns (fly, back) - turn_start
            lap_markers.extend([t[0] for t in turn_events[:2] if t[1] == 'turn_start'])
            # Next turn (breast) - turn_end 
            lap_markers.extend([t[0] for t in turn_events[2:3] if t[1] == 'turn_end'])
            # Next 3 turns (free) - turn_start
            lap_markers.extend([t[0] for t in turn_events[3:6] if t[1] == 'turn_start'])
            # Final turn - turn_end
            lap_markers.extend([t[0] for t in turn_events[6:7] if t[1] == 'turn_end'])
        
        elif distance == "400":
            # 400 IM: turn_start (fly) -> turn_end (back) (crossover turn)-> turn_start (breast) -> turn_end (free)
            turn_events = [(e['time'], e['type']) for e in events if e['type'] in ['turn_start', 'turn_end']]
            turn_events.sort(key=lambda x: x[0])
            
            # First 4 turns (fly) - turn_start
            lap_markers.extend([t[0] for t in turn_events[:4] if t[1] == 'turn_start'])
            # Next 3 turns (back) - turn_end
            lap_markers.extend([t[0] for t in turn_events[4:7] if t[1] == 'turn_end'])
            # Next 5 turns (breast) - turn_start
            lap_markers.extend([t[0] for t in turn_events[7:12] if t[1] == 'turn_start'])
            # Last 3 turns (free) - turn_end
            lap_markers.extend([t[0] for t in turn_events[12:] if t[1] == 'turn_end'])
    else:
        # For freestyle and backstroke, use turn_end events
        lap_markers.extend([e['time'] for e in events if e['type'] == 'turn_end'])
    
    # Add the final time
    lap_markers.append([e['time'] for e in events if e['type'] == 'end'][0])
    
    num_laps = len(lap_markers) - 1  # Number of laps is one less than number of markers
    
    for lap in range(num_laps):
        lap_stat = {"Lap": lap + 1}
        
        # Calculate lap time (time between markers)
        lap_start = lap_markers[lap]
        lap_end = lap_markers[lap + 1]
        lap_stat["Lap Time"] = round(lap_end - lap_start, 2)
        
        # Get all strokes and turns in this lap
        lap_strokes = [e for e in events 
                      if e['type'] == 'stroke' 
                      and lap_start <= e['time'] <= lap_end]
        lap_turns = [e for e in events 
                    if e['type'].startswith('turn_') 
                    and lap_start <= e['time'] <= lap_end]
        
        # Calculate stroke to wall time (from last stroke to next turn event)
        if lap_strokes:
            last_stroke = max(s['time'] for s in lap_strokes)
            next_turn = min((t['time'] for t in lap_turns if t['time'] > last_stroke), default=lap_end)
            lap_stat["Stroke to Wall"] = round(next_turn - last_stroke, 2)
        
        # Calculate turn time only if we have both start and end
        turn_start = next((t for t in lap_turns if t['type'] == 'turn_start'), None)
        turn_end = next((t for t in lap_turns if t['type'] == 'turn_end'), None)
        
        if turn_start and turn_end:
            lap_stat["Turn Time"] = round(turn_end['time'] - turn_start['time'], 2)
        
        # Count strokes in this lap
        strokes = len(lap_strokes)
        if strokes > 0:
            # Use breakout time if it exists, otherwise find first stroke
            start_swimming = lap_stat.get("Breakout Time") or lap_strokes[0]['time']
            swimming_duration = lap_end - start_swimming
            
            lap_stat.update({
                "Stroke Count": int(strokes),
                "Strokes per Second": round(strokes / swimming_duration if swimming_duration > 0 else 0, 2)
            })
        
        # Add breakout and 15m data if available
        if all(x is not None for x in [breakout_data, breakout_distances, fifteen_times]):
            if lap < len(breakout_data):  # Check if we have data for this lap
                lap_stat.update({
                    "Breakout Time": round(breakout_data[lap], 2),
                    "Breakout Distance": round(breakout_distances[lap], 2),
                    "Underwater Speed": round(breakout_distances[lap] / breakout_data[lap], 2),
                    "Breakout to 15m Time": round(fifteen_times[lap] - breakout_data[lap], 2),
                    "15m to Turn Time": round(lap_end - fifteen_times[lap], 2)
                })
        
        lap_stats.append(lap_stat)
    
    return pd.DataFrame(lap_stats)

def count_strokes_in_lap(events, lap_start, lap_end):
    """
    Count the number of strokes that occurred during the specified lap timeframe.
    """
    return sum(1 for e in events 
              if e['type'] == 'stroke' 
              and lap_start <= e['time'] <= lap_end)

def calculate_turn_speed(events, turn_time):
    """
    Calculate the turn speed based on turn start and end times.
    Only applicable for breaststroke and butterfly.
    """
    # Find the turn_start and turn_end events around this turn time
    turn_events = [e for e in events 
                  if e['type'].startswith('turn_') 
                  and abs(e['time'] - turn_time) < 1.0]  # Within 1 second of turn
    
    if len(turn_events) >= 2:
        turn_start = min(e['time'] for e in turn_events)
        turn_end = max(e['time'] for e in turn_events)
        return 1.0 / (turn_end - turn_start)  # Speed as 1/duration
    return None

def calculate_overall_stats(lap_stats):
    """
    Calculate overall statistics across all laps.
    """
    stats = {}
    
    # Calculate means for all numeric columns
    for column in lap_stats.select_dtypes(include=['float64', 'int64']).columns:
        if column != "Lap":  # Skip the lap number
            stats[f"Average {column}"] = round(lap_stats[column].mean(), 2)
    
    return stats

def generate_pdf_report(lap_stats, overall_stats, filepath, race_details):
    """
    Generate a PDF report with lap statistics split into two tables:
    1. Stroke-related statistics
    2. Turn/breakout/15m statistics
    """
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    elements = []
    
    # Get folder name from filepath
    folder_name = os.path.basename(os.path.dirname(filepath))
    
    # Title and Race Details
    elements.append(canvas.Canvas(filepath).drawString(100, 750, "Race Statistics Report"))
    
    # Add race details table
    race_info = [
        ["Swimmer:", race_details['swimmer_name']],
        ["Gender:", race_details['gender'].value],
        ["Distance:", f"{race_details['distance'].value}m"],
        ["Stroke:", race_details['stroke'].value],
        ["Session:", race_details['session'].value],
        ["Data Folder:", folder_name]
    ]
    
    race_table = Table(race_info, colWidths=[100, 200])
    race_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(race_table)
    elements.append(Spacer(1, 20))  # Add some space after race details
    
    if not lap_stats.empty:
        # Split data into two tables
        stroke_columns = ["Lap", "Lap Time", "Strk Count", "Strk/Sec", "Strk->Wall"]
        turn_columns = ["Lap", "Breakout Time", "Breakout Distance", "UW Speed", 
                       "Break->15m", "15m->Turn", "Turn Time"]
        
        # Format integers, ignoring NaN values
        lap_stats["Lap"] = lap_stats["Lap"].fillna(0).astype(int)
        lap_stats["Stroke Count"] = lap_stats["Stroke Count"].fillna(0).astype(int)
        
        # Create stroke data table
        stroke_data = [stroke_columns]
        for _, row in lap_stats.iterrows():
            stroke_data.append([
                int(row["Lap"]),
                row.get("Lap Time", ""),
                int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                row.get("Strokes per Second", ""),
                row.get("Stroke to Wall", "")
            ])
        
        # Create turn/breakout data table
        turn_data = [turn_columns]
        for _, row in lap_stats.iterrows():
            turn_data.append([
                int(row["Lap"]),
                row.get("Breakout Time", ""),
                row.get("Breakout Distance", ""),
                row.get("Underwater Speed", ""),
                row.get("Breakout to 15m Time", ""),
                row.get("15m to Turn Time", ""),
                row.get("Turn Time", "")
            ])
        
        # Style for both tables
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),  # Slightly larger font
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ])
        
        # Add stroke table
        elements.append(canvas.Canvas(filepath).drawString(100, 700, "Stroke Statistics"))
        stroke_table = Table(stroke_data, colWidths=[30, 50, 50, 50, 50])
        stroke_table.setStyle(table_style)
        elements.append(stroke_table)
        
        # Add some space between tables
        elements.append(Spacer(1, 20))
        
        # Add turn/breakout table
        elements.append(canvas.Canvas(filepath).drawString(100, 650, "Turn and Breakout Statistics"))
        turn_table = Table(turn_data, colWidths=[30, 50, 60, 50, 50, 50, 50])
        turn_table.setStyle(table_style)
        elements.append(turn_table)
    
    # Add a page break before overall stats
    elements.append(PageBreak())
    
    # Overall Statistics
    elements.append(canvas.Canvas(filepath).drawString(100, 750, "Overall Statistics:"))
    y_position = 720
    
    # Format overall stats in two columns
    stats_items = list(overall_stats.items())
    mid_point = len(stats_items) // 2
    
    for i in range(mid_point):
        # Left column
        left_stat = stats_items[i]
        elements.append(canvas.Canvas(filepath).drawString(
            50, y_position, f"{left_stat[0]}: {left_stat[1]:.2f}"))
        
        # Right column (if it exists)
        if i + mid_point < len(stats_items):
            right_stat = stats_items[i + mid_point]
            elements.append(canvas.Canvas(filepath).drawString(
                300, y_position, f"{right_stat[0]}: {right_stat[1]:.2f}"))
        
        y_position -= 20
    
    doc.build(elements)

def prepare_report_file(race_details, base_directory):
    """
    Prepare the file path for the report and check if it exists.
    Prompt the user for overwrite confirmation if necessary.
    Return the existence status of stroke and turn data, and 15m and breakout data.
    """
    # Construct the file paths based on race details
    filename = f"{race_details['swimmer_name'].replace(' ', '_')}_{race_details['gender'].value}_{race_details['distance'].value}_{race_details['stroke'].value}.csv"
    
    stroke_and_turn_filepath = os.path.join(base_directory, "stroke_and_turn", race_details['session'].value, filename)
    break_and_fifteen_filepath = os.path.join(base_directory, "break_and_fifteen", race_details['session'].value, filename)
    
    stroke_and_turn_exists = os.path.exists(stroke_and_turn_filepath)
    break_and_fifteen_exists = os.path.exists(break_and_fifteen_filepath)
    
    if not stroke_and_turn_exists and not break_and_fifteen_exists:
        print(f"No data found for {filename}.")
        return None, None
    
    # Prepare the report file path
    base_report_directory = base_directory.replace("data", "reports", 1)
    pdf_filename = filename.replace('.csv', '.pdf')
    pdf_filepath = os.path.join(base_report_directory, race_details['session'].value, pdf_filename)
    
    # Check if the report already exists
    if os.path.exists(pdf_filepath):
        confirm = input(f"Report {pdf_filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return None, None
    
    data_paths = []
    if stroke_and_turn_exists:
        data_paths.append(stroke_and_turn_filepath)
    if break_and_fifteen_exists:
        data_paths.append(break_and_fifteen_filepath)
        
    return data_paths, pdf_filepath

def run(race_details, base_directory):
    """
    Generate a report based on race details and data in the specified directory.
    """
    data_paths, pdf_filepath = prepare_report_file(race_details, base_directory)
    
    if not data_paths or pdf_filepath is None:
        return
    
    # Read the data from the CSV files
    data = {}
    
    # Read stroke and turn data
    stroke_turn_path = [p for p in data_paths if 'stroke_and_turn' in p]
    if stroke_turn_path:
        events_df = pd.read_csv(stroke_turn_path[0])
        data['events'] = events_df.to_dict('records')
        data['stroke'] = race_details['stroke'].value
    
    # Read breakout and fifteen data
    breakout_path = [p for p in data_paths if 'break_and_fifteen' in p]
    if breakout_path:
        breakout_df = pd.read_csv(breakout_path[0])
        data.update(breakout_df.to_dict('list'))
    
    # Calculate statistics
    lap_stats = calculate_per_lap_stats(data, race_details)
    overall_stats = calculate_overall_stats(lap_stats)
    
    # Generate PDF report
    os.makedirs(os.path.dirname(pdf_filepath), exist_ok=True)
    generate_pdf_report(lap_stats, overall_stats, pdf_filepath, race_details)
    
    print(f"Report generated: {pdf_filepath}")

def main():
    # Example data
    """ data = {
        "breakout_times": [1.2, 1.3, 1.1],
        "breakout_distances": [5.0, 5.2, 5.1],
        "fifteen_times": [5.5, 5.6, 5.4],
        "turn_times": [0.8, 0.9, 0.85],  # Example turn times
        "turn_end_times": [0.5, 1.0, 1.5],  # Example turn end times
        "water_entry_times": [0.2, 0.3, 0.25]  # Example water entry times
    }
    
    lap_stats = calculate_per_lap_stats(data)
    overall_stats = calculate_overall_stats(lap_stats)
    generate_pdf_report(lap_stats, overall_stats, "race_statistics_report.pdf") """

if __name__ == "__main__":
    main() 