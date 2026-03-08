#!/usr/bin/env python3
"""
YouTube Shorts Builder v3.7 beta - Global Search + Subtitles
Fix: Scene alignment now records the actual first matched word position
instead of the scan start position, eliminating early audio cuts.
Added: VAD Aesthetic Silence Compressor precisely on locked boundaries (Squashing empty 2s whisper bleedings accurately).
"""

import os
import json
import random 
import subprocess
import requests
import base64
from flask import Flask, request, jsonify, send_file
from pathlib import Path
import shutil
from datetime import datetime
import traceback
import re

# Transitions module
try:
    from transitions import (
        PILLOW_AVAILABLE, VALID_TRANSITIONS,
        prepare_image_for_shorts, build_video_with_transitions
    )
except ImportError:
    PILLOW_AVAILABLE = False
    VALID_TRANSITIONS = ['none']

# Effects module
try:
    from effects import get_random_ken_burns_effect, KEN_BURNS_EFFECTS
except ImportError:
    get_random_ken_burns_effect = None

app = Flask(__name__)

TEMP_DIR = Path("./temp/shorts_builder")
OUTPUT_DIR = Path("./output/shorts_output")
BGM_DIR = Path("./assets/bgm")   
OVERLAYS_DIR = Path("./assets/overlays")  
CONFIG_PATH = Path("./config.json")
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BGM_DIR.mkdir(parents=True, exist_ok=True)
OVERLAYS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "audio": {
        "add_bgm_by_default": True,
        "default_bgm_volume": 0.2
    },
    "subtitles": {
        "font_name": "Impact",
        "font_size_word": 90,
        "font_size_highlight": 72,
        "font_color_primary": "&H0000FFFF",  # Yellow in ASS format (AABBGGRR)
        "font_color_white": "&H00FFFFFF",    # White in ASS format
        "margin_v": 150,                     # Vertical Position (Higher = further up the screen)
        "alignment": 2                       # 2 = Bottom Center, 5 = Middle Center, 8 = Top Center
    },
    "video": {
        "default_transition": "none",
        "default_transition_duration": 0.5,
        "ken_burns_movement": True
    }
}

def load_config():
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️ Error reading config.json, using defaults: {e}")
        return DEFAULT_CONFIG

# Load it globally when the script starts
CONFIG = load_config()

# Words too common to match on
SKIP_WORDS = frozenset({
    'a', 'an', 'the', 'in', 'on', 'of', 'to', 'and', 'is', 'it',
    'its', 'was', 'were', 'are', 'be', 'been', 'has', 'had', 'have',
    'for', 'with', 'at', 'by', 'from', 'that', 'this', 'but', 'not',
    'or', 'as', 'if', 'she', 'he', 'they', 'her', 'his', 'you', 'i',
    'so', 'do', 'did', 'does', 'will', 'would', 'could', 'should',
    'can', 'may', 'my', 'your', 'we', 'our', 'their', 'me', 'him',
    'us', 'them', 'who', 'what', 'how', 'when', 'where', 'why',
    'which', 'no', 'yes', 'all', 'any', 'some', 'one', 'two',
    'up', 'out', 'about', 'into', 'over', 'each', 'still'
})


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def clean_word(w):
    """Remove punctuation from a word"""
    return re.sub(r'[^\w]', '', w.lower().strip())


def clean_text_for_matching(text):
    """Basic normalization"""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s']", ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def convert_gdrive_url_to_direct(url):
    if not url:
        return None
    if "drive.google.com/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def download_file(url, output_path):
    url = convert_gdrive_url_to_direct(url)
    log(f"📥 Downloading: {url[:80]}...")
    try:
        session = requests.Session()
        response = session.get(url, stream=True, timeout=120, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            log("   ⚠️  Got HTML (Google Drive confirmation)")
            if 'id=' in url:
                file_id = re.search(r'id=([0-9A-Za-z_-]+)', url).group(1)
            else:
                file_id = url.split('/')[-1]
            confirmed_url = (
                f"https://drive.google.com/uc?export=download"
                f"&id={file_id}&confirm=t"
            )
            log("   🔄 Retrying with confirmation...")
            response = session.get(confirmed_url, stream=True, timeout=120, allow_redirects=True)
            response.raise_for_status()

        temp_path = str(output_path) + ".temp"
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        file_size = os.path.getsize(temp_path)
        log(f"   Downloaded: {file_size} bytes")

        with open(temp_path, 'rb') as f:
            first_bytes = f.read(200)

        if b'<!DOCTYPE' in first_bytes or b'<html' in first_bytes:
            os.remove(temp_path)
            raise Exception("Google Drive returned HTML, not audio. Check sharing settings.")

        is_base64 = False
        if len(first_bytes) > 0:
            is_audio = (first_bytes[:4] == b'RIFF' or first_bytes[:3] == b'ID3' or
                        first_bytes[:2] == b'\xff\xfb' or first_bytes[:4] == b'OggS')
            printable = sum(1 for b in first_bytes if 32 <= b <= 126 or b in (9, 10, 13))
            if printable > len(first_bytes) * 0.95 and not is_audio:
                is_base64 = True

        if is_base64:
            log("   🔄 Decoding base64...")
            with open(temp_path, 'rb') as f:
                data = f.read()
            data = data.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
            try:
                decoded = base64.b64decode(data)
                with open(output_path, 'wb') as f:
                    f.write(decoded)
                os.remove(temp_path)
            except Exception:
                os.rename(temp_path, output_path)
        else:
            log("   ✅ Binary file")
            os.rename(temp_path, output_path)

        with open(output_path, 'rb') as f:
            h = f.read(4)
        if h[:4] == b'RIFF':
            log("   📂 WAV")
        elif h[:3] == b'ID3' or h[:2] == b'\xff\xfb':
            log("   📂 MP3")
        else:
            log(f"   📂 type: {h.hex()}")

        return output_path
    except Exception as e:
        log(f"❌ Download failed: {str(e)}")
        temp_path = str(output_path) + ".temp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def ensure_wav(input_path, wav_path):
    with open(input_path, 'rb') as f:
        header = f.read(4)
    if header[:4] == b'RIFF':
        log("   ✅ Already WAV")
        if str(input_path) != str(wav_path):
            shutil.copy2(str(input_path), str(wav_path))
        return wav_path
    log("   🔊 Converting to WAV...")
    cmd =[
        'ffmpeg', '-i', str(input_path),
        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-y', str(wav_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Cannot convert: {result.stderr[:200]}")
    log(f"   ✅ WAV ready: {os.path.getsize(wav_path)} bytes")
    return wav_path

def mix_background_music(vo_path, bgm_path, output_path, volume=0.2):
    log(f" 🎵 Mixing Background Music: {os.path.basename(bgm_path)} at {volume*100}% volume")
    
    # FFmpeg filter: 
    # -stream_loop -1: loops the BGM infinitely so it covers the whole video
    # normalize=0: prevents FFmpeg from automatically lowering the voiceover volume
    cmd = [
        'ffmpeg',
        '-i', str(vo_path),
        '-stream_loop', '-1', '-i', str(bgm_path),
        '-filter_complex', f"[0:a]volume=1.0[vo];[1:a]volume={volume}[bgm];[vo][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]",
        '-map', '[aout]',
        '-acodec', 'pcm_s16le', '-ar', '16000',
        '-y', str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback to standard amix if normalize=0 is not supported on older FFmpeg versions
        log("   ⚠️ normalize=0 failed, trying legacy amix...")
        cmd[8] = f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        result2 = subprocess.run(cmd, capture_output=True, text=True)
        if result2.returncode != 0:
            log(f"   ❌ BGM mixing failed, continuing without music. Error: {result2.stderr[:100]}")
            shutil.copy2(str(vo_path), str(output_path))
            return output_path
            
    log("   ✅ BGM mixed successfully!")
    return output_path


def get_audio_duration(audio_path):
    cmd =[
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    d = float(result.stdout.strip())
    log(f"   📏 Duration: {d:.2f}s")
    return d


def transcribe_audio_with_whisper(audio_path):
    import whisper
    log("🎤 Transcribing...")
    log("   Loading model...")
    model = whisper.load_model("small")
    log("   Transcribing...")
    result = model.transcribe(str(audio_path), word_timestamps=True, language='en')
    all_words = []
    for seg in result['segments']:
        for w in seg.get('words', []):
            all_words.append({
                'word': w['word'].strip().lower(),
                'start': w['start'],
                'end': w['end']
            })
    log(f"   ✅ {len(all_words)} words")
    return all_words, result['text']


def align_scenes_to_timestamps(transcribed_words, scene_texts):
    """
    SEQUENTIAL matching: find each scene's first few words IN ORDER.
    v3.7 fix: records the actual first matched word position instead of
    the scan start position, so scene boundaries land on the correct word.
    Fix + Added gap trimmer over anchored bounds securely locking bleeding effectively!
    """
    if not transcribed_words:
        raise Exception("No transcribed words")

    total_duration = transcribed_words[-1]['end']
    num_scenes = len(scene_texts)

    log(f"🔍 Aligning {num_scenes} scenes to {len(transcribed_words)} words ({total_duration:.2f}s)")

    trans_clean = [clean_word(w['word']) for w in transcribed_words]
    scene_positions =[]

    for si, text in enumerate(scene_texts):
        cleaned = clean_text_for_matching(text)
        all_words = cleaned.split()
        all_clean = [clean_word(w) for w in all_words if w]

        log(f"\n   Scene {si+1}:")
        log(f"      Words: {all_clean[:12]}...")

        if len(all_clean) < 2:
            log(f"      ⚠️  Too few words")
            scene_positions.append(None)
            continue

        match_words =[]
        for w in all_clean:
            if w not in SKIP_WORDS or len(match_words) < 2:
                match_words.append(w)
            if len(match_words) >= 6:
                break

        log(f"      Match sequence: {match_words}")

        best_score = 0
        best_pos = -1

        for pos in range(len(transcribed_words)):
            score = 0
            ti = pos
            first_match = -1 

            for mi, mw in enumerate(match_words):
                found = False
                for skip in range(3):
                    if ti + skip >= len(transcribed_words):
                        break
                    tw = trans_clean[ti + skip]
                    if mw == tw:
                        score += 1.0
                        if first_match == -1: first_match = ti + skip
                        ti = ti + skip + 1
                        found = True
                        break
                    if len(mw) >= 4 and len(tw) >= 4:
                        if mw in tw or tw in mw:
                            score += 0.7
                            if first_match == -1: first_match = ti + skip
                            ti = ti + skip + 1
                            found = True
                            break
                if not found:
                    ti += 1

            if score > best_score:
                best_score = score
                best_pos = first_match  # actual exact vocal target boundary securely matched here cleanly safely.

        threshold = max(2, len(match_words) * 0.4)
        if best_score >= threshold and best_pos >= 0:
            
            # --- INCORPORATED: Exact Silhouette Whisper Pad Compression ("Squasher Fix") ---
            ti_node = transcribed_words[best_pos]
            w_start, w_end = ti_node['start'], ti_node['end']
            w_max_human_len = 0.5 + (len(clean_word(ti_node['word'])) * 0.09)

            if w_end - w_start > w_max_human_len + 0.35:
                p_s = w_start
                # Updates precise transcribed arrays object locking bounds efficiently tracking completely comfortably fixing subs as well flawlessly correctly effortlessly 
                ti_node['start'] = w_end - w_max_human_len 
                log(f"      🗜️ Trimmed Whisper Padding: gap closed natively ({p_s:.2f}s → {ti_node['start']:.2f}s)")
            # -------------------------------------------------------------
                
            t = ti_node['start']
            log(f"      ✅ MATCHED at word[{best_pos}] '{ti_node['word']}' = {t:.2f}s (score {best_score:.1f}/{len(match_words)})")
            scene_positions.append(best_pos)
        else:
            log(f"      ❌ No match (best {best_score:.1f}, need {threshold:.1f})")
            scene_positions.append(None)


    last_pos = -1
    for i in range(num_scenes):
        if scene_positions[i] is not None:
            if scene_positions[i] <= last_pos:
                log(f"   Scene {i+1}: ⚠️ Out of order → dropped")
                scene_positions[i] = None
            else:
                last_pos = scene_positions[i]

    matched_count = sum(1 for m in scene_positions if m is not None)
    log(f"\n   📊 Matched: {matched_count}/{num_scenes}")


    starts = [None] * num_scenes
    for i in range(num_scenes):
        if scene_positions[i] is not None:
            starts[i] = transcribed_words[scene_positions[i]]['start']

    starts[0] = 0.0

    i = 0
    while i < num_scenes:
        if starts[i] is not None:
            j = i + 1
            while j < num_scenes and starts[j] is None:
                j += 1
            if j < num_scenes and j > i + 1:
                gap = starts[j] - starts[i]
                n = j - i
                for k in range(1, n):
                    starts[i + k] = round(starts[i] + gap * k / n, 2)
            elif j >= num_scenes and j > i + 1:
                remaining = total_duration - starts[i]
                n = num_scenes - i
                for k in range(1, n):
                    starts[i + k] = round(starts[i] + remaining * k / n, 2)
            i = j if j > i else i + 1
        else:
            i += 1


    log(f"\n   ⏱️ Final timing:")
    scenes_timing = []

    for i in range(num_scenes):
        s = starts[i] if starts[i] is not None else 0.0
        if i + 1 < num_scenes and starts[i + 1] is not None:
            e = starts[i + 1]
        else:
            e = total_duration

        if e - s < 1.0:
            e = min(s + 1.0, total_duration)

        s = round(s, 2)
        e = round(e, 2)
        d = round(e - s, 2)
        matched = scene_positions[i] is not None

        icon = "✅" if matched else "📐"
        log(f"      {icon} Scene {i+1}: {s:.2f}s → {e:.2f}s ({d:.2f}s)")

        scenes_timing.append({
            'start': s, 'end': e, 'duration': d,
            'scene_index': i + 1, 'matched': matched
        })

    return scenes_timing


def extract_audio_chunk(input_wav, output_wav, start_time, end_time):
    if end_time <= start_time:
        end_time = start_time + 2.0

    probe =['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(input_wav)]
    r = subprocess.run(probe, capture_output=True, text=True, check=True)
    total = float(r.stdout.strip())

    if end_time > total:
        end_time = total
    if start_time >= total:
        start_time = max(0, total - 2.0)
        end_time = total

    log(f"      ✂️  Cutting: {start_time:.2f}s → {end_time:.2f}s")

    cmd =['ffmpeg', '-i', str(input_wav), '-ss', str(start_time),
           '-to', str(end_time), '-acodec', 'copy', '-y', str(output_wav)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg cut failed: {result.stderr[:200]}")


def create_video_clip(image_path, audio_path, output_path):
    probe =['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)]
    r = subprocess.run(probe, capture_output=True, text=True, check=True)
    duration = float(r.stdout.strip())

    cmd =[
        'ffmpeg', '-loop', '1', '-i', str(image_path),
        '-i', str(audio_path),
        '-c:v', 'libx264', '-preset', 'medium', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '128k', '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,'
               'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
        '-t', str(duration), '-shortest', '-y', str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def concatenate_videos(video_paths, output_path):
    concat_file = TEMP_DIR / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for vp in video_paths:
            f.write(f"file '{os.path.abspath(vp)}'\n")
    cmd =['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
           '-c', 'copy', '-y', str(output_path)]
    subprocess.run(cmd, check=True, capture_output=True)


# ============================================================
# SUBTITLES
# ============================================================

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def parse_ass_time(time_str):
    parts = time_str.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s_cs = parts[2].split('.')
    s = int(s_cs[0])
    cs = int(s_cs[1]) if len(s_cs) > 1 else 0
    return h * 3600 + m * 60 + s + cs / 100.0


def generate_word_subtitles(word_timestamps, ass_path, style="word_by_word"):
    """Bold yellow word-by-word at BOTTOM of screen"""
    log(f"   📝 Generating subtitles ({style})...")

    if style == "highlight":
        return generate_highlight_subtitles(word_timestamps, ass_path)
    
    # Load from config
    sub_cfg = CONFIG['subtitles']
    font_name = sub_cfg.get('font_name', 'Impact')
    font_size = sub_cfg.get('font_size_word', 90)
    color = sub_cfg.get('font_color_primary', '&H0000FFFF')
    margin_v = sub_cfg.get('margin_v', 150)
    align = sub_cfg.get('alignment', 2)

    header = f"""[Script Info]
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{font_name},{font_size},{color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,{align},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events =[]
    for w in word_timestamps:
        start = format_ass_time(w['start'])
        end = format_ass_time(w['end'])
        word = w['word'].strip().upper()
        word = word.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
        if not word:
            continue
        events.append(f"Dialogue: 0,{start},{end},Word,,0,0,0,,{word}")

    with open(ass_path, 'w', encoding='utf-8-sig') as f:
        f.write(header)
        f.write("\n".join(events))
        f.write("\n")

    log(f"   ✅ {len(events)} subtitle events")
    return ass_path


def generate_highlight_subtitles(word_timestamps, ass_path, words_per_group=4):
    """Groups of words, current highlighted yellow, rest white - at BOTTOM"""
    log(f"   📝 Generating highlight subtitles...")

    # Load from config
    sub_cfg = CONFIG['subtitles']
    font_name = sub_cfg.get('font_name', 'Impact')
    font_size = sub_cfg.get('font_size_highlight', 72)
    color_pri = sub_cfg.get('font_color_primary', '&H0000FFFF')
    color_wht = sub_cfg.get('font_color_white', '&H00FFFFFF')
    margin_v = sub_cfg.get('margin_v', 150)
    align = sub_cfg.get('alignment', 2)

    header = f"""[Script Info]
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Highlight,{font_name},{font_size},{color_wht},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,{align},30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # (Update the parts list loop below so it uses the correct color)
    events = []
    groups = [word_timestamps[i:i+words_per_group]
              for i in range(0, len(word_timestamps), words_per_group)]

    for group in groups:
        for wi, cw in enumerate(group):
            w_start = format_ass_time(cw['start'])
            w_end = format_ass_time(group[wi+1]['start'] if wi < len(group)-1 else cw['end'])

            parts = []
            for j, w in enumerate(group):
                wt = w['word'].strip().upper()
                if not wt:
                    continue
                if j == wi:
                    # Dynamically inject the primary color for the highlighted word
                    parts.append(r"{\c" + color_pri + r"&\fscx110\fscy110}" + wt +
                                 r"{\c" + color_wht + r"&\fscx100\fscy100}")
                else:
                    parts.append(wt)

            events.append(f"Dialogue: 0,{w_start},{w_end},Highlight,,0,0,0,,{' '.join(parts)}")

    with open(ass_path, 'w', encoding='utf-8-sig') as f:
        f.write(header)
        f.write("\n".join(events))
        f.write("\n")

    log(f"   ✅ {len(events)} highlight events")
    return ass_path


def burn_subtitles(video_path, ass_path, output_path):
    log("   🔤 Burning subtitles...")
    ass_str = str(ass_path).replace('\\', '/').replace(':', '\\:')

    cmd =['ffmpeg', '-i', str(video_path),
           '-vf', f"ass='{ass_str}'",
           '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium',
           '-pix_fmt', 'yuv420p', '-map_metadata', '-1', '-y', str(output_path)] # <--- Added map_metadata

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log("      ⚠️  ASS failed, trying subtitles filter...")
        cmd2 =['ffmpeg', '-i', str(video_path),
                '-vf', f"subtitles='{ass_str}'",
                '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium',
                '-pix_fmt', 'yuv420p', '-map_metadata', '-1', '-y', str(output_path)] # <--- Added map_metadata
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        if result2.returncode != 0:
            log("      ⚠️  Using drawtext fallback...")
            burn_subtitles_drawtext(video_path, ass_path, output_path)
            return

    log("   ✅ Subtitles burned!")


def burn_subtitles_drawtext(video_path, ass_path, output_path):
    log("   🔤 Drawtext fallback...")
    words =[]
    with open(ass_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            if line.startswith('Dialogue:'):
                parts = line.strip().split(',', 9)
                if len(parts) >= 10:
                    text = re.sub(r'\{[^}]*\}', '', parts[9].strip())
                    if text:
                        words.append({
                            'word': text,
                            'start': parse_ass_time(parts[1].strip()),
                            'end': parse_ass_time(parts[2].strip())
                        })

    if not words:
        shutil.copy2(str(video_path), str(output_path))
        return

    filters =[]
    for w in words[:200]:
        word = w['word'].replace("'", "'\\\\\\''").replace(":", "\\:")
        filters.append(
            f"drawtext=text='{word}':fontsize=80:fontcolor=yellow"
            f":borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.75"
            f":enable='between(t,{w['start']:.3f},{w['end']:.3f})'"
        )

    cmd =['ffmpeg', '-i', str(video_path), '-vf', ",".join(filters),
           '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium',
           '-pix_fmt', 'yuv420p', '-y', str(output_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    log("   ✅ Drawtext applied!")


# ============================================================
# ROUTES
# ============================================================

@app.route('/', methods=['GET'])
def index():
    if 'text/html' in request.headers.get('Accept', ''):
        return """
<!DOCTYPE html>
<html><head><title>Shorts Builder v3.7 beta</title></head>
<body style="font-family:sans-serif;padding:40px;background:#667eea;color:white;">
<h1>🎬 YouTube Shorts Builder v3.7 beta</h1>
<p>Global Search + Subtitles + Precise Word Alignment + Transitions</p>
<h3>Transitions:</h3>
<ul>
<li><b>fade</b> — Cross-dissolve</li>
<li><b>fade_black</b> — Fade to black, then in</li>
<li><b>slide_left / slide_right / slide_up / slide_down</b> — Push</li>
<li><b>zoom</b> — Zoom out + fade</li>
<li><b>wipe_left / wipe_down</b> — Wipe reveal</li>
<li><b>none</b> — Hard cut (default)</li>
</ul>
</body></html>"""
    return jsonify({
        "service": "Shorts Builder",
        "version": "3.7-beta",
        "status": "running",
        "transitions": VALID_TRANSITIONS
    })


@app.route('/health', methods=['GET'])
def health_check():
    try:
        import whisper
        w = True
    except Exception:
        w = False
    return jsonify({
        "status": "healthy",
        "version": "3.7-beta",
        "ffmpeg": shutil.which('ffmpeg') is not None,
        "whisper": w,
        "pillow": PILLOW_AVAILABLE,
        "transitions": VALID_TRANSITIONS
    })


@app.route('/build', methods=['POST'])
def build_video():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON"}), 400

        log("=" * 60)
        log("🎬 BUILD v3.7 beta - Precise Alignment + Transitions")
        log("=" * 60)

        title = data.get('title', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        full_audio_url = data.get('full_audio_url')
        scenes = data.get('scenes', [])
        subtitles_enabled = data.get('subtitles', False)
        subtitle_style = data.get('subtitle_style', 'word_by_word')
        transition_effect = data.get('transition', 'none')
        transition_duration = float(data.get('transition_duration', 0.5))
        add_bgm = data.get('add_bgm', CONFIG['audio']['add_bgm_by_default'])
        bgm_volume = float(data.get('bgm_volume', CONFIG['audio']['default_bgm_volume']))
        use_ken_burns = data.get('ken_burns', CONFIG['video'].get('ken_burns_movement', True))

        if not full_audio_url:
            return jsonify({"success": False, "error": "full_audio_url required"}), 400
        if not scenes:
            return jsonify({"success": False, "error": "No scenes"}), 400

        # Validate transition settings
        if transition_effect not in VALID_TRANSITIONS:
            log(f"   ⚠️  Unknown transition '{transition_effect}', falling back to 'none'")
            transition_effect = 'none'
        if transition_effect != 'none' and not PILLOW_AVAILABLE:
            log("   ⚠️  Pillow not installed, transitions disabled")
            transition_effect = 'none'
        transition_duration = max(0.2, min(2.0, transition_duration))

        log(f"📝 Title: {title}")
        log(f"📊 Scenes: {len(scenes)}")
        log(f"📝 Subtitles: {subtitles_enabled} ({subtitle_style})")
        log(f"🔄 Transition: {transition_effect} ({transition_duration}s)")

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]

        work_dir = TEMP_DIR / f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        work_dir.mkdir(exist_ok=True)

        # ── STEP 1: DOWNLOAD AUDIO ──
        log("\n>>> STEP 1: DOWNLOAD AUDIO")
        raw_audio = work_dir / "full_audio_raw"
        download_file(full_audio_url, raw_audio)
        full_audio_wav = work_dir / "full_audio.wav"
        ensure_wav(raw_audio, full_audio_wav)
        total_duration = get_audio_duration(full_audio_wav)

        # ── STEP 2: TRANSCRIBE ──
        log("\n>>> STEP 2: TRANSCRIBE")
        transcribed_words, full_transcript = transcribe_audio_with_whisper(full_audio_wav)
        log(f"\n📄 TRANSCRIPT:\n   {full_transcript}")
        log(f"   ({len(transcribed_words)} words)")

            # ── STEP 2.5: ADD BACKGROUND MUSIC ──
        if add_bgm:
            valid_bgm_exts = ('.mp3', '.wav', '.m4a', '.ogg')
            bgm_files = [f for f in BGM_DIR.iterdir() if f.is_file() and f.suffix.lower() in valid_bgm_exts]
            
            if not bgm_files:
                log("\n>>> STEP 2.5: ADD BGM (Skipped - No music found in ./assets/bgm/)")
            else:
                log("\n>>> STEP 2.5: ADD BACKGROUND MUSIC")
                chosen_bgm = random.choice(bgm_files)
                mixed_audio_wav = work_dir / "full_audio_mixed.wav"
                
                # Mix them together
                mix_background_music(full_audio_wav, chosen_bgm, mixed_audio_wav, volume=bgm_volume)
                
                # Replace the old audio path with the newly mixed one for the rest of the script
                full_audio_wav = mixed_audio_wav

        # ── STEP 3: ALIGN SCENES ──
        log("\n>>> STEP 3: ALIGN SCENES (Global Search + Precise Alignment)")
        scene_texts = [s.get('text', '') for s in scenes]
        scenes_timing = align_scenes_to_timestamps(transcribed_words, scene_texts)

        # ── STEP 4: BUILD VIDEO ──
        final_output = OUTPUT_DIR / f"{safe_title}.mp4"

        if transition_effect != 'none' or use_ken_burns:  # <--- EDITED THIS LINE
            log(f"\n>>> STEP 4: BUILD ADVANCED PATH (Transitions / Ken Burns)")

            scenes_data = []
            for idx, (scene, timing) in enumerate(zip(scenes, scenes_timing), 1):
                if timing['duration'] < 0.3:
                    continue

                image_url = scene.get('image_url')
                if not image_url:
                    continue

                scene_trans = scene.get('transition', transition_effect)
                if scene_trans not in VALID_TRANSITIONS:
                    scene_trans = transition_effect
                scene_dur = float(scene.get('transition_duration', transition_duration))
                scene_dur = max(0.2, min(2.0, scene_dur))

                log(f"   📥 Scene {idx}: downloading image...")
                image_path = work_dir / f"scene_{idx}_image.jpg"
                download_file(image_url, image_path)

                pil_img = prepare_image_for_shorts(image_path)
                
                # --- NEW KEN BURNS DATA ---
                from PIL import Image
                raw_img = Image.open(image_path).convert('RGB')
                # Check if the JSON specified a valid effect, otherwise pick randomly
                requested_fx = scene.get('ken_burns_effect')
                if requested_fx in KEN_BURNS_EFFECTS:
                    kb_fx = requested_fx
                else:
                    kb_fx = get_random_ken_burns_effect() if (use_ken_burns and get_random_ken_burns_effect) else None

                scenes_data.append({
                    'image': pil_img,
                    'raw_image': raw_img,     # <--- ADDED
                    'kb_effect': kb_fx,       # <--- ADDED
                    'start': timing['start'],
                    'end': timing['end'],
                    'scene_index': idx,
                    'transition': scene_trans,
                    'transition_duration': scene_dur
                })
                log(f"   ✅ Scene {idx}: {timing['start']:.2f}s → {timing['end']:.2f}s")

            if not scenes_data:
                raise Exception("No valid scenes to build!")

            log(f"\n   🎬 Building video with {len(scenes_data)} scenes...")
            build_video_with_transitions(
                scenes_data,
                str(full_audio_wav),
                str(final_output),
                transition_effect=transition_effect,
                transition_duration=transition_duration
            )
            scenes_processed = len(scenes_data)

        else:
            # ═══════════════════════════════════════════
            # ORIGINAL PATH: per-clip + concatenation
            # ═══════════════════════════════════════════
            log("\n>>> STEP 4: BUILD CLIPS (no transitions)")
            video_clips = []

            for idx, (scene, timing) in enumerate(zip(scenes, scenes_timing), 1):
                log(f"\n🎬 SCENE {idx}/{len(scenes)}")
                log(f"   Time: {timing['start']:.2f}s → {timing['end']:.2f}s ({timing['duration']:.2f}s)")

                if timing['duration'] < 0.5:
                    log("   ⚠️  Too short, skipping")
                    continue

                image_url = scene.get('image_url')
                if not image_url:
                    log("   ⚠️  No image, skipping")
                    continue

                image_path = work_dir / f"scene_{idx}_image.jpg"
                download_file(image_url, image_path)

                scene_audio = work_dir / f"scene_{idx}_audio.wav"
                extract_audio_chunk(full_audio_wav, scene_audio, timing['start'], timing['end'])

                clip_path = work_dir / f"scene_{idx}_clip.mp4"
                create_video_clip(image_path, scene_audio, clip_path)

                video_clips.append(str(clip_path))
                log(f"   ✅ Scene {idx} done!")

            if not video_clips:
                raise Exception("No clips created!")

            log(f"\n>>> STEP 5: CONCATENATE {len(video_clips)} CLIPS")
            concatenate_videos(video_clips, str(final_output))
            scenes_processed = len(video_clips)

        # ── STEP 6: SUBTITLES ──
        if subtitles_enabled and transcribed_words:
            log(f"\n>>> STEP 6: SUBTITLES ({subtitle_style})")
            ass_path = work_dir / "subtitles.ass"
            generate_word_subtitles(transcribed_words, str(ass_path), style=subtitle_style)
            final_subs = OUTPUT_DIR / f"{safe_title}_subs.mp4"
            burn_subtitles(str(final_output), str(ass_path), str(final_subs))
            if final_subs.exists() and final_subs.stat().st_size > 1000:
                final_output.unlink()
                final_subs.rename(final_output)
                log("   ✅ Subtitles added!")
            else:
                log("   ⚠️  Subtitle issue, keeping original")
        else:
            log("\n>>> STEP 6: SUBTITLES SKIPPED")

        # ── CLEANUP ──
        shutil.rmtree(work_dir)
        file_size_mb = round(final_output.stat().st_size / 1024 / 1024, 2)

        log("\n" + "=" * 60)
        log(f"✅ DONE! {final_output} ({file_size_mb} MB)")
        log("=" * 60)

        video_id = safe_title 
        download_url = f"/download/{video_id}"

        return jsonify({
        "success": True,
        "version": "3.7-beta",
        "video_id": video_id,
        "download_url": download_url,
        "title": title,
        "scenes_processed": scenes_processed,
        "file_size_mb": file_size_mb,
        "subtitles": subtitles_enabled,
        "transcript_preview": full_transcript[:200]
        }), 200

    except Exception as e:
        log(f"\n❌ FAILED: {str(e)}")
        log(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<video_id>', methods=['GET'])
def download_video(video_id):
    # Sanitize the ID for security
    safe_id = "".join(c for c in video_id if c.isalnum() or c in ('_', '-'))
    file_path = OUTPUT_DIR / f"{safe_id}.mp4"
    
    if not file_path.exists():
        return jsonify({"error": "Video not found or already deleted"}), 404
        
    log(f" 📤 Streaming video to Make.com: {safe_id}.mp4")
    
    return send_file(
        file_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=f"{safe_id}.mp4"
    )

if __name__ == '__main__':
    log("=" * 60)
    log("🚀 YouTube Shorts Builder v3.7 beta")
    log("   Precise Alignment + Transitions + Subtitles")
    log("=" * 60)
    if shutil.which('ffmpeg'):
        log("✅ FFmpeg")
    else:
        log("❌ FFmpeg NOT found")
    try:
        import whisper
        log("✅ Whisper")
    except Exception:
        log("❌ Whisper NOT found")
    if PILLOW_AVAILABLE:
        log(f"✅ Pillow (transitions: {', '.join(VALID_TRANSITIONS)})")
    else:
        log("⚠️  Pillow NOT found — transitions disabled, hard cuts only")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)