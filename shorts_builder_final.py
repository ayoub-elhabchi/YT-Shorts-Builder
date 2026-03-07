#!/usr/bin/env python3
"""
YouTube Shorts Builder v3.7 beta - Global Search + Subtitles
Fix: Scene alignment now records the actual first matched word position
instead of the scan start position, eliminating early audio cuts.
"""

import os
import json
import subprocess
import requests
import base64
from flask import Flask, request, jsonify
from pathlib import Path
import shutil
from datetime import datetime
import traceback
import re

app = Flask(__name__)

TEMP_DIR = Path("./temp/shorts_builder")
OUTPUT_DIR = Path("./output/shorts_output")
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    cmd = [
        'ffmpeg', '-i', str(input_path),
        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-y', str(wav_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Cannot convert: {result.stderr[:200]}")
    log(f"   ✅ WAV ready: {os.path.getsize(wav_path)} bytes")
    return wav_path


def get_audio_duration(audio_path):
    cmd = [
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
    """
    if not transcribed_words:
        raise Exception("No transcribed words")

    total_duration = transcribed_words[-1]['end']
    num_scenes = len(scene_texts)

    log(f"🔍 Aligning {num_scenes} scenes to {len(transcribed_words)} words ({total_duration:.2f}s)")

    # Clean all transcribed words once
    trans_clean = [clean_word(w['word']) for w in transcribed_words]

    # === For each scene, find WHERE its words appear in sequence ===
    scene_positions = []

    for si, text in enumerate(scene_texts):
        cleaned = clean_text_for_matching(text)
        all_words = cleaned.split()
        all_clean = [clean_word(w) for w in all_words]

        # Remove empty
        all_clean = [w for w in all_clean if w]

        log(f"\n   Scene {si+1}:")
        log(f"      Words: {all_clean[:12]}...")

        if len(all_clean) < 2:
            log(f"      ⚠️  Too few words")
            scene_positions.append(None)
            continue

        # Take first 6 non-trivial words for SEQUENTIAL matching
        match_words = []
        for w in all_clean:
            if w not in SKIP_WORDS or len(match_words) < 2:
                match_words.append(w)
            if len(match_words) >= 6:
                break

        log(f"      Match sequence: {match_words}")

        # Search every position: score by how many of the first N words
        # match IN ORDER at that position
        best_score = 0
        best_pos = -1

        for pos in range(len(transcribed_words)):
            score = 0
            ti = pos  # transcript index
            first_match = -1  # v3.7: track actual first matched word

            for mi, mw in enumerate(match_words):
                # Allow up to 2 skipped words in transcript
                found = False
                for skip in range(3):
                    if ti + skip >= len(transcribed_words):
                        break
                    tw = trans_clean[ti + skip]
                    if mw == tw:
                        score += 1.0
                        if first_match == -1:
                            first_match = ti + skip
                        ti = ti + skip + 1
                        found = True
                        break
                    if len(mw) >= 4 and len(tw) >= 4:
                        if mw in tw or tw in mw:
                            score += 0.7
                            if first_match == -1:
                                first_match = ti + skip
                            ti = ti + skip + 1
                            found = True
                            break

                if not found:
                    # Allow one miss
                    ti += 1

            if score > best_score:
                best_score = score
                best_pos = first_match  # v3.7: use actual match, not scan start

        threshold = max(2, len(match_words) * 0.4)
        if best_score >= threshold and best_pos >= 0:
            t = transcribed_words[best_pos]['start']
            log(f"      ✅ MATCHED at word[{best_pos}] = {t:.2f}s (score {best_score:.1f}/{len(match_words)})")
            scene_positions.append(best_pos)
        else:
            log(f"      ❌ No match (best {best_score:.1f}, need {threshold:.1f})")
            scene_positions.append(None)

    # === Enforce chronological order ===
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

    # === Build start times ===
    starts = [None] * num_scenes
    for i in range(num_scenes):
        if scene_positions[i] is not None:
            starts[i] = transcribed_words[scene_positions[i]]['start']

    starts[0] = 0.0

    # === Interpolate gaps ===
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

    # === Final timing ===
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

    probe = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(input_wav)]
    r = subprocess.run(probe, capture_output=True, text=True, check=True)
    total = float(r.stdout.strip())

    if end_time > total:
        end_time = total
    if start_time >= total:
        start_time = max(0, total - 2.0)
        end_time = total

    log(f"      ✂️  Cutting: {start_time:.2f}s → {end_time:.2f}s")

    cmd = ['ffmpeg', '-i', str(input_wav), '-ss', str(start_time),
           '-to', str(end_time), '-acodec', 'copy', '-y', str(output_wav)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg cut failed: {result.stderr[:200]}")


def create_video_clip(image_path, audio_path, output_path):
    probe = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)]
    r = subprocess.run(probe, capture_output=True, text=True, check=True)
    duration = float(r.stdout.strip())

    cmd = [
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
    cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
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

    header = """[Script Info]
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,Impact,90,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
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

    header = """[Script Info]
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Highlight,Impact,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,30,30,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

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
                    parts.append(r"{\c&H0000FFFF&\fscx110\fscy110}" + wt +
                                 r"{\c&H00FFFFFF&\fscx100\fscy100}")
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

    cmd = ['ffmpeg', '-i', str(video_path),
           '-vf', f"ass='{ass_str}'",
           '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium',
           '-pix_fmt', 'yuv420p', '-y', str(output_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log("      ⚠️  ASS failed, trying subtitles filter...")
        cmd2 = ['ffmpeg', '-i', str(video_path),
                '-vf', f"subtitles='{ass_str}'",
                '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium',
                '-pix_fmt', 'yuv420p', '-y', str(output_path)]
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        if result2.returncode != 0:
            log("      ⚠️  Using drawtext fallback...")
            burn_subtitles_drawtext(video_path, ass_path, output_path)
            return

    log("   ✅ Subtitles burned!")


def burn_subtitles_drawtext(video_path, ass_path, output_path):
    log("   🔤 Drawtext fallback...")
    words = []
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

    filters = []
    for w in words[:200]:
        word = w['word'].replace("'", "'\\\\\\''").replace(":", "\\:")
        filters.append(
            f"drawtext=text='{word}':fontsize=80:fontcolor=yellow"
            f":borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.75"
            f":enable='between(t,{w['start']:.3f},{w['end']:.3f})'"
        )

    cmd = ['ffmpeg', '-i', str(video_path), '-vf', ",".join(filters),
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
<p>Global Search + Subtitles + Precise Word Alignment</p>
</body></html>"""
    return jsonify({"service": "Shorts Builder", "version": "3.7-beta", "status": "running"})


@app.route('/health', methods=['GET'])
def health_check():
    try:
        import whisper
        w = True
    except Exception:
        w = False
    return jsonify({"status": "healthy", "version": "3.7-beta",
                    "ffmpeg": shutil.which('ffmpeg') is not None, "whisper": w})


@app.route('/build', methods=['POST'])
def build_video():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON"}), 400

        log("=" * 60)
        log("🎬 BUILD v3.7 beta - Global Search + Precise Alignment")
        log("=" * 60)

        title = data.get('title', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        full_audio_url = data.get('full_audio_url')
        scenes = data.get('scenes', [])
        subtitles_enabled = data.get('subtitles', False)
        subtitle_style = data.get('subtitle_style', 'word_by_word')

        if not full_audio_url:
            return jsonify({"success": False, "error": "full_audio_url required"}), 400
        if not scenes:
            return jsonify({"success": False, "error": "No scenes"}), 400

        log(f"📝 Title: {title}")
        log(f"📊 Scenes: {len(scenes)}")
        log(f"📝 Subtitles: {subtitles_enabled} ({subtitle_style})")

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]

        work_dir = TEMP_DIR / f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        work_dir.mkdir(exist_ok=True)

        # STEP 1
        log("\n>>> STEP 1: DOWNLOAD AUDIO")
        raw_audio = work_dir / "full_audio_raw"
        download_file(full_audio_url, raw_audio)
        full_audio_wav = work_dir / "full_audio.wav"
        ensure_wav(raw_audio, full_audio_wav)
        total_duration = get_audio_duration(full_audio_wav)

        # STEP 2
        log("\n>>> STEP 2: TRANSCRIBE")
        transcribed_words, full_transcript = transcribe_audio_with_whisper(full_audio_wav)
        log(f"\n📄 TRANSCRIPT:\n   {full_transcript}")
        log(f"   ({len(transcribed_words)} words)")

        # STEP 3
        log("\n>>> STEP 3: ALIGN SCENES (Global Search + Precise Alignment)")
        scene_texts = [s.get('text', '') for s in scenes]
        scenes_timing = align_scenes_to_timestamps(transcribed_words, scene_texts)

        # STEP 4
        log("\n>>> STEP 4: BUILD CLIPS")
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

        # STEP 5
        log(f"\n>>> STEP 5: CONCATENATE {len(video_clips)} CLIPS")
        final_output = OUTPUT_DIR / f"{safe_title}.mp4"
        concatenate_videos(video_clips, str(final_output))

        # STEP 6
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

        shutil.rmtree(work_dir)
        file_size_mb = round(final_output.stat().st_size / 1024 / 1024, 2)

        log("\n" + "=" * 60)
        log(f"✅ DONE! {final_output} ({file_size_mb} MB)")
        log("=" * 60)

        return jsonify({
            "success": True, "version": "3.7-beta", "title": title,
            "output_path": str(final_output),
            "scenes_processed": len(video_clips),
            "file_size_mb": file_size_mb,
            "subtitles": subtitles_enabled,
            "transcript_preview": full_transcript[:200]
        }), 200

    except Exception as e:
        log(f"\n❌ FAILED: {str(e)}")
        log(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("🚀 YouTube Shorts Builder v3.7 beta - Precise Word Alignment")
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)