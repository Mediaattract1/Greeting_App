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
    n_chars = max(len(name), 4)  # avoid tiny denominators
    approx = int(1300 / n_chars)  # main knob: bigger -> larger text

    # Clamp to a reasonable range
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
    """
    Create a 1920x1080 MP4 where the given name appears one letter at a time.

    If background_video_path is provided:
        - That video (cake, animation, etc.) is resized to 1920x1080 and used as background.
        - Typing happens in the first `type_fraction` of the video duration.

    If background_video_path is None:
        - A solid color background is used.
        - Duration is: (typing time) + (hold_time).

    Parameters
    ----------
    name : str
        The name to display (can be multiple words).
    output_path : str
        Path of the output MP4 file.
    background_video_path : str | None
        Optional path to an existing MP4 used as background.
    bg_color : tuple[int, int, int]
        Background color when no background video is provided.
    text_color : str
        Color of the name text.
    font : str
        System font available in the Render container.
    letter_interval : float | None
        Seconds per letter. If None, computed automatically.
    type_fraction : float
        When using a background video, fraction of its duration used for typing.
    hold_time : float | None
        Extra time to hold the full name (no background video mode).
    fade_in : float
        Fade-in duration (seconds).
    fade_out : float
        Fade-out duration (seconds).
    """
    name = (name or "").strip()
    if not name:
        name = "Friend"

    n_chars = len(name)
    fontsize = _compute_fontsize(name)

    # --------- Background clip ---------
    if background_video_path:
        bg = VideoFileClip(background_video_path).resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        duration = bg.duration

        type_duration = max(0.5, duration * type_fraction)

        if letter_interval is None:
            letter_interval = max(0.05, type_duration / max(n_chars, 1))

        bg_clip = bg
    else:
        # Solid background mode
        if letter_interval is None:
            # Target roughly 1.2–1.8 sec typing total
            letter_interval = max(0.05, min(0.18, 1.4 / max(n_chars, 1)))

        type_duration = n_chars * letter_interval
        if hold_time is None:
            hold_time = 1.5  # seconds full name on screen

        duration = type_duration + hold_time

        bg_clip = ColorClip(
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            color=bg_color,
            duration=duration,
        )

    # --------- Precompute partial text clips ---------
    partial_texts = [name[:i] for i in range]()_
