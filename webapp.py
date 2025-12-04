import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import time
import shutil
import gc

# --- CONFIGURATION ---
# The single file everyone watches
TARGET_FILE = "video.mp4" 
TEMPLATE_FILE = "HB Layout1.mp4"
TARGET_RES = (1920, 1080) 

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

# --- HELPERS ---
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

    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while True:
        total_w = 0
        kerning = int(font_size * 0.06)
        for char in text:
            cw = int(font_size * 0.25) if char == " " else (dummy.textbbox((0, 0), char, font)[2] - dummy.textbbox((0, 0), char, font)[0])
            total_w += cw
        if len(text) > 1: total_w -= (len(text) - 1) * kerning
        if total_w < max_width or font_size < 20: break
        font_size = int(font_size * 0.9)
        try: font = ImageFont.truetype("arialbd.ttf", font_size)
        except: pass
    return font, font_size

def create_letter_image(char, font, filename):
    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    char_w = dummy.textbbox((0, 0), char, font=font, anchor="ls")[2] - dummy.textbbox((0, 0), char, font, anchor="ls")[0]
    img = Image.new('RGBA', (int(char_w + 200), 600), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    for x in range(-3,4):
        for y in range(-3,4): d.text((100+x, 400+y), char, font, fill="black", anchor="ls")
    d.text((100, 400), char, font, fill="white", anchor="ls")
    img.rotate(0, expand=False, resample=Image.BICUBIC).save(filename)
    return char_w

# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="centered")

# CSS to hide menus for the TV
st.markdown("""<style>[data-testid="stSidebar"],header,footer,#MainMenu{display:none;}</style>""", unsafe_allow_html=True)

query_params = st.query_params
mode = query_params.get("mode", "display")

# === UPDATE MODE (The Controller) ===
if mode == "update":
    st.title("Update Sign")
    
    with st.form("update_form"):
        name_input = st.text_input("Enter Name:", max_chars=20).strip()
        submit = st.form_submit_button("Update TV")
    
    if submit and name_input:
        status = st.empty()
        status.info("Processing... Please wait 30s.")
        
        try:
            full_text = name_input + "!"
            temp_out = "temp_render.mp4"
            gc.collect()

            clip = VideoFileClip(TEMPLATE_FILE)
            clip = safe_resize(clip, TARGET_RES)
            
            # Font & Metrics
            font, font_size = get_font_and_metrics(full_text, clip.w * 0.45, int(clip.h * 0.11))
            kerning = int(font_size * 0.06)
            
            # Width Calc
            dummy = ImageDraw.Draw(Image.new('RGB', (1,1)))
            total_w = sum([int(font_size*0.25) if c==" " else (dummy.textbbox((0,0),c,font)[2]-dummy.textbbox((0,0),c,font)[0]) for c in full_text])
            total_w -= (len(full_text)-1)*kerning
            
            curr_x = (clip.w * 0.65) - (total_w / 2)
            target_y = (clip.h * 0.75) - 400
            
            clips = [clip]
            temp_imgs = []
            
            # Generate Letters
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
            
            # Ad
            ad = get_ad_file()
            if ad:
                try:
                    ac = VideoFileClip(ad) if ad.endswith(('.mp4','.mov')) else ImageClip(ad).with_duration(15)
                    ac = safe_resize(ac, TARGET_RES).with_start(final.duration)
                    final = CompositeVideoClip([final, ac])
                except: pass
            
            # WRITE (Safe Mode)
            final.write_videofile(temp_out, codec='libx264', audio_codec='aac', fps=clip.fps, logger=None, threads=1)
            
            clip.close()
            final.close()
            gc.collect()
            
            # Overwrite the live file
            shutil.move(temp_out, TARGET_FILE)
            
            for f in temp_imgs: 
                if os.path.exists(f): os.remove(f)
                
            status.success("Success! TV will update shortly.")
            
        except Exception as e:
            status.error(f"Error: {e}")

# === DISPLAY MODE (The TV Stick) ===
else:
    if os.path.exists(TARGET_FILE):
        # 1. Play the video in a loop
        st.video(TARGET_FILE, autoplay=True, loop=True)
        
        # 2. Check for updates silently
        # We store the file's "Last Modified" time in the session
        current_stats = os.stat(TARGET_FILE).st_mtime
        
        if "last_version" not in st.session_state:
            st.session_state.last_version = current_stats
            
        # Wait a bit, then check if file changed
        time.sleep(10)
        
        if current_stats > st.session_state.last_version:
            st.rerun() # Reload page to pick up new video
        else:
            st.rerun() # Just keep the app alive
            
    else:
        st.info("Waiting for first update...")
        time.sleep(5)
        st.rerun()