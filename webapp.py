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

def create_full_name_image(text, video_w, video_h, filename):
    # 1. Setup Font
    # Font size = 12% of screen height
    font_size = int(video_h * 0.12) 
    
    try: font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try: font = ImageFont.truetype("arial.ttf", font_size)
        except: font = ImageFont.load_default()

    # 2. Measure Text
    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # 3. Create Canvas
    # Add padding so outlines don't get cut off
    pad = 50
    img = Image.new('RGBA', (text_w + pad*2, text_h + pad*2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 4. Draw Text (Centered in canvas)
    x = pad
    y = pad
    stroke = 4
    
    # Black Outline
    for i in range(-stroke, stroke+1):
        for j in range(-stroke, stroke+1):
            draw.text((x+i, y+j), text, font=font, fill="black")
            
    # White Fill
    draw.text((x, y), text, font=font, fill="white")
    
    # Save
    img.save(filename)
    return img.width, img.height

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
    .stTextInput input {color: black !important;}
    </style>
""", unsafe_allow_html=True)

# === UPDATE MODE (Controller) ===
if mode == "update":
    st.markdown("""<style>.block-container {padding: 2rem !important;}</style>""", unsafe_allow_html=True)
    
    if "status" not in st.session_state:
        st.session_state.status = "idle"

    if st.session_state.status == "idle":
        st.title("Create Greeting")
        with st.form("update_form"):
            name_input = st.text_input("Enter Name:", max_chars=20).strip()
            submit = st.form_submit_button("Create", type="primary")
        
        if submit and name_input:
            st.session_state.status = "processing"
            st.session_state.name_input = name_input
            st.rerun()

    elif st.session_state.status == "processing":
        st.info("Creating Video... Please wait.")
        prog = st.progress(0)
        
        try:
            full_text = st.session_state.name_input + "!"
            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            temp_img = "temp_text_overlay.png"
            
            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}")
                st.stop()

            # 1. Load Background
            clip = VideoFileClip(TEMPLATE_FILE)
            clip = safe_resize(clip, TARGET_RES)
            
            # 2. Create ONE Text Image (Fixes Broadcasting Error)
            img_w, img_h = create_full_name_image(full_text, clip.w, clip.h, temp_img)
            
            prog.progress(30)
            
            # 3. Create Overlay Clip
            txt_clip = ImageClip(temp_img).with_duration(clip.duration)
            
            # 4. Position Logic (Align with Cake)
            # Target X: Centered in the right-side empty space (approx 70% across screen)
            center_point_x = clip.w * 0.70
            target_x = center_point_x - (img_w / 2)
            
            # Target Y: Aligned with cake (75% down)
            target_y = (clip.h * 0.75) - (img_h / 2)
            
            # 5. Slide Animation
            start_time = 2.0
            slide_dur = 1.0
            
            def slide_pos(t):
                if t < slide_dur:
                    # Ease out math
                    p = 1 - ((1 - t) ** 3)
                    # Start off screen (clip.w) -> Slide to target_x
                    curr_x = clip.w - ((clip.w - target_x) * p)
                    return (int(curr_x), int(target_y))
                return (int(target_x), int(target_y))
            
            txt_clip = txt_clip.with_start(start_time).with_position(slide_pos)
            
            # Fade Out Text at end
            try:
                if FadeOut: txt_clip = txt_clip.with_effects([FadeOut(1.0)])
                else: txt_clip = txt_clip.fadeout(1.0)
            except: pass

            final = CompositeVideoClip([clip, txt_clip])

            # 6. Ad Logic
            ad = get_ad_file()
            if ad:
                try:
                    ac = VideoFileClip(ad) if ad.endswith(('.mp4','.mov')) else ImageClip(ad).with_duration(15)
                    ac = safe_resize(ac, TARGET_RES).with_start(final.duration)
                    final = CompositeVideoClip([final, ac])
                except: pass
            
            prog.progress(60)
            
            # 7. Write File
            final.write_videofile(temp_out, codec='libx264', audio_codec='aac', fps=24, logger=None)
            
            # Cleanup
            clip.close()
            final.close()
            gc.collect()
            
            shutil.move(temp_out, os.path.join(OUTPUT_FOLDER, TARGET_FILE))
            if os.path.exists(temp_img): os.remove(temp_img)
            
            prog.progress(100)
            st.session_state.status = "done"
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {e}")
            if st.button("Try Again"):
                st.session_state.status = "idle"
                st.rerun()

    elif st.session_state.status == "done":
        st.balloons()
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
        
        # HTML5 PLAYER (Fit to Screen)
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
            .video-container {{
                position: absolute; top: 0; left: 0;
                width: 100vw; height: 100vh;
                display: flex; align-items: center; justify-content: center;
                background-color: black;
            }}
            video {{
                width: 100%; height: 100%;
                object-fit: contain;
                pointer-events: none;
            }}
        </style>
        </head>
        <body>
            <div class="video-container">
                <video autoplay loop muted playsinline>
                    <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                </video>
            </div>
            <script>
                setTimeout(function(){{
                    window.location.reload(true);
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