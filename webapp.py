import streamlit as st
import os
import base64
import time

# --- CONFIGURATION ---
# We are skipping generation. We are just playing the raw background file.
TEMPLATE_FILE = "HB Layout1.mp4"

st.set_page_config(page_title="Background Test", layout="wide", initial_sidebar_state="collapsed")

# === CSS: FORCE FULL SCREEN, NO UI, BLACK BACKGROUND ===
st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"] {display: none !important;}
    .block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
    ::-webkit-scrollbar {display: none;}
    body, .stApp {background-color: black;}
    </style>
""", unsafe_allow_html=True)

# === DISPLAY LOGIC ===
# No modes. No updates. Just play the file.

if os.path.exists(TEMPLATE_FILE):
    # Read the raw template file directly
    video_bytes = open(TEMPLATE_FILE, 'rb').read()
    video_b64 = base64.b64encode(video_bytes).decode()
    
    # HTML5 PLAYER WITH ANDROID FIXES
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body, html {{ 
            background-color: black; 
            margin: 0; padding: 0; 
            width: 100vw; height: 100vh;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .video-container {{
            width: 100%; 
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        video {{
            /* This forces the video to fit inside the screen without stretching */
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain; 
        }}
    </style>
    </head>
    <body>
        <div class="video-container">
            <video autoplay loop muted playsinline>
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
        </div>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=1080, scrolling=False)
    
else:
    st.error(f"Could not find {TEMPLATE_FILE}. Is it uploaded to GitHub?")