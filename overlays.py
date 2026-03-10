#!/usr/bin/env python3
"""
overlays.py - Cinematic Foreground Overlays (Scene-Specific + Superfast)
"""
import subprocess
import shutil

def apply_scene_overlays(base_video, scene_overlays, output_path):
    """
    Applies multiple looping overlays to specific timestamps on a single video.
    scene_overlays = [{'file': 'dust.mp4', 'start': 1.0, 'end': 4.5, 'opacity': 0.35}, ...]
    """
    if not scene_overlays:
        shutil.copy2(base_video, output_path)
        return output_path

    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-loglevel', 'error',
        '-i', str(base_video)
    ]
    
    # Load every overlay video as an infinite loop input
    for ov in scene_overlays:
        cmd.extend(['-stream_loop', '-1', '-i', str(ov['file'])])
        
    filter_chains = []
    current_v = "0:v"
    
    # Build the math for turning them on and off at exact seconds
    for i, ov in enumerate(scene_overlays):
        in_idx = i + 1
        start = ov['start']
        end = ov['end']
        opacity = ov['opacity']
        
        # Scale the overlay to 1080x1920 and ensure pixel format matches
        filter_chains.append(f"[{in_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p[ov_scaled_{i}]")
        
        # Blend it using the timeline 'enable' feature
                # Blend it using the timeline 'enable' feature
        filter_chains.append(f"[{current_v}][ov_scaled_{i}]blend=c0_mode=screen:c1_mode=normal:c2_mode=normal:all_opacity={opacity}:enable='between(t,{start},{end})'[v_b_{i}]")
        current_v = f"v_b_{i}"

    cmd.extend(['-filter_complex', ";".join(filter_chains)])
    
        # Render with the 'superfast' engine
    cmd.extend([
        '-map', f'[{current_v}]',
        '-map', '0:a',
        '-c:v', 'libx264',
        '-preset', 'superfast',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        '-crf', '28',   # <--- ADDS COMPRESSION 
        '-map_metadata', '-1',
        '-shortest',             # <--- FIX: Forces FFmpeg to stop when the main video ends!
        '-y', str(output_path)
    ])
    
    # FIX: Route stdout to DEVNULL to prevent OS pipe deadlocks
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Overlay timeline failed: {result.stderr[:500]}")
    
    return output_path