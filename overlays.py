#!/usr/bin/env python3
"""
overlays.py - Cinematic Foreground Overlays (Dust, Film Grain, Light Leaks)
"""
import subprocess

def apply_video_overlay(main_video_path, overlay_video_path, output_path, opacity=0.4):
    """
    Overlays a looping video (black background) onto the main video using 'Screen' blend mode.
    This strips out the black background, leaving only the white/colored particles,
    and applies opacity so it doesn't overpower the image.
    """
    cmd = [
        'ffmpeg',
        '-hide_banner',                   # <--- Hides the copyright text so we can read real errors
        '-loglevel', 'error',             # <--- Only show actual errors
        '-i', str(main_video_path),
        '-stream_loop', '-1',             # Loop the overlay video infinitely
        '-i', str(overlay_video_path),
        '-filter_complex',
        # Scale and crop the overlay to exactly 1080x1920 so it fits perfectly
       f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[ov_scaled];"
        f"[0:v][ov_scaled]blend=all_mode=screen:all_opacity={opacity}:shortest=1[outv]",
        '-map', '[outv]',                 # Map the newly blended video
        '-map', '0:a',                    # Keep the exact audio from the main video
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        '-y', str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Overlay FFmpeg failed: {result.stderr[:200]}")
    
    return output_path