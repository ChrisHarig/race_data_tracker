import os
import time
from enum import Enum
import pandas as pd
import keyboard
import reporting

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

def record_race_strokes_and_turns(race_details, base_directory):
    """
    Record race events via keyboard clicks.
    The very first 'p' press starts the race (time zero).
    Each subsequent key press records events:
    - w key: records water entry
    - k key: records strokes
    - Enter key: records turn events (alternates between turn_start and turn_end)
    - p key: ends recording and records final time
    Returns a list of dictionaries with event times and types.
    """
    # Check if file exists and request overwrite confirmation
    directory, filename, filepath = make_file_info(race_details, "stroke_and_turn", base_directory)
    
    if os.path.exists(filepath):
        confirm = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
    
    events = []

    # Always turn_end if freestyle or backstroke, otherwise turn_start
    turn_state = "start" if race_details['stroke'] == Stroke.BREASTSTROKE or race_details['stroke'] == Stroke.BUTTERFLY else "end"  
    
    print("\nInstructions:")
    print("- Press p to start the race: ")
    print("- Press w for water entry (required as second event)")
    print("- Press k for strokes")
    print("- Press ENTER for turn events (press once for hands and once for pushoff on breaststroke or butterfly)")
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

    # Water entry is second event
    while True:
        event = keyboard.read_event(suppress=True)
        if event.event_type == 'down' and event.name == 'w':
            event_time = time.time() - start_time
            events.append({"type": "water_entry", "time": event_time})
            print(f"Recorded water entry at {event_time:.2f} seconds")
            break
        elif event.event_type == 'down':  # Ignore any other keys
            print("Please record water entry first (press 'w')")

    # Continue with rest of race events
    while True:
        event = keyboard.read_event(suppress=True)
        if event.event_type != 'down':  # Only process key down events
            continue
            
        event_time = time.time() - start_time
        
        if event.name == "k":  # k key for strokes
            events.append({"type": "stroke", "time": event_time})
            print(f"Recorded stroke at {event_time:.2f} seconds")
        elif event.name == "enter":  # Enter key for turns
            if race_details['stroke'] == Stroke.IM:
                # Check if last event was a turn
                if events and events[-1]['type'] == "turn_end":
                    # If we get another turn, mark the first as start and this as end
                    events[-1]['type'] = "turn_start"
                    events.append({"type": "turn_end", "time": event_time})
                    print(f"Recorded turn sequence (start/end) ending at {event_time:.2f} seconds")
                else:
                    # Otherwise just record a turn_end
                    events.append({"type": "turn_end", "time": event_time})
                    print(f"Recorded turn end at {event_time:.2f} seconds")
            elif race_details['stroke'] in [Stroke.BREASTSTROKE, Stroke.BUTTERFLY]:
                events.append({"type": f"turn_{turn_state}", "time": event_time})
                print(f"Recorded turn {turn_state} at {event_time:.2f} seconds")
                turn_state = "end" if turn_state == "start" else "start"
            else:  # Freestyle or Backstroke
                events.append({"type": "turn_end", "time": event_time})
                print(f"Recorded turn end at {event_time:.2f} seconds")
        elif event.name == "p": # p for race end
            events.append({"type": "end", "time": event_time})
            print(f"Recorded final time at {event_time:.2f} seconds")
            break

    print(f"Race recording completed. Total events recorded: {len(events)}")
    
    save_data(events, filepath)
    return events

def enter_break_and_fifteen_data(race_details, base_directory):
    """
    Manually enter breakout times, distances, and 15m times for each lap.
    """
    # Check if file exists and request overwrite confirmation
    directory, filename, filepath = make_file_info(race_details, "break_and_fifteen", base_directory)
    
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
            breakout_distance = float(input(f"Enter breakout distance for lap {lap + 1} (yards): ").strip())
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
    save_data(data, filepath)

def save_data(data, filepath):
    """
    Save race data to a CSV file in the appropriate directory based on data type.
    """
    # Already asked user for confirmation of overwrite if file exists, so just save file
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"Data saved to {filepath}")

def make_file_info(race_details, data_type, base_directory):
    """
    Create file information based on data type and user-defined base directory.
    """
    # Construct the directory path based on user input and data type
    directory = os.path.join(base_directory, data_type, race_details['session'].value)
    
    os.makedirs(directory, exist_ok=True)
    filename = f"{race_details['swimmer_name'].replace(' ', '_')}_{race_details['gender'].value}_{race_details['distance'].value}_{race_details['stroke'].value}.csv"
    filepath = os.path.join(directory, filename)

    return (directory, filename, filepath)

def parse_race_details():
    """
    Prompt user for race details and return a dictionary with swimmer's name, gender, distance, stroke, session, and relay status.
    """
    print("\nPlease enter race details:")
    
    # Ask for swimmer name
    while True:
        swimmer_name = input("Enter swimmer's name: ").strip()
        if swimmer_name:  # Check if name is not empty
            break
        print("Please enter a valid name.")
    
    # Get gender
    while True:
        gender_input = input("Select gender (m/f): ").strip().lower()
        if gender_input in ['m', 'f']:
            gender = Gender.MEN if gender_input == "m" else Gender.WOMEN
            break
        print("Invalid input. Please enter 'm' for men or 'f' for women.")
    
    # Get relay status
    while True:
        relay_input = input("Is this a relay? (y/n): ").strip().lower()
        if relay_input in ['y', 'n']:
            relay = relay_input == 'y'
            break
        print("Invalid input. Please enter 'y' for yes or 'n' for no.")
    
    # Get session
    while True:
        session_input = input("Prelims or Finals? (p/f): ").strip().lower()
        if session_input in ['p', 'f']:
            session = Session.PRELIMS if session_input == "p" else Session.FINALS
            break
        print("Invalid input. Please enter 'p' for prelims or 'f' for finals.")
    
    # Get distance
    distance_map = {
        "1": Distance.D50,
        "2": Distance.D100,
        "3": Distance.D200,
        "4": Distance.D400,
        "5": Distance.D500,
        "6": Distance.D1000,
        "7": Distance.D1650
    }
    
    while True:
        print("Select distance:")
        print("1. 50m")
        print("2. 100m")
        print("3. 200m")
        print("4. 400m")
        print("5. 500m")
        print("6. 1000m")
        print("7. 1650m")
        distance_input = input("Enter choice (1-7): ").strip()
        
        if distance_input in distance_map:
            distance = distance_map[distance_input]
            break
        print("Invalid choice. Please enter a number between 1 and 7.")
    
    # Get stroke
    stroke_map = {
        "1": Stroke.BUTTERFLY,
        "2": Stroke.BACKSTROKE,
        "3": Stroke.BREASTSTROKE,
        "4": Stroke.FREESTYLE,
        "5": Stroke.IM
    }
    
    while True:
        print("Select stroke:")
        print("1. Butterfly")
        print("2. Backstroke") 
        print("3. Breaststroke")
        print("4. Freestyle")
        print("5. IM")
        stroke_input = input("Enter choice (1-5): ").strip()
        
        if stroke_input in stroke_map:
            stroke = stroke_map[stroke_input]
            break
        print("Invalid choice. Please enter a number between 1 and 5.")
    
    return {
        "swimmer_name": swimmer_name,
        "gender": gender,
        "distance": distance,
        "stroke": stroke,
        "session": session,
        "relay": relay
    }

def generate_report(race_details, base_directory):
    """
    Generate a report for the given race details.
    """
    reporting.run(race_details, base_directory)

def confirm_action(action_description):
    """
    Ask the user to confirm an action before proceeding.
    
    Args:
        action_description (str): Description of the action to confirm
        
    Returns:
        bool: True if user confirms, False otherwise
    """
    while True:
        confirm = input(f"Confirm {action_description}? (y/n): ").strip().lower()
        if confirm == 'y':
            return True
        elif confirm == 'n':
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def main():
    race_details = None
    base_directory = None
    
    while True:
        # If we don't have race details from a previous run, get them
        if not race_details:
            print("\nPlease select an option:")
            print("1. Record a Race")
            print("2. Enter breakout and 15 meter data")
            print("3. Generate a Report")
            print("4. Exit")
            action = input("Enter choice (1-4): ").strip()
            
            if action == "4":
                print("Goodbye!")
                break
                
            if action not in ["1", "2", "3"]:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
                continue
            
            try:
                race_details = parse_race_details()
                base_directory = input("Enter the base directory for saving data (e.g., 'user_dir_1/user_sub_dir_1'/...): ").strip()
                base_directory = os.path.join("data", base_directory)
                
                # Confirm race details after entry
                print("\nRace details:", 
                      f"\nSwimmer: {race_details['swimmer_name']}"
                      f"\nGender: {race_details['gender'].value}"
                      f"\nRelay: {'Yes' if race_details.get('relay', False) else 'No'}"
                      f"\nDistance: {race_details['distance'].value}"
                      f"\nStroke: {race_details['stroke'].value}"
                      f"\nSession: {race_details['session'].value}"
                      f"\nDirectory: {base_directory}")
                
                if not confirm_action("these race details"):
                    race_details = None
                    print("Race details cancelled. Returning to main menu.")
                    continue
                
            except ValueError as e:
                print(f"Error: {e}")
                continue
        else:
            # We have race details from before, ask if user wants to reuse them
            print("\nPrevious race details:", 
                  f"\nSwimmer: {race_details['swimmer_name']}"
                  f"\nGender: {race_details['gender'].value}"
                  f"\nRelay: {'Yes' if race_details.get('relay', False) else 'No'}"
                  f"\nDistance: {race_details['distance'].value}"
                  f"\nStroke: {race_details['stroke'].value}"
                  f"\nSession: {race_details['session'].value}")
            
            print("\nPlease select an option:")
            print("1. Record a Race")
            print("2. Enter breakout and 15 meter data")
            print("3. Generate a Report")
            print("4. Start new race details")
            print("5. Exit")
            action = input("Enter choice (1-5): ").strip()
            
            if action == "5":
                print("Goodbye!")
                break
            
            if action == "4":
                race_details = None
                continue
                
            if action not in ["1", "2", "3"]:
                print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                continue
        
        try:
            if action == "1":
                print("\n--- Race Event Recording ---")
                record_race_strokes_and_turns(race_details, base_directory)
                # Confirm after recording is complete
                if confirm_action("save this race recording"):
                    print("\nRace recording saved successfully!")
                else:
                    print("Race recording discarded.")
                    # Here you might want to add code to delete the saved file
            elif action == "2":
                print("\n--- Manual Data Entry ---")
                enter_break_and_fifteen_data(race_details, base_directory)
                # Confirm after data entry is complete
                if confirm_action("save this breakout and 15m data"):
                    print("\nBreakout and 15m data saved successfully!")
                else:
                    print("Breakout and 15m data discarded.")
                    # Here you might want to add code to delete the saved file
            elif action == "3":
                print("\n--- Generating Report ---")
                generate_report(race_details, base_directory)
                print("\nReport generated successfully!")
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("Returning to main menu...")
            continue

if __name__ == "__main__":
    main()
