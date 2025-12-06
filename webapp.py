import os
import tempfile

import streamlit as st
import numpy as np
from moviepy.editor import (
    VideoClip,
    ColorClip,
    TextClip,
    VideoFileClip,
    vfx,
)

# -----------------------
# GLOBAL CONFIG
# -----------------------
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30


# -----------------------
# VIDEO GENERATION LOGIC
# -----------------------
def _compute_fontsize(name: str) -> int:
    """
    Decide font size based on name length.
    Shorter names -> larger font, longer names -> smaller font.
    Tuned for 1920x1080.
    """
    name = name or ""
    n_chars = max(len(name), 4)
    approx = int(1300 / n_chars)

    return max(50, min(220, approx))


def create_name_animation(
    name: str,
    output_path: str,
    *,
    background_video_path: str | None = None,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    text_color: str = "white",
    font: str = "DejaVu-Sans-Bold",
    letter_interval: float | None = None,
    type_fraction: float = 0.6,
    hold_time: float | None = None,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
) -> None:

    name = (name or "").strip()
    if not name:
        name = "Friend"

    n_chars = len(name)
    fontsize = _compute_fontsize(name)

    # --------- Background ---------
    if background_video_path:
        bg = VideoFileClip(background_video_path).resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        duration = bg.duration

        type_duration = max(0.5, duration * type_fraction)

        if letter_interval is None:
            letter_interval = max(0.05, type_duration / max(n_chars, 1))

        bg_clip = bg
    else:
        if letter_interval is None:
            letter_interval = max(0.05, min(0.18, 1.4 / max(n_chars, 1)))

        type_duration = n_chars * letter_interval
        if hold_time is None:
            hold_time = 1.5

        duration = type_duration + hold_time

        bg_clip = ColorClip(
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            color=bg_color,
            duration=duration,
        )

    # ✅ ✅ ✅ FIXED LINE — THIS WAS YOUR SYNTAX ERROR
    partial_texts = [name[:i] for i in range(1, n_chars + 1)]

    max_text_width = int(VIDEO_WIDTH * 0.8)
    partial_clips = []

    for txt in partial_texts:
        tc = TextClip(
            txt,
            fontsize=fontsize,
            color=text_color,
            font=font,
            method="caption",
            size=(max_text_width, None),
            align="center",
        )
        partial_clips.append(tc)

    # --------- Frame Generator ---------
    def make_frame(t: float):
        frame = bg_clip.get_frame(t).copy()

        if t <= 0:
            index = 1
        else:
            index = int(t / letter_interval) + 1
            index = max(1, min(index, n_chars))

        text_clip = partial_clips[index - 1]
        text_frame = text_clip.get_frame(0)
        th, tw, _ = text_frame.shape

        x = (VIDEO_WIDTH - tw) // 2
        y = (VIDEO_HEIGHT - th) // 2

        frame[y:y + th, x:x + tw, :] = text_frame
        return frame

    animated_clip = VideoClip(make_frame, duration=duration)

    if fade_in > 0:
        animated_clip = animated_clip.fx(vfx.fadein, fade_in)
    if fade_out > 0:
        animated_clip = animated_clip.fx(vfx.fadeout, fade_out)

    animated_clip.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="medium",
        threads=4,
    )


# -----------------------
# STREAMLIT APP
# -----------------------
def main():
    st.title("Greeting Video Generator")

    st.write(
        "Enter a name and optionally upload a background MP4. "
        "The video will be generated at 1920×1080 with a typewriter effect."
    )

    name = st.text_input("Name to display", value="Happy Birthday Mary")

    bg_file = st.file_uploader(
        "Optional background video (MP4)",
        type=["mp4"],
    )

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
                bg_path = None
                if bg_file is not None:
                    bg_path = os.path.join(tmpdir, "background.mp4")
                    with open(bg_path, "wb") as f:
                        f.write(bg_file.read())

                output_path = os.path.join(tmpdir, "name_greeting.mp4")

                create_name_animation(
                    name=name,
                    output_path=output_path,
                    background_video_path=bg_path,
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
