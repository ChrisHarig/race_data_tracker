import os
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, PageBreak, Spacer, Paragraph, Image
from reportlab.lib.styles import ParagraphStyle
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import io
import copy
import glob
from enum import Enum

DEBUG_MODE = False  # Set to True to enable debug output

def debug_print(*args, **kwargs):
    """Print debug messages only when DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        print("DEBUG:", *args, **kwargs)

def calculate_lap_markers(events, stroke, distance):
    """
    Calculate lap markers based on stroke type and distance.
    Returns a list of timestamps marking the start/end of each lap.
    """
    lap_markers = [0.0]  # Start with 0 for first lap
    laps_with_turn_pairs = set()  # Track which laps have turn_start/turn_end pairs
    
    debug_print(f"Processing {stroke} race with distance {distance}")
    
    if stroke in ["breaststroke", "butterfly"]:
        # For breast/fly, use turn_start events
        lap_markers.extend([e['time'] for e in events if e['type'] == 'turn_start'])
        # All laps have turn pairs
        laps_with_turn_pairs = set(range(1, len(lap_markers)))
    elif stroke == "im":
        # For IM, we need a more sophisticated approach to handle the turn patterns
        
        # Get all turn events sorted by time
        all_turns = [(e['time'], e['type']) for e in events if e['type'] in ['turn_start', 'turn_end']]
        all_turns.sort(key=lambda x: x[0])
        
        debug_print(f"IM race with distance {distance}")
        debug_print(f"Found {len(all_turns)} turn events")
        
        # For 200 IM (8 laps - 2 of each stroke)
        if distance == 200:
            # Process turns to identify lap boundaries
            current_lap = 1
            expected_laps = 8  # 200 IM has 8 laps (2 of each stroke)
            
            # Group turns by pairs (start/end) where applicable
            i = 0
            while i < len(all_turns) and current_lap < expected_laps:
                turn_time, turn_type = all_turns[i]
                
                # For butterfly portions (laps 1-2)
                # We expect turn_start followed by turn_end
                if current_lap in [1, 2]:
                    if turn_type == 'turn_start':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                        # Skip the corresponding turn_end
                        if i+1 < len(all_turns) and all_turns[i+1][1] == 'turn_end':
                            i += 2
                            continue
                
                # For backstroke portions (laps 3-4)
                # We expect turn_end for lap 3, but special case for lap 4 (backstroke to breaststroke)
                elif current_lap == 3:
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        # No turn pair for backstroke
                        current_lap += 1
                
                # Special case: backstroke to breaststroke transition (lap 4)
                # This has both turn_start and turn_end
                elif current_lap == 4:
                    # For the backstroke to breaststroke transition, use turn_end
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                
                # For breaststroke portions (laps 5-6)
                # We expect turn_start followed by turn_end
                elif current_lap in [5, 6]:
                    if turn_type == 'turn_start':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                        # Skip the corresponding turn_end
                        if i+1 < len(all_turns) and all_turns[i+1][1] == 'turn_end':
                            i += 2
                            continue
                
                # For freestyle portion (lap 7)
                # We expect just turn_end
                elif current_lap == 7:
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        # No turn pair for freestyle
                        current_lap += 1
                
                i += 1
            
            # If we didn't get enough lap markers, use a simpler approach
            if len(lap_markers) < expected_laps:
                debug_print("Not enough lap markers found with sophisticated approach, using simpler method")
                lap_markers = [0.0]  # Reset and try simpler approach
                laps_with_turn_pairs = set()  # Reset turn pairs
                
                # For 200 IM, we need 7 turn markers to create 8 laps
                # Just use the first 7 turn events regardless of type
                turn_times = [t[0] for t in all_turns]
                if len(turn_times) >= 7:
                    lap_markers.extend(turn_times[:7])
                else:
                    # Use whatever we have
                    lap_markers.extend(turn_times)
        
        # For 400 IM (16 laps - 4 of each stroke)
        elif distance == 400:
            # Similar approach for 400 IM but with more laps
            # Process turns to identify lap boundaries
            current_lap = 1
            expected_laps = 16  # 400 IM has 16 laps (4 of each stroke)
            
            # Group turns by pairs (start/end) where applicable
            i = 0
            while i < len(all_turns) and current_lap < expected_laps:
                turn_time, turn_type = all_turns[i]
                
                # For butterfly portions (laps 1-4)
                # We expect turn_start followed by turn_end
                if current_lap in [1, 2, 3, 4]:
                    if turn_type == 'turn_start':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                        # Skip the corresponding turn_end
                        if i+1 < len(all_turns) and all_turns[i+1][1] == 'turn_end':
                            i += 2
                            continue
                
                # For backstroke portions (laps 5-8)
                # We expect turn_end for laps 5-7, but special case for lap 8 (backstroke to breaststroke)
                elif current_lap in [5, 6, 7]:
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        # No turn pair for backstroke
                        current_lap += 1
                
                # Special case: backstroke to breaststroke transition (lap 8)
                # This has both turn_start and turn_end
                elif current_lap == 8:
                    # For the backstroke to breaststroke transition, use turn_end
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                
                # For breaststroke portions (laps 9-12)
                # We expect turn_start followed by turn_end
                elif current_lap in [9, 10, 11, 12]:
                    if turn_type == 'turn_start':
                        lap_markers.append(turn_time)
                        laps_with_turn_pairs.add(current_lap)  # This lap has a turn pair
                        current_lap += 1
                        # Skip the corresponding turn_end
                        if i+1 < len(all_turns) and all_turns[i+1][1] == 'turn_end':
                            i += 2
                            continue
                
                # For freestyle portions (laps 13-15)
                # We expect just turn_end
                elif current_lap in [13, 14, 15]:
                    if turn_type == 'turn_end':
                        lap_markers.append(turn_time)
                        # No turn pair for freestyle
                        current_lap += 1
                
                i += 1
            
            # If we didn't get enough lap markers, use a simpler approach
            if len(lap_markers) < expected_laps:
                debug_print("Not enough lap markers found with sophisticated approach, using simpler method")
                lap_markers = [0.0]  # Reset and try simpler approach
                laps_with_turn_pairs = set()  # Reset turn pairs
                
                # For 400 IM, we need 15 turn markers to create 16 laps
                turn_times = [t[0] for t in all_turns]
                if len(turn_times) >= 15:
                    lap_markers.extend(turn_times[:15])
                else:
                    # Use whatever we have
                    lap_markers.extend(turn_times)
    else:
        # For freestyle and backstroke, use turn_end events
        lap_markers.extend([e['time'] for e in events if e['type'] == 'turn_end'])
    
    # Add the final time
    end_events = [e['time'] for e in events if e['type'] == 'end']
    if end_events:
        lap_markers.append(end_events[0])
    
    debug_print(f"DEBUG: Lap markers before filtering: {lap_markers}")
    
    # Ensure lap markers are sorted
    lap_markers.sort()
    
    # Remove any markers that are too close together (within 0.1 seconds)
    filtered_markers = [lap_markers[0]]  # Always keep the first marker (start time)
    for i in range(1, len(lap_markers)):
        if lap_markers[i] - filtered_markers[-1] > 0.1:  # Only add if more than 0.1s from previous
            filtered_markers.append(lap_markers[i])
    
    lap_markers = filtered_markers
    
    debug_print(f"DEBUG: Lap markers after filtering: {lap_markers}")
    debug_print(f"DEBUG: Number of laps: {len(lap_markers) - 1}")
    debug_print(f"DEBUG: Laps with turn pairs: {laps_with_turn_pairs}")
    
    return lap_markers, laps_with_turn_pairs

def calculate_per_lap_stats(data, race_details):
    """
    Calculate statistics for each lap from the event data and breakout/fifteen data.
    All measurements are in yards for consistency.
    Handles cases where breakout/fifteen data might be missing.
    """
    stroke = race_details['stroke'].value
    
    # Convert distance to integer if it's a string
    distance = race_details['distance'].value
    if isinstance(distance, str):
        distance = int(distance)
    
    # Get the events from stroke_and_turn data
    events = data.get('events', [])  # List of {type, time} dictionaries
    
    # Debug: Print all events to see what we're working with
    debug_print(f"DEBUG: Total events: {len(events)}")
    debug_print(f"DEBUG: Event types: {set(e['type'] for e in events)}")
    turn_events = [e for e in events if e['type'].startswith('turn_')]
    debug_print(f"DEBUG: Turn events: {len(turn_events)}")
    for i, e in enumerate(turn_events):
        debug_print(f"DEBUG: Turn {i+1}: {e['type']} at {e['time']:.2f}s")
    
    # Get breakout/fifteen data if available
    breakout_times = data.get('breakout_times', None)
    breakout_distances = data.get('breakout_distances', None)
    fifteen_times = data.get('fifteen_times', None)
    
    # Check if we have complete breakout/fifteen data
    has_breakout_data = all(x is not None for x in [breakout_times, breakout_distances, fifteen_times])
    debug_print(f"DEBUG: Has breakout data: {has_breakout_data} in calculate_per_lap_stats")
    
    # Calculate lap markers using the new function
    lap_markers, laps_with_turn_pairs = calculate_lap_markers(events, stroke, distance)
    
    num_laps = len(lap_markers) - 1  # Number of laps is one less than number of markers
    
    # Pre-calculate turn times for all turn_start/turn_end pairs
    # This is a simpler approach that doesn't rely on associating turns with laps
    turn_times = {}  # Dictionary to store turn times by lap
    
    # Sort all turn events by time
    all_turn_events = sorted([e for e in events if e['type'].startswith('turn_')], key=lambda x: x['time'])
    
    # Process turn events in pairs
    i = 0
    while i < len(all_turn_events) - 1:
        current = all_turn_events[i]
        next_event = all_turn_events[i + 1]
        
        # If we find a turn_start followed by a turn_end
        if current['type'] == 'turn_start' and next_event['type'] == 'turn_end':
            # Calculate the turn time
            turn_time = next_event['time'] - current['time']
            
            # Find which lap this turn belongs to
            for lap in range(num_laps):
                lap_start = lap_markers[lap]
                lap_end = lap_markers[lap + 1]
                
                # If the turn_start is in this lap or the turn_end is in the next lap
                if lap_start <= current['time'] <= lap_end or (lap < num_laps - 1 and lap_end <= next_event['time'] <= lap_markers[lap + 2]):
                    turn_times[lap + 1] = round(turn_time, 2)
                    break
            
            i += 2  # Skip both events
        else:
            i += 1  # Move to next event
    
    debug_print(f"DEBUG: Calculated turn times: {turn_times} in calculate_per_lap_stats")
    
    # Check if this is freestyle or backstroke (no turn time)
    is_free_or_back = stroke in ["freestyle", "backstroke"]
    
    # Get water entry events
    water_entry_events = [e for e in events if e['type'] == 'water_entry']

    if len(water_entry_events) > 1:
        debug_print("DEBUG: Found multiple water entry events, using the first one in calculate_per_lap_stats")
        water_entry_events = water_entry_events[:1]
    
    lap_stats = []
    
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
        last_stroke_time = None
        if lap_strokes:
            last_stroke_time = max(s['time'] for s in lap_strokes)
            next_turn = min((t['time'] for t in lap_turns if t['time'] > last_stroke_time), default=lap_end)
            lap_stat["Stroke to Wall"] = round(next_turn - last_stroke_time, 2)
        
        # Use the pre-calculated turn time for this lap if available
        lap_stat["Turn Time"] = turn_times.get(lap + 1, None)
        
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
        if has_breakout_data and lap < len(breakout_times):
            # For first lap, use water entry time if available, otherwise use start time
            if lap == 0 and water_entry_events:
                underwater_start_time = water_entry_events[0]['time']
            else:
                # For subsequent laps, use the lap marker (turn end)
                underwater_start_time = lap_markers[lap]
            
            # Calculate breakout time relative to the underwater start time
            relative_breakout_time = breakout_times[lap] - underwater_start_time
            
            # Breakout distance is already in yards (user input)
            breakout_yards = breakout_distances[lap]
            
            # Calculate underwater speed in yards per second
            underwater_speed = breakout_yards / relative_breakout_time if relative_breakout_time > 0 else 0
            
            # Calculate overwater speed (from breakout to last stroke)
            # Distance is 25 yards minus breakout distance minus 0.5 yards (to account for hand touch)
            overwater_distance = 25.0 - breakout_yards - 0.5
            
            # Time is from breakout to last stroke (if available)
            if last_stroke_time and last_stroke_time > breakout_times[lap]:
                overwater_time = last_stroke_time - breakout_times[lap]
            else:
                # Fallback to using lap end time if no stroke data
                overwater_time = lap_end - breakout_times[lap]
            
            # Calculate speed in yards per second
            overwater_speed = overwater_distance / overwater_time if overwater_time > 0 else 0
            
            # Calculate breakout to 15m time
            # Note: 15m mark is at 16.4042 yards but we keep the name "15m" for reference
            breakout_to_fifteen = fifteen_times[lap] - breakout_times[lap]
            
            lap_stat.update({
                "Breakout Time": round(relative_breakout_time, 2),
                "Breakout Dist": round(breakout_yards, 2),
                "UW Speed": round(underwater_speed, 2),
                "OW Speed": round(overwater_speed, 2),
                "Break->15": round(breakout_to_fifteen, 2),
                "15->Turn": round(lap_end - fifteen_times[lap], 2),
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
                  and abs(e['time'] - turn_time) < 1.8]  # Within 1 second of turn
    
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

def create_stroke_by_stroke_plot(events, lap_start, lap_end, lap_number, breakout_times=None):
    """
    Create a plot showing individual stroke rates for a single lap.
    X-axis is stroke number, Y-axis is stroke rate (strokes/second).
    Includes a line of best fit to show trend.
    """
    # Get all strokes in this lap
    lap_strokes = [e for e in events 
                  if e['type'] == 'stroke' 
                  and lap_start <= e['time'] <= lap_end]
    
    # Sort strokes by time
    lap_strokes.sort(key=lambda x: x['time'])
    
    debug_print(f"Lap {lap_number}: Found {len(lap_strokes)} strokes")
    
    # If we have fewer than 2 strokes, we can't calculate rates
    if len(lap_strokes) < 2:
        debug_print(f"  Lap {lap_number}: Not enough strokes to calculate rates")
        # Create an empty plot
        plt.figure(figsize=(5, 4))
        plt.title(f'Lap {lap_number}: Stroke Rate')
        plt.xlabel('Stroke Number')
        plt.ylabel('Stroke Rate (strokes/second)')
        plt.grid(True, alpha=0.3)
        plt.text(0.5, 0.5, 'Not enough strokes to calculate rates', 
                ha='center', va='center', transform=plt.gca().transAxes)
        
        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
    
    # Extract stroke times
    stroke_times = [s['time'] for s in lap_strokes]
    
    # Calculate individual stroke rates (time between consecutive strokes)
    stroke_numbers = list(range(1, len(stroke_times)))
    stroke_rates = []
    
    for i in range(1, len(stroke_times)):
        time_diff = stroke_times[i] - stroke_times[i-1]
        rate = 1.0 / time_diff if time_diff > 0 else 0
        stroke_rates.append(rate)
        debug_print(f"    Stroke {i+1} at {stroke_times[i]:.2f}: Rate = {rate:.2f} strokes/sec")
    
    # Create plot
    plt.figure(figsize=(5, 4))
    
    # Scatter plot of individual stroke rates
    plt.scatter(stroke_numbers, stroke_rates, color='green', s=40)
    
    # Add line of best fit if we have enough points
    if len(stroke_rates) >= 2:
        # Calculate line of best fit
        x = np.array(stroke_numbers)
        y = np.array(stroke_rates)
        m, b = np.polyfit(x, y, 1)
        plt.plot(x, m*x + b, color='blue', linestyle='--')
    
    # Add data labels
    for i, rate in enumerate(stroke_rates):
        plt.annotate(f"{rate:.2f}", 
                    (stroke_numbers[i], rate),
                    xytext=(0, 5), textcoords='offset points',
                    ha='center', fontsize=8)
    
    plt.title(f'Lap {lap_number}: Stroke Rate')
    plt.xlabel('Stroke Number')
    plt.ylabel('Stroke Rate (strokes/second)')
    plt.grid(True, alpha=0.3)
    
    # Set reasonable y-axis limits
    if stroke_rates:
        max_rate = max(stroke_rates)
        min_rate = min(stroke_rates)
        buffer = (max_rate - min_rate) * 0.1 if max_rate > min_rate else 0.2
        plt.ylim(max(0, min_rate - buffer), max_rate + buffer)
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    
    return buf

def create_continuous_stroke_graph(data, race_details):
    """
    Create a continuous stroke graph showing stroke rate across all laps.
    Returns a bytes buffer containing the image.
    """
    events = data.get('events', [])
    
    # Get stroke events
    stroke_events = [e for e in events if e['type'] == 'stroke']
    
    if not stroke_events:
        # Create an empty plot with a message if no stroke data
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No stroke data available', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.axis('off')
    else:
        # Get stroke and distance
        stroke = race_details['stroke'].value
        
        # Convert distance to integer if it's a string
        distance = race_details['distance'].value
        if isinstance(distance, str):
            distance = int(distance)
        
        # Calculate lap markers using the new function
        lap_markers, _ = calculate_lap_markers(events, stroke, distance)
        
        # Create the plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Calculate stroke rate over time
        # Group strokes by lap
        lap_strokes = []
        for i in range(len(lap_markers) - 1):
            lap_start = lap_markers[i]
            lap_end = lap_markers[i + 1]
            lap_stroke_events = [e for e in stroke_events if lap_start <= e['time'] <= lap_end]
            lap_strokes.append(lap_stroke_events)
        
        # Calculate stroke rate for each stroke
        stroke_rates = []
        for lap_idx, lap_stroke_events in enumerate(lap_strokes):
            if len(lap_stroke_events) < 2:
                continue
                
            # Calculate time between consecutive strokes
            for i in range(len(lap_stroke_events) - 1):
                time1 = lap_stroke_events[i]['time']
                time2 = lap_stroke_events[i + 1]['time']
                if time2 > time1:  # Ensure valid time difference
                    stroke_time = time2 - time1
                    stroke_rate = 1.0 / stroke_time if stroke_time > 0 else 0
                    stroke_rates.append((time1, stroke_rate))
        
        # Plot stroke rates as green dots
        times, rates = zip(*stroke_rates) if stroke_rates else ([], [])
        ax.scatter(times, rates, color='green', s=50, alpha=0.7)
        
        # Add data labels for stroke rates
        for time, rate in stroke_rates:
            ax.annotate(f"{rate:.2f}", 
                       (time, rate),
                       xytext=(0, 5), textcoords='offset points',
                       ha='center', fontsize=8)
        
        # Add a trend line
        if stroke_rates:
            z = np.polyfit(times, rates, 1)
            p = np.poly1d(z)
            ax.plot(times, p(times), "b--", alpha=0.7)
        
        # Add lap markers as vertical red lines
        for i, marker in enumerate(lap_markers):
            if i == 0:
                label = "Start"
            elif i == len(lap_markers) - 1:
                label = "Finish"
            else:
                label = f"Lap {i}"
            
            ax.axvline(x=marker, color='red', linestyle='-', linewidth=1)
            ax.text(marker, ax.get_ylim()[1] * 0.95, label, 
                   ha='center', va='top', fontsize=8, color='red', fontweight='bold')
        
        # Set titles and labels
        ax.set_title('Continuous Stroke Rate Analysis')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Stroke Rate (strokes/second)')
        
        # Add a grid for better readability
        ax.grid(True, alpha=0.3)
        
        # Adjust the plot to show all data
        if lap_markers:
            ax.set_xlim(0, lap_markers[-1] * 1.02)  # Add a little padding
    
    plt.tight_layout()
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf

def create_stroke_by_stroke_analysis_elements(data, race_details):
    """
    Create stroke-by-stroke analysis elements for the PDF.
    Returns a list of flowable elements to add to the PDF.
    """
    elements = []
    
    # Get events
    events = data.get('events', [])
    
    # Get stroke and distance
    stroke = race_details['stroke'].value
    
    # Convert distance to integer if it's a string
    distance = race_details['distance'].value
    if isinstance(distance, str):
        distance = int(distance)
    
    # Calculate lap markers using the new function
    lap_markers, _ = calculate_lap_markers(events, stroke, distance)
    
    # Get breakout times if available
    breakout_times = data.get('breakout_times', None)
    
    # Create stroke-by-stroke plots for each lap
    num_laps = len(lap_markers) - 1  # Calculate actual number of laps
    
    debug_print(f"DEBUG: Creating stroke-by-stroke plots for {num_laps} laps")
    
    # Generate all plots first
    all_plots = []
    for lap in range(num_laps):
        lap_start = lap_markers[lap]
        lap_end = lap_markers[lap + 1]
        
        # Create the plot for this lap
        stroke_plot_buf = create_stroke_by_stroke_plot(events, lap_start, lap_end, lap + 1, breakout_times)
        
        # Create a paragraph for the lap title
        lap_title = Paragraph(f"Lap {lap+1}", ParagraphStyle(
            'Title',
            fontSize=10,
            fontName='Helvetica-Bold',
            alignment=0,
            spaceAfter=4
        ))
        
        # Create the image
        stroke_plot_img = Image(stroke_plot_buf, width=250, height=200)
        
        # Add both to the list
        all_plots.append((lap_title, stroke_plot_img))
    
    # Now arrange the plots in a grid, 2x2 per page
    for i in range(0, len(all_plots), 4):
        # Take up to 4 plots for this page
        page_plots = all_plots[i:i+4]
        
        # Create a table for this page
        data = []
        
        # Add plots to the table, 2 per row
        for j in range(0, len(page_plots), 2):
            row_plots = page_plots[j:j+2]
            row = []
            
            for title, img in row_plots:
                # Create a container for these elements
                container = []
                container.append(title)
                container.append(img)
                row.append(container)
            
            # Pad with empty cells if needed
            while len(row) < 2:
                row.append("")
                
            data.append(row)
        
        # Create the table
        plot_table = Table(data, colWidths=[275, 275])
        plot_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(plot_table)
        
        # Add a page break after each table (except the last one)
        if i + 4 < len(all_plots):
            elements.append(PageBreak())
    
    return elements

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
        debug_print(f"No data found for {filename}.")
        return None, None
    
    # Prepare the report file path
    base_report_directory = base_directory.replace("data", "reports", 1)
    pdf_filename = filename.replace('.csv', '.pdf')
    pdf_filepath = os.path.join(base_report_directory, race_details['session'].value, pdf_filename)
    
    # Check if the report already exists
    if os.path.exists(pdf_filepath):
        confirm = input(f"Report {pdf_filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            debug_print("Operation cancelled.")
            return None, None
    
    data_paths = []
    if stroke_and_turn_exists:
        data_paths.append(stroke_and_turn_filepath)
    if break_and_fifteen_exists:
        data_paths.append(break_and_fifteen_filepath)
        
    return data_paths, pdf_filepath

def run(race_details, base_directory):
    """
    Main function to run the reporting process.
    Loads data, calculates statistics, and generates the report.
    """
    # Prepare file paths
    if base_directory.startswith('data/'):
        base_directory = base_directory[5:]  # Remove 'data/' prefix
    data_dir = os.path.join('data', base_directory)
    
    # Create the reports directory
    reports_dir = os.path.join("reports", base_directory, race_details['session'].value)
    os.makedirs(reports_dir, exist_ok=True)
    # Print debug info about reports directory
    debug_print(f"DEBUG: Reports directory: {reports_dir}")
    
    # Construct the filename pattern for searching
    swimmer_name = race_details['swimmer_name'].replace(' ', '_')
    gender = race_details['gender'].value
    
    # Include relay 
    relay_part = ""
    if race_details.get('relay', False):
        relay_part = "relay_"
    
    distance = str(race_details['distance'].value)
    stroke = race_details['stroke'].value
    
    # Create the filename pattern
    filename_pattern = f"{swimmer_name}_{gender}_{relay_part}{distance}_{stroke}.csv"
    
    # Find the stroke and turn data file
    stroke_turn_dir = os.path.join(data_dir, "stroke_and_turn", race_details['session'].value)
    stroke_turn_file = os.path.join(stroke_turn_dir, filename_pattern)
    debug_print(f"Looking for stroke and turn data file: {stroke_turn_file}")
    
    # Find the breakout and fifteen data file
    break_fifteen_dir = os.path.join(data_dir, "break_and_fifteen", race_details['session'].value)
    break_fifteen_file = os.path.join(break_fifteen_dir, filename_pattern)
    debug_print(f"Looking for breakout and fifteen data file: {break_fifteen_file}")
    
    # Check if files exist
    if not os.path.exists(stroke_turn_file):
        debug_print(f"Error: Stroke and turn data file not found: {stroke_turn_file}")
        return
    
    # Load the data
    data = {}
    
    # Load stroke and turn data
    stroke_turn_data = pd.read_csv(stroke_turn_file)
    
    # Print column names for debugging
    debug_print(f"DEBUG: CSV columns: {stroke_turn_data.columns.tolist()}")
    
    # Convert to events list
    events = []
    for _, row in stroke_turn_data.iterrows():
        event_type = row['type'] if 'type' in stroke_turn_data.columns else row['event_type']
        events.append({
            'type': event_type,
            'time': row['time']
        })
    
    data['events'] = events
    data['stroke'] = stroke
    
    # Load breakout and fifteen data if available
    if os.path.exists(break_fifteen_file):
        break_fifteen_data = pd.read_csv(break_fifteen_file)
        
        # Check column names
        debug_print(f"DEBUG: Breakout CSV columns: {break_fifteen_data.columns.tolist()}")
        
        # Add each column to data - check for both singular and plural forms
        if 'breakout_time' in break_fifteen_data.columns:
            data['breakout_times'] = break_fifteen_data['breakout_time'].tolist()
        elif 'breakout_times' in break_fifteen_data.columns:
            data['breakout_times'] = break_fifteen_data['breakout_times'].tolist()
        
        if 'breakout_distance' in break_fifteen_data.columns:
            data['breakout_distances'] = break_fifteen_data['breakout_distance'].tolist()
        elif 'breakout_distances' in break_fifteen_data.columns:
            data['breakout_distances'] = break_fifteen_data['breakout_distances'].tolist()
        
        if 'fifteen_time' in break_fifteen_data.columns:
            data['fifteen_times'] = break_fifteen_data['fifteen_time'].tolist()
        elif 'fifteen_times' in break_fifteen_data.columns:
            data['fifteen_times'] = break_fifteen_data['fifteen_times'].tolist()
    
    # Calculate statistics
    lap_stats = calculate_per_lap_stats(data, race_details)
    overall_stats = calculate_overall_stats(lap_stats)
    
    # Generate the report
    report_filename = filename_pattern.replace('.csv', '.pdf')
    
    # Create the report directory with the same structure as the data
    # For example, if base_directory is "data/Big12's/Day2", we want "reports/Big12's/Day2/finals"
    # Strip off "data/" prefix if present
    clean_base_dir = base_directory.replace('data/', '').replace('data\\', '')
    report_dir = os.path.join("reports", clean_base_dir, race_details['session'].value)
    # Create the directory if it doesn't exist
    os.makedirs(report_dir, exist_ok=True)
    
    report_filepath = os.path.join(report_dir, report_filename)
    
    generate_pdf_report(lap_stats, overall_stats, report_filepath, race_details, data)
    
    debug_print(f"Report generated: {report_filepath}")
    return report_filepath

def generate_pdf_report(lap_stats, overall_stats, filepath, race_details, data=None):
    """
    Generate a PDF report with all statistics in a single compact table.
    All speeds and distances are in yards/second and yards respectively.
    Handles cases where breakout/fifteen data might be missing.
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
    # Check if relay is present in race_details and include it if it exists
    relay_text = ""
    if 'relay' in race_details and race_details['relay']:
        relay_text = "Relay "
    
    race_string = f"{race_details['gender'].value.capitalize()} {relay_text}{race_details['distance'].value}yd {race_details['stroke'].value.capitalize()} {race_details['session'].value.capitalize()}"
    
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
        # Determine which columns we have data for
        has_breakout_data = 'Breakout Time' in lap_stats.columns and not lap_stats['Breakout Time'].isna().all()
        
        # Check if this is freestyle or backstroke (no turn time)
        is_free_or_back = race_details['stroke'].value in ["freestyle", "backstroke"]
        
        # Define columns based on available data
        if has_breakout_data:
            if is_free_or_back:
                columns = [
                    "Lap", "Break Time", "Break->15", "15->Turn", "Strk->Wall",
                    "Lap Time", "Break Dist", "UW Speed", "OW Speed", "Strk Count", "Strk/Sec"
                ]
            else:
                columns = [
                    "Lap", "Break Time", "Break->15", "15->Turn", "Strk->Wall",
                    "Turn Time", "Lap Time", "Break Dist", "UW Speed", "OW Speed", "Strk Count", "Strk/Sec"
                ]
        else:
            if is_free_or_back:
                columns = [
                    "Lap", "Strk->Wall", "Lap Time", "Strk Count", "Strk/Sec"
                ]
            else:
                columns = [
                    "Lap", "Strk->Wall", "Turn Time", "Lap Time", "Strk Count", "Strk/Sec"
                ]
        
        # Format integers, ignoring NaN values
        lap_stats["Lap"] = lap_stats["Lap"].fillna(0).astype(int)
        lap_stats["Stroke Count"] = lap_stats["Stroke Count"].fillna(0).astype(int)
        
        # Create combined data table with new column order
        data_table = [columns]  # Header row
        
        # Determine which cells need asterisks
        last_lap_index = lap_stats["Lap"].max()
        
        # Create a mapping of column names to indices for easier reference
        column_indices = {col: idx for idx, col in enumerate(columns)}
        
        for _, row in lap_stats.iterrows():
            lap_num = int(row["Lap"])
            
            # Prepare data row based on available columns and stroke type
            if has_breakout_data:
                if is_free_or_back:
                    data_row = [
                        lap_num,
                        row.get("Breakout Time", ""),
                        row.get("Break->15", ""),
                        row.get("15->Turn", ""),
                        row.get("Stroke to Wall", ""),
                        row.get("Lap Time", ""),
                        row.get("Breakout Dist", ""),
                        row.get("UW Speed", ""),
                        row.get("OW Speed", ""),
                        int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                        row.get("Strokes per Second", "")
                    ]
                else:
                    data_row = [
                        lap_num,
                        row.get("Breakout Time", ""),
                        row.get("Break->15", ""),
                        row.get("15->Turn", ""),
                        row.get("Stroke to Wall", ""),
                        row.get("Turn Time", ""),
                        row.get("Lap Time", ""),
                        row.get("Breakout Dist", ""),
                        row.get("UW Speed", ""),
                        row.get("OW Speed", ""),
                        int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                        row.get("Strokes per Second", "")
                    ]
            else:
                if is_free_or_back:
                    data_row = [
                        lap_num,
                        row.get("Stroke to Wall", ""),
                        row.get("Lap Time", ""),
                        int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                        row.get("Strokes per Second", "")
                    ]
                else:
                    data_row = [
                        lap_num,
                        row.get("Stroke to Wall", ""),
                        row.get("Turn Time", ""),
                        row.get("Lap Time", ""),
                        int(row.get("Stroke Count", 0)) if pd.notna(row.get("Stroke Count")) else "",
                        row.get("Strokes per Second", "")
                    ]
            
            # Add asterisks to specific cells using column indices
            if lap_num == 1 and "UW Speed" in column_indices and pd.notna(row.get("UW Speed")):
                # Double asterisk for UW Speed in lap 1
                uw_speed_idx = column_indices["UW Speed"]
                if uw_speed_idx < len(data_row):
                    data_row[uw_speed_idx] = f"{data_row[uw_speed_idx]}**"
            
            if lap_num == last_lap_index:
                # Stroke to Wall on last lap gets an asterisk
                if "Strk->Wall" in column_indices and pd.notna(row.get("Stroke to Wall")):
                    strk_wall_idx = column_indices["Strk->Wall"]
                    if strk_wall_idx < len(data_row):
                        data_row[strk_wall_idx] = f"{data_row[strk_wall_idx]}*"
                
                # 15->Turn on last lap gets an asterisk
                if "15->Turn" in column_indices and pd.notna(row.get("15->Turn")):
                    fifteen_turn_idx = column_indices["15->Turn"]
                    if fifteen_turn_idx < len(data_row):
                        data_row[fifteen_turn_idx] = f"{data_row[fifteen_turn_idx]}*"
            
            data_table.append(data_row)
        
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
            elif col == "Strk->Wall":
                col_key = "Stroke to Wall"
            
            avg_key = f"Average {col_key}"
            avg_value = overall_stats.get(avg_key, "")
            avg_row.append(avg_value)
        
        data_table.append(avg_row)
        
        # Calculate column widths based on number of columns
        available_width = 572  # letter width (612) - margins (40)
        col_widths = [25]  # Lap column
        remaining_cols = len(columns) - 1
        standard_col_width = (available_width - 25) / remaining_cols
        col_widths.extend([standard_col_width] * remaining_cols)
        
        # Create and style table
        table = Table(data_table, colWidths=col_widths)
        
        # Basic table styling
        table_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),  # Smaller font size
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Standard thin grid
            ('TOPPADDING', (0, 0), (-1, -1), 1),  # Minimal padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Header row text color
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row bold
        ]
        
        # Add thicker vertical lines around Lap Time column
        lap_time_idx = column_indices.get("Lap Time")
        if lap_time_idx is not None:
            for row in range(len(data_table)):
                # Left border of Lap Time column
                table_style.append(('LINEAFTER', (lap_time_idx-1, row), (lap_time_idx-1, row), 1.5, colors.black))
                # Right border of Lap Time column
                table_style.append(('LINEAFTER', (lap_time_idx, row), (lap_time_idx, row), 1.5, colors.black))
        
        # Add thicker line after UW Speed column if it exists
        uw_speed_idx = column_indices.get("UW Speed")
        if uw_speed_idx is not None:
            for row in range(len(data_table)):
                table_style.append(('LINEAFTER', (uw_speed_idx, row), (uw_speed_idx, row), 1.5, colors.black))
        
        # Style the averages row
        avg_row_index = len(data_table) - 1
        table_style.extend([
            ('BACKGROUND', (0, avg_row_index), (-1, avg_row_index), colors.grey),
            ('TEXTCOLOR', (0, avg_row_index), (-1, avg_row_index), colors.white),
            ('FONTNAME', (0, avg_row_index), (-1, avg_row_index), 'Helvetica-Bold'),
            ('LINEABOVE', (0, avg_row_index), (-1, avg_row_index), 1.5, colors.black),  # Thicker line above averages
        ])
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        # Add measurement note with both asterisk explanations
        elements.append(Spacer(1, 5))
        note = "Note: All distances in yards, speeds in yards/second. 15m mark (16.4042 yards) used for calculations. " \
               "Underwater speed is breakout distance/breakout time. Overwater speed is (25-breakout-0.5)/(last stroke time-breakout time). " \
               "* indicates exceptional value due to race finish. ** indicates first lap underwater speed affected by dive/start."
        
        note_style = ParagraphStyle(
            'Note',
            fontSize=7,
            fontName='Helvetica-Oblique'
        )
        debug_print(f"DEBUG: Extracting user folder from filepath: {filepath}")
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
            "OW Speed: Overwater speed (yards/second)",
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
        
        # Add race metrics plots on the next page
        elements.append(PageBreak())
        
        # Create race metrics plots (for all races)
        race_metrics_buf = create_race_metrics_plots(lap_stats)
        race_metrics_img = Image(race_metrics_buf, width=500, height=250)
        
        # Add title for the race metrics plots
        elements.append(Paragraph("Race Performance Metrics", title_style))
        elements.append(Spacer(1, 10))
        elements.append(race_metrics_img)
        
        # For races up to 200 yards, add stroke-by-stroke analysis
        debug_print(f"DEBUG in generate_pdf_report: data: {data is not None}")
        debug_print(f"DEBUG in generate_pdf_report: 'events' in data: {data and 'events' in data}")
        debug_print(f"DEBUG in generate_pdf_report: distance <= 200: {int(race_details['distance'].value) <= 200}")
        debug_print(f"DEBUG in generate_pdf_report: Condition check: {data and 'events' in data and int(race_details['distance'].value) <= 200}")
        
        if data and 'events' in data and int(race_details['distance'].value) <= 200:
            debug_print("DEBUG: Adding stroke-by-stroke analysis")
            elements.append(PageBreak())
            elements.append(Paragraph("Stroke-by-Stroke Analysis", title_style))
            elements.append(Spacer(1, 10))
            
            try:
                # Add stroke-by-stroke analysis
                debug_print("DEBUG: About to call create_stroke_by_stroke_analysis_elements")
                stroke_analysis_elements = create_stroke_by_stroke_analysis_elements(data, race_details)
                debug_print(f"DEBUG: Got {len(stroke_analysis_elements)} elements back")
                elements.extend(stroke_analysis_elements)
                
                # Add continuous stroke graph across all laps
                debug_print("DEBUG: About to call create_continuous_stroke_graph")
                continuous_stroke_buf = create_continuous_stroke_graph(data, race_details)
                debug_print("DEBUG: Got continuous stroke graph buffer back")
                continuous_stroke_img = Image(continuous_stroke_buf, width=500, height=300)
                elements.append(continuous_stroke_img)
            except Exception as e:
                debug_print(f"ERROR in stroke analysis: {str(e)}")
                import traceback
                traceback.print_exc()
    
    doc.build(elements)

def create_race_metrics_plots(lap_stats):
    """
    Create plots showing underwater speed, overwater speed, and stroke rate across the race.
    Handles cases where underwater speed data might be missing.
    """
    # Check if we have underwater and overwater speed data
    has_uw_data = 'UW Speed' in lap_stats.columns and not lap_stats['UW Speed'].isna().all()
    has_ow_data = 'OW Speed' in lap_stats.columns and not lap_stats['OW Speed'].isna().all()
    has_stroke_data = 'Strokes per Second' in lap_stats.columns and not lap_stats['Strokes per Second'].isna().all()
    
    if (has_uw_data or has_ow_data) and has_stroke_data:
        # Create side-by-side plots if we have both types of data
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
        
        # Filter out rows with missing data
        valid_uw_data = lap_stats.dropna(subset=['UW Speed']) if has_uw_data else pd.DataFrame()
        valid_ow_data = lap_stats.dropna(subset=['OW Speed']) if has_ow_data else pd.DataFrame()
        valid_strk_data = lap_stats.dropna(subset=['Strokes per Second'])
        
        # Plot underwater and overwater speed on the same axis
        if has_uw_data or has_ow_data:
            if has_uw_data:
                ax1.plot(valid_uw_data['Lap'], valid_uw_data['UW Speed'], 
                        marker='o', linestyle='-', color='red', linewidth=2, markersize=8,
                        label='Underwater')
                
                # Add data labels for underwater speed
                for i, row in valid_uw_data.iterrows():
                    ax1.annotate(f"{row['UW Speed']}", 
                                (row['Lap'], row['UW Speed']),
                                xytext=(0, 5), textcoords='offset points',
                                ha='center')
            
            if has_ow_data:
                ax1.plot(valid_ow_data['Lap'], valid_ow_data['OW Speed'], 
                        marker='s', linestyle='-', color='blue', linewidth=2, markersize=8,
                        label='Overwater')
                
                # Add data labels for overwater speed
                for i, row in valid_ow_data.iterrows():
                    ax1.annotate(f"{row['OW Speed']}", 
                                (row['Lap'], row['OW Speed']),
                                xytext=(0, -15), textcoords='offset points',
                                ha='center')
            
            ax1.legend()
        
        # Plot stroke rate
        ax2.plot(valid_strk_data['Lap'], valid_strk_data['Strokes per Second'], 
                marker='o', linestyle='-', color='green', linewidth=2, markersize=8)
        
        # Add data labels for stroke rate
        for i, row in valid_strk_data.iterrows():
            ax2.annotate(f"{row['Strokes per Second']}", 
                        (row['Lap'], row['Strokes per Second']),
                        xytext=(0, 5), textcoords='offset points',
                        ha='center')
        
        # Set titles and labels
        ax1.set_title('Swimming Speed by Lap')
        ax1.set_xlabel('Lap')
        ax1.set_ylabel('Speed (yards/second)')
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(lap_stats['Lap'])
        
        ax2.set_title('Stroke Rate by Lap')
        ax2.set_xlabel('Lap')
        ax2.set_ylabel('Stroke Rate (strokes/second)')
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(lap_stats['Lap'])
    
    elif has_stroke_data:
        # Create only stroke rate plot if that's all we have
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Filter out rows with missing data
        valid_strk_data = lap_stats.dropna(subset=['Strokes per Second'])
        
        # Plot stroke rate
        ax.plot(valid_strk_data['Lap'], valid_strk_data['Strokes per Second'], 
               marker='o', linestyle='-', color='blue', linewidth=2, markersize=8)
        
        # Add data labels for stroke rate
        for i, row in valid_strk_data.iterrows():
            ax.annotate(f"{row['Strokes per Second']}", 
                      (row['Lap'], row['Strokes per Second']),
                      xytext=(0, 5), textcoords='offset points',
                      ha='center')
        
        # Set titles and labels
        ax.set_title('Stroke Rate by Lap')
        ax.set_xlabel('Lap')
        ax.set_ylabel('Stroke Rate (strokes/second)')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(lap_stats['Lap'])
    
    elif has_uw_data:
        # Create only underwater speed plot if that's all we have
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Filter out rows with missing data
        valid_uw_data = lap_stats.dropna(subset=['UW Speed'])
        
        # Plot underwater speed
        ax.plot(valid_uw_data['Lap'], valid_uw_data['UW Speed'], 
               marker='o', linestyle='-', color='red', linewidth=2, markersize=8)
        
        # Add data labels for underwater speed
        for i, row in valid_uw_data.iterrows():
            ax.annotate(f"{row['UW Speed']}", 
                      (row['Lap'], row['UW Speed']),
                      xytext=(0, 5), textcoords='offset points',
                      ha='center')
        
        # Set titles and labels
        ax.set_title('Underwater Speed by Lap')
        ax.set_xlabel('Lap')
        ax.set_ylabel('Underwater Speed (yards/second)')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(lap_stats['Lap'])
    
    else:
        # Create an empty plot with a message if we have neither
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, 'No metrics data available', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.axis('off')
    
    plt.tight_layout()
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf

def generate_batch_reports(base_directory, session=None):
    """
    Generate reports for all swimmers in a directory.
    """
    debug_print(f"Generating batch reports for directory: {base_directory}")
    
    # Initialize counters
    success_count = 0
    failure_count = 0
    skipped_count = 0
    debug_print(f"DEBUG: Starting batch report generation for base directory: {base_directory}")
    # Define the data directories to search
    data_dir = os.path.join("data", base_directory)
    
    # Get all sessions if not specified
    if session:
        sessions = [session]
    else:
        # Look for all session directories
        stroke_turn_dir = os.path.join(data_dir, "stroke_and_turn")
        debug_print(f"DEBUG: Looking for stroke_and_turn directory at: {stroke_turn_dir}")
        if os.path.exists(stroke_turn_dir):
            sessions = [d for d in os.listdir(stroke_turn_dir) 
                      if os.path.isdir(os.path.join(stroke_turn_dir, d))]
        else:
            debug_print(f"Error: Directory {stroke_turn_dir} not found")
            return 0, 0, 0
    
    debug_print(f"Processing sessions: {sessions}")
    
    # Process each session
    for session_name in sessions:
        # Look for CSV files in the stroke_and_turn directory
        stroke_turn_path = os.path.join(data_dir, "stroke_and_turn", session_name)
        debug_print(f"DEBUG: Looking for stroke and turn data at: {stroke_turn_path}")
        if not os.path.exists(stroke_turn_path):
            debug_print(f"Warning: No stroke and turn data found for session {session_name}")
            continue
            
        csv_files = glob.glob(os.path.join(stroke_turn_path, "*.csv"))
        
        # Process each CSV file
        for csv_file in csv_files:
            try:
                # Extract race details from filename
                filename = os.path.basename(csv_file)
                name_parts = filename.replace('.csv', '').split('_')
                
                if len(name_parts) < 4:
                    debug_print(f"Warning: Invalid filename format: {filename}")
                    skipped_count += 1
                    continue
                
                # Parse the filename parts
                # The last part is always the stroke
                stroke = name_parts[-1]
                
                # The second-to-last part is always the distance
                distance = name_parts[-2]
                
                # Check if "relay" is in the parts
                is_relay = "relay" in name_parts
                
                # If relay is present, it affects the position of gender
                if is_relay:
                    # Find the index of "relay"
                    relay_index = name_parts.index("relay")
                    # Gender is before relay
                    gender = name_parts[relay_index-1]
                    # Swimmer name is everything before gender
                    swimmer_name = ' '.join(name_parts[:relay_index-1])
                else:
                    # No relay - gender is the third-to-last part
                    gender = name_parts[-3]
                    # Swimmer name is everything before gender
                    swimmer_name = ' '.join(name_parts[:-3])
                
                # Create a simple class that mimics the behavior of the Enum classes
                class MockEnum:
                    def __init__(self, value):
                        self.value = value
                
                # Create the race details dictionary with mock enum objects
                race_details = {
                    'swimmer_name': swimmer_name,
                    'gender': MockEnum(gender),
                    'distance': MockEnum(int(distance)),
                    'stroke': MockEnum(stroke),
                    'session': MockEnum(session_name),
                    'relay': is_relay
                }
                
                # Generate the report
                relay_text = "Relay " if is_relay else ""
                debug_print(f"Generating report for: {swimmer_name} - {gender} {relay_text}{distance}yd {stroke} ({session_name})")
                
                # Preserve the full directory structure
                data_dir = os.path.join("data", base_directory)
                # Get the relative path from the data directory to the csv_file directory
                relative_path = os.path.dirname(csv_file).replace(data_dir, "").lstrip(os.path.sep)
                debug_print(f"Debug - Base Directory: {base_directory}, Relative Path: {relative_path}")
                # Pass the base directory plus the relative path to maintain structure
                run(race_details, base_directory) #correct directory passed in
                
                success_count += 1
                
            except Exception as e:
                debug_print(f"Error processing {csv_file}: {str(e)}")
                import traceback
                traceback.print_exc()
                failure_count += 1
    
    # Print summary
    debug_print(f"\nBatch report generation complete:")
    debug_print(f"  Success: {success_count}")
    debug_print(f"  Failed: {failure_count}")
    debug_print(f"  Skipped: {skipped_count}")
    
    return success_count, failure_count, skipped_count

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