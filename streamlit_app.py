import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="N64 LEADERBOARD", layout="wide")

# Cache downloaded image bytes so the app is faster on reruns
@st.cache_data(ttl=3600)
def download_image_bytes(url):
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content

# 1. Setup Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Read Data (Replace with your actual public URL)
# Hint: Ensure your Sheet has columns: Name, Points, Bio, Image_URL, Game_Played, Result
df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1ns0sXbWEQtfNcPQ8HZ6tYLyQYCdtDdQb6cVLqbUZdwM/edit?usp=sharing", ttl="0") 

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

st.title("🎮 N64 LEADERBOARD")

# --- 3. THE ROW DISPLAY ---
st.subheader("CURRENT STANDINGS")

# Import here to avoid repetition
import requests
from io import BytesIO
from PIL import Image, ImageOps

# Calculate min and max points for URL selection
min_points = df['Points'].min()
max_points = df['Points'].max()

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

    player_cols = pivot_df.columns[3:]

    def has_numeric_values(row):
        return any(pd.to_numeric(row[player_cols], errors='coerce').notna())

    # Check first row: if no numbers entered, use B to identify benched players
    if len(pivot_df) > 0:
        first_row = pivot_df.iloc[0]
        if not has_numeric_values(first_row):
            benched = [col for col in player_cols if str(first_row[col]).strip().upper() == 'B']
            benched_players.update(benched)

    # Check subsequent rows using transition logic
    for i in range(1, len(pivot_df)):
        prev_row = pivot_df.iloc[i - 1]
        current_row = pivot_df.iloc[i]
        if has_numeric_values(prev_row) and not has_numeric_values(current_row):
            benched = [col for col in player_cols if str(current_row[col]).strip().upper() == 'B']
            benched_players.update(benched)
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
st.subheader("🕹️ MATCH SCHEDULE & RESULTS")

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
    st.error("Ensure your spreadsheet has 'Game_Title', 'Round_No', 'Player_Name', and 'Score' columns.")
    st.write(e)

# Place this at the bottom of your sidebar or footer
st.caption(f"SYSTEM_STATUS: Sync Complete at {datetime.now().strftime('%H:%M:%S')} AST")