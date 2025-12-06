import streamlit as st
import os
import base64

# --- CONFIGURATION ---
# We are playing the raw uploaded file directly to test fit
TEMPLATE_FILE = "template_HB1_wide.mp4"

st.set_page_config(page_title="Background Test", layout="wide", initial_sidebar_state="collapsed")

# === CSS: FORCE FULL SCREEN, NO UI, BLACK BACKGROUND ===
st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"] {display: none !important;}
    .block-container {
        padding: 0 !important; 
        margin: 0 !important; 
        max-width: 100% !important;
    }
    ::-webkit-scrollbar {display: none;}
    body, .stApp {background-color: black;}
    </style>
""", unsafe_allow_html=True)

# === DISPLAY LOGIC ===
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
        video {{
            /* Forces video to fit inside the screen perfectly */
            width: 100%;
            height: 100%;
            object-fit: contain; 
        }}
    </style>
    </head>
    <body>
        <video autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
        </video>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=1080, scrolling=False)
    
else:
    # DEBUGGING MESSAGE
    st.error(f"CRITICAL ERROR: Could not find '{TEMPLATE_FILE}' on the server.")
    st.info("Please check your GitHub repository:")
    st.info(f"1. Is the file uploaded?")
    st.info(f"2. Is it named EXACTLY '{TEMPLATE_FILE}'?")