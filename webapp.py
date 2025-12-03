import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys

# --- CONFIGURATION ---
# Make sure these match your file names exactly
TEMPLATE_FILE = "HB Layout1.mp4" 
AD_FILE_PREFIX = "ad"

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
def get_ad_file():
    extensions = ['.mp4', '.mov', '.gif', '.png', '.jpg']
    for ext in extensions:
        if os.path.exists("ad" + ext):
            return "ad" + ext
    return None

def get_font_and_metrics(text, max_width, start_size):
    font_size = start_size
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    
    while True:
        total_w = 0
        kerning = int(font_size * 0.06)
        for char in text:
            if char == " ":
                cw = int(font_size * 0.25) 
                total_w += cw
            else:
                bbox = dummy_draw.textbbox((0, 0), char, font=font)
                total_w += (bbox[2] - bbox[0])
        
        if len(text) > 1:
            total_w -= (len(text) - 1) * kerning
        
        if total_w < max_width or font_size < 20:
            break
        font_size = int(font_size * 0.9)
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
            font = ImageFont.truetype("arial.ttf", font_size)

    ref_bbox = dummy_draw.textbbox((0, 0), "Ay!^_", font=font, anchor="ls")
    fixed_height = (-ref_bbox[1]) + ref_bbox[3]
    max_ascent = -ref_bbox[1]
    
    return font, font_size, fixed_height, max_ascent

def create_single_letter_image(char, font, filename, fixed_height, max_ascent):
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), char, font=font, anchor="ls")
    char_w = bbox[2] - bbox[0]
    
    canvas_height = 600
    canvas_baseline = 400 
    padding_x = 200
    img_w = int(char_w + padding_x)
    
    img = Image.new('RGBA', (img_w, canvas_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw_x = padding_x // 2
    stroke_width = 3
    
    for x in range(-stroke_width, stroke_width+1):
        for y in range(-stroke_width, stroke_width+1):
            draw.text((draw_x+x, canvas_baseline+y), char, font=font, fill="black", anchor="ls")
    draw.text((draw_x, canvas_baseline), char, font=font, fill="white", anchor="ls")
    
    img = img.rotate(0, expand=False, resample=Image.BICUBIC)
    img.save(filename)
    return char_w

# --- STREAMLIT APP LAYOUT ---
st.set_page_config(page_title="Birthday Video", page_icon="🎂", layout="centered")

st.title("🎂 Birthday Video Maker")

if not os.path.exists(TEMPLATE_FILE):
    st.error(f"Error: Could not find '{TEMPLATE_FILE}' in the folder.")
    st.stop()

name_input = st.text_input("Enter Name:", max_chars=20)

if st.button("Create Video"):
    if not name_input:
        st.warning("Please enter a name first.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Initializing...")
        
        try:
            # --- PROCESSING LOGIC ---
            raw_name = name_input.strip()
            full_text = raw_name + "!"
            output_filename = f"Birthday_{raw_name}.mp4"
            
            clip = VideoFileClip(TEMPLATE_FILE)
            
            # Metrics
            max_w = clip.w * 0.45 
            start_size = int(clip.h * 0.11) 
            font, font_size, fixed_height, max_ascent = get_font_and_metrics(full_text, max_w, start_size)
            kerning = int(font_size * 0.06)

            # Calculate Widths
            dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
            total_text_width = 0
            char_widths = []
            for char in full_text:
                if char == " ":
                    cw = int(font_size * 0.25)
                    char_widths.append(cw)
                    total_text_width += cw
                else:
                    bbox = dummy_draw.textbbox((0, 0), char, font=font)
                    cw = bbox[2] - bbox[0]
                    char_widths.append(cw)
                    total_text_width += cw
            total_text_width -= (len(full_text) - 1) * kerning

            # Positions
            center_x = clip.w * 0.65 
            current_target_x = center_x - (total_text_width / 2)
            visual_baseline_y = clip.h * 0.75
            target_y_top = visual_baseline_y - 400

            clips_to_composite = [clip] 
            start_time_base = 2.0
            stagger_delay = 0.1 
            slide_duration = 1.0 
            fade_duration = 1.0
            
            temp_files = []

            # Generate Letters
            status_text.text("Generating text animation...")
            progress_bar.progress(20)
            
            for i, char in enumerate(full_text):
                if char == " ":
                    current_target_x += char_widths[i] - kerning
                    continue
                
                temp_file = f"temp_char_{i}.png"
                temp_files.append(temp_file)
                create_single_letter_image(char, font, temp_file, fixed_height, max_ascent)
                
                letter_clip = ImageClip(temp_file).with_duration(clip.duration)
                try:
                    if FadeOut:
                        letter_clip = letter_clip.with_effects([FadeOut(fade_duration)])
                    else:
                        letter_clip = letter_clip.fadeout(fade_duration)
                except: pass

                my_start_time = start_time_base + (i * stagger_delay)
                my_target_x = current_target_x 
                my_visual_x = my_target_x - 100 
                my_start_x = clip.w - 1 

                def get_slide_pos(t, sx=my_start_x, tx=my_visual_x, ty=target_y_top, dur=slide_duration):
                    if t < 0: return (int(sx), int(ty))
                    if t < dur:
                        ratio = t / dur
                        progress = 1 - ((1 - ratio) ** 3)
                        curr_x = sx - ((sx - tx) * progress)
                        return (int(curr_x), int(ty))
                    return (int(tx), int(ty))

                letter_clip = letter_clip.with_start(my_start_time).with_position(get_slide_pos)
                clips_to_composite.append(letter_clip)
                current_target_x += char_widths[i] - kerning

            final_birthday_part = CompositeVideoClip(clips_to_composite)
            
            # Ad Logic
            ad_file = get_ad_file()
            if ad_file:
                try:
                    ext = os.path.splitext(ad_file)[1].lower()
                    if ext in ['.mp4', '.mov', '.gif']:
                        ad_clip = VideoFileClip(ad_file)
                    else:
                        ad_clip = ImageClip(ad_file).with_duration(10) # 10s Static
                    
                    try:
                        ad_clip = ad_clip.resized(new_size=clip.size)
                    except:
                        ad_clip = ad_clip.resize(newsize=clip.size)
                    
                    start_time_of_ad = final_birthday_part.duration
                    ad_clip = ad_clip.with_start(start_time_of_ad)
                    final_output = CompositeVideoClip([final_birthday_part, ad_clip])
                except:
                    final_output = final_birthday_part
            else:
                final_output = final_birthday_part

            # Render
            status_text.text("Rendering video... please wait.")
            progress_bar.progress(50)
            
            # Write to temp file first
            final_output.write_videofile(output_filename, codec='libx264', audio_codec='aac', fps=clip.fps, logger=None)
            
            progress_bar.progress(100)
            status_text.success("Done!")
            
            # Display Video
            st.video(output_filename)
            
            # Cleanup
            for f in temp_files:
                if os.path.exists(f): os.remove(f)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")