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
#     * Slides in from off-screen right
#     * Ends LOWER on the screen, centered in the right side area
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

    # -------- POSITIONING --------
    # Vertical: lower, roughly where the cake text band would be
    # tweakable: 0.70 = 70% down the screen
    band_center_y = int(VIDEO_HEIGHT * 0.70)
    base_y = band_center_y - full_h // 2

    # Horizontal: center in the right-side area
    # assume cake occupies ~left 55% of the screen
    # we center the name around ~72% of the width
    target_center_x = int(VIDEO_WIDTH * 0.72)

    # -------- ANIMATION TIMING --------
    # typewriter: how many frames per letter
    letter_interval_sec = 0.12
    frames_per_letter = max(int(letter_interval_sec * fps), 1)

    # slide: we tie slide progress to how many letters are visible
    total_letters = len(name)
    total_steps = total_letters  # one step per new letter

    # start center way off to the right, enough to hide full text
    start_center_x = VIDEO_WIDTH + full_w

    frame_index = 0
    for frame in reader:
        # how many letters should be visible at this frame?
        step_index = frame_index // frames_per_letter
        letters_visible = min(total_letters, step_index + 1)
        visible_text = name[:letters_visible]

        # slide progress is based on letters revealed (0..1)
        progress = letters_visible / float(total_letters)

        # current center X based on progress
        current_center_x = int(
            start_center_x + (target_center_x - start_center_x) * progress
        )

        # Base frame → PIL → resize to 1920x1080
        pil_frame = Image.fromarray(frame).convert("RGB")
        if pil_frame.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
            pil_frame = pil_frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(pil_frame)

        # measure current substring to center it on current_center_x
        sub_bbox = d.textbbox((0, 0), visible_text, font=font)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]

        x = current_center_x - sub_w // 2
        y = base_y  # vertical stays locked

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
    # Try to visually maximize the video area inside Streamlit
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
        # In desktop Chrome, you may still have to click Play once
        # (autoplay policy). On the stick in kiosk mode, this
        # typically auto-plays as soon as the page loads.
        st.video(OUTPUT_PATH)
