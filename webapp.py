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

# --- TEXT ENGINE (Reverted to the Desktop Logic you liked) ---
def get_text_width_with_kerning(draw, text, font, kerning):
    total_width = 0
    for char in text:
        bbox = draw.textbbox((0, 0), char, font=font)
        char_w = bbox[2] - bbox[0]
        total_width += char_w
    if len(text) > 1:
        total_width -= (len(text) - 1) * kerning
    return total_width

def create_text_image_file(text, video_width, video_height, filename):
    # 1. Font Setup
    font_size = int(video_height * 0.15)
    try: font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try: font = ImageFont.truetype("arial.ttf", font_size)
        except: font = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    # 2. Sizing Loop (Shrink if too big)
    max_allowed_width = video_width * 0.55
    
    while True:
        kerning = int(font_size * 0.06)
        text_w = get_text_width_with_kerning(draw, text, font, kerning)
        
        if text_w < max_allowed_width or font_size < 20:
            break
        
        font_size = int(font_size * 0.9)
        try: font = ImageFont.truetype("arialbd.ttf", font_size)
        except: font = ImageFont.truetype("arial.ttf", font_size)
    
    # 3. Final Dimensions
    kerning = int(font_size * 0.06)
    text_w = get_text_width_with_kerning(draw, text, font, kerning)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]

    # 4. Create Image
    padding = 100
    # Add extra height to accommodate rotation without clipping
    txt_img = Image.new('RGBA', (text_w + padding, text_h + padding + 50), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    
    start_x = padding // 2
    start_y = padding // 2
    stroke_width = 5

    # 5. Draw (Tight Kerning Logic)
    # Pass 1: Outlines
    current_x = start_x
    for char in text:
        c_bbox = txt_draw.textbbox((0, 0), char, font=font)
        char_w = c_bbox[2] - c_bbox[0]
        for x in range(-stroke_width, stroke_width+1):
            for y in range(-stroke_width, stroke_width+1):
                txt_draw.text((current_x+x, start_y+y), char, font=font, fill="black")
        current_x += char_w - kerning

    # Pass 2: Fill
    current_x = start_x
    for char in text:
        c_bbox = txt_draw.textbbox((0, 0), char, font=font)
        char_w = c_bbox[2] - c_bbox[0]
        txt_draw.text((current_x, start_y), char, font=font, fill="white")
        current_x += char_w - kerning
    
    # 6. Rotate 3 Degrees (The angle you liked)
    rotated_img = txt_img.rotate(3, expand=True, resample=Image.BICUBIC)
    rotated_img.save(filename)
    return filename

# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")

# === CSS: Fix Colors & Layout ===
st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"] {display: none !important;}
    
    /* Remove padding to fix scrollbar issues on stick */
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    ::-webkit-scrollbar {display: none;}
    
    body, .stApp {background-color: black;}
    
    /* Input Form Styling */
    p, label, h1, h2, h3 {color: white !important;}
    
    /* FORCE INPUT TEXT BLACK so you can read it */
    .stTextInput input {
        color: black !important;
        background-color: white !important;
    }
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
            
            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}")
                st.stop()

            clip = VideoFileClip(TEMPLATE_FILE)
            clip = safe_resize(clip, TARGET_RES)
            
            # Create ONE image for the name (Fixes jumbled letters)
            temp_img = "temp_name_overlay.png"
            create_text_image_file(full_text, clip.w, clip.h, temp_img)
            
            txt_clip = ImageClip(temp_img).with_duration(clip.duration)
            
            # Position Logic
            # Center of empty space is roughly 75% across screen
            center_target = clip.w * 0.75
            # We want to center the IMAGE on that point
            # But since ImageClip doesn't expose .w easily before render in some versions,
            # we rely on the visual calculation:
            
            # Animation
            start_time = 2.0
            slide_duration = 1.5
            
            # Load image to get width for math
            with Image.open(temp_img) as img_ref:
                img_w, img_h = img_ref.size
                
            target_x = center_target - (img_w / 2)
            target_y = (clip.h * 0.65) - (img_h / 2)
            start_x = clip.w + 10
            
            def slide_position(t):
                if t < 0: return (int(start_x), int(target_y))
                if t < slide_duration:
                    ratio = t / slide_duration
                    progress = 1 - ((1 - ratio) ** 3)
                    curr_x = start_x - ((start_x - target_x) * progress)
                    return (int(curr_x), int(target_y))
                return (int(target_x), int(target_y))

            txt_clip = txt_clip.with_start(start_time).with_position(slide_position)
            
            final = CompositeVideoClip([clip, txt_clip])

            # Ad Logic
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
        
        # HTML5 PLAYER:
        # object-fit: contain (Fixes Squashed Image)
        # width: 100vw, height: 100vh (Fixes Scroll bars)
        # margin: 0 (Fixes White edges)
        html_code = f"""
        <html>
        <head>
        <style>
            body, html {{ 
                background-color: black; 
                margin: 0; padding: 0; 
                overflow: hidden; 
                width: 100vw; height: 100vh;
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
                // HARD RELOAD every 5 seconds to catch updates
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
            
        st.components.v1.html(html_code, height=1080, scrolling=False)
        
        if current_stats > st.session_state.last_version:
            st.session_state.last_version = current_stats
            st.rerun()
            
    else:
        st.info("Waiting for first update...")
        time.sleep(3)
        st.rerun()