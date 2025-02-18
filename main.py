#!/usr/bin/env python3
import time
from enum import Enum
from reporting import print_summary, generate_pdf_report

class Stroke(Enum):
    FREESTYLE = "freestyle"
    BUTTERFLY = "butterfly"
    BREASTSTROKE = "breaststroke"
    BACKSTROKE = "backstroke"
    IM = "im"

class Gender(Enum):
    MEN = "men"
    WOMEN = "women"

class Distance(Enum):
    D50 = 50
    D100 = 100
    D200 = 200
    D400 = 400
    D500 = 500
    D1000 = 1000
    D1650 = 1650

def record_race_events(stroke, record_fifteen=False):
    """
    Record race events via keyboard clicks.
    The very first Enter press starts the race (time zero).
    Each subsequent key press records events:
    - Enter: records strokes
    - l key: records turn events (alternates between turn_start and turn_end, 
             with breakout automatically recorded after turn_end)
    - p key: ends recording and records final time
    Returns a list of dictionaries with event times and types.
    """
    events = []
    turn_state = "start"  # Will alternate between "start" and "end"
    
    print("\nInstructions:")
    print("- Press ENTER to record race start: ")
    print("- Press ENTER for water entry (when head enters water): ")
    print("- Press ENTER for breakouts (when head exits water)")
    print("- Press ENTER for strokes")
    print("- Press l for turn events  (press once for hands and once for pushoff on breaststroke or butterfly)")
    print("- Press p for race finish")
    print()

    input()
    start_time = time.time()
    events.append({"type": "start", "time": 0.0})
    print("Race started!")
    
    # Record water entry (always second event)
    input()
    water_entry_time = time.time() - start_time
    events.append({"type": "water_entry", "time": water_entry_time})
    print(f"Recorded water entry at {water_entry_time:.2f} seconds")
    
    while True:
        inp = input().strip()
        event_time = time.time() - start_time
        
        if inp == "":  # Enter key
            events.append({"type": "stroke", "time": event_time})
            print(f"Recorded stroke at {event_time:.2f} seconds")
        elif inp == "l":
            if stroke in [Stroke.FREESTYLE, Stroke.BACKSTROKE]:
                # For freestyle and backstroke, only one turn event
                events.append({"type": "turn_end", "time": event_time})
                print(f"Recorded turn end at {event_time:.2f} seconds")
                # Automatically record breakout after turn
                breakout_time = time.time() - start_time
                events.append({"type": "breakout", "time": breakout_time})
                print(f"Recorded breakout at {breakout_time:.2f} seconds")
            else:
                # For other strokes, alternate between start and end
                events.append({"type": f"turn_{turn_state}", "time": event_time})
                print(f"Recorded turn {turn_state} at {event_time:.2f} seconds")
                if turn_state == "end":
                    # Automatically record breakout after turn_end
                    breakout_time = time.time() - start_time
                    events.append({"type": "breakout", "time": breakout_time})
                    print(f"Recorded breakout at {breakout_time:.2f} seconds")
                turn_state = "end" if turn_state == "start" else "start"  # Toggle state
        elif inp == "p":
            events.append({"type": "end", "time": event_time})
            print(f"Recorded final time at {event_time:.2f} seconds")
            break
        else:
            print("Invalid input. Press Enter for strokes, l for turns, p to end.")
            continue
            
    print(f"Race recording completed. Total events recorded: {len(events)}")
    return events

def compute_underwater_times(breakouts, turn_ends, race_start_time=0.0, water_entry_time=0.0):
    """
    Compute underwater times based on breakout events.
    For the first breakout, underwater time = breakout time - water entry time.
    For subsequent breakouts, underwater time = breakout time - previous turn end.
    """
    underwater_times = []
    for i, breakout in enumerate(breakouts):
        if i == 0:
            lap_start = water_entry_time
        elif i - 1 < len(turn_ends):
            lap_start = turn_ends[i - 1]["time"]
        else:
            lap_start = breakout["time"]
        underwater_times.append(breakout["time"] - lap_start)
    return underwater_times

def process_events(raw_events):
    """
    Process raw events and compute all relevant statistics.
    """
    data = {}
    
    # Extract key events
    start_event = next((e for e in raw_events if e["type"] == "start"), None)
    end_event = next((e for e in raw_events if e["type"] == "end"), None)
    water_entry_event = next((e for e in raw_events if e["type"] == "water_entry"), None)
    
    if not start_event or not end_event:
        raise ValueError("Missing start or end event.")
    
    race_start_time = start_event["time"]
    race_end_time = end_event["time"]
    data["total_time"] = race_end_time
    data["water_entry_time"] = water_entry_event["time"] if water_entry_event else None

    # Breakout events
    breakouts = [e for e in raw_events if e["type"] == "breakout"]
    data["breakouts"] = breakouts
    if breakouts:
        data["avg_breakout_distance"] = sum(b.get("extra", {}).get("distance", 0.0) for b in breakouts) / len(breakouts)
        data["avg_breakout_time"] = sum(b["time"] for b in breakouts) / len(breakouts)
    else:
        data["avg_breakout_distance"] = None
        data["avg_breakout_time"] = None

    # Turn events
    turn_starts = [e for e in raw_events if e["type"] == "turn_start"]
    turn_ends = [e for e in raw_events if e["type"] == "turn_end"]
    data["turn_starts"] = turn_starts
    data["turn_ends"] = turn_ends
    if turn_starts and turn_ends and (len(turn_starts) == len(turn_ends)):
        turn_times = [te["time"] - ts["time"] for ts, te in zip(turn_starts, turn_ends)]
        data["turn_times"] = turn_times
        data["avg_turn_time"] = sum(turn_times) / len(turn_times)
    else:
        data["turn_times"] = []
        data["avg_turn_time"] = None

    # Stroke events - use events encoded as "stroke"
    strokes = [e for e in raw_events if e["type"] == "stroke"]
    data["strokes"] = strokes
    if len(strokes) > 1:
        stroke_intervals = [strokes[i]["time"] - strokes[i-1]["time"] for i in range(1, len(strokes))]
        data["stroke_intervals"] = stroke_intervals
        data["avg_stroke_interval"] = sum(stroke_intervals) / len(stroke_intervals)
    else:
        data["stroke_intervals"] = []
        data["avg_stroke_interval"] = None

    # Underwater times based on breakouts and turn events
    data["underwater_times"] = compute_underwater_times(breakouts, turn_ends, race_start_time)
    if data["underwater_times"]:
        data["avg_underwater_time"] = sum(data["underwater_times"]) / len(data["underwater_times"])
    else:
        data["avg_underwater_time"] = None

    # Optionally, record 15m event if present in events
    fifteen_event = next((e for e in raw_events if e["type"] == "fifteen"), None)
    data["fifteen_time"] = fifteen_event["time"] if fifteen_event else None
    
    return data

def parse_race_details(race_details):
    """
    Parse race details string in format "Gender's Distance Stroke"
    e.g. "Men's 50 Freestyle" or "Women's 200 Breaststroke"
    Returns dictionary with gender, distance, and stroke
    """
    try:
        # Split into parts and clean up
        parts = race_details.strip().split()
        
        # Get gender (remove 's)
        gender_str = parts[0].lower().replace("'s", "")
        gender = Gender(gender_str)
        
        # Get distance (should be a number)
        distance = int(parts[1])
        distance_enum = Distance(f"D{distance}")
        
        # Get stroke (rest of the string)
        stroke_str = " ".join(parts[2:]).lower()
        stroke = Stroke(stroke_str)
        # Print successful parsing details
        print(f"Successfully parsed race details:")
        print(f"  Gender: {gender.value}")
        print(f"  Distance: {distance}m")
        print(f"  Stroke: {stroke.value}")
        return {
            "gender": gender,
            "distance": distance_enum,
            "stroke": stroke
        }
    except Exception as e:
        raise ValueError(f"Invalid race details format. Expected 'Gender's Distance Stroke'. Error: {str(e)}")

def main():
    # Ask for swimmer name and race details
    swimmer = input("Enter swimmer's name: ").strip()
    race_details_input = input("Enter race details (e.g. Men's 50 Freestyle): ").strip()
    
    race_details = parse_race_details(race_details_input)

    # Ask if user wants to record 15m marks during the race
    record_fifteen = input("Do you want to record 15m marks during the race? (y/n): ").strip().lower() == 'y'

    # --- Phase 1: Race Event Recording ---
    print("\n== Race Event Recording ==")
    raw_events = record_race_events(race_details['stroke'], record_fifteen)

    # Extract all relevant statistics from raw_events
    data = process_events(raw_events)

    # Print the summary and generate the PDF report
    print_summary(swimmer, race_details, data)
    generate_pdf_report(swimmer, race_details, data)

if __name__ == "__main__":
    main()
