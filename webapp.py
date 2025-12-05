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
    
    # Restore Spacing Logic
    while True:
        total_w = 0
        kerning = int(font_size * 0.06)
        for char in text:
            if char == " ":
                cw = int(font_size * 0.25) 
                total_w += cw
            else:
                bbox = dummy_draw.textbbox((0, 0), char, font=font)
                total_w += (bbox[2] - bbox[0])
        
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
    
    # Massive canvas for alignment
    canvas_h = 600
    canvas_base = 400
    
    padding_x = 200
    img_w = int(char_w + padding_x)
    
    img = Image.new('RGBA', (img_w, canvas_h), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    draw_x = padding_x // 2
    
    # Draw Outline
    for x in range(-3, 4):
        for y in range(-3, 4): 
            d.text((draw_x+x, canvas_base+y), char, font=font, fill="black", anchor="ls")
    # Draw Fill
    d.text((draw_x, canvas_base), char, font=font, fill="white", anchor="ls")
    
    # RESTORED: 7 Degree Tilt (High Quality)
    img.rotate(7, expand=False, resample=Image.BICUBIC).save(filename)
    return char_w

# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")

# CSS: Black Background, Hidden Menus
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

# === UPDATE MODE ===
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
            
            # Sizing Logic
            max_w = clip.w * 0.45 
            start_size = int(clip.h * 0.11) 
            font, font_size = get_font_and_metrics(full_text, max_w, start_size)
            kerning = int(font_size * 0.06)
            
            dummy = ImageDraw.Draw(Image.new('RGB', (1,1)))
            total_w = sum([int(font_size*0.25) if c==" " else (dummy.textbbox((0,0),c,font)[2]-dummy.textbbox((0,0),c,font)[0]) for c in full_text])
            total_w -= (len(full_text)-1)*kerning
            
            # Position: Right side, aligned with Cake
            center_x = clip.w * 0.65
            curr_x = center_x - (total_w / 2)
            
            # Vertical Position (75% down - adjusted for canvas offset)
            target_y = (clip.h * 0.75) - 400
            
            clips = [clip]
            temp_imgs = []
            
            prog.progress(20)
            
            # RESTORED: Staggered Skating Animation
            for i, char in enumerate(full_text):
                if char == " ":
                    curr_x += int(font_size*0.25) - kerning
                    continue
                fname = f"t_{i}.png"
                temp_imgs.append(fname)
                
                # Create Tilted Image
                create_letter_image(char, font, fname)
                
                lc = ImageClip(fname).with_duration(clip.duration)
                try: lc = lc.with_effects([FadeOut(1.0)]) if FadeOut else lc.fadeout(1.0)
                except: pass
                
                # Staggered Start Time
                st_t = 2.0 + (i*0.1)
                
                # Visual X (Compensate for padding)
                visual_x = curr_x - 100 
                
                # Slide In Animation
                def pos(t):
                    start_x = clip.w - 1
                    if t < 1.0: 
                        p = 1 - ((1 - t)**3)
                        current = start_x - ((start_x - visual_x) * p)
                        return (int(current), int(target_y))
                    return (int(visual_x), int(target_y))
                
                clips.append(lc.with_start(st_t).with_position(pos))
                curr_x += (dummy.textbbox((0,0),char,font)[2]-dummy.textbbox((0,0),char,font)[0]) - kerning

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
        # 1. Read File stats
        current_stats = os.stat(real_target).st_mtime
        
        # 2. Encode Video
        video_bytes = open(real_target, 'rb').read()
        video_b64 = base64.b64encode(video_bytes).decode()
        
        # 3. HTML5 Player with FORCE RELOAD logic
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
                object-fit: contain; /* Prevents Stretching */
            }}
        </style>
        </head>
        <body>
            <video autoplay loop muted playsinline id="vplayer">
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
            <script>
                // Brute force reload every 10 seconds to catch updates
                setTimeout(function(){{
                    window.location.reload(true);
                }}, 10000);
            </script>
        </body>
        </html>
        """
        
        # Key=Timestamp forces Streamlit to re-mount the component if file changed
        st.components.v1.html(html_code, height=1200, scrolling=False)
        
        # Python-side polling as backup
        if "last_version" not in st.session_state:
            st.session_state.last_version = current_stats
            
        time.sleep(5)
        
        if current_stats > st.session_state.last_version:
            st.session_state.last_version = current_stats
            st.rerun()
            
    else:
        st.info("Waiting for first update...")
        time.sleep(3)
        st.rerun()