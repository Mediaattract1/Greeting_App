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
TEMPLATE_FILE = "HB Layout1.mp4"
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
        # FIX: Reduced kerning to 0 to stop letters from squishing together
        kerning = 0 
        for char in text:
            cw = int(font_size * 0.25) if char == " " else (dummy_draw.textbbox((0, 0), char, font)[2] - dummy_draw.textbbox((0, 0), char, font)[0])
            total_w += cw
        
        if total_w < max_width or font_size < 20: break
        font_size = int(font_size * 0.9)
        try: font = ImageFont.truetype("arialbd.ttf", font_size)
        except: pass
    return font, font_size

def create_letter_image(char, font, filename):
    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy.textbbox((0, 0), char, font=font, anchor="ls")
    char_w = bbox[2] - bbox[0]
    
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

# === CSS: FULL SCREEN BLACK & HIDE UI ===
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
    p, label, h1, h2, h3 {color: white !important;}
    
    /* Styling for the Controller inputs */
    .stTextInput input {
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

# === UPDATE MODE (Controller) ===
if mode == "update":
    # Add padding back for the controller view
    st.markdown("""<style>.block-container {padding: 2rem !important;}</style>""", unsafe_allow_html=True)
    
    if "status" not in st.session_state:
        st.session_state.status = "idle"

    # 1. INPUT FORM
    if st.session_state.status == "idle":
        st.title("Create Greeting")
        with st.form("update_form"):
            name_input = st.text_input("Enter Name:", max_chars=20).strip()
            submit = st.form_submit_button("Create", type="primary")
        
        if submit and name_input:
            st.session_state.status = "processing"
            st.session_state.name_input = name_input
            st.rerun()

    # 2. PROCESSING STATE
    elif st.session_state.status == "processing":
        st.info("Creating Video... Please wait.")
        prog = st.progress(0)
        
        try:
            full_text = st.session_state.name_input + "!"
            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            
            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}")
                st.stop()

            clip = VideoFileClip(TEMPLATE_FILE)
            clip = safe_resize(clip, TARGET_RES)
            
            font, font_size = get_font_and_metrics(full_text, clip.w * 0.45, int(clip.h * 0.11))
            
            # FIX: Kerning removed to stop squishing
            kerning = 0 
            
            dummy = ImageDraw.Draw(Image.new('RGB', (1,1)))
            total_w = sum([int(font_size*0.25) if c==" " else (dummy.textbbox((0,0),c,font)[2]-dummy.textbbox((0,0),c,font)[0]) for c in full_text])
            
            curr_x = (clip.w * 0.65) - (total_w / 2)
            target_y = (clip.h * 0.75) - 400
            
            clips = [clip]
            temp_imgs = []
            
            prog.progress(20)
            
            for i, char in enumerate(full_text):
                if char == " ":
                    curr_x += int(font_size*0.25)
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
                curr_x += w 

            final = CompositeVideoClip(clips)
            ad = get_ad_file()
            if ad:
                try:
                    ac = VideoFileClip(ad) if ad.endswith(('.mp4','.mov')) else ImageClip(ad).with_duration(15)
                    ac = safe_resize(ac, TARGET_RES).with_start(final.duration)
                    final = CompositeVideoClip([final, ac])
                except: pass
            
            prog.progress(60)
            final.write_videofile(temp_out, codec='libx264', audio_codec='aac', fps=24, logger=None)
            
            clip.close()
            final.close()
            gc.collect()
            
            shutil.move(temp_out, os.path.join(OUTPUT_FOLDER, TARGET_FILE))
            for f in temp_imgs: 
                if os.path.exists(f): os.remove(f)
            
            prog.progress(100)
            st.session_state.status = "done"
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {e}")
            if st.button("Try Again"):
                st.session_state.status = "idle"
                st.rerun()

    # 3. DONE STATE (Updated Message)
    elif st.session_state.status == "done":
        st.balloons()
        # FIX: Updated success message
        st.success(f"Success! Your Greeting for **{st.session_state.name_input}** is playing on the Screen.")
        
        st.write("") 
        if st.button("Create New Greeting"):
            st.session_state.status = "idle"
            st.rerun()

# === DISPLAY MODE (The Kiosk Player) ===
else:
    TARGET_FILE = "video.mp4"
    real_target = os.path.join(OUTPUT_FOLDER, TARGET_FILE)
    
    if os.path.exists(real_target):
        video_bytes = open(real_target, 'rb').read()
        video_b64 = base64.b64encode(video_bytes).decode()
        
        # HTML PLAYER FIX: Changed 'fill' to 'contain' to stop stretching/flattening
        html_code = f"""
        <html>
        <head>
        <style>
            body, html {{ 
                background-color: black; 
                margin: 0; padding: 0; 
                overflow: hidden; 
                width: 100vw; height: 100vh;
                cursor: none;
            }}
            video {{
                position: absolute;
                top: 0; left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain; /* Ensures perfect aspect ratio (no squash/stretch) */
            }}
        </style>
        </head>
        <body>
            <video autoplay loop muted playsinline id="vplayer">
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
            <script>
                setTimeout(function(){{
                    location.reload();
                }}, 5000);
            </script>
        </body>
        </html>
        """
        
        current_stats = os.stat(real_target).st_mtime
        if "last_version" not in st.session_state:
            st.session_state.last_version = current_stats
            
        st.components.v1.html(html_code, height=1200, scrolling=False)
        
        if current_stats > st.session_state.last_version:
            st.session_state.last_version = current_stats
            st.rerun()
            
    else:
        st.info("Waiting for first update...")
        time.sleep(3)
        st.rerun()