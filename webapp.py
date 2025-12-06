import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
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

# --- MOVIEPY IMPORTS (MODULAR, RENDER SAFE) ---
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.fx import all as vfx

    def apply_fadeout(clip, duration):
        try:
            return vfx.fadeout(clip, duration)
        except Exception:
            return clip

    def apply_fadein(clip, duration):
        try:
            return vfx.fadein(clip, duration)
        except Exception:
            return clip

    def apply_typewriter(clip, duration):
        w, h = clip.size

        def x2_func(t):
            progress = min(1.0, max(0.0, t / duration))
            return int(w * progress)

        try:
            return vfx.crop(clip, x1=0, y1=0, x2=x2_func, y2=h)
        except Exception:
            return clip

except ImportError as e:
    raise RuntimeError(
        "MoviePy failed to import. Ensure moviepy, imageio, and imageio-ffmpeg are installed."
    ) from e


# --- HELPER FUNCTIONS ---
def get_ad_file():
    for ext in ['.mp4', '.mov', '.gif', '.png', '.jpg']:
        if os.path.exists("ad" + ext):
            return "ad" + ext
    return None


def measure_text_size(text, font):
    img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def create_full_name_image(text, video_w, video_h, filename, max_width_ratio=0.75):
    max_text_width = int(video_w * max_width_ratio)
    font_size = int(video_h * 0.22)

    def load_font(sz):
        for f in ["arialbd.ttf", "arial.ttf"]:
            try:
                return ImageFont.truetype(f, sz)
            except:
                pass
        return ImageFont.load_default()

    while font_size > 12:
        font = load_font(font_size)
        tw, th = measure_text_size(text, font)
        if tw <= max_text_width:
            break
        font_size -= 2

    font = load_font(font_size)
    tw, th = measure_text_size(text, font)

    pad = 50
    img_w, img_h = tw + pad * 2, th + pad * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for i in range(-3, 4):
        for j in range(-3, 4):
            draw.text((pad + i, pad + j), text, font=font, fill="black")

    draw.text((pad, pad), text, font=font, fill="white")
    img.save(filename)

    return img_w, img_h


# --- STREAMLIT PAGE SETUP ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")
if isinstance(mode, list):
    mode = mode[0]

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

# =====
