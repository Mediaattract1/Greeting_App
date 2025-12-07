import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import time
import shutil
import gc
import base64

# --- CONFIGURATION ---
BASE_URL = "https://greeting-app-wh2w.onrender.com"
TEMPLATE_FILE = "template_HB1_wide.mp4"
OUTPUT_FOLDER = "generated_videos"
TARGET_RES = (1920, 1080)

# --- SAFE SETUP ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- MOVIEPY IMPORT FIXER ---
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.VideoClip import ImageClip
    try:
        from moviepy.video.fx import FadeOut
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            FadeOut = vfx.FadeOut
        except:
            FadeOut = None
except ImportError:
    import moviepy.editor as mp
    VideoFileClip = mp.VideoFileClip
    CompositeVideoClip = mp.CompositeVideoClip
    ImageClip = mp.ImageClip
    FadeOut = None

# --- HELPER FUNCTIONS ---
def safe_resize(clip, size):
    try:
        return clip.resized(new_size=size)
    except:
        return clip.resize(newsize=size)

def get_ad_file():
    # Kept for future use, but currently unused (ad playback disabled)
    for ext in ['.mp4', '.mov', '.gif', '.png', '.jpg']:
        if os.path.exists("ad" + ext):
            return "ad" + ext
    return None

def create_full_name_image(text, video_h, filename):
    # 🔹 FONT SIZE INCREASED (was 0.12, now 0.16)
    font_size = int(video_h * 0.16)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

    dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad = 50
    img = Image.new('RGBA', (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    x = pad
    y = pad
    stroke = 4
    for i in range(-stroke, stroke + 1):
        for j in range(-stroke, stroke + 1):
            draw.text((x + i, y + j), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")

    img.save(filename)
    return img.width, img.height

# --- APP LOGIC ---
st.set_page_config(page_title="Sign Manager", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
mode = query_params.get("mode", "display")

st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"] {display: none !important;}
    .block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
    ::-webkit-scrollbar {display: none;}
    body, .stApp {background-color: black;}
    p, label, h1, h2, h3 {color: white !important;}
    .stTextInput input {color: black !important;}
    </style>
""", unsafe_allow_html=True)

# === UPDATE MODE ===
if mode == "update":
    st.markdown("""<style>.block-container {padding: 2rem !important;}</style>""", unsafe_allow_html=True)

    if "status" not in st.session_state:
        st.session_state.status = "idle"

    if st.session_state.status == "idle":
        st.title("Create Greeting")
        with st.form("update_form"):
            name_input = st.text_input("Enter Name:", max_chars=20).strip()
            submit = st.form_submit_button("Update Sign", type="primary")

        if submit and name_input:
            st.session_state.status = "processing"
            st.session_state.name_input = name_input
            st.rerun()

    elif st.session_state.status == "processing":
        st.info("Creating Video... Please wait.")
        prog = st.progress(0)

        try:
            full_text = st.session_state.name_input + "!"
            TARGET_FILE = "video.mp4"
            temp_out = "temp_render.mp4"
            temp_img = "temp_text_overlay.png"

            gc.collect()

            if not os.path.exists(TEMPLATE_FILE):
                st.error(f"Missing {TEMPLATE_FILE}")
                st.stop()

            clip = VideoFileClip(TEMPLATE_FILE)
            img_w, img_h = create_full_name_image(full_text, clip.h, temp_img)
            prog.progress(30)

            txt_clip = ImageClip(temp_img).with_duration(clip.duration)

            center_point_x = clip.w * 0.70
            target_x = center_point_x - (img_w / 2)
            target_y = (clip.h * 0.75) - (img_h / 2)

            start_time = 2.0
            slide_dur = 1.0

            def slide_pos(t):
                if t < slide_dur:
                    p = 1 - ((1 - t) ** 3)
                    curr_x = clip.w - ((clip.w - target_x) * p)
                    return (int(curr_x), int(target_y))
                return (int(target_x), int(target_y))

            txt_clip = txt_clip.with_start(start_time).with_position(slide_pos)

            try:
                if FadeOut:
                    txt_clip = txt_clip.with_effects([FadeOut(1.0)])
                else:
                    txt_clip = txt_clip.fadeout(1.0)
            except:
                pass

            # Base birthday video with name overlay
            final = CompositeVideoClip([clip, txt_clip])

            # 🔹 ad.mp4 / ad.png DISABLED FOR NOW
            # ad = get_ad_file()
            # if ad:
            #     try:
            #         if ad.endswith(('.mp4', '.mov')):
            #             ac = VideoFileClip(ad)
            #         else:
            #             ac = ImageClip(ad).with_duration(15)
            #
            #         try:
            #             ac = ac.resized(new_size=clip.size)
            #         except:
            #             ac = ac.resize(newsize=clip.size)
            #
            #         ac = ac.with_start(final.duration)
            #         final = CompositeVideoClip([final, ac])
            #     except:
            #         pass

            prog.progress(60)
            final.write_videofile(temp_out, codec='libx264', audio_codec='aac', fps=24, logger=None)

            clip.close()
            final.close()
            gc.collect()

            shutil.move(temp_out, os.path.join(OUTPUT_FOLDER, TARGET_FILE))
            if os.path.exists(temp_img):
                os.remove(temp_img)

            prog.progress(100)
            st.session_state.status = "done"
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            if st.button("Try Again"):
                st.session_state.status = "idle"
                st.rerun()

    elif st.session_state.status == "done":
        st.balloons()
        st.success(f"Success! Your Greeting for **{st.session_state.name_input}** is playing on the Screen.")
        st.write("")
        if st.button("Create New Greeting"):
            st.session_state.status = "idle"
            st.rerun()

# === DISPLAY MODE (3-LOOP / 30s CYCLE WITH FADE-IN + FADE-OUT) ===
else:
    TARGET_FILE = "video.mp4"
    real_target = os.path.join(OUTPUT_FOLDER, TARGET_FILE)

    if os.path.exists(real_target):
        video_bytes = open(real_target, 'rb').read()
        video_b64 = base64.b64encode(video_bytes).decode()

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100vw;
                height: 100vh;
                background-color: black;
                overflow: hidden;
            }}

            body {{
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            }}

            body.fade-in {{ opacity: 1; }}
            body.fade-out {{ opacity: 0; }}

            .video-wrapper {{
                position: fixed;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: black;
            }}

            video {{
                width: 100vw;
                height: 100vh;
                object-fit: contain;
                pointer-events: none;
            }}
        </style>
        </head>
        <body id="body">
            <div class="video-wrapper">
                <video id="hbVideo" autoplay loop muted playsinline>
                    <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                </video>
            </div>

            <script>
                const video = document.getElementById("hbVideo");

                // Fade in as soon as the video can play
                video.addEventListener("canplay", function() {{
                    document.body.classList.add("fade-in");
                }});

                // 3 loops ≈ 30 seconds for a 10s template
                setTimeout(function() {{
                    document.body.classList.remove("fade-in");
                    document.body.classList.add("fade-out");

                    setTimeout(function() {{
                        window.parent.location.reload(true);
                    }}, 600);
                }}, 30000);
            </script>
        </body>
        </html>
        """

        current_stats = os.stat(real_target).st_mtime
        if "last_version" not in st.session_state:
            st.session_state.last_version = current_stats

        st.components.v1.html(html_code, height=600, scrolling=False)

        if current_stats > st.session_state.last_version:
            st.session_state.last_version = current_stats
            st.rerun()

    else:
        st.info("Waiting for first update...")
        time.sleep(3)
        st.rerun()
