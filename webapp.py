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
TEMPLATE_FILE = "template_HB1_wide.mp4"
OUTPUT_FOLDER = "generated_videos"
TARGET_RES = (1920, 1080)

# --- SAFE SETUP ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- MOVIEPY IMPORT FIXER (MODULAR IMPORTS, NO moviepy.editor) ---
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.fx import all as vfx

    moviepy_fadeout = vfx.fadeout
    moviepy_fadein = vfx.fadein
    crop = vfx.crop

    def apply_fadeout(clip, duration):
        try:
            return moviepy_fadeout(clip, duration)
        except Exception:
            return clip

    def apply_fadein(clip, duration):
        try:
            return moviepy_fadein(clip, duration)
        except Exception:
            return clip

    def apply_typewriter(clip, duration):
        """
        Reveal the text from left to right over `duration` seconds.
        Uses a horizontal crop that grows with time (typewriter-like).
        """
        w, h = clip.size

        if duration <= 0:
            return clip

        def x2_func(t):
            # t is local to this clip (after set_start); 0..duration
            progress = max(0.0, min(1.0, t / duration))
            return int(w * progress)

        try:
            return crop(clip, x1=0, y1=0, x2=x2_func, y2=h)
        except Exception:
            # If crop fx is unavailable, just return the original clip
            return clip

except ImportError as e:
    raise RuntimeError(
        "MoviePy is required but not installed correctly. "
        "Make sure 'moviepy', 'imageio', and 'imageio-ffmpeg' are in requirements.txt."
    ) from e


# --- HELPER FUNCTIONS ---
def safe_resize(clip, size):
    try:
        return clip.resized(new_size=size)
    except Exception:
        return clip.resize(newsize=size)


def get_ad_file():
    for ext in ['.mp4', '.mov', '.gif', '.png', '.jpg']:
        if os.path.exists("ad" + ext):
            return "ad" + ext
    return None


def measure_text_size(text, font):
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    return text_w, text_h


def create_full_name_image(text, video_w, video_h, filename, max_width_ratio=0.75):
    """
    Create a PNG with the name text, automatically adjusting font size
    so that the text width <= max_width_ratio * video_w.

    Returns (img_w, img_h).
    """
    max_text_width = int(video_w * max_width_ratio)

    # Start with a relatively large font size proportional to height
    base_font_size = int(video_h * 0.20)
    font_size = base_font_size

    # Try bold first, then regular, then default
    def load_font(fs):
        for fname in ["arialbd.ttf", "arial.ttf"]:
            try:
                return ImageFont.truetype(fname, fs)
            except Exception:
                continue
        return ImageFont.load_default()

    # Decrease font until text fits the desired width or font becomes too small
    while font_size > 10:
        font = load_font(font_size)
        text_w, text_h = measure_text_size(text, font)
        if text_w <= max_text_width:
            break
        font_size -= 2

    # Use final font to render
    font = load_font(font_size)
    text_w, text_h = measure_text_size(text, font)

    pad = 50
    img_w = text_w + pad * 2
    img_h = text_h + pad * 2

    img = Image.new('RGBA', (img_w, img_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    x = pad
    y = pad
    stroke = 4

    # Outline
    for i in range(-stroke, stroke + 1):
        for j in range(-stroke, stroke + 1):
            draw.text((x + i, y + j), text, font=font, fill="black")

    # Main text
    draw.text((x, y), text, font=font, fill="white")

    img.save(filename)
    return img_w, img_h


# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
_raw_mode = query_params.get("mode", "display")
if isinstance(_raw_mode, list):
    mode = _raw_mode[0] if _raw_mode else "display"
else:
    mode = _raw_mode or "display"

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
            full_text = st.session_state.name_input + "!"
            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            temp_img = "temp_text_overlay.png"

            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}")
                st.stop()

            # Load base template video
            clip = VideoFileClip(TEMPLATE_FILE)
            prog.progress(10)

            # Create dynamic-sized name image based on name length and video width
            img_w, img_h = create_full_name_image(full_text, clip.w, clip.h, temp_img)
            prog.progress(25)

            # Build text clip for entire duration
            txt_clip = ImageClip(temp_i
