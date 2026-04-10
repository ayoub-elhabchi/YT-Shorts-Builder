#!/usr/bin/env python3
"""
Shake and Zoom Effects for YouTube Shorts Builder
"""
import random
from PIL import Image

try:
    RESAMPLE_FILTER = Image.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.ANTIALIAS

def apply_shake_zoom_effect(img, progress, shake_intensity=0.5, zoom_out_factor=1.1, width=1080, height=1920, shake_config=None):
    """
    Applies a shaking effect combined with zoom out to a PIL image.
    
    Args:
        img: PIL Image object
        progress: Progress of the effect (0.0 to 1.0)
        shake_intensity: Intensity of the shaking effect (default 0.5)
        zoom_out_factor: Zoom out factor (default 1.1)
        width: Target width (default 1080)
        height: Target height (default 1920)
    """
    if shake_config:
        shake_intensity = float(shake_config.get("shake_intensity", shake_intensity))
        if "zoom_out" in shake_config:
            zoom_out_factor = float(shake_config["zoom_out"])
        elif "zoom_in" in shake_config:
            # zoom_in: 1.1 becomes zoom_out_factor: 1/1.1
            zoom_out_factor = 1.0 / max(0.001, float(shake_config["zoom_in"]))
        elif "zoom_out_factor" in shake_config:
            zoom_out_factor = float(shake_config["zoom_out_factor"])
    progress = max(0.0, min(1.0, float(progress)))
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

    # Apply zoom out effect
    # To truly 'zoom out', we need to start zoomed in and end at 1.0
    z_factor = float(zoom_out_factor)
    if z_factor > 1.0:
        zoom_factor = z_factor - (z_factor - 1.0) * progress
    elif z_factor < 1.0:
        target_zoom = 1.0 / max(0.001, z_factor)
        zoom_factor = 1.0 + (target_zoom - 1.0) * progress
    else:
        zoom_factor = 1.0
    crop_w = base_w / zoom_factor
    crop_h = base_h / zoom_factor

    # Calculate shake effect
    shake_offset_x = (random.random() - 0.5) * shake_intensity * (img_w - crop_w)
    shake_offset_y = (random.random() - 0.5) * shake_intensity * (img_h - crop_h)

    # Calculate center position with shake offset
    x = (img_w - crop_w) / 2 + shake_offset_x
    y = (img_h - crop_h) / 2 + shake_offset_y

    # Ensure bounds are safe
    x = max(0, min(x, img_w - crop_w))
    y = max(0, min(y, img_h - crop_h))

    # Apply crop and resize
    box = (x, y, x + crop_w, y + crop_h)
    return img.resize((width, height), resample=RESAMPLE_FILTER, box=box)