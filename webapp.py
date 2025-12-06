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
FPS_DEFAULT = 30
STATIC_VIDEO_PATH = "static/current.mp4"
BASE_VIDEO_PATH = "assets/birthday_base.mp4"  # <-- put your cake video here

os.makedirs("static", exist_ok=True)

st.set_page_config(layout="wide")


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
# Background: existing birthday cake video
# Text: slides in from left to center, then stays.
# ===========================
def create_name_animation(name: str, output_path: str):
    # Smart capitalization: ALL CAPS stays, otherwise Title Case
    raw_name = (name or "").strip() or "Friend"
    if raw_name.isupper():
        name = raw_name
    else:
        name = raw_name.title()

    # Open base birthday video
    if not os.path.exists(BASE_VIDEO_PATH):
        raise FileNotFoundError(f"Base video not found at {BASE_VIDEO_PATH}")

    reader = imageio.get_reader(BASE_VIDEO_PATH, format="ffmpeg")
    meta = reader.get_meta_data()
    fps = meta.get("fps", FPS_DEFAULT)

    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        format="ffmpeg",
    )

    # Prepare font and measure full text once
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    # We’ll need text size for centering and slide calculation
    dummy_img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    pil_dummy = Image.fromarray(dummy_img)
    draw_dummy = ImageDraw.Draw(pil_dummy)
    bbox = draw_dummy.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Vertical center stays fixed
    y = (VIDEO_HEIGHT - text_h) // 2

    # Sliding: over the first ~1.5 seconds, we move from off-screen left to center
    slide_seconds = 1.5
    slide_frames = int(slide_seconds * fps)

    # Final centered x position
    x_center = (VIDEO_WIDTH - text_w) // 2
    # Start completely off-screen left
    x_start = -text_w

    # Process each frame of the base video
    for i, frame in enumerate(reader):
        frame_h, frame_w = frame.shape[0], frame.shape[1]

        # Ensure frame is 1920x1080 by resizing if needed
        pil_frame = Image.fromarray(frame).convert("RGB")
        if (frame_w, frame_h) != (VIDEO_WIDTH, VIDEO_HEIGHT):
            pil_frame = pil_frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(pil_frame)

        # Compute horizontal position based on frame index
        if i < slide_frames:
            # Progress from 0.0 to 1.0
            progress = i / max(slide_frames - 1, 1)
            x = int(x_start + (x_center - x_start) * progress)
        else:
            x = x_center

        # Draw the text over the frame
        draw.text((x, y), name, font=font, fill=(255, 255, 255))

        writer.append_data(np.array(pil_frame))

    reader.close()
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
# UPDATE MODE (Name Entry ONLY)
# No test video, just regenerate the birthday MP4.
# ===========================
if mode == "update":
    st.title("Birthday Greeting Update")
    name = st.text_input("Enter Name Only", "")

    if st.button("Update Greeting Video"):
        if not name.strip():
            st.error("Please enter a name.")
        else:
            try:
                with st.spinner("Creating birthday greeting..."):
                    create_name_animation(name, STATIC_VIDEO_PATH)
                st.success("Greeting updated. The display should pick it up.")
            except FileNotFoundError as e:
                st.error(str(e))


# ===========================
# PLAYER MODE (Android Stick)
# Just shows the current.mp4 full screen.
# Your stick / remote logic is responsible for reloading when needed.
# ===========================
else:
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
        """
        <video autoplay muted loop>
            <source src="/static/current.mp4" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )
