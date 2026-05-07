import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd

# 1. Place this at the top of your script
st.set_page_config(page_title="N64 Leaderboard", layout="wide")

# 2. Inject the CSS
st.markdown(
    """
    <style>
    /* Target the main Streamlit container */
    [data-testid="stAppViewContainer"]::before {
        content: " ";
        display: block;
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                    linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
        z-index: 999999;
        background-size: 100% 4px, 3px 100%;
        pointer-events: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)
#st_autorefresh(interval=60000)  # Refresh every 60 seconds
st.set_page_config(page_title="N64 LEADERBOARD", layout="wide")

# Cache downloaded image bytes so the app is faster on reruns
@st.cache_data(ttl=3600)
def download_image_bytes(url):
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content

# 1. Setup Connection
conn = st.connection("gsheets_players", type=GSheetsConnection)
#conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Read Data (Replace with your actual public URL)
# Hint: Ensure your Sheet has columns: Name, Points, Bio, Image_URL, Game_Played, Result
#df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1ns0sXbWEQtfNcPQ8HZ6tYLyQYCdtDdQb6cVLqbUZdwM/edit?usp=sharing", ttl="0") 
df = conn.read(ttl="0")

# 3. Custom CSS for the N64 "Vibe"
st.markdown("""
    <style>
    /* Retro Pixel Font (Import from Google Fonts) */
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Press Start 2P', cursive;
    }
    
    .stApp {
        background: linear-gradient(135deg, #01009A 0%, #111111 100%);
    }

    /* Constrain the app body to around 65% width */
    div[data-testid="stAppViewContainer"] section .main > div,
    div[data-testid="stAppViewContainer"] section .block-container,
    div[data-testid="stAppViewContainer"] section .css-18e3th9,
    div[data-testid="stAppViewContainer"] section .css-1outpf7 {
        max-width: 65% !important;
        width: 65% !important;
        margin: 0 auto !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    /* Player Cards styling */
    .player-card {
        border: 4px solid #F5B201;
        padding: 5px;
        border-radius: 5px;
        background-color: rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }

    .player-name {
        text-align: center;
    }
            
    .player-points {
        text-align: center;
    }

    /* Match table styling */
    .match-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }

    .match-table th, .match-table td {
        border: 2px solid #F5B201;
        padding: 2px;
        text-align: center;
        background-color: rgba(255, 255, 255, 0.1);
    }

    .match-table th {
        background-color: rgba(245, 181, 1, 0.2);
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

#st.title("🎮 N64 LEADERBOARD")
st.title("N64 LEADERBOARD")

# --- 3. THE ROW DISPLAY ---
st.subheader("CURRENT STANDINGS")

# Import here to avoid repetition
import requests
from io import BytesIO
from PIL import Image, ImageOps

# Calculate min and max points for URL selection
min_points = df['Points'].min()
max_points = df['Points'].max()

#first row check
start_images = False

# Determine benched players from match data
benched_players = set()
try:
    conn2 = st.connection("gsheets_matches", type=GSheetsConnection)
    dfm = conn2.read()
    pivot_df = dfm.pivot(
        index=['Game_ID', 'Game_Title', 'Round_No'], 
        columns='Player_Name', 
        values='Score'
    ).reset_index()
    pivot_df.columns.name = None
    pivot_df = pivot_df.fillna("")

    player_cols = list(pivot_df.columns[3:])

    benched_players = set()
    latest_benched = None
    # Collect all rounds across games, sorted by Game_ID then Round_No
    all_rounds = []
    for game_id in dfm['Game_ID'].unique():
        game_df = dfm[dfm['Game_ID'] == game_id]
        rounds = sorted(game_df['Round_No'].unique())
        for round_no in rounds:
            all_rounds.append((game_id, round_no))
    all_rounds.sort()  # Sort by game_id, round_no
    
    for idx, (game_id, round_no) in enumerate(all_rounds):
        if idx == 0:
            # For the first row in the table, use the benched player_status in that row
            benched_in_current = dfm[(dfm['Game_ID'] == game_id) & (dfm['Round_No'] == round_no) & (dfm['Player_Status'] == 'benched')]['Player_Name']
            if len(benched_in_current) == 1:
                latest_benched = benched_in_current.iloc[0]
        else:
            # For subsequent rows, check if the previous row is populated with values
            prev_game_id, prev_round_no = all_rounds[idx-1]
            prev_active = dfm[(dfm['Game_ID'] == prev_game_id) & (dfm['Round_No'] == prev_round_no) & (dfm['Player_Status'] == 'active')]
            if len(prev_active) > 0 and all(prev_active['Score'].notna() & (prev_active['Score'] != '')):
                benched_in_current = dfm[(dfm['Game_ID'] == game_id) & (dfm['Round_No'] == round_no) & (dfm['Player_Status'] == 'benched')]['Player_Name']
                if len(benched_in_current) == 1:
                    latest_benched = benched_in_current.iloc[0]
    benched_players = {latest_benched} if latest_benched else set()

    start_images = len(benched_players) > 0

    # Collapse Game_ID groups into one Total row if all player columns are populated
    collapsed_data = []
    for game_id, group in pivot_df.groupby('Game_ID', sort=False):
        if len(group) <= 1:
            # Single row: keep as-is
            collapsed_data.extend(group.values.tolist())
        else:
            # Multiple rows: check if all scores for each round are populated where the user is active
            has_empty = False
            for _, row in group.iterrows():
                game_id_check = row['Game_ID']
                round_no_check = row['Round_No']
                active_players = dfm[(dfm['Game_ID'] == game_id_check) & (dfm['Round_No'] == round_no_check) & (dfm['Player_Status'] == 'active')]['Player_Name'].unique()
                for player in active_players:
                    score_series = dfm[(dfm['Game_ID'] == game_id_check) & (dfm['Round_No'] == round_no_check) & (dfm['Player_Name'] == player)]['Score']
                    if score_series.empty or pd.isna(score_series.iloc[0]) or str(score_series.iloc[0]).strip() == "":
                        has_empty = True
                        break
                if has_empty:
                    break
            
            if not has_empty:
                # All populated: collapse into one Total row
                total_row = group.iloc[0].copy()
                total_row['Round_No'] = 'Total'
                for col in player_cols:
                    active_scores = dfm[(dfm['Game_ID'] == game_id) & (dfm['Player_Name'] == col) & (dfm['Player_Status'] == 'active')]['Score']
                    total = 0.0
                    for val in active_scores:
                        try:
                            total += float(val)
                        except (ValueError, TypeError):
                            pass
                    total_row[col] = int(total) if total == int(total) else total
                collapsed_data.append(total_row.tolist())
            else:
                # Has empty cells: keep all rows
                collapsed_data.extend(group.values.tolist())

    pivot_df = pd.DataFrame(collapsed_data, columns=pivot_df.columns)
    player_cols = list(pivot_df.columns[3:])
except Exception as e:
    pass  # Silently ignore if match data fails

# Create a row of columns based on the number of players
cols = st.columns(len(df))

# Display player cards with images, names, and points
for idx, (col, (_, row)) in enumerate(zip(cols, df.iterrows())):
    with col:
        ## Select URL based on benched status first, then points ranking
        if row['Name'] in benched_players:
            url = row['benched_URL']
        elif row['Points'] == min_points and start_images:
            url = row['neutral_URL']
        elif row['Points'] == min_points:
            url = row['sad_URL']    
        elif row['Points'] == max_points:
            url = row['happy_URL']
        else:
            url = row['neutral_URL']
        
        if pd.isna(url) or url == "":
            st.warning(f"No image for {row['Name']}")
        else:
            try:
                img_bytes = download_image_bytes(url)
                img = Image.open(BytesIO(img_bytes))
                img = ImageOps.fit(img.convert("RGB"), (175, 250), Image.LANCZOS)

                if row['Name'] in benched_players:
                    img = ImageOps.grayscale(img).convert("RGB")

                st.image(img, width=250)
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        # Display player info
        st.markdown(f"""
            <div class="player-card">
                <div class="player-name">{row['Name'].upper()}</div>
                <div class="player-points">{int(row['Points'])} PTS</div>
            </div>
            """, unsafe_allow_html=True)
#for index, row in df.iterrows():
#    with cols[index]:
#        # Using a container to apply our CSS styling
#        st.markdown(f"""
#            <div class="player-container">
#                <img src="{row['happy_URL']}" width="100%" style="border-radius: 5px;">
#                <div class="player-name">{row['Name'].upper()}</div>
#                <div class="player-points">{row['Points']} PTS</div>
#            </div>
#            """, unsafe_allow_html=True)

#st.write("---")
# Load Match Data specifically from the 'Matches' worksheet

# --- 2. MATCH HISTORY DISPLAY ---
#st.subheader("🕹️ MATCH SCHEDULE & RESULTS")
st.subheader("MATCH SCHEDULE & RESULTS")

try:
    # Display the output as styled HTML table
    # Build HTML table
    html_table = '<table class="match-table">'
    
    # Header row (exclude Game_ID)
    html_table += '<tr>'
    for col in pivot_df.columns:
        if col != 'Game_ID':
            html_table += f'<th>{col}</th>'
    html_table += '</tr>'
    
    # Data rows (exclude Game_ID)
    for _, row in pivot_df.iterrows():
        html_table += '<tr>'
        for col in pivot_df.columns:
            if col != 'Game_ID':
                value = row[col]
                # Check if this player is benched in this round
                game_id = row['Game_ID']
                round_no = row['Round_No']
                player_name = col
                is_benched = not dfm[(dfm['Game_ID'] == game_id) & (dfm['Round_No'] == round_no) & (dfm['Player_Name'] == player_name) & (dfm['Player_Status'] == 'benched')].empty
                if is_benched:
                    value = "-"
                elif value == "":
                    value = ""  # Keep blank for empty active player cells
                html_table += f'<td>{value}</td>'
        html_table += '</tr>'
    
    html_table += '</table>'
    
    st.markdown(html_table, unsafe_allow_html=True)

    # Show benched messages
    if benched_players:
        names = ', '.join(sorted(benched_players))
        st.write(f"Currently benched player(s): {names}")
    else:
        st.write("No current benched player detected.")

    # Optional: Add a sidebar filter for Games
    #all_games = ["All"] + sorted(df["Game_Title"].unique().tolist())
    #game_filter = st.sidebar.selectbox("Filter by Game", all_games)

    #if game_filter != "All":
    #    filtered_view = pivot_df[pivot_df["Game_Title"] == game_filter]
    #    st.write(f"Showing results for **{game_filter}**")
    #    st.table(filtered_view)

except Exception as e:
    st.error("Ensure your spreadsheet has 'Game_ID', 'Game_Title', 'Round_No', 'Player_Name', 'Player_Status', and 'Score' columns.")
    st.write(e)

# Place this at the bottom of your sidebar or footer
st.caption(f"SYSTEM_STATUS: Sync Complete at {datetime.now().strftime('%H:%M:%S')} AST")