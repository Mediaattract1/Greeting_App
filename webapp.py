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

BASE_VIDEO_PATH = "template_HB1_wide.mp4"  # your birthday template in root
OUTPUT_FOLDER = "generated_videos"
OUTPUT_PATH = os.path.join(OUTPUT_FOLDER, "video.mp4")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
# Uses template_HB1_wide.mp4 as background,
# draws the name sliding in from the left and then staying centered.
# ===========================
def create_name_animation(name: str, output_path: str):
    # Smart capitalization: ALL CAPS stays, otherwise Title Case
    raw_name = (name or "").strip() or "Friend"
    if raw_name.isupper():
        name = raw_name
    else:
        name = raw_name.title()

    if not os.path.exists(BASE_VIDEO_PATH):
        raise FileNotFoundError(f"Base video not found: {BASE_VIDEO_PATH}")

    reader = imageio.get_reader(BASE_VIDEO_PATH, format="ffmpeg")
    meta = reader.get_meta_data()
    fps = meta.get("fps", FPS_DEFAULT)

    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        format="ffmpeg",
    )

    # Prepare font and measure full text
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    dummy = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    pimg = Image.fromarray(dummy)
    d = ImageDraw.Draw(pimg)
    bbox = d.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Vertical center
    y = (VIDEO_HEIGHT - text_h) // 2

    # Slide in over first 1.5s
    slide_seconds = 1.5
    slide_frames = int(slide_seconds * fps)

    x_center = (VIDEO_WIDTH - text_w) // 2
    x_start = -text_w  # fully off-screen to the left

    for i, frame in enumerate(reader):
        pil_frame = Image.fromarray(frame).convert("RGB")

        # Ensure 1920x1080
        if pil_frame.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
            pil_frame = pil_frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(pil_frame)

        # Compute x position
        if i < slide_frames:
            progress = i / max(slide_frames - 1, 1)
            x = int(x_start + (x_center - x_start) * progress)
        else:
            x = x_center

        # Draw text
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
# UPDATE MODE: just generate the video, no preview
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
                    create_name_animation(name, OUTPUT_PATH)
                st.success("Greeting updated on the display.")
            except Exception as e:
                st.error(str(e))


# ===========================
# PLAYER MODE: used by the Stick
# Always loads generated_videos/video.mp4
# ===========================
else:
    st.markdown(
        """
        <style>
        body { background-color: black; margin: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not os.path.exists(OUTPUT_PATH):
        st.write("Waiting for first greeting video...")
    else:
        # This is what the stick sees: the current video, always.
        st.video(OUTPUT_PATH)
