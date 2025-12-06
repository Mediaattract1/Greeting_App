import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, VideoClip
import streamlit as st

# ===========================
# PATHS & GLOBAL SETTINGS
# ===========================
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS_DEFAULT = 30

# Template (silent for now, that's fine)
BASE_VIDEO_PATH = "template_HB1_wide.mp4"  # must be in repo root

# Output used by the players (served from /static/)
STATIC_FOLDER = "static"
STATIC_VIDEO_PATH = os.path.join(STATIC_FOLDER, "current.mp4")
STATIC_VERSION_PATH = os.path.join(STATIC_FOLDER, "current.version")

os.makedirs(STATIC_FOLDER, exist_ok=True)

st.set_page_config(layout="wide")


# ===========================
# FONT HELPERS
# ===========================
def _compute_fontsize(name: str) -> int:
    """Scale font size based on name length."""
    n = max(len(name), 4)
    size = int(1300 / n)
    return max(60, min(220, size))


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try a few fonts; fall back to default."""
    for fname in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(fname, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ===========================
# VIDEO GENERATOR (MoviePy)
# - Uses template_HB1_wide.mp4 frames
# - No music required (template has no audio, that's OK)
# - Name:
#     * Smart caps (ALL CAPS preserved, else Title Case)
#     * Types in from the RIGHT, one letter at a time
#     * Slides smoothly from off-screen right
#     * Ends lower on the screen, in the right-side area
# ===========================
def create_name_animation(name: str, output_path: str, version_path: str) -> None:
    # --- Smart capitalization ---
    raw_name = (name or "").strip() or "Friend"
    if raw_name.isupper():
        name = raw_name
    else:
        name = raw_name.title()

    if not os.path.exists(BASE_VIDEO_PATH):
        raise FileNotFoundError(f"Template video not found: {BASE_VIDEO_PATH}")

    base_clip = VideoFileClip(BASE_VIDEO_PATH)
    duration = base_clip.duration
    fps = base_clip.fps or FPS_DEFAULT

    # --- Font & full text metrics ---
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    dummy_img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw_dummy = ImageDraw.Draw(dummy_img)
    full_bbox = draw_dummy.textbbox((0, 0), name, font=font)
    full_w = full_bbox[2] - full_bbox[0]
    full_h = full_bbox[3] - full_bbox[1]

    # --- Positioning: lower right-side region ---
    # Vertical: ~70% down the screen (around cake height)
    band_center_y = int(VIDEO_HEIGHT * 0.70)
    y_final = band_center_y - full_h // 2

    # Horizontal: center in the right-side area (between cake & right edge)
    target_center_x = int(VIDEO_WIDTH * 0.72)
    x_final = target_center_x - full_w // 2

    # Start completely off-screen to the right
    x_start = VIDEO_WIDTH + full_w

    # --- Timing ---
    letter_interval = 0.12  # seconds per letter
    slide_duration = min(1.5, duration)  # seconds for slide-in

    total_letters = len(name)

    def make_frame(t: float) -> np.ndarray:
        # Base frame from template
        frame = base_clip.get_frame(t)
        frame_img = Image.fromarray(frame).convert("RGB")
        frame_img = frame_img.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        draw = ImageDraw.Draw(frame_img)

        # Typewriter: number of letters visible at time t
        letters_visible = max(1, min(total_letters, int(t / letter_interval) + 1))
        visible_text = name[:letters_visible]

        # Smooth slide progress 0..1
        p = min(1.0, t / slide_duration) if slide_duration > 0 else 1.0

        # Current x between off-screen right and final position (no jitter)
        x_current = int(x_start + (x_final - x_start) * p)
        y_current = y_final

        draw.text((x_current, y_current), visible_text, font=font, fill=(255, 255, 255))

        return np.array(frame_img)

    animated_clip = VideoClip(make_frame, duration=duration)

    # No audio for now (template is silent); this is safe even if template has no audio
    if base_clip.audio is not None:
        animated_clip = animated_clip.set_audio(base_clip.audio)

    # Write final MP4
    animated_clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac" if base_clip.audio is not None else None,
        logger=None,  # keep logs quiet
    )

    base_clip.close()
    animated_clip.close()

    # Update version file for heartbeat/auto-update
    with open(version_path, "w") as vf:
        vf.write(str(time.time()))


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
# UPDATE MODE (name entry)
# ===========================
if mode == "update":
    st.title("Birthday Greeting Update")

    name = st.text_input("Enter Name Only", "")

    if st.button("Update Greeting Video"):
        if not name.strip():
            st.error("Please enter a name.")
        else:
            try:
                with st.spinner("Rendering birthday video..."):
                    create_name_animation(name, STATIC_VIDEO_PATH, STATIC_VERSION_PATH)
                st.success("Greeting updated. Screens will switch automatically.")
            except Exception as e:
                st.error(str(e))


# ===========================
# PLAYER MODE (Android Stick / TV)
# ===========================
else:
    initial_ts = int(time.time())

    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          background-color: black;
          overflow: hidden;
        }}
        #hbVideo {{
          width: 100vw;
          height: 100vh;
          object-fit: contain;
          background-color: black;
        }}
        /* Hide default controls where possible */
        video::-webkit-media-controls {{
          display: none !important;
        }}
        video::-moz-media-controls {{
          display: none !important;
        }}
      </style>
    </head>
    <body>
      <video id="hbVideo" autoplay loop muted>
        <source id="hbSource" src="/static/current.mp4?ts={initial_ts}" type="video/mp4" />
      </video>

      <script>
        let lastVersion = null;

        async function checkUpdate() {{
          try {{
            const res = await fetch("/static/current.version?ts=" + Date.now());
            if (!res.ok) return;
            const text = (await res.text()).trim();
            if (lastVersion !== null && text !== lastVersion) {{
              const v = document.getElementById("hbVideo");
              const s = document.getElementById("hbSource");
              const stamp = Date.now();
              s.src = "/static/current.mp4?ts=" + stamp;
              v.load();
              v.play();
            }}
            lastVersion = text;
          }} catch (e) {{
            // ignore network errors, try again later
          }}
        }}

        // Heartbeat: check every 15 seconds
        setInterval(checkUpdate, 15000);
      </script>
    </body>
    </html>
    """

    st.markdown(html, unsafe_allow_html=True)
