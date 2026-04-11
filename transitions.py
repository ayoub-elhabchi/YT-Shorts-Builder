#!/usr/bin/env python3
"""
transitions.py - Pillow-based scene transitions for YouTube Shorts Builder
Supports: fade, fade_black, slide_left/right/up/down, zoom, wipe_left/down
"""

import subprocess
from datetime import datetime

try:
    from effects import apply_ken_burns
    from effects_shake import apply_shake_zoom_effect
except ImportError:
    pass

# Try importing Pillow
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
    try:
        RESAMPLE_FILTER = Image.LANCZOS
    except AttributeError:
        RESAMPLE_FILTER = Image.ANTIALIAS
except ImportError:
    PILLOW_AVAILABLE = False
    RESAMPLE_FILTER = None

# ── Constants ──
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

VALID_TRANSITIONS = [
    'none',
    'fade',
    'fade_black',
    'slide_left',
    'slide_right',
    'slide_up',
    'slide_down',
    'zoom',
    'wipe_left',
    'wipe_down'
]


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


# ── Easing ──

def ease_in_out(t):
    """Smoothstep easing for natural-looking motion"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ── Image Helpers ──

def paste_at(canvas, source, x, y):
    """Paste source onto canvas, handling negative/overflow positions safely"""
    cw, ch = canvas.size
    sw, sh = source.size

    src_left = max(0, -x)
    src_top = max(0, -y)
    src_right = min(sw, cw - x)
    src_bottom = min(sh, ch - y)

    dst_x = max(0, x)
    dst_y = max(0, y)

    if src_right <= src_left or src_bottom <= src_top:
        return

    region = source.crop((src_left, src_top, src_right, src_bottom))
    canvas.paste(region, (dst_x, dst_y))


def prepare_image_for_shorts(image_path, width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Load image, resize maintaining aspect ratio,
    center on black background at 1080x1920
    """
    img = Image.open(str(image_path)).convert('RGB')

    img_ratio = img.width / img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        new_w = width
        new_h = max(1, int(width / img_ratio))
    else:
        new_h = height
        new_w = max(1, int(height * img_ratio))

    img = img.resize((new_w, new_h), RESAMPLE_FILTER)

    result = Image.new('RGB', (width, height), (0, 0, 0))
    result.paste(img, ((width - new_w) // 2, (height - new_h) // 2))
    return result


# ── Frame Generation ──

def make_transition_frame(img_out, img_in, effect, progress,
                          width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Generate one transition frame between two PIL Images.
    progress: 0.0 = fully img_out → 1.0 = fully img_in
    """
    t = ease_in_out(max(0.0, min(1.0, progress)))
    black = Image.new('RGB', (width, height), (0, 0, 0))

    if effect == 'fade':
        return Image.blend(img_out, img_in, max(0.0, min(1.0, t)))

    elif effect == 'fade_black':
        if t < 0.5:
            alpha = min(1.0, t * 2)
            return Image.blend(img_out, black, alpha)
        else:
            alpha = min(1.0, (t - 0.5) * 2)
            return Image.blend(black, img_in, alpha)

    elif effect == 'slide_left':
        frame = Image.new('RGB', (width, height), (0, 0, 0))
        offset = int(width * t)
        paste_at(frame, img_out, -offset, 0)
        paste_at(frame, img_in, width - offset, 0)
        return frame

    elif effect == 'slide_right':
        frame = Image.new('RGB', (width, height), (0, 0, 0))
        offset = int(width * t)
        paste_at(frame, img_out, offset, 0)
        paste_at(frame, img_in, offset - width, 0)
        return frame

    elif effect == 'slide_up':
        frame = Image.new('RGB', (width, height), (0, 0, 0))
        offset = int(height * t)
        paste_at(frame, img_out, 0, -offset)
        paste_at(frame, img_in, 0, height - offset)
        return frame

    elif effect == 'slide_down':
        frame = Image.new('RGB', (width, height), (0, 0, 0))
        offset = int(height * t)
        paste_at(frame, img_out, 0, offset)
        paste_at(frame, img_in, 0, offset - height)
        return frame

    elif effect == 'zoom':
        if t < 0.5:
            scale = 1.0 + t
            new_w = int(width * scale)
            new_h = int(height * scale)
            if new_w > 0 and new_h > 0:
                zoomed = img_out.resize((new_w, new_h), RESAMPLE_FILTER)
                cx = (new_w - width) // 2
                cy = (new_h - height) // 2
                cropped = zoomed.crop((cx, cy, cx + width, cy + height))
                alpha = max(0.0, 1.0 - t * 2)
                return Image.blend(black, cropped, alpha)
            return black
        else:
            alpha = min(1.0, (t - 0.5) * 2)
            return Image.blend(black, img_in, alpha)

    elif effect == 'wipe_left':
        frame = img_out.copy()
        boundary = int(width * t)
        if boundary > 0:
            revealed = img_in.crop((0, 0, boundary, height))
            frame.paste(revealed, (0, 0))
        return frame

    elif effect == 'wipe_down':
        frame = img_out.copy()
        boundary = int(height * t)
        if boundary > 0:
            revealed = img_in.crop((0, 0, width, boundary))
            frame.paste(revealed, (0, 0))
        return frame

    else:
        # Fallback: hard cut at midpoint
        return img_in if progress >= 0.5 else img_out


# ── Main Video Builder ──

def build_video_with_transitions(scenes_data, audio_path, output_path,
                                 transition_effect='fade',
                                 transition_duration=0.5,
                                 fps=VIDEO_FPS):
    """
    Build complete video by generating frames with Pillow and piping
    raw RGB data to ffmpeg.

    Args:
        scenes_data: list of dicts, each with:
            - 'image': PIL.Image (1080x1920)
            - 'start': float (seconds)
            - 'end': float (seconds)
        audio_path: path to full audio WAV file
        output_path: where to save final MP4
        transition_effect: one of VALID_TRANSITIONS
        transition_duration: seconds for each transition
        fps: frames per second

    Returns:
        output_path on success
    """
    if not PILLOW_AVAILABLE:
        raise Exception("Pillow is required for transitions. Install with: pip install Pillow")

    width, height = VIDEO_WIDTH, VIDEO_HEIGHT

    # Get audio duration
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    r = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    total_duration = float(r.stdout.strip())

    total_frames = int(total_duration * fps) + 1
    half_trans = transition_duration / 2.0
    num_scenes = len(scenes_data)

    log(f"   🎞️ Generating {total_frames} frames ({total_duration:.2f}s @ {fps}fps)")
    log(f"   🔄 Effect: {transition_effect} ({transition_duration}s)")

    black = Image.new('RGB', (width, height), (0, 0, 0))

    # Pre-cache raw bytes for static frames (no Pillow work needed per frame)
    scene_bytes = {}
    for i in range(num_scenes):
        scene_bytes[i] = scenes_data[i]['image'].tobytes()
    black_bytes = black.tobytes()

   # Start ffmpeg with rawvideo input pipe
    cmd = [
    'ffmpeg',
    '-loglevel', 'warning',   # <--- FIX 1: Stops ffmpeg from spamming progress and causing deadlock
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    '-s', f'{width}x{height}',
    '-r', str(fps),
    '-i', 'pipe:0',
    '-i', str(audio_path),
    '-c:v', 'libx264',
    '-preset', 'superfast',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-shortest',
    '-map_metadata', '-1',
    '-y', str(output_path)
]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, # Anti-deadlock fix
        stderr=subprocess.PIPE
    )

    frames_written = 0
    last_log_pct = -1

    try:
        for fn in range(total_frames):
            t = fn / fps

            # Find which scene this timestamp belongs to
            si = num_scenes - 1
            for i in range(num_scenes):
                if i + 1 < num_scenes and t < scenes_data[i + 1]['start']:
                    si = i
                    break

                        # Check if we're inside a transition zone between any two scenes
            wrote_transition = False

            for bi in range(num_scenes - 1):
                boundary = scenes_data[bi + 1]['start']
                
                # Retrieve the specific effect and duration for THIS entry boundary
                effect = scenes_data[bi + 1]['transition']
                dur = scenes_data[bi + 1]['transition_duration']
                half_trans = dur / 2.0

                # Clamp transition so it doesn't exceed 40% of either scene
                dur_before = scenes_data[bi]['end'] - scenes_data[bi]['start']
                dur_after = scenes_data[bi + 1]['end'] - scenes_data[bi + 1]['start']
                ht = min(half_trans, dur_before * 0.4, dur_after * 0.4)

                if ht > 0.02 and boundary - ht <= t <= boundary + ht:
                    trans_progress = (t - (boundary - ht)) / (2.0 * ht)
                    
                    # Default to static images
                    img_out = scenes_data[bi]['image']
                    img_in = scenes_data[bi + 1]['image']

                    # --- DYNAMIC SEAMLESS BLEND: Calculate motion for BOTH scenes during overlap ---
                    if scenes_data[bi].get('kb_effect'):
                        p_out = (t - scenes_data[bi]['start']) / max(0.1, scenes_data[bi]['end'] - scenes_data[bi]['start'])
                        img_out = apply_ken_burns(scenes_data[bi]['raw_image'], max(0.0, min(1.0, p_out)), scenes_data[bi]['kb_effect'], width, height)
                    elif scenes_data[bi].get('shake_effect'):
                        p_out = t / total_duration  # Continuous from start to end
                        shk = scenes_data[bi]['shake_effect']
                        img_out = apply_shake_zoom_effect(scenes_data[bi]['raw_image'], max(0.0, min(1.0, p_out)), width=width, height=height, shake_config=shk)

                    if scenes_data[bi + 1].get('kb_effect'):
                        p_in = (t - scenes_data[bi + 1]['start']) / max(0.1, scenes_data[bi + 1]['end'] - scenes_data[bi + 1]['start'])
                        img_in = apply_ken_burns(scenes_data[bi + 1]['raw_image'], max(0.0, min(1.0, p_in)), scenes_data[bi + 1]['kb_effect'], width, height)
                    elif scenes_data[bi + 1].get('shake_effect'):
                        p_in = t / total_duration  # Continuous from start to end
                        shk = scenes_data[bi + 1]['shake_effect']
                        img_in = apply_shake_zoom_effect(scenes_data[bi + 1]['raw_image'], max(0.0, min(1.0, p_in)), width=width, height=height, shake_config=shk)
                    
                    # Blend the two moving images together
                    frame = make_transition_frame(img_out, img_in, effect, trans_progress, width, height)
                    process.stdin.write(frame.tobytes())
                    wrote_transition = True
                    break

            if not wrote_transition:
                # First scene: fade in from black 
                start_dur = scenes_data[0]['transition_duration']
                start_ht = start_dur / 2.0
                if si == 0 and t < start_ht and start_ht > 0.02:
                    progress = t / start_ht
                    
                    # --- DYNAMIC KEN BURNS FADE IN ---
                    img_target = scenes_data[0]['image']
                    if scenes_data[0].get('kb_effect'):
                        s_prog = (t - scenes_data[0]['start']) / max(0.1, scenes_data[0]['end'] - scenes_data[0]['start'])
                        img_target = apply_ken_burns(scenes_data[0]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[0]['kb_effect'], width, height)
                    elif scenes_data[0].get('shake_effect'):
                        s_prog = t / total_duration  # Continuous from start to end
                        shk = scenes_data[0]['shake_effect']
                        img_target = apply_shake_zoom_effect(scenes_data[0]['raw_image'], max(0.0, min(1.0, s_prog)), width=width, height=height, shake_config=shk)
                    
                    frame = make_transition_frame(black, img_target, 'fade', progress, width, height)
                    process.stdin.write(frame.tobytes())

                # Last scene: fade out to black at end
                elif si == num_scenes - 1 and total_duration - t < (scenes_data[-1]['transition_duration'] / 2.0):
                    end_dur = scenes_data[-1]['transition_duration']
                    end_ht = end_dur / 2.0
                    time_left = total_duration - t
                    progress = 1.0 - (time_left / end_ht)
                    
                    # --- DYNAMIC KEN BURNS FADE OUT ---
                    img_source = scenes_data[-1]['image']
                    if scenes_data[-1].get('kb_effect'):
                        s_prog = (t - scenes_data[-1]['start']) / max(0.1, scenes_data[-1]['end'] - scenes_data[-1]['start'])
                        img_source = apply_ken_burns(scenes_data[-1]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[-1]['kb_effect'], width, height)
                    elif scenes_data[-1].get('shake_effect'):
                        s_prog = t / total_duration  # Continuous from start to end
                        shk = scenes_data[-1]['shake_effect']
                        img_source = apply_shake_zoom_effect(scenes_data[-1]['raw_image'], max(0.0, min(1.0, s_prog)), width=width, height=height, shake_config=shk)
                        
                    frame = make_transition_frame(img_source, black, 'fade', progress, width, height)
                    process.stdin.write(frame.tobytes())

                # Standard Frame (No fade in/out)
                else:
                    if scenes_data[si].get('kb_effect'):
                        # --- GENERATE KEN BURNS FRAME ON THE FLY ---
                        s_prog = (t - scenes_data[si]['start']) / max(0.1, scenes_data[si]['end'] - scenes_data[si]['start'])
                        frame = apply_ken_burns(scenes_data[si]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[si]['kb_effect'], width, height)
                        process.stdin.write(frame.tobytes())
                    elif scenes_data[si].get('shake_effect'):
                        # --- GENERATE SHAKE FRAME ON THE FLY ---
                        s_prog = t / total_duration  # Continuous from start to end
                        shk = scenes_data[si]['shake_effect']
                        frame = apply_shake_zoom_effect(scenes_data[si]['raw_image'], max(0.0, min(1.0, s_prog)), width=width, height=height, shake_config=shk)
                        process.stdin.write(frame.tobytes())
                    else:
                        # Fallback to static fast cache
                        process.stdin.write(scene_bytes[si])

            frames_written += 1

            # Progress logging every 10%
            pct = int(fn / total_frames * 100)
            if pct >= last_log_pct + 10:
                log(f"      🎞️ {pct}% — frame {fn}/{total_frames} ({t:.1f}s)")
                last_log_pct = pct

        process.stdin.close()
        stdout, stderr = process.communicate(timeout=600)

        if process.returncode != 0:
            raise Exception(f"FFmpeg encoding failed: {stderr.decode()[:500]}")

        log(f"   ✅ Video built: {frames_written} frames using dynamic per-scene transitions")
        return output_path

    except Exception as e:
        try:
            process.stdin.close()
        except Exception:
            pass
        process.kill()
        raise