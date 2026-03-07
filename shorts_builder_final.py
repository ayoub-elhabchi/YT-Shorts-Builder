#!/usr/bin/env python3
"""
YouTube Shorts Builder v3.1 - Fixed Audio Splitting
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


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


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
    response = requests.get(url, stream=True, timeout=120, allow_redirects=True)
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

    is_base64 = False
    if len(first_bytes) > 0:
        printable_count = sum(1 for b in first_bytes if 32 <= b <= 126 or b in (9, 10, 13))
        if printable_count > len(first_bytes) * 0.95:
            is_base64 = True

    if is_base64:
        log("   🔄 Decoding base64...")
        with open(temp_path, 'rb') as f:
            encoded_data = f.read()
        encoded_data = encoded_data.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
        try:
            decoded_data = base64.b64decode(encoded_data)
            with open(output_path, 'wb') as f:
                f.write(decoded_data)
            os.remove(temp_path)
        except Exception:
            os.rename(temp_path, output_path)
    else:
        log("   ✅ Binary file")
        os.rename(temp_path, output_path)
    return output_path


def ensure_wav(input_path, wav_path):
    """Convert to WAV if needed - auto-detect format"""
    with open(input_path, 'rb') as f:
        header = f.read(4)

    if header[:4] == b'RIFF':
        log("   ✅ File is already WAV - copying as-is")
        if str(input_path) != str(wav_path):
            shutil.copy2(str(input_path), str(wav_path))
        return wav_path

    log("   🔊 File is raw PCM - converting to WAV...")
    cmd = [
        'ffmpeg', '-f', 's16le', '-ar', '24000', '-ac', '1',
        '-i', str(input_path),
        '-acodec', 'pcm_s16le', '-y', str(wav_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"   ⚠️  PCM conversion failed, trying auto-detect...")
        cmd2 = [
            'ffmpeg', '-i', str(input_path),
            '-acodec', 'pcm_s16le', '-ar', '24000', '-ac', '1',
            '-y', str(wav_path)
        ]
        subprocess.run(cmd2, capture_output=True, text=True, check=True)

    wav_size = os.path.getsize(wav_path)
    log(f"   ✅ WAV ready: {wav_size} bytes")
    return wav_path


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    log(f"   📏 Total audio duration: {duration:.2f}s")
    return duration


def transcribe_audio_with_whisper(audio_path):
    import whisper
    log("🎤 Transcribing audio with Whisper...")
    log("   Loading model...")
    model = whisper.load_model("base")
    log("   Transcribing...")
    result = model.transcribe(str(audio_path), word_timestamps=True, language='en')
    all_words = []
    for segment in result['segments']:
        for word_info in segment.get('words', []):
            all_words.append({
                'word': word_info['word'].strip().lower(),
                'start': word_info['start'],
                'end': word_info['end']
            })
    log(f"   ✅ Transcribed: {len(all_words)} words")
    log(f"   Words: {[w['word'] for w in all_words[:20]]}...")
    return all_words, result['text']


def clean_scene_text(text):
    """Remove ALL non-spoken content"""
    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    return cleaned


def align_scenes_to_timestamps(transcribed_words, scene_texts, total_duration):
    """
    Align scene texts to audio timestamps.
    If matching fails, divide audio equally.
    """
    log("🔍 Aligning scenes to audio timestamps...")

    num_scenes = len(scene_texts)
    if num_scenes == 0:
        return []

    # Clean all scene texts
    cleaned_texts = []
    for i, text in enumerate(scene_texts):
        cleaned = clean_scene_text(text)
        words = re.findall(r'\w+', cleaned)
        cleaned_texts.append(words)
        log(f"   Scene {i+1} cleaned: '{' '.join(words[:8])}...' ({len(words)} words)")

    # Try to match each scene
    matched_starts = []
    word_cursor = 0

    for scene_idx, scene_words in enumerate(cleaned_texts):
        if not scene_words:
            log(f"   Scene {scene_idx+1}: empty after cleaning")
            matched_starts.append(None)
            continue

        found = False
        search_words = scene_words[:3]

        for i in range(word_cursor, len(transcribed_words)):
            check_count = min(3, len(scene_words))
            matches = 0
            for j in range(check_count):
                if i + j >= len(transcribed_words):
                    break
                tw = transcribed_words[i + j]['word']
                sw = scene_words[j]
                if sw in tw or tw in sw:
                    matches += 1
            if matches >= check_count:
                start_t = transcribed_words[i]['start']
                log(f"   Scene {scene_idx+1}: ✅ MATCHED at {start_t:.2f}s")
                matched_starts.append(start_t)
                word_cursor = i + len(scene_words)
                found = True
                break

        if not found:
            log(f"   Scene {scene_idx+1}: ❌ no match")
            matched_starts.append(None)

    matched_count = sum(1 for s in matched_starts if s is not None)
    log(f"\n   📊 Matched {matched_count}/{num_scenes} scenes to audio")

    # DECISION: If less than half matched, divide equally
    if matched_count < num_scenes / 2:
        log(f"   ⚠️  Too few matches → DIVIDING AUDIO EQUALLY")
        log(f"   ⚠️  Each scene gets {total_duration / num_scenes:.2f}s")
        chunk = total_duration / num_scenes
        scenes_timing = []
        for i in range(num_scenes):
            start = round(i * chunk, 2)
            end = round((i + 1) * chunk, 2)
            dur = round(end - start, 2)
            scenes_timing.append({'start': start, 'end': end, 'duration': dur})
            log(f"      Scene {i+1}: {start:.2f}s → {end:.2f}s ({dur:.2f}s)")
        return scenes_timing

    # Enough matches - use them with progressive fill
    log("   ✅ Using matched timestamps with progressive fill")
    scenes_timing = []
    current_pos = 0.0

    for i in range(num_scenes):
        if matched_starts[i] is not None:
            start = matched_starts[i]
        else:
            start = current_pos

        # Find next known start
        next_start = None
        for j in range(i + 1, num_scenes):
            if matched_starts[j] is not None:
                next_start = matched_starts[j]
                break

        if next_start is not None:
            gap_scenes = 1
            for j in range(i + 1, num_scenes):
                if matched_starts[j] is not None:
                    break
                gap_scenes += 1
            end = start + (next_start - start) / gap_scenes
        elif i == num_scenes - 1:
            end = total_duration
        else:
            remaining = num_scenes - i
            chunk = (total_duration - start) / remaining
            end = start + chunk

        # ENFORCE MINIMUM 2 SECONDS
        if end - start < 2.0:
            end = min(start + 2.0, total_duration)

        # NEVER exceed total duration
        if end > total_duration:
            end = total_duration
        if start >= total_duration:
            start = max(total_duration - 2.0, 0)
            end = total_duration

        start = round(start, 2)
        end = round(end, 2)
        dur = round(end - start, 2)

        scenes_timing.append({'start': start, 'end': end, 'duration': dur})
        log(f"      Scene {i+1}: {start:.2f}s → {end:.2f}s ({dur:.2f}s)")
        current_pos = end

    return scenes_timing


def extract_audio_chunk(input_wav, output_wav, start_time, end_time):
    """Extract audio chunk - with safety checks"""
    # ABSOLUTE SAFETY: never allow zero or negative duration
    if end_time <= start_time:
        log(f"      ⚠️  SAFETY: fixing {start_time:.2f} → {end_time:.2f}")
        end_time = start_time + 2.0

    log(f"      Cutting: {start_time:.2f}s → {end_time:.2f}s")

    cmd = [
        'ffmpeg',
        '-i', str(input_wav),
        '-ss', str(start_time),
        '-to', str(end_time),
        '-acodec', 'copy',
        '-y',
        str(output_wav)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"      ⚠️  FFmpeg stderr: {result.stderr[:200]}")
        raise Exception(f"FFmpeg failed: {result.stderr[:200]}")


def create_video_clip(image_path, audio_path, output_path):
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())

    cmd = [
        'ffmpeg',
        '-loop', '1', '-i', str(image_path),
        '-i', str(audio_path),
        '-c:v', 'libx264', '-preset', 'medium', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
        '-t', str(duration),
        '-shortest', '-y',
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def concatenate_videos(video_paths, output_path):
    concat_file = TEMP_DIR / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for vp in video_paths:
            f.write(f"file '{os.path.abspath(vp)}'\n")
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy', '-y', str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "Shorts Builder", "version": "3.1", "status": "running"})


@app.route('/health', methods=['GET'])
def health_check():
    try:
        import whisper
        w = True
    except Exception:
        w = False
    return jsonify({"status": "healthy", "ffmpeg": shutil.which('ffmpeg') is not None, "whisper": w})


@app.route('/build', methods=['POST'])
def build_video():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON"}), 400

        log("=" * 60)
        log("🎬 BUILD REQUEST v3.1")
        log("=" * 60)

        title = data.get('title', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        full_audio_url = data.get('full_audio_url')
        scenes = data.get('scenes', [])

        if not full_audio_url:
            return jsonify({"success": False, "error": "full_audio_url required"}), 400
        if not scenes:
            return jsonify({"success": False, "error": "No scenes"}), 400

        log(f"📝 Title: {title}")
        log(f"📊 Scenes: {len(scenes)}")

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]

        work_dir = TEMP_DIR / f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        work_dir.mkdir(exist_ok=True)

        # STEP 1: Download audio
        log("\n>>> STEP 1: DOWNLOAD AUDIO")
        raw_audio = work_dir / "full_audio_raw"
        download_file(full_audio_url, raw_audio)

        # Convert/copy to WAV
        full_audio_wav = work_dir / "full_audio.wav"
        ensure_wav(raw_audio, full_audio_wav)

        # Get duration
        total_duration = get_audio_duration(full_audio_wav)

        # STEP 2: Transcribe
        log("\n>>> STEP 2: TRANSCRIBE")
        transcribed_words, full_transcript = transcribe_audio_with_whisper(full_audio_wav)
        log(f"   Preview: {full_transcript[:200]}...")

        # STEP 3: Align
        log("\n>>> STEP 3: ALIGN SCENES")
        scene_texts = [scene.get('text', '') for scene in scenes]
        scenes_timing = align_scenes_to_timestamps(transcribed_words, scene_texts, total_duration)

        # VERIFY - print all timings
        log("\n   === FINAL TIMING ===")
        for i, t in enumerate(scenes_timing):
            log(f"   Scene {i+1}: {t['start']:.2f}s → {t['end']:.2f}s ({t['duration']:.2f}s)")

        # STEP 4: Build clips
        log("\n>>> STEP 4: BUILD CLIPS")
        video_clips = []

        for idx, (scene, timing) in enumerate(zip(scenes, scenes_timing), 1):
            log(f"\n🎬 SCENE {idx}/{len(scenes)}")
            log(f"   Time: {timing['start']:.2f}s → {timing['end']:.2f}s ({timing['duration']:.2f}s)")

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

        # STEP 5: Concatenate
        log(f"\n>>> STEP 5: CONCATENATE {len(video_clips)} CLIPS")
        final_output = OUTPUT_DIR / f"{safe_title}.mp4"
        concatenate_videos(video_clips, str(final_output))

        shutil.rmtree(work_dir)
        file_size_mb = round(final_output.stat().st_size / 1024 / 1024, 2)

        log("\n" + "=" * 60)
        log(f"✅ DONE! {final_output} ({file_size_mb} MB)")
        log("=" * 60)

        return jsonify({
            "success": True,
            "title": title,
            "output_path": str(final_output),
            "scenes_processed": len(video_clips),
            "file_size_mb": file_size_mb
        }), 200

    except Exception as e:
        log(f"\n❌ FAILED: {str(e)}")
        log(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("🚀 YouTube Shorts Builder v3.1")
    log("=" * 60)

    if shutil.which('ffmpeg'):
        log("✅ FFmpeg found")
    else:
        log("❌ FFmpeg NOT found")

    try:
        import whisper
        log("✅ Whisper found")
    except Exception:
        log("❌ Whisper NOT found")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)