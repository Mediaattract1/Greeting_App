import os
import tempfile

import numpy as np
import imageio.v3 as iio
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# -----------------------
# GLOBAL CONFIG
# -----------------------
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30


# -----------------------
# FONT + SIZE HELPERS
# -----------------------
def _compute_fontsize(name: str) -> int:
    """
    Decide font size based on name length.
    Shorter names -> larger font, longer names -> smaller font.
    Tuned for 1920x1080.
    """
    name = name or ""
    n_chars = max(len(name), 4)
    approx = int(1300 / n_chars)  # main knob

    return max(50, min(220, approx))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try a few common fonts; fall back to Pillow's default if none are found.
    """
    for fname in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(fname, size)
        except Exception:
            continue
    return ImageFont.load_default()


# -----------------------
# VIDEO GENERATION
# -----------------------
def create_name_animation(
    name: str,
    output_path: str,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    text_color: tuple[int, int, int] = (255, 255, 255),
    fade_in: float = 0.5,
    fade_out: float = 0.5,
) -> None:
    """
    Create a 1920x1080 MP4 where `name` appears one letter at a time.

    - Uses solid background color (bg_color).
    - Adds fade in/out for smoother loop transitions.
    """

    name = (name or "").strip()
    if not name:
        name = "Friend"

    n_chars = len(name)
    fontsize = _compute_fontsize(name)
    font = _load_font(fontsize)

    # Timing: typewriter + hold
    letter_interval = max(0.05, min(0.18, 1.4 / max(n_chars, 1)))
    hold_time = 1.5  # seconds to hold full name
    type_duration = n_chars * letter_interval
    total_duration = type_duration + hold_time

    total_frames = int(total_duration * FPS)
    fade_in_frames = int(fade_in * FPS)
    fade_out_frames = int(fade_out * FPS)

    # Use imageio-ffmpeg via imageio.v3 to write MP4
    with iio.get_writer(
        output_path,
        fps=FPS,
        codec="libx264",
    ) as writer:
        for frame_idx in range(total_frames):
            t = frame_idx / FPS

            # How many letters should be visible at this time?
            if t <= 0:
                num_letters = 1
            else:
                num_letters = min(n_chars, int(t / letter_interval) + 1)
            text_to_show = name[:num_letters]

            # Create base image
            img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Measure text and center it
            text_w, text_h = draw.textsize(text_to_show, font=font)
            x = (VIDEO_WIDTH - text_w) // 2
            y = (VIDEO_HEIGHT - text_h) // 2
            draw.text((x, y), text_to_show, font=font, fill=text_color)

            frame = np.array(img).astype(np.float32)

            # Fade in
            if fade_in_frames > 0 and frame_idx < fade_in_frames:
                alpha = frame_idx / max(fade_in_frames, 1)
                frame *= alpha

            # Fade out
            if fade_out_frames > 0 and frame_idx >= total_frames - fade_out_frames:
                beta = (total_frames - 1 - frame_idx) / max(fade_out_frames, 1)
                beta = max(beta, 0.0)
                frame *= beta

            frame = np.clip(frame, 0, 255).astype(np.uint8)
            writer.append_data(frame)


# -----------------------
# STREAMLIT APP
# -----------------------
def main():
    st.title("Greeting Video Generator")

    st.write(
        "Enter a name and we’ll generate a 1920×1080 MP4 where the name "
        "appears one letter at a time, with automatic font sizing."
    )

    name = st.text_input("Name to display", value="Happy Birthday Mary")

    col1, col2 = st.columns(2)
    with col1:
        fade_in = st.slider("Fade in (seconds)", 0.0, 2.0, 0.5, 0.1)
    with col2:
        fade_out = st.slider("Fade out (seconds)", 0.0, 2.0, 0.5, 0.1)

    if st.button("Create Video"):
        if not name.strip():
            st.error("Please enter a name.")
            return

        with st.spinner("Generating video..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, "name_greeting.mp4")

                create_name_animation(
                    name=name,
                    output_path=output_path,
                    fade_in=fade_in,
                    fade_out=fade_out,
                )

                with open(output_path, "rb") as f:
                    video_bytes = f.read()

        st.success("Video created successfully!")
        st.video(video_bytes)

        st.download_button(
            "Download MP4",
            data=video_bytes,
            file_name="name_greeting.mp4",
            mime="video/mp4",
        )


if __name__ == "__main__":
    main()
