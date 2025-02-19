import os
import time
from enum import Enum
import pandas as pd
import keyboard
#from reporting import print_summary, generate_pdf_report

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

class Session(Enum):
    PRELIMS = "prelims"
    FINALS = "finals"

def record_race_strokes_and_turns(swimmer, race_details, session, stroke):
    """
    Record race events via keyboard clicks.
    The very first 'p' press starts the race (time zero).
    Each subsequent key press records events:
    - k key: records strokes
    - Enter key: records turn events (alternates between turn_start and turn_end)
    - p key: ends recording and records final time
    Returns a list of dictionaries with event times and types.
    """
    # Check if file exists and request overwrite confirmation
    directory, filename, filepath = make_file_info(swimmer, race_details, session)
    
    if os.path.exists(filepath):
        confirm = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
    
    events = []
    turn_state = "start"  # Will alternate between "start" and "end"
    
    print("\nInstructions:")
    print("- Press p to start the race: ")
    print("- Press k for strokes")
    print("- Press ENTER for turn events  (press once for hands and once for pushoff on breaststroke or butterfly)")
    print("- Press p again for race finish")
    print()

    # Wait for 'p' to start race
    while True:
        event = keyboard.read_event(suppress=True)
        if event.event_type == 'down' and event.name == 'p':
            start_time = time.time()
            events.append({"type": "start", "time": 0.0})
            print("Race started!")
            break

    while True:
        event = keyboard.read_event(suppress=True)
        if event.event_type != 'down':  # Only process key down events
            continue
            
        event_time = time.time() - start_time
        
        if event.name == "k":  # k key for strokes
            events.append({"type": "stroke", "time": event_time})
            print(f"Recorded stroke at {event_time:.2f} seconds")
        elif event.name == "enter":  # Enter key for turns
            events.append({"type": f"turn_{turn_state}", "time": event_time})
            print(f"Recorded turn {turn_state} at {event_time:.2f} seconds")
            turn_state = "end" if turn_state == "start" else "start"  # Toggle state
        elif event.name == "p":
            events.append({"type": "end", "time": event_time})
            print(f"Recorded final time at {event_time:.2f} seconds")
            break

    print(f"Race recording completed. Total events recorded: {len(events)}")
    
    save_data(swimmer, race_details, session, {"events": events}, data_type="stroke_and_turn")
    return events

def enter_break_and_fifteen_data(swimmer, race_details, session):
    """
    Manually enter breakout times, distances, and 15m times for each lap.
    """

    # Check if file exists and request overwrite confirmation
    directory, filename, filepath = make_file_info(swimmer, race_details, session, data_type="break_and_fifteen")
    
    if os.path.exists(filepath):
        confirm = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
        
    data = {
        "breakout_times": [],
        "breakout_distances": [],
        "fifteen_times": []
    }
    
    # Calculate number of laps based on race distance
    num_laps = race_details['distance'].value // 25  
    
    print(f"\nEntering data for {num_laps} laps:")
    
    for lap in range(num_laps):
        print(f"\nLap {lap + 1}:")
        try:
            breakout_time = float(input(f"Enter breakout time for lap {lap + 1} (seconds): ").strip())
            breakout_distance = float(input(f"Enter breakout distance for lap {lap + 1} (meters): ").strip())
            fifteen_time = float(input(f"Enter 15m time for lap {lap + 1} (seconds): ").strip())
            
            data["breakout_times"].append(breakout_time)
            data["breakout_distances"].append(breakout_distance)
            data["fifteen_times"].append(fifteen_time)
        except ValueError:
            print("Invalid input. Please enter numeric values.")
            # Reset to start of current lap
            if len(data["breakout_times"]) > lap:
                data["breakout_times"].pop()
            if len(data["breakout_distances"]) > lap:
                data["breakout_distances"].pop()
            if len(data["fifteen_times"]) > lap:
                data["fifteen_times"].pop()
            lap -= 1
            continue

    print("\nBreakout and 15m data recorded successfully.")
    save_data(swimmer, race_details, session, data, data_type="break_and_fifteen")

def save_data(swimmer, race_details, session, data, data_type):
    """
    Save race data to a CSV file in the appropriate directory based on data type.
    """
    # Check if file exists and confirm overwrite
    directory, filename, filepath = make_file_info(swimmer, race_details, session, data_type)
    
    if os.path.exists(filepath):
        confirm = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
    
    # Save as CSV
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"Data saved to {filepath}")

def make_file_info(swimmer, race_details, session, data_type):
    """
    Create file information based on data type.
    """
    if data_type == "stroke_and_turn":
        directory = os.path.join("data", "stroke_and_turn_data", session.value)
    elif data_type == "break_and_fifteen":
        directory = os.path.join("data", "15_and_break_data", session.value)
    else:
        directory = os.path.join("data", session.value)
    
    os.makedirs(directory, exist_ok=True)
    filename = f"{swimmer.replace(' ', '_')}_{race_details['gender'].value}_{race_details['distance'].value}_{race_details['stroke'].value}.csv"
    filepath = os.path.join(directory, filename)

    return (directory, filename, filepath)

def parse_race_details():
    """
    Prompt user for race details and return a dictionary with gender, distance, stroke, and session.
    """
    print("\nPlease enter race details:")
    
    gender_input = input("Select gender (m/f): ").strip().lower()
    gender = Gender.MEN if gender_input == "m" else Gender.WOMEN
    
    session_input = input("Prelims or Finals? (p/f): ").strip().lower()
    session = Session.PRELIMS if session_input == "p" else Session.FINALS
    
    # Get distance
    print("Select distance:")
    print("1. 50m")
    print("2. 100m")
    print("3. 200m")
    print("4. 400m")
    print("5. 500m")
    print("6. 1000m")
    print("7. 1650m")
    distance_input = input("Enter choice (1-7): ").strip()

    distance_map = {
        "1": Distance.D50,
        "2": Distance.D100,
        "3": Distance.D200,
        "4": Distance.D400,
        "5": Distance.D500,
        "6": Distance.D1000,
        "7": Distance.D1650
    }
    distance = distance_map.get(distance_input, Distance.D50)
    
    print("Select stroke:")
    print("1. Butterfly")
    print("2. Backstroke") 
    print("3. Breaststroke")
    print("4. Freestyle")
    print("5. IM")
    stroke_input = input("Enter choice (1-5): ").strip()

    stroke_map = {
        "1": Stroke.BUTTERFLY,
        "2": Stroke.BACKSTROKE,
        "3": Stroke.BREASTSTROKE,
        "4": Stroke.FREESTYLE,
        "5": Stroke.IM
    }
    stroke = stroke_map.get(stroke_input, Stroke.FREESTYLE)
    
    return {
        "gender": gender,
        "distance": distance,
        "stroke": stroke,
        "session": session
    }

def main():
    # Ask for swimmer name
    swimmer = input("Enter swimmer's name: ").strip()
    
    # Get race details
    race_details = parse_race_details()

    # Ask if user wants to record a race or manually enter data
    print("\nPlease select an option:")
    print("1. Record a Race")
    print("2. Enter breakout and 15 meter data")
    action = input("Enter choice (1 or 2): ").strip()
    action = "record" if action == "1" else "manual"
    
    if action == "record":
        print("\n--- Race Event Recording ---")
        record_race_strokes_and_turns(swimmer, race_details, race_details['session'], race_details['stroke'])
    elif action == "manual":
        print("\n--- Manual Data Entry ---")
        enter_break_and_fifteen_data(swimmer, race_details, race_details['session'])
    else:
        print("Invalid action. Please enter 'record' or 'manual'.")

if __name__ == "__main__":
    main()
