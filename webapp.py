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

BASE_VIDEO_PATH = "template_HB1_wide.mp4"  # birthday template in root
OUTPUT_FOLDER = "generated_videos"
OUTPUT_PATH = os.path.join(OUTPUT_FOLDER, "video.mp4")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

st.set_page_config(layout="wide")


# ===========================
# FONT HELPERS
# ===========================
def _compute_fontsize(name: str) -> int:
    """Scale font size based on name length."""
    n = max(len(name), 4)
    size = int(1300 / n)
    return max(60, min(220, size))


def _load_font(size: int):
    """Try a few fonts; fall back to default."""
    for f in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ===========================
# VIDEO GENERATOR
# - Uses template_HB1_wide.mp4 as background
# - Name:
#     * Smart caps (ALL CAPS respected, else Title Case)
#     * Types in from the RIGHT, one letter at a time
#     * Ends up LOWER on the screen (cake height)
#     * Centered in the RIGHT HALF between cake and right edge
# ===========================
def create_name_animation(name: str, output_path: str):
    # Smart capitalization
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

    # Font & full text metrics
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    dummy = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    pimg = Image.fromarray(dummy)
    d = ImageDraw.Draw(pimg)
    full_bbox = d.textbbox((0, 0), name, font=font)
    full_w = full_bbox[2] - full_bbox[0]
    full_h = full_bbox[3] - full_bbox[1]

    # -------- POSITIONING LOGIC --------
    # Vertical: lower, closer to cake height (around 70% down)
    cake_band_center_y = int(VIDEO_HEIGHT * 0.70)
    y = cake_band_center_y - full_h // 2

    # Horizontal: assume cake occupies roughly LEFT 55% of the screen.
    # We center the name in the RIGHT HALF between cake edge and screen edge.
    cake_right_x = int(VIDEO_WIDTH * 0.55)
    right_edge_x = int(VIDEO_WIDTH * 0.98)
    target_center_x = (cake_right_x + right_edge_x) // 2

    # Sliding from off-screen right
    slide_seconds = 1.5
    slide_frames = max(int(slide_seconds * fps), 1)

    # Typewriter timing
    letter_interval = 0.12  # seconds per letter

    frame_index = 0
    for frame in reader:
        t = frame_index / fps

        # Typewriter: letters visible based on time
        letters_visible = min(len(name), max(1, int(t / letter_interval) + 1))
        visible_text = name[:letters_visible]

        # Slide progress 0..1 over slide_seconds
        if t < slide_seconds:
            progress_slide = t / slide_seconds
        else:
            progress_slide = 1.0

        # Base frame → PIL → resize to 1920x1080 to fill as much as possible
        pil_frame = Image.fromarray(frame).convert("RGB")
        if pil_frame.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
            pil_frame = pil_frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(pil_frame)

        # Width of current substring
        sub_bbox = d.textbbox((0, 0), visible_text, font=font)
        sub_w = sub_bbox[2] - sub_bbox[0]

        # Slide center from off-screen right to target_center_x
        start_center_x = VIDEO_WIDTH + sub_w // 2
        current_center_x = int(
            start_center_x + (target_center_x - start_center_x) * progress_slide
        )
        x = current_center_x - sub_w // 2

        draw.text((x, y), visible_text, font=font, fill=(255, 255, 255))

        writer.append_data(np.array(pil_frame))
        frame_index += 1

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
# UPDATE MODE (no preview, just generate)
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
# PLAYER MODE (Stick / browser viewer)
# ===========================
else:
    # Try to visually maximize the video area
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            margin: 0;
            padding: 0;
            background-color: black;
        }
        .stVideo > video {
            width: 100vw !important;
            height: 100vh !important;
            object-fit: contain !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not os.path.exists(OUTPUT_PATH):
        st.write("Waiting for first greeting video...")
    else:
        # For the stick: it will load this URL and play this video.
        # For browsers: some may require you to hit "play" once, depending on autoplay policy.
        st.video(OUTPUT_PATH)
