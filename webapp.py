import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import time
import shutil
import uuid

# --- CONFIGURATION ---
# PASTE YOUR REAL RENDER URL HERE (No trailing slash)
BASE_URL = "https://greeting-app-wh2w.onrender.com"

TEMPLATE_FILE = "HB Layout1.mp4"
OUTPUT_FOLDER = "generated_videos"
TARGET_RES = (1920, 1080) 

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

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

# --- HELPER: SAFE RESIZE ---
def safe_resize(clip, size):
    try:
        return clip.resized(new_size=size)
    except:
        return clip.resize(newsize=size)

# --- HELPER FUNCTIONS ---
def get_ad_file():
    for ext in ['.mp4', '.mov', '.gif', '.png', '.jpg']:
        if os.path.exists("ad" + ext):
            return "ad" + ext
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
        except: font = ImageFont.truetype("arial.ttf", font_size)

    return font, font_size

def create_single_letter_image(char, font, filename):
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), char, font=font, anchor="ls")
    char_w = bbox[2] - bbox[0]
    
    canvas_height = 600
    canvas_baseline = 400 
    
    padding_x = 200
    img_w = int(char_w + padding_x)
    img = Image.new('RGBA', (img_w, canvas_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw_x = padding_x // 2
    stroke_width = 3
    for x in range(-stroke_width, stroke_width+1):
        for y in range(-stroke_width, stroke_width+1):
            draw.text((draw_x+x, canvas_baseline+y), char, font=font, fill="black", anchor="ls")
    draw.text((draw_x, canvas_baseline), char, font=font, fill="white", anchor="ls")
    
    img = img.rotate(0, expand=False, resample=Image.BICUBIC)
    img.save(filename)
    return char_w

# --- MAIN APP LOGIC ---
st.set_page_config(page_title="Greeting App", page_icon="🎂", layout="centered")

query_params = st.query_params
url_role = query_params.get("role", "landing")
url_id = query_params.get("id", None)

# --- MODE 1: OWNER REMOTE (Phone) ---
if url_role == "owner":
    if not url_id:
        st.error("❌ Invalid Link. Please scan the QR code on your device again.")
        st.stop()

    st.title("📱 Remote Control")
    
    with st.form("birthday_form"):
        name_input = st.text_input("Enter Name:", max_chars=20, placeholder="e.g. Grandpa").strip()
        submit_btn = st.form_submit_button("Play Video on TV", type="primary")

    if submit_btn:
        if not name_input:
            st.warning("Please enter a name.")
        else:
            status = st.empty()
            prog = st.progress(0)
            
            try:
                status.info("Creating TV-Ready Video (1080p)...")
                full_text = name_input + "!"
                temp_filename = f"temp_{url_id}.mp4"
                final_path = os.path.join(OUTPUT_FOLDER, f"{url_id}.mp4")
                
                # --- PROCESSING ---
                clip = VideoFileClip(TEMPLATE_FILE)
                clip = safe_resize(clip, TARGET_RES)
                
                max_w = clip.w * 0.45 
                start_size = int(clip.h * 0.11) 
                font, font_size = get_font_and_metrics(full_text, max_w, start_size)
                kerning = int(font_size * 0.06)
                
                dummy = ImageDraw.Draw(Image.new('RGB', (1,1)))
                total_w = 0
                widths = []
                for char in full_text:
                    if char == " ":
                        w = int(font_size*0.25)
                        widths.append(w)
                        total_w += w
                    else:
                        w = dummy.textbbox((0,0),char,font)[2]-dummy.textbbox((0,0),char,font)[0]
                        widths.append(w)
                        total_w += w
                total_w -= (len(full_text)-1)*kerning
                
                center_x = clip.w * 0.65
                curr_x = center_x - (total_w / 2)
                
                visual_baseline_y = clip.h * 0.75
                target_y_top = visual_baseline_y - 400
                
                clips = [clip]
                temp_imgs = []
                
                prog.progress(20)
                
                for i, char in enumerate(full_text):
                    if char == " ":
                        curr_x += widths[i] - kerning
                        continue
                    fname = f"t_{i}_{url_id}.png"
                    temp_imgs.append(fname)
                    create_single_letter_image(char, font, fname)
                    lc = ImageClip(fname).with_duration(clip.duration)
                    try:
                        if FadeOut: lc = lc.with_effects([FadeOut(1.0)])
                        else: lc = lc.fadeout(1.0)
                    except: pass
                    
                    st_time = 2.0 + (i*0.1)
                    tx = curr_x - 100 
                    
                    def pos(t): 
                        start_x = clip.w - 1
                        if t < 1.0: 
                            p = 1 - ((1 - t)**3)
                            current = start_x - ((start_x - tx) * p)
                            return (int(current), int(target_y_top))
                        return (int(tx), int(target_y_top))
                    
                    lc = lc.with_start(st_time).with_position(pos)
                    clips.append(lc)
                    curr_x += widths[i] - kerning
                
                final_part = CompositeVideoClip(clips)
                
                ad = get_ad_file()
                if ad:
                    try:
                        if ad.endswith(('.mp4','.mov','.gif')):
                            ac = VideoFileClip(ad)
                        else:
                            ac = ImageClip(ad).with_duration(15)
                        
                        ac = safe_resize(ac, TARGET_RES)
                        ac = ac.with_start(final_part.duration)
                        final_part = CompositeVideoClip([final_part, ac])
                    except: pass
                
                prog.progress(60)
                
                # Write file
                final_part.write_videofile(temp_filename, codec='libx264', audio_codec='aac', fps=clip.fps, logger=None)
                shutil.move(temp_filename, final_path)
                
                prog.progress(100)
                status.success("Sent to TV!")
                
                for f in temp_imgs: 
                    if os.path.exists(f): os.remove(f)
                    
            except Exception as e:
                st.error(f"Error: {e}")

# --- MODE 2: DISPLAY SCREEN (Stick) ---
elif url_role == "display":
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            section.main {padding-top: 0px;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            #MainMenu {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    if not url_id:
        st.error("Setup Error: No Stick ID found in URL.")
        st.stop()

    target_file = os.path.join(OUTPUT_FOLDER, f"{url_id}.mp4")
    
    if os.path.exists(target_file):
        file_stats = os.stat(target_file)
        current_mod_time = file_stats.st_mtime
        
        if "last_played_time" not in st.session_state:
            st.session_state.last_played_time = 0

        if current_mod_time > st.session_state.last_played_time:
            st.video(target_file, autoplay=True)
            st.session_state.last_played_time = current_mod_time
        else:
            st.info(f"Ready. ID: {url_id}")
    else:
        st.title("Waiting for setup...")
        st.write(f"Device ID: {url_id}")

    time.sleep(3)
    st.rerun()

# --- MODE 3: ADMIN ---
else:
    st.title("🏭 Factory Setup")
    
    if "CHANGE-THIS" in BASE_URL:
        st.error("⚠️ WARNING: Please edit Line 12 of webapp.py and paste your Render URL.")
        
    if st.button("Generate New Device ID"):
        new_id = str(uuid.uuid4())[:8] 
        st.success(f"Created ID: {new_id}")
        st.code(f"{BASE_URL}/?role=display&id={new_id}")
        st.code(f"{BASE_URL}/?role=owner&id={new_id}")