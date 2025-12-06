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
# Name comes from the RIGHT, one letter at a time,
# and ends up on the RIGHT side between cake & screen edge.
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

    # Prepare font and measure FULL text once (for vertical centering)
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    dummy = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    pimg = Image.fromarray(dummy)
    d = ImageDraw.Draw(pimg)
    full_bbox = d.textbbox((0, 0), name, font=font)
    full_h = full_bbox[3] - full_bbox[1]

    # Vertical center of the text (stays fixed so it doesn't jump)
    y = (VIDEO_HEIGHT - full_h) // 2

    # Horizontal behavior:
    # - Text appears one letter at a time (typewriter)
    # - While it is appearing, the whole block slides in from the RIGHT
    # - Final position is on the RIGHT side of the screen
    slide_seconds = 1.5
    slide_frames = max(int(slide_seconds * fps), 1)

    # We anchor the RIGHT edge of the text near the screen's right side.
    # Example: 96% of width (a little padding from the edge).
    target_right = int(VIDEO_WIDTH * 0.96)

    # We start completely off-screen to the right
    # (we will animate this right edge position)
    # We'll use the full text width for starting offset to ensure fully off-screen.
    full_w = full_bbox[2] - full_bbox[0]
    start_right = VIDEO_WIDTH + full_w

    # Process each frame of the base video
    for i, frame in enumerate(reader):
        pil_frame = Image.fromarray(frame).convert("RGB")

        # Make sure frame is 1920x1080
        if pil_frame.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
            pil_frame = pil_frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(pil_frame)

        # Determine progress (0 to 1) during the slide-in phase
        if i < slide_frames:
            progress = i / float(slide_frames - 1 if slide_frames > 1 else 1)
        else:
            progress = 1.0

        # Number of letters visible (typewriter effect)
        total_letters = len(name)
        letters_visible = max(1, int(progress * total_letters))
        visible_text = name[:letters_visible]

        # Measure the current visible substring
        sub_bbox = d.textbbox((0, 0), visible_text, font=font)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]

        # Vertical stays fixed based on full text
        y_current = (VIDEO_HEIGHT - full_h) // 2

        # Animate the RIGHT edge from off-screen to target_right
        current_right = int(start_right + (target_right - start_right) * progress)

        # Left X is right edge minus width of current substring
        x_current = current_right - sub_w

        # Draw the text
        draw.text((x_current, y_current), visible_text, font=font, fill=(255, 255, 255))

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
# Loads generated_videos/video.mp4 and plays it.
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
        # NOTE: st.video may require one manual "play" click in a browser,
        # but once playing, it will loop. For the Android stick signage,
        # this matches your original pattern of pointing the stick at this URL.
        st.video(OUTPUT_PATH)
