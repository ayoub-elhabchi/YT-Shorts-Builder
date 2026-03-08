#!/usr/bin/env python3
"""
effects.py - Dynamic Camera Motion (Ken Burns) for YouTube Shorts Builder
"""
import random
from PIL import Image

try:
    RESAMPLE_FILTER = Image.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.ANTIALIAS

KEN_BURNS_EFFECTS = [
    'zoom_in', 'zoom_out', 
    'pan_left', 'pan_right', 
    'pan_up', 'pan_down'
]

def get_random_ken_burns_effect():
    """Picks a random camera movement"""
    return random.choice(KEN_BURNS_EFFECTS)

def apply_ken_burns(img, progress, effect_type, width=1080, height=1920):
    """
    Applies a Ken Burns crop/scale to a PIL image based on scene progress (0.0 to 1.0).
    Unlike normal static images, this zooms in to completely remove black borders
    and fills the entire vertical screen like a documentary.
    """
    img_w, img_h = img.size
    target_ratio = width / height
    img_ratio = img_w / img_h

    # Find the max bounding box that fits the 9:16 target ratio
    if img_ratio > target_ratio:
        base_w = int(img_h * target_ratio)
        base_h = img_h
    else:
        base_w = img_w
        base_h = int(img_w / target_ratio)

    zoom_factor = 0.15  # The image will scale/move by 15% across the clip

    if effect_type == 'zoom_in':
        current_scale = 1.0 - (zoom_factor * progress)
    elif effect_type == 'zoom_out':
        current_scale = (1.0 - zoom_factor) + (zoom_factor * progress)
    else:
        # Pans maintain a constant zoom so they have room to slide
        current_scale = 1.0 - zoom_factor

    crop_w = base_w * current_scale
    crop_h = base_h * current_scale

    max_x = img_w - crop_w
    max_y = img_h - crop_h

    # Default to center
    x = (img_w - crop_w) / 2
    y = (img_h - crop_h) / 2

    # Calculate sliding pan positions based on progress (0.0 -> 1.0)
    if effect_type == 'pan_left':
        x = max_x * (1.0 - progress)
    elif effect_type == 'pan_right':
        x = max_x * progress
    elif effect_type == 'pan_up':
        y = max_y * (1.0 - progress)
    elif effect_type == 'pan_down':
        y = max_y * progress

    # Ensure bounds are safe
    x = max(0, min(x, max_x))
    y = max(0, min(y, max_y))

    # FIX: Keep floats for sub-pixel precision. Do NOT use int() or crop().
    # Passing the 'box' directly into resize forces Pillow to render perfectly smooth decimals.
    box = (x, y, x + crop_w, y + crop_h)
    
    return img.resize((width, height), resample=RESAMPLE_FILTER, box=box)