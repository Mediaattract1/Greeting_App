import os
import time
import numpy as np
import imageio
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ===========================
# GLOBAL SETTINGS
# ===========================
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
STATIC_VIDEO_PATH = "static/current.mp4"

os.makedirs("static", exist_ok=True)

# Set layout once, at top
st.set_page_config(layout="wide")


# ===========================
# FONT HELPERS
# ===========================
def _compute_fontsize(name: str) -> int:
    n = max(len(name), 4)
    size = int(1300 / n)
    return max(60, min(220, size))


def _load_font(size: int):
    # Try a few common fonts; fall back to default
    for f in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ===========================
# VIDEO GENERATOR
# ===========================
def create_name_animation(name: str, output_path: str):
    # Smart capitalization:
    # - If ALL CAPS, keep it
    # - Otherwise, Title Case
    raw_name = (name or "").strip() or "Friend"
    if raw_name.isupper():
        name = raw_name
    else:
        name = raw_name.title()

    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    # Timing defaults
    letter_interval = 0.12   # seconds per letter
    hold_time = 1.6          # seconds holding full name
    fade_time = 0.5          # seconds fade in/out

    type_time = max(len(name) * letter_interval, letter_interval)
    total_time = type_time + hold_time

    total_frames = max(int(total_time * FPS), 1)
    fade_frames = min(int(fade_time * FPS), total_frames // 2)

    # Precompute vertical centering using the FINAL full name
    tmp_img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp_img)
    full_bbox = tmp_draw.textbbox((0, 0), name, font=font)
    full_h = full_bbox[3] - full_bbox[1]
    y_center = (VIDEO_HEIGHT - full_h) // 2

    writer = imageio.get_writer(
        output_path,
        fps=FPS,
        codec="libx264",
        format="ffmpeg",
    )

    for i in range(total_frames):
        t = i / FPS
        visible_letters = min(len(name), max(1, int(t / letter_interval) + 1))
        text = name[:visible_letters]

        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Horizontal centering (width changes as we type)
        if text:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
        else:
            w = 0

        x = (VIDEO_WIDTH - w) // 2
        y = y_center

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        frame = np.array(img).astype(np.float32)

        # Fade In
        if fade_frames > 0 and i < fade_frames:
            frame *= i / float(fade_frames)

        # Fade Out
        if fade_frames > 0 and i >= total_frames - fade_frames:
            frame *= max((total_frames - 1 - i) / float(fade_frames), 0.0)

        writer.append_data(frame.astype(np.uint8))

    writer.close()


# ===========================
# STREAMLIT ROUTER
# ===========================
params = st.query_params
mode_val = params.get("mode", "player")
if isinstance(mode_val, list):
    mode = (mode_val[0] or "player").lower()
else:
    mode = (mode_val or "player").lower()


# ===========================
# UPDATE MODE (Name Entry)
# ===========================
if mode == "update":
    st.title("Greeting Video Update")
    name = st.text_input("Enter Name Only", "")

    if st.button("Update Greeting Video"):
        if not name.strip():
            st.error("Please enter a name.")
        else:
            with st.spinner("Creating new greeting..."):
                create_name_animation(name, STATIC_VIDEO_PATH)

            st.success("Greeting Updated!")

            # Read bytes for preview to avoid any caching oddities
            try:
                with open(STATIC_VIDEO_PATH, "rb") as f:
                    video_bytes = f.read()
                st.video(video_bytes)
            except FileNotFoundError:
                st.error("Video file not found after generation.")


# ===========================
# PLAYER MODE (Android Stick)
# ===========================
else:
    # Compute a cache-busting query string based on file modification time
    if os.path.exists(STATIC_VIDEO_PATH):
        ts = int(os.path.getmtime(STATIC_VIDEO_PATH))
    else:
        ts = int(time.time())  # fallback, though file should exist after first update

    src_url = f"/static/current.mp4?ts={ts}"

    # Fullscreen-style player page
    st.markdown(
        """
        <style>
        body { background-color: black; margin: 0; }
        video { width: 100vw; height: 100vh; object-fit: contain; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <video autoplay muted loop>
            <source src="{src_url}" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )
