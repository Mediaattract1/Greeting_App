"""
Generate a 1920x1080 MP4 where a name appears one letter at a time,
with automatic font sizing based on name length.

Can either:
- Use a solid background color, OR
- Overlay the animated name on top of an existing background video
  (e.g. your cake / greeting animation).

This is designed to plug into your existing Render / GitHub / Streamlit setup.
"""

import numpy as np
from moviepy.editor import (
    VideoClip,
    ColorClip,
    TextClip,
    VideoFileClip,
    vfx,
)


VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30


def _compute_fontsize(name: str) -> int:
    """
    Heuristic to pick a font size based on name length.
    Short names => bigger font, long names => smaller font.
    Tuned for 1920x1080 output.
    """
    n_chars = max(len(name), 4)  # avoid tiny denominators
    approx = int(1300 / n_chars)  # main knob: bigger number -> bigger text

    # Clamp to a reasonable range
    return max(50, min(220, approx))


def create_name_animation(
    name: str,
    output_path: str = "name_greeting.mp4",
    *,
    # If you pass a path here, the name will be overlaid on that video.
    # If None, we use a solid background.
    background_video_path: str | None = None,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    text_color: str = "white",
    font: str = "DejaVu-Sans-Bold",
    # Timing controls
    letter_interval: float | None = None,
    type_fraction: float = 0.6,   # fraction of duration spent "typing"
    hold_time: float | None = None,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
):
    """
    Create a 1920x1080 MP4 with the given name animated letter-by-letter.

    Parameters
    ----------
    name : str
        The name to display (can be multiple words).
    output_path : str
        Output MP4 file path.
    background_video_path : str | None
        If provided, this video is used as the background and resized to 1920x1080.
        If None, a solid bg_color is used.
    bg_color : (R, G, B)
        Background color when no background_video_path is supplied.
    text_color : str
        Name text color.
    font : str
        Font name installed in the Render container.
    letter_interval : float | None
        Seconds per letter. If None, computed from duration & name length.
    type_fraction : float
        For background videos: fraction of total duration used for the typing effect (0–1).
        Ignored when there is no background video (we compute timing from name length).
    hold_time : float | None
        Extra time to hold the full name after typing finishes when using *no* background video.
        If None and background_video_path is set, we just use the background video duration.
    fade_in / fade_out : float
        Fade duration (seconds) at start/end for smoother looping.
    """
    name = (name or "").strip()
    if not name:
        name = "Friend"

    n_chars = len(name)
    fontsize = _compute_fontsize(name)

    # --------- Background clip setup ---------
    if background_video_path is not None:
        bg = VideoFileClip(background_video_path).resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        duration = bg.duration

        # Typing happens in the first part of the clip
        type_duration = max(0.5, duration * type_fraction)

        if letter_interval is None:
            letter_interval = max(0.05, type_duration / max(n_chars, 1))

        # No separate hold_time needed; background duration controls end
        bg_clip = bg

    else:
        # No background video: we build a solid-color clip whose duration
        # is driven by the typing + optional hold.
        if letter_interval is None:
            # Target ~1.2–1.8 seconds total typing
            letter_interval = max(0.05, min(0.18, 1.4 / max(n_chars, 1)))

        type_duration = n_chars * letter_interval
        if hold_time is None:
            hold_time = 1.5  # seconds to keep full name on screen

        duration = type_duration + hold_time

        bg_clip = ColorClip(
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            color=bg_color,
            duration=duration,
        )

    # --------- Precompute partial text clips ---------
    partial_texts = [name[:i] for i in range(1, n_chars + 1)]
    max_text_width = int(VIDEO_WIDTH * 0.8)  # margin on left/right

    partial_clips = []
    for txt in partial_texts:
        # method="caption" handles multi-word strings nicely
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

    # --------- Frame generator ---------
    def make_frame(t: float):
        # Background frame
        frame = bg_clip.get_frame(t).copy()

        # Decide how many letters should be visible at time t
        if t <= 0:
            index = 1  # show first letter at t ~ 0
        else:
            index = int(t / letter_interval) + 1
            index = max(1, min(index, n_chars))

        text_clip = partial_clips[index - 1]

        text_frame = text_clip.get_frame(0)
        th, tw, _ = text_frame.shape
        x = (VIDEO_WIDTH - tw) // 2
        y = (VIDEO_HEIGHT - th) // 2

        # Overlay text in the center
        frame[y:y + th, x:x + tw, :] = text_frame

        return frame

    animated_clip = VideoClip(make_frame, duration=duration)

    # Fade in/out so your Android loop doesn’t feel abrupt
    if fade_in > 0:
        animated_clip = animated_clip.fx(vfx.fadein, fade_in)
    if fade_out > 0:
        animated_clip = animated_clip.fx(vfx.fadeout, fade_out)

    # --------- Export ---------
    animated_clip.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="medium",
        threads=4,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate name animation video.")
    parser.add_argument("name", help="Name to display, e.g. 'Happy Birthday Mary Ann'")
    parser.add_argument(
        "-o",
        "--output",
        default="name_greeting.mp4",
        help="Output MP4 filename (default: name_greeting.mp4)",
    )
    parser.add_argument(
        "-b",
        "--background",
        default=None,
        help="Optional background video path (cake, animation, etc.)",
    )
    args = parser.parse_args()

    create_name_animation(
        name=args.name,
        output_path=args.output,
        background_video_path=args.background if args.background else None,
    )
