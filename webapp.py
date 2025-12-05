import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import time
import shutil
import gc
import base64

# --- CONFIGURATION ---
BASE_URL = "https://greeting-app-wh2w.onrender.com" 
TEMPLATE_FILE = "HB Layout1.mp4" # We are back to 1080p!
OUTPUT_FOLDER = "generated_videos"
TARGET_RES = (1920, 1080) 

# --- SAFE SETUP ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- MOVIEPY IMPORT FIXER ---
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.VideoClip import ImageClip
    try:
        from moviepy.video.fx import FadeOut
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            FadeOut = vfx.FadeOut
        except:
            FadeOut = None
except ImportError:
    import moviepy.editor as mp
    VideoFileClip = mp.VideoFileClip
    CompositeVideoClip = mp.CompositeVideoClip
    ImageClip = mp.ImageClip
    FadeOut = None

# --- HELPER FUNCTIONS ---
def safe_resize(clip, size):
    try: return clip.resized(new_size=size)
    except: return clip.resize(newsize=size)

def get_ad_file():
    for ext in ['.mp4', '.mov', '.gif', '.png', '.jpg']:
        if os.path.exists("ad" + ext): return "ad" + ext
    return None

def get_font_and_metrics(text, max_width, start_size):
    font_size = start_size
    try: font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try: font = ImageFont.truetype("arial.ttf", font_size)
        except: font = ImageFont.load_default()

    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while True:
        total_w = 0
        kerning = int(font_size * 0.06)
        for char in text:
            cw = int(font_size * 0.25) if char == " " else (dummy_draw.textbbox((0, 0), char, font)[2] - dummy_draw.textbbox((0, 0), char, font)[0])
            total_w += cw
        if len(text) > 1: total_w -= (len(text) - 1) * kerning
        if total_w < max_width or font_size < 20: break
        font_size = int(font_size * 0.9)
        try: font = ImageFont.truetype("arialbd.ttf", font_size)
        except: pass
    return font, font_size

def create_letter_image(char, font, filename):
    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy.textbbox((0, 0), char, font=font, anchor="ls")
    char_w = bbox[2] - bbox[0]
    
    # 1080p Canvas Size
    canvas_h = 600
    canvas_base = 400
    
    img = Image.new('RGBA', (int(char_w + 200), canvas_h), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    for x in range(-3, 4):
        for y in range(-3, 4): 
            d.text((100+x, canvas_base+y), char, font=font, fill="black", anchor="ls")
    d.text((100, canvas_base), char, font=font, fill="white", anchor="ls")
    
    img.rotate(0, expand=False, resample=Image.BICUBIC).save(filename)
    return char_w

# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")

# === CSS INVISIBILITY CLOAK (Hides Logos & Menus) ===
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# === UPDATE MODE (The Controller) ===
if mode == "update":
    st.title("Update Sign")
    
    with st.form("update_form"):
        name_input = st.text_input("Enter Name:", max_chars=20).strip()
        submit = st.form_submit_button("Update TV")
    
    if submit and name_input:
        status = st.empty()
        status.info("Processing 1080p Video... (Takes ~15s)")
        
        try:
            full_text = name_input + "!"
            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            
            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}. Please upload the 1080p file to GitHub.")
                st.stop()

            clip = VideoFileClip(TEMPLATE_FILE)
            clip = safe_resize(clip, TARGET_RES)
            
            font, font_size = get_font_and_metrics(full_text, clip.w * 0.45, int(clip.h * 0.11))
            kerning = int(font_size * 0.06)
            
            dummy = ImageDraw.Draw(Image.new('RGB', (1,1)))
            total_w = sum([int(font_size*0.25) if c==" " else (dummy.textbbox((0,0),c,font)[2]-dummy.textbbox((0,0),c,font)[0]) for c in full_text])
            total_w -= (len(full_text)-1)*kerning
            
            curr_x = (clip.w * 0.65) - (total_w / 2)
            target_y = (clip.h * 0.75) - 400
            
            clips = [clip]
            temp_imgs = []
            
            for i, char in enumerate(full_text):
                if char == " ":
                    curr_x += int(font_size*0.25) - kerning
                    continue
                fname = f"t_{i}.png"
                temp_imgs.append(fname)
                w = create_letter_image(char, font, fname)
                
                lc = ImageClip(fname).with_duration(clip.duration)
                try: lc = lc.with_effects([FadeOut(1.0)]) if FadeOut else lc.fadeout(1.0)
                except: pass
                
                st_t = 2.0 + (i*0.1)
                tx = curr_x - 100
                def pos(t):
                    if t < 1.0: return (int(clip.w - ((clip.w-tx)*(1-((1-t)**3)))), int(target_y))
                    return (int(tx), int(target_y))
                
                clips.append(lc.with_start(st_t).with_position(pos))
                curr_x += w - kerning

            final = CompositeVideoClip(clips)
            
            ad = get_ad_file()
            if ad:
                try:
                    ac = VideoFileClip(ad) if ad.endswith(('.mp4','.mov')) else ImageClip(ad).with_duration(15)
                    ac = safe_resize(ac, TARGET_RES).with_start(final.duration)
                    final = CompositeVideoClip([final, ac])
                except: pass
            
            # WRITE 1080p (Standard Settings for Quality)
            final.write_videofile(
                temp_out, 
                codec='libx264', 
                audio_codec='aac', 
                fps=24, 
                logger=None
            )
            
            clip.close()
            final.close()
            gc.collect()
            
            shutil.move(temp_out, os.path.join(OUTPUT_FOLDER, TARGET_FILE))
            
            for f in temp_imgs: 
                if os.path.exists(f): os.remove(f)
            
            status.success("Success! TV will update.")
            
        except Exception as e:
            status.error(f"Error: {e}")

# === DISPLAY MODE (The Kiosk Player) ===
else:
    TARGET_FILE = "video.mp4"
    real_target = os.path.join(OUTPUT_FOLDER, TARGET_FILE)
    
    if os.path.exists(real_target):
        # KIOSK PLAYER (HTML5 Hack)
        # - Removes controls
        # - Forces Loop/Autoplay
        # - Hides Cursor
        # - Fills Screen
        
        video_bytes = open(real_target, 'rb').read()
        video_b64 = base64.b64encode(video_bytes).decode()
        
        html_code = f"""
        <style>
        body {{ 
            background-color: black; 
            margin: 0; 
            overflow: hidden; 
            cursor: none; 
        }}
        video {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            pointer-events: none; /* Prevents clicking/pausing */
        }}
        </style>
        
        <video autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
        </video>
        
        <script>
        // Reload page every 15 seconds to check for updates
        // This replaces the Python loop with a cleaner Browser loop
        setTimeout(function(){{
            location.reload();
        }}, 15000);
        </script>
        """
        
        # Check modification time to see if we actually need to reload content
        current_stats = os.stat(real_target).st_mtime
        if "last_version" not in st.session_state:
            st.session_state.last_version = current_stats
            
        # If file hasn't changed, we just show the player
        # The JavaScript inside the HTML handles the periodic refresh
        st.components.v1.html(html_code, height=1080)
        
        # Update state logic
        if current_stats > st.session_state.last_version:
            st.session_state.last_version = current_stats
            st.rerun()
            
    else:
        st.info("Waiting for first update...")
        time.sleep(5)
        st.rerun()