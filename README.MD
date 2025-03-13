# Swimming Race Analysis Tool

A Python application for recording and analyzing swimming race data, including stroke timing, turn events, breakouts, and 15-meter splits.

## Features

### Race Recording
Record race events in real-time using keyboard inputs:
- Press 'p' to start and end the race
- Press 'k' to record each stroke
- Press 'Enter' to record turn events
  - For breaststroke/butterfly: Press once for hands touching, once for feet touching
  - For freestyle/backstroke: Single press for flip turn

### Manual Data Entry
Enter additional race metrics after recording:
- Breakout times for each lap
- Breakout distances (in meters)
- 15-meter split times

### Data Storage
- All data is automatically saved to CSV files
- Organized by session type (prelims/finals)
- Separate storage for stroke/turn data and breakout/15m data
- Files named by swimmer, gender, distance, and stroke

### Race Categories
Supports all standard swimming events:
- Distances: 50m, 100m, 200m, 400m, 500m, 1000m, 1650m
- Strokes: Freestyle, Butterfly, Breaststroke, Backstroke, Individual Medley
- Sessions: Preliminaries and Finals
- Gender: Men's and Women's events

## Usage

1. Run the program and enter swimmer's name
2. Select race details:
   - Gender (m/f)
   - Session (prelims/finals)
   - Distance
   - Stroke
3. Choose recording mode:
   - Race recording (stroke and turn events)
   - Manual data entry (breakouts and 15m times)

## Data Analysis (Coming Soon)
Future updates will include:
- Automated calculation of underwater times
- Stroke count analysis
- Turn time analysis
- Race segment breakdowns
- Visual data representation
- PDF report generation

### Try -->
- More metrics (over water speed, ...)
- graph over water speed next to underwater speed
- change asterisk locations