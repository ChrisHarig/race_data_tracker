import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, PageBreak, Spacer, Paragraph
from reportlab.lib.styles import ParagraphStyle

def calculate_per_lap_stats(data, race_details):
    """
    Calculate statistics for each lap from the event data and breakout/fifteen data.
    All measurements are in yards for consistency.
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
                # Find the most recent turn_end or start event
                if lap == 0:
                    # For first lap, use the start time (0.0)
                    previous_turn_end = 0.0
                else:
                    # For subsequent laps, use the previous lap marker
                    previous_turn_end = lap_markers[lap]
                
                # Calculate breakout time relative to the turn end
                relative_breakout_time = breakout_data[lap] - previous_turn_end
                
                # Breakout distance is already in yards (user input)
                breakout_yards = breakout_distances[lap]
                
                # Calculate underwater speed in yards per second
                underwater_speed = breakout_yards / relative_breakout_time if relative_breakout_time > 0 else 0
                
                # Calculate breakout to 15m time
                # Note: 15m mark is at 16.4042 yards but we keep the name "15m" for reference
                breakout_to_fifteen = fifteen_times[lap] - breakout_data[lap]
                
                lap_stat.update({
                    "Breakout Time": round(relative_breakout_time, 2),  # Relative to turn end
                    "Breakout Dist": round(breakout_yards, 2),          # Already in yards
                    "UW Speed": round(underwater_speed, 2),             # Yards/sec
                    "Break->15": round(breakout_to_fifteen, 2),
                    "15->Turn": round(lap_end - fifteen_times[lap], 2),
                    "Turn Time": round(lap_stat.get("Turn Time", 0), 2)
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
    Generate a PDF report with all statistics in a single compact table.
    All speeds and distances are in yards/second and yards respectively.
    """
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,  # Keep left margin small
        topMargin=40,
        bottomMargin=40
    )
    elements = []
    
    # Get folder name from filepath - use the user-created directory
    folder_parts = filepath.split(os.sep)
    reports_index = folder_parts.index('reports')
    user_folder = folder_parts[reports_index + 1]
    
    # Format race details string more concisely
    race_string = f"{race_details['gender'].value.capitalize()} {race_details['distance'].value}yd {race_details['stroke'].value.capitalize()} {race_details['session'].value.capitalize()}"
    
    # Create a Paragraph for each line of race info with left alignment
    title_style = ParagraphStyle(
        'Title',
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=0,  # 0 = left, 1 = center, 2 = right
        spaceAfter=6  # Increased spacing after the title
    )
    
    info_style = ParagraphStyle(
        'Info',
        fontSize=9,
        fontName='Helvetica',
        alignment=0,
        spaceAfter=2  # Increased spacing after each info line
    )
    
    # Add race details as left-aligned paragraphs
    elements.append(Paragraph(race_details['swimmer_name'], title_style))
    elements.append(Paragraph(race_string, info_style))
    elements.append(Paragraph(user_folder, info_style))
    elements.append(Spacer(1, 5))  # Reduced spacer after all header info
    
    if not lap_stats.empty:
        # Combined columns for all statistics in new order
        columns = [
            "Lap", "Break Time", "Break->15", "15->Turn", "Strk->Wall",
            "Turn Time", "Lap Time", "Break Dist", "UW Speed", "Strk Count", "Strk/Sec"
        ]
        
        # Format integers, ignoring NaN values
        lap_stats["Lap"] = lap_stats["Lap"].fillna(0).astype(int)
        lap_stats["Stroke Count"] = lap_stats["Stroke Count"].fillna(0).astype(int)
        
        # Create combined data table with new column order
        data = [columns]  # Header row
        for _, row in lap_stats.iterrows():
            data_row = [
                int(row["Lap"]),
                row.get("Breakout Time", ""),
                row.get("Break->15", ""),
                row.get("15->Turn", ""),
                row.get("Stroke to Wall", ""),
                row.get("Turn Time", ""),
                row.get("Lap Time", ""),
                row.get("Breakout Dist", ""),
                row.get("UW Speed", ""),
                int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                row.get("Strokes per Second", "")
            ]
            data.append(data_row)
        
        # Add averages row
        avg_row = ["AVG"]
        for col in columns[1:]:  # Skip the "Lap" column
            col_key = col
            if col == "Break Time":
                col_key = "Breakout Time"
            elif col == "Break Dist":
                col_key = "Breakout Dist"
            elif col == "Strk Count":
                col_key = "Stroke Count"
            elif col == "Strk/Sec":
                col_key = "Strokes per Second"
            
            avg_key = f"Average {col_key}"
            avg_value = overall_stats.get(avg_key, "")
            avg_row.append(avg_value)
        
        data.append(avg_row)
        
        # Calculate column widths to fit on page
        available_width = 572  # letter width (612) - margins (40)
        col_widths = [25]  # Lap column
        remaining_cols = len(columns) - 1
        standard_col_width = (available_width - 25) / remaining_cols
        col_widths.extend([standard_col_width] * remaining_cols)
        
        # Create and style table
        table = Table(data, colWidths=col_widths)
        table_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),  # Smaller font size
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Thinner grid lines
            ('TOPPADDING', (0, 0), (-1, -1), 1),  # Minimal padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]
        
        # Style the averages row
        avg_row_index = len(data) - 1
        table_style.extend([
            ('BACKGROUND', (0, avg_row_index), (-1, avg_row_index), colors.lightgrey),
            ('FONTNAME', (0, avg_row_index), (-1, avg_row_index), 'Helvetica-Bold'),
        ])
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        # Add measurement note
        elements.append(Spacer(1, 5))
        note = "Note: All distances in yards, speeds in yards/second. 15m mark (16.4042 yards) used for calculations."
        
        note_style = ParagraphStyle(
            'Note',
            fontSize=7,
            fontName='Helvetica-Oblique'
        )
        
        elements.append(Paragraph(note, note_style))
        
        # Add variable descriptions
        elements.append(Spacer(1, 8))
        
        description_style = ParagraphStyle(
            'Description',
            fontSize=7,
            fontName='Helvetica',
            leading=9  # Line spacing
        )
        
        descriptions = [
            "Break Time: Time from wall/start to breakout (seconds)",
            "Break->15: Time from breakout to 15m mark (seconds)", 
            "15->Turn: Time from 15m mark to next turn/finish (seconds)",
            "Strk->Wall: Time from last stroke to wall (seconds)",
            "Turn Time: Time from hand touch to push off (seconds)",
            "Lap Time: Total time for the lap (seconds)",
            "Break Dist: Distance travelled underwater (yards)",
            "UW Speed: Underwater speed (yards/second)",
            "Strk Count: Number of strokes in the lap (strokes)",
            "Strk/Sec: Stroke rate (strokes per second)"
        ]
        
        # Create a multi-column layout for descriptions
        num_cols = 2
        rows = []
        for i in range(0, len(descriptions), num_cols):
            row = descriptions[i:i+num_cols]
            # Pad with empty strings if needed
            while len(row) < num_cols:
                row.append("")
            rows.append(row)
        
        # Create table for descriptions
        desc_table = Table(rows, colWidths=[280, 280])
        desc_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(desc_table)
    
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