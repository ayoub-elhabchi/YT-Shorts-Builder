#!/usr/bin/env python3
"""
evidence.py - Dynamic "Classified Document" Overlays for Shorts
Fixes: Exact bounding box, Manual X/Y Controls, Slide-In & Slide-Out Animation.
"""
import subprocess
import shutil
import textwrap
from PIL import Image, ImageDraw, ImageFont

def create_evidence_image(data_dict, output_path):
    """
    Draws a Classified File box that is EXACTLY the size of the text.
    No extra transparent space, making FFmpeg positioning mathematically perfect.
    """
    try:
        font_title = ImageFont.truetype("courbd.ttf", 40)
        font_text = ImageFont.truetype("cour.ttf", 32)
    except Exception:
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 40)
            font_text = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()

    box_w = 700
    padding = 40
    
    title = str(data_dict.get('title', 'CLASSIFIED DOCUMENT')).upper()
    date_str = data_dict.get('date')
    excerpt = data_dict.get('excerpt')

    # 1. CALCULATE EXACT HEIGHT
    h_title = 45 + 20 
    h_date = 45 if date_str else 0
    h_excerpt = 0
    
    wrapped_text = []
    if excerpt:
        h_excerpt += 40 
        wrapped_text = textwrap.wrap(excerpt, width=32)
        h_excerpt += len(wrapped_text) * 38

    total_height = padding + h_title + h_date + h_excerpt + padding

    # Create image exactly the size of the box (No dead space)
    img = Image.new('RGBA', (box_w, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 2. DRAW THE BOX (From 0,0 to the exact edges)
    draw.rectangle([0, 0, box_w-1, total_height-1], fill=(15, 15, 15, 230))
    draw.rectangle([0, 0, box_w-1, total_height-1], outline=(255, 204, 0, 255), width=3)

    # 3. DRAW THE TEXT
    text_y = padding
    
    draw.text((padding, text_y), title, font=font_title, fill=(255, 204, 0, 255))
    text_y += 50
    
    draw.line([(padding, text_y), (box_w - padding, text_y)], fill=(255, 204, 0, 255), width=2)
    text_y += 20

    if date_str:
        draw.text((padding, text_y), f"DATE: {date_str}", font=font_text, fill=(200, 200, 200, 255))
        text_y += 45

    if excerpt:
        draw.text((padding, text_y), "EXCERPT:", font=font_text, fill=(200, 200, 200, 255))
        text_y += 40
        for line in wrapped_text:
            draw.text((padding, text_y), f'"{line}"', font=font_text, fill=(255, 255, 255, 255))
            text_y += 38

    img.save(output_path)
    return output_path


def apply_evidence_overlays(base_video, evidence_list, output_path):
    """
    Applies the transparent PNGs using advanced IF/ELSE math to Slide In AND Slide Out.
    """
    if not evidence_list:
        shutil.copy2(base_video, output_path)
        return output_path

    # ==========================================
    # 🛠️ MANUAL POSITION CONTROL
    # Edit these numbers to move the card!
    # ==========================================
    CARD_X = 40        # Left/Right position (40 = Hard Left)
    CARD_Y = 1050      # Up/Down position (1250 is usually safely above subtitles)
    
    ANIM_TIME = 1    # How fast it slides (0.4 seconds)
    SLIDE_DIST = 800   # How many pixels it travels from off-screen
    # ==========================================

    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(base_video)]

    for ev in evidence_list:
        cmd.extend(['-i', str(ev['image'])])

    filter_chains = []
    current_input = "0:v"

    # Slide-In & Slide-Out Math Formula
    speed = SLIDE_DIST / ANIM_TIME

    for i, ev in enumerate(evidence_list):
        in_idx = i + 1
        start = ev['start']
        end = ev['end']
        
        # FFmpeg expression:
        # Phase 1: If time is < start + anim_time -> Move from left off-screen to CARD_X
        # Phase 2: If time is > end - anim_time   -> Move from CARD_X back to left off-screen
        # Phase 3: Otherwise                      -> Stay locked at CARD_X
        slide_expr = (
            f"if(lt(t,{start}+{ANIM_TIME}), ({CARD_X}-{SLIDE_DIST})+{speed}*(t-{start}), "
            f"if(gt(t,{end}-{ANIM_TIME}), {CARD_X}-{speed}*(t-({end}-{ANIM_TIME})), {CARD_X}))"
        )
        
        filter_chains.append(f"[{current_input}][{in_idx}:v]overlay=x='{slide_expr}':y={CARD_Y}:enable='between(t,{start},{end})'[v_ev_{i}]")
        current_input = f"v_ev_{i}"

    cmd.extend([
        '-filter_complex', ";".join(filter_chains),
        '-map', f'[{current_input}]',
        '-map', '0:a',
        '-c:v', 'libx264',
        '-preset', 'superfast',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        '-map_metadata', '-1',
        '-y', str(output_path)
    ])

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Evidence timeline failed: {result.stderr[:500]}")

    return output_path