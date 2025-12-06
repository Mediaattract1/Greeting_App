import os
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

# ===========================
# FONT HELPERS
# ===========================
def _compute_fontsize(name: str) -> int:
    n = max(len(name), 4)
    size = int(1300 / n)
    return max(60, min(220, size))


def _load_font(size: int):
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
    name = name.strip() if name.strip() else "Friend"

    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    # 🔒 Locked-in safe defaults (no UI dials)
    letter_interval = 0.12
    hold_time = 1.6
    fade_time = 0.5

    type_time = len(name) * letter_interval
    total_time = type_time + hold_time

    total_frames = int(total_time * FPS)
    fade_frames = int(fade_time * FPS)

    writer = imageio.get_writer(
        output_path,
        fps=FPS,
        codec="libx264"
    )

    for i in range(total_frames):
        t = i / FPS
        visible_letters = min(len(name), int(t / letter_interval) + 1)
        text = name[:visible_letters]

        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        w, h = draw.textsize(text, font=font)
        x = (VIDEO_WIDTH - w) // 2
        y = (VIDEO_HEIGHT - h) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        frame = np.array(img).astype(np.float32)

        # Fade In
        if i < fade_frames:
            frame *= i / fade_frames

        # Fade Out
        if i > total_frames - fade_frames:
            frame *= max((total_frames - i) / fade_frames, 0)

        writer.append_data(frame.astype(np.uint8))

    writer.close()


# ===========================
# STREAMLIT ROUTER (UPDATED ✅)
# ===========================
query = st.query_params
mode = query.get("mode", "player").lower()


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
                temp_path = STATIC_VIDEO_PATH + ".tmp"
                create_name_animation(name, temp_path)
                os.replace(temp_path, STATIC_VIDEO_PATH)

            st.success("Greeting Updated!")
            st.video(STATIC_VIDEO_PATH)


# ===========================
# PLAYER MODE (Android Stick)
# ===========================
else:
    st.set_page_config(layout="wide")
    st.markdown(
        """
        <style>
        body { background-color: black; margin: 0; }
        video { width: 100vw; height: 100vh; object-fit: contain; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <video autoplay muted loop>
            <source src="/static/current.mp4" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True
    )
