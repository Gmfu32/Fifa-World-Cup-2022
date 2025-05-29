# importing libraries
from flask import Flask, render_template, request
import pandas as pd
import os 
import datetime 

app = Flask(__name__)

# converting the date col
def format_time_to_ampm(time_str):
    if not isinstance(time_str, str) or ':' not in time_str:
        return "N/A" 
    try:
        cleaned_time_str = "".join(time_str.split()) 
        time_obj = datetime.datetime.strptime(cleaned_time_str, "%H:%M").time()
        return time_obj.strftime("%I:%M %p") 
    except ValueError:
        return time_str 


# loading the CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(BASE_DIR, 'Fifa_world_cup_matches.csv')

try:
    df = pd.read_csv(CSV_FILE_PATH)
    print(f"Successfully loaded CSV: {CSV_FILE_PATH}")

    # clean team names for consistent matching
    if 'team1' in df.columns:
        df['team1'] = df['team1'].str.strip()
    if 'team2' in df.columns:
        df['team2'] = df['team2'].str.strip()

    possession_cols = ['possession team1', 'possession team2']
    for col in possession_cols:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.rstrip('%').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'number of goals team1' in df.columns:
        df['number of goals team1'] = pd.to_numeric(df['number of goals team1'], errors='coerce').fillna(0).astype(int)
    if 'number of goals team2' in df.columns:
        df['number of goals team2'] = pd.to_numeric(df['number of goals team2'], errors='coerce').fillna(0).astype(int)

    # populate teams_list for dropdowns
    if 'team1' in df.columns and 'team2' in df.columns:
        unique_team_names_team1 = df['team1'].dropna().unique()
        unique_team_names_team2 = df['team2'].dropna().unique()
        all_unique_team_names = pd.concat([pd.Series(unique_team_names_team1), pd.Series(unique_team_names_team2)]).dropna().unique()
        teams_list = sorted([str(team).strip() for team in all_unique_team_names])
        print(f"Debug: Teams loaded for dropdown: {teams_list}") 
    else:
        teams_list = ["Error: Team columns not found"]
        print("Error: 'team1' or 'team2' columns not found in the DataFrame.")

except FileNotFoundError:
    print(f"Error: The file '{CSV_FILE_PATH}' was not found.")
    df = pd.DataFrame()
    teams_list = ["Error: CSV file not found"]
except Exception as e:
    print(f"Error loading or processing CSV data: {e}")
    df = pd.DataFrame()
    teams_list = ["Error: Could not process CSV data"]

def get_flag_filename(team_name_str):
    if not isinstance(team_name_str, str) or not team_name_str.strip():
        print(f"Debug (get_flag_filename): Invalid or empty team_name_str: '{team_name_str}'")
        return None 
    
    team_name_processed = team_name_str.upper().strip()
    generated_filename = f"{team_name_processed}_flag.webp" 
    
    print(f"Debug (get_flag_filename): For team '{team_name_str}', processed as '{team_name_processed}', generated filename: '{generated_filename}'")
    return generated_filename


@app.route('/', methods=['GET'])
def index():
    current_year = datetime.datetime.now().year
    return render_template('index.html', teams=teams_list, result=None, year=current_year)

@app.route('/get_match_result', methods=['POST'])
def get_match_result():
    current_year = datetime.datetime.now().year
    if df.empty:
        return render_template('index.html', teams=teams_list, result={'error': 'Data could not be loaded.'}, year=current_year)

    selected_team1 = request.form.get('team1')
    selected_team2 = request.form.get('team2')
    
    print(f"Debug (get_match_result): Selected Team 1 from form: '{selected_team1}'")
    print(f"Debug (get_match_result): Selected Team 2 from form: '{selected_team2}'")

    if not selected_team1 or not selected_team2:
        return render_template('index.html', teams=teams_list, result={'error': 'Please select both teams.'}, year=current_year)

    if selected_team1 == selected_team2:
        return render_template('index.html', teams=teams_list, result={'error': 'Please select two different teams.'}, year=current_year)

    selected_team1_cleaned = selected_team1.strip()
    selected_team2_cleaned = selected_team2.strip()

    match_data = df[
        ((df['team1'].str.upper() == selected_team1_cleaned.upper()) & (df['team2'].str.upper() == selected_team2_cleaned.upper())) |
        ((df['team1'].str.upper() == selected_team2_cleaned.upper()) & (df['team2'].str.upper() == selected_team1_cleaned.upper()))
    ]

    if match_data.empty:
        result_display = {
            'error': f"No match found between {selected_team1} and {selected_team2}."
        }
    else:
        match = match_data.iloc[0]

        team1_name_for_display = selected_team1 
        team2_name_for_display = selected_team2

        actual_match_team1 = match['team1'] 
        actual_match_team2 = match['team2']

        if actual_match_team1.upper() == selected_team1_cleaned.upper():
            score1 = match['number of goals team1']
            score2 = match['number of goals team2']
            possession1 = match.get('possession team1', 'N/A')
            possession2 = match.get('possession team2', 'N/A')
        else: 
            score1 = match['number of goals team2']
            score2 = match['number of goals team1']
            possession1 = match.get('possession team2', 'N/A')
            possession2 = match.get('possession team1', 'N/A')
        
        original_hour = match.get('hour', 'N/A')
        formatted_hour = format_time_to_ampm(original_hour) 

        team1_flag_file = get_flag_filename(team1_name_for_display)
        team2_flag_file = get_flag_filename(team2_name_for_display)

        result_display = {
            'team1': team1_name_for_display,
            'team2': team2_name_for_display,
            'team1_flag_filename': team1_flag_file, 
            'team2_flag_filename': team2_flag_file, 
            'score1': int(score1) if pd.notna(score1) else 'N/A',
            'score2': int(score2) if pd.notna(score2) else 'N/A',
            'date': match.get('date', 'N/A'),
            'hour': formatted_hour, 
            'possession_team1': f"{possession1:.0f}" if pd.notna(possession1) and isinstance(possession1, (int, float)) else possession1,
            'possession_team2': f"{possession2:.0f}" if pd.notna(possession2) and isinstance(possession2, (int, float)) else possession2,
            'error': None
        }

    return render_template('index.html', teams=teams_list, result=result_display, year=current_year)

if __name__ == '__main__':
    app.run(debug=True)



