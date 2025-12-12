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
TEMPLATE_FILE = "template_HB1_wide.mp4"
OUTPUT_FOLDER = "generated_videos"
TARGET_RES = (1920, 1080)

# How often the display page should refresh (seconds)
DISPLAY_REFRESH_SECONDS = 180  # 3 minutes

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

# --- NAME NORMALIZATION (Capitalization Helper) ---
def normalize_name(name: str) -> str:
    """
    Fixes capitalization for:
    - Multi-word names
    - Hyphenated names (Anna-Maria)
    - Apostrophes (O'Connor)
    """
    name = name.strip()

    def fix_word(w: str) -> str:
        # Handle O'Connor / D'Angelo
        if "'" in w:
            parts = w.split("'")
            return "'".join(p.capitalize() for p in parts if p)

        # Handle Anna-Maria / Jean-Paul
        if "-" in w:
            parts = w.split("-")
            return "-".join(p.capitalize() for p in parts if p)

        return w.capitalize()

    return " ".join(fix_word(w) for w in name.split() if w)

# --- HELPERS ---
def safe_resize(clip, size):
    try:
        return clip.resized(new_size=size)
    except:
        return clip.resize(newsize=size)

def create_full_name_image(text, video_h, filename, max_width=None):
    """
    Render the name text into an image.
    If max_width is given, automatically shrink the font so that
    the rendered text width does not exceed max_width.
    """
    # Start with the "normal" large size
    base_font_size = int(video_h * 0.16)
    font_size = base_font_size

    # Don't let it get ridiculously tiny
    min_font_size = max(int(video_h * 0.08), 24)

    def load_font(size):
        try:
            return ImageFont.truetype("arialbd.ttf", size)
        except:
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                return ImageFont.load_default()

    # Find a font size that fits within max_width (if provided)
    while True:
        font = load_font(font_size)
        dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        bbox = dummy.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if (max_width is None) or (text_w <= max_width) or (font_size <= min_font_size):
            break

        # Reduce font size a bit and try again
        font_size = int(font_size * 0.9)
        if font_size < min_font_size:
            font_size = min_font_size

    # Now render with the chosen font
    pad = 50
    img = Image.new('RGBA', (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    x, y = pad, pad
    stroke = 4
    for i in range(-stroke, stroke + 1):
        for j in range(-stroke, stroke + 1):
            draw.text((x + i, y + j), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")

    img.save(filename)
    return img.width, img.height

# --- APP SETUP ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")

# === GLOBAL CSS ===
st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"] {display: none !important;}
    .block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
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
            submit = st.form_submit_button("Update Sign", type="primary")

        if submit and name_input:
            st.session_state.status = "processing"
            st.session_state.name_input = name_input
            st.rerun()

    elif st.session_state.status == "processing":
        st.info("Creating Video... Please wait.")
        prog = st.progress(0)

        try:
            # Normalize the name for display & rendering
            normalized = normalize_name(st.session_state.name_input)
            full_text = normalized + "!"

            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            temp_img = "temp_text_overlay.png"

            gc.collect()

            clip = VideoFileClip(TEMPLATE_FILE)

            # Allow the name text to occupy up to ~55% of the video width
            max_name_width = int(clip.w * 0.55)

            img_w, img_h = create_full_name_image(
                full_text,
                clip.h,
                temp_img,
                max_width=max_name_width
            )
            prog.progress(30)

            txt_clip = ImageClip(temp_img).with_duration(clip.duration)

            # Position (same layout as before)
            center_point_x = clip.w * 0.70
            target_x = center_point_x - (img_w / 2)
            target_y = (clip.h * 0.75) - (img_h / 2)

            start_time = 2.0
            slide_dur = 1.0

            def slide_pos(t):
                if t < slide_dur:
                    p = 1 - ((1 - t) ** 3)
                    curr_x = clip.w - ((clip.w - target_x) * p)
                    return (int(curr_x), int(target_y))
                return (int(target_x), int(target_y))

            txt_clip = txt_clip.with_start(start_time).with_position(slide_pos)

            try:
                if FadeOut:
                    txt_clip = txt_clip.with_effects([FadeOut(1.0)])
                else:
                    txt_clip = txt_clip.fadeout(1.0)
            except:
                pass

            final = CompositeVideoClip([clip, txt_clip])

            prog.progress(60)
            final.write_videofile(temp_out, codec='libx264', audio_codec='aac', fps=24, logger=None)

            clip.close()
            final.close()
            gc.collect()

            # Overwrite the live file
            shutil.move(temp_out, os.path.join(OUTPUT_FOLDER, TARGET_FILE))
            if os.path.exists(temp_img):
                os.remove(temp_img)

            prog.progress(100)
            st.session_state.display_name = normalized
            st.session_state.status = "done"
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            if st.button("Try Again"):
                st.session_state.status = "idle"
                st.rerun()

    elif st.session_state.status == "done":
        st.balloons()
        display_name = st.session_state.get("display_name", st.session_state.get("name_input", ""))
        st.success(f"Success! Your Greeting for **{display_name}** is playing on the Screen.")
        if st.button("Create New Greeting"):
            st.session_state.status = "idle"
            st.rerun()

# === DISPLAY MODE (COMPONENT HTML + JS RELOAD) ===
else:
    TARGET_FILE = "video.mp4"
    real_target = os.path.join(OUTPUT_FOLDER, TARGET_FILE)

    if os.path.exists(real_target):
        # Read and base64 encode the video each run
        with open(real_target, "rb") as f:
            video_bytes = f.read()
        video_b64 = base64.b64encode(video_bytes).decode()

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            background-color: black;
            overflow: hidden;
        }}
        video {{
            width: 100vw;
            height: 100vh;
            object-fit: contain;
            background-color: black;
        }}
        </style>
        </head>
        <body>
            <video autoplay loop muted playsinline>
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                Your browser does not support the video tag.
            </video>

            <script>
                // Reload the page every DISPLAY_REFRESH_SECONDS so new videos are picked up
                const RELOAD_MS = {DISPLAY_REFRESH_SECONDS * 1000};
                setTimeout(function() {{
                    window.location.reload(true);
                }}, RELOAD_MS);
            </script>
        </body>
        </html>
        """

        st.components.v1.html(html_code, height=600, scrolling=False)

    else:
        st.markdown(
            "<h2 style='text-align:center; color:white;'>Waiting for first update...</h2>",
            unsafe_allow_html=True,
        )
        # Try again every 5 seconds until the first video exists
        wait_html = """
        <script>
        setTimeout(function() {
            window.location.reload(true);
        }, 5000);
        </script>
        """
        st.markdown(wait_html, unsafe_allow_html=True)
