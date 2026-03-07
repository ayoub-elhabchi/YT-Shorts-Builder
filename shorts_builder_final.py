#!/usr/bin/env python3
"""
YouTube Shorts Builder v3.1 - Optimized Audio Splitting Edition
- SSML tag cleaning ([emotion], <break/> tags)
- Robust text matching
- Better error handling
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

# Configuration
TEMP_DIR = Path("./temp/shorts_builder")
OUTPUT_DIR = Path("./output/shorts_output")
SAMPLE_RATE = 24000
CHANNELS = 1
BITS_PER_SAMPLE = 16

# Create directories
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(message):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def clean_text_for_matching(text):
    """
    Clean text by removing SSML tags, emotion markers, and normalizing
    
    Removes:
    - Emotion tags: [past], [somber], [excited], etc.
    - SSML break tags: <break time='0.6s'/>, <break time="1s"/>
    - Other SSML tags: <emphasis>, <prosody>, etc.
    - Extra whitespace
    
    Example:
    Input:  "[past][somber]A cargo ship vanished<break time='0.6s'/> in 1803."
    Output: "a cargo ship vanished in 1803"
    """
    if not text:
        return ""
    
    # Remove emotion/style tags in square brackets: [past], [somber], etc.
    text = re.sub(r'\[[\w\s]+\]', '', text)
    
    # Remove SSML break tags: <break time='0.6s'/>, <break time="1s"/>
    text = re.sub(r'<break\s+time=["\'][\d.]+s["\']\s*/>', ' ', text)
    
    # Remove other SSML tags: <emphasis>, </emphasis>, <prosody rate="slow">, etc.
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace (multiple spaces to single space)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Convert to lowercase for matching
    text = text.lower()
    
    # Remove most punctuation except apostrophes (for words like "don't")
    # Keep periods for sentence boundaries
    text = re.sub(r'[,;:!?"""''—\-]', '', text)
    
    return text


def normalize_for_matching(text):
    """
    Further normalize text for fuzzy matching
    - Removes all punctuation including periods
    - Collapses whitespace
    """
    # Remove all punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def convert_gdrive_url_to_direct(url):
    """Convert Google Drive sharing URL to direct download URL"""
    if not url:
        return None
    
    if "drive.google.com/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    elif "uc?id=" in url:
        return url
    elif "id=" in url:
        return url
    
    return url


def download_file(url, output_path):
    """Download file from URL and handle base64 decoding if needed"""
    url = convert_gdrive_url_to_direct(url)
    log(f"📥 Downloading: {url[:80]}...")
    
    try:
        response = requests.get(url, stream=True, timeout=120, allow_redirects=True)
        response.raise_for_status()
        
        # Download to temp file first
        temp_path = str(output_path) + ".temp"
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(temp_path)
        log(f"   Downloaded: {file_size} bytes")
        
        # Check if file is base64-encoded
        with open(temp_path, 'rb') as f:
            first_bytes = f.read(200)
        
        is_base64 = False
        if len(first_bytes) > 0:
            printable_count = sum(1 for b in first_bytes if 32 <= b <= 126 or b in (9, 10, 13))
            if printable_count > len(first_bytes) * 0.95:
                log("   ⚠️  Detected base64 encoding")
                is_base64 = True
        
        if is_base64:
            log("   🔄 Decoding base64...")
            with open(temp_path, 'rb') as f:
                encoded_data = f.read()
            
            encoded_data = encoded_data.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
            
            try:
                decoded_data = base64.b64decode(encoded_data)
                log(f"   ✅ Decoded: {len(encoded_data)} → {len(decoded_data)} bytes")
                
                with open(output_path, 'wb') as f:
                    f.write(decoded_data)
                
                os.remove(temp_path)
                
            except Exception as e:
                log(f"   ❌ Base64 decode failed: {e}, using as-is")
                os.rename(temp_path, output_path)
        else:
            log("   ✅ Binary file (not base64)")
            os.rename(temp_path, output_path)
        
        return output_path
        
    except Exception as e:
        log(f"❌ Download failed: {str(e)}")
        temp_path = str(output_path) + ".temp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def pcm_to_wav(pcm_path, wav_path, sample_rate=SAMPLE_RATE, channels=CHANNELS):
    """Convert raw PCM to WAV using FFmpeg"""
    try:
        log("🔊 Converting to WAV...")
        
        cmd = [
            'ffmpeg',
            '-f', 's16le',
            '-ar', str(sample_rate),
            '-ac', str(channels),
            '-i', str(pcm_path),
            '-acodec', 'pcm_s16le',
            '-y',
            str(wav_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not os.path.exists(wav_path):
            raise Exception("WAV file not created")
        
        wav_size = os.path.getsize(wav_path)
        if wav_size < 1000:
            raise Exception(f"WAV too small: {wav_size} bytes")
        
        log(f"   ✅ WAV created: {wav_size} bytes")
        return wav_path
        
    except subprocess.CalledProcessError as e:
        log(f"   ❌ FFmpeg error: {e.stderr}")
        raise


def transcribe_audio_with_whisper(audio_path):
    """Transcribe audio and get word-level timestamps using Whisper"""
    try:
        import whisper
        
        log("🎤 Transcribing audio with Whisper...")
        log("   Loading Whisper model...")
        
        # Use 'base' model for speed, 'small' or 'medium' for better accuracy
        model = whisper.load_model("base")
        
        log("   Transcribing (this may take 30-60 seconds)...")
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language='en'
        )
        
        # Extract all words with timestamps
        all_words = []
        for segment in result['segments']:
            for word_info in segment.get('words', []):
                all_words.append({
                    'word': word_info['word'].strip().lower(),
                    'start': word_info['start'],
                    'end': word_info['end']
                })
        
        log(f"   ✅ Transcribed: {len(all_words)} words")
        return all_words, result['text']
        
    except ImportError:
        log("   ❌ Whisper not installed!")
        log("   Install with: pip install openai-whisper")
        raise Exception("Whisper not installed. Run: pip install openai-whisper")
    except Exception as e:
        log(f"   ❌ Transcription failed: {str(e)}")
        raise


def align_scenes_to_timestamps(transcribed_words, scene_texts):
    """
    Find timestamp boundaries for each scene based on text
    Now with SSML tag cleaning and robust matching!
    
    If too many scenes fail to match, falls back to equal division.
    """
    log("🔍 Aligning scenes to audio timestamps...")
    log("   (Cleaning SSML tags: [emotion], <break/>, etc.)")
    
    # Get total audio duration from transcription
    if not transcribed_words:
        raise Exception("No transcribed words available")
    
    total_duration = transcribed_words[-1]['end']
    log(f"   📏 Total audio duration: {total_duration:.2f}s")
    
    scenes_timing = []
    word_index = 0
    matched_count = 0
    
    for scene_idx, scene_text_raw in enumerate(scene_texts, 1):
        log(f"\n   📝 Scene {scene_idx}:")
        log(f"      Raw: {scene_text_raw[:80]}...")
        
        # Clean the scene text (remove SSML tags)
        scene_text_clean = clean_text_for_matching(scene_text_raw)
        log(f"      Cleaned: {scene_text_clean[:80]}...")
        
        # Extract words for matching
        scene_words = scene_text_clean.split()
        
        if not scene_words or len(scene_words) < 2:
            log(f"      ⚠️  Scene {scene_idx} too short after cleaning")
            scenes_timing.append({
                'start': 0,
                'end': 0,
                'duration': 0,
                'scene_index': scene_idx,
                'matched': False
            })
            continue
        
        # Find first few words of scene in transcription
        start_time = None
        start_word_idx = word_index
        
        # Use first 3-5 words for matching (more reliable)
        search_phrase = scene_words[:min(5, len(scene_words))]
        log(f"      🔎 Searching for: {' '.join(search_phrase)}")
        
        # Search for scene start
        max_search = len(transcribed_words) - len(search_phrase)
        found = False
        
        while word_index <= max_search and not found:
            # Check if search phrase matches transcription
            matches = 0
            for i, scene_word in enumerate(search_phrase):
                if word_index + i >= len(transcribed_words):
                    break
                
                trans_word = transcribed_words[word_index + i]['word']
                
                # Normalize both for comparison (remove punctuation)
                scene_word_norm = normalize_for_matching(scene_word)
                trans_word_norm = normalize_for_matching(trans_word)
                
                # Check if words match (or one contains the other)
                if (scene_word_norm == trans_word_norm or 
                    scene_word_norm in trans_word_norm or 
                    trans_word_norm in scene_word_norm):
                    matches += 1
            
            # If we matched at least 70% of search phrase, consider it found
            if matches >= len(search_phrase) * 0.7:
                start_time = transcribed_words[word_index]['start']
                start_word_idx = word_index
                found = True
                matched_count += 1
                log(f"      ✅ Found at {start_time:.2f}s (word: '{transcribed_words[word_index]['word']}')")
                log(f"         Matched {matches}/{len(search_phrase)} words")
                break
            
            word_index += 1
        
        if not found:
            log(f"      ⚠️  Could not find scene {scene_idx} in audio")
            scenes_timing.append({
                'start': 0,
                'end': 0,
                'duration': 0,
                'scene_index': scene_idx,
                'matched': False
            })
            continue
        
        # Find end of scene
        # Estimate based on word count (more accurate than before)
        words_to_advance = min(len(scene_words), len(transcribed_words) - start_word_idx - 1)
        end_word_idx = start_word_idx + words_to_advance
        
        # Make sure we don't go past the end
        if end_word_idx >= len(transcribed_words):
            end_word_idx = len(transcribed_words) - 1
        
        end_time = transcribed_words[end_word_idx]['end']
        
        # Move word_index forward for next scene
        word_index = end_word_idx + 1
        
        duration = end_time - start_time
        log(f"      ⏱️  Timing: {start_time:.2f}s → {end_time:.2f}s (duration: {duration:.2f}s)")
        
        scenes_timing.append({
            'start': start_time,
            'end': end_time,
            'duration': duration,
            'scene_index': scene_idx,
            'matched': True
        })
    
    # CRITICAL: Check if too many scenes failed to match
    match_rate = matched_count / len(scene_texts) if scene_texts else 0
    
    log(f"\n   📊 Match Summary: {matched_count}/{len(scene_texts)} scenes matched ({match_rate*100:.0f}%)")
    
    if match_rate < 0.5:
        log(f"\n   ⚠️  WARNING: Less than 50% of scenes matched!")
        log(f"   ⚠️  This usually means scene texts don't match the audio content.")
        log(f"   ⚠️  FALLBACK: Dividing audio equally among {len(scene_texts)} scenes")
        
        # Divide audio equally
        chunk_duration = total_duration / len(scene_texts)
        scenes_timing = []
        
        for i in range(len(scene_texts)):
            start = i * chunk_duration
            end = (i + 1) * chunk_duration
            scenes_timing.append({
                'start': start,
                'end': end,
                'duration': chunk_duration,
                'scene_index': i + 1,
                'matched': False,
                'fallback': True
            })
            log(f"      Scene {i+1}: {start:.2f}s → {end:.2f}s (equal division)")
        
        log(f"\n   ⚠️  RECOMMENDATION: Check that your scene texts match what's actually spoken in the audio!")
    else:
        log(f"   ✅ Good match rate! Proceeding with aligned timestamps.")
    
    return scenes_timing


def extract_audio_chunk(input_wav, output_wav, start_time, end_time):
    """Extract audio chunk using FFmpeg with safety checks"""
    # SAFETY: Ensure minimum 2 second duration
    duration = end_time - start_time
    if duration < 0.1:
        log(f"      ⚠️  WARNING: Duration too short ({duration:.2f}s), adjusting to 2s minimum")
        end_time = start_time + 2.0
    
    # SAFETY: Ensure we don't go past audio end
    # Get total audio duration
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(input_wav)
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    total_duration = float(result.stdout.strip())
    
    if end_time > total_duration:
        log(f"      ⚠️  WARNING: End time ({end_time:.2f}s) exceeds audio duration ({total_duration:.2f}s)")
        end_time = total_duration
    
    if start_time >= total_duration:
        log(f"      ⚠️  WARNING: Start time ({start_time:.2f}s) at or past audio end, using last 2s")
        start_time = max(0, total_duration - 2.0)
        end_time = total_duration
    
    log(f"      ✂️  Extracting: {start_time:.2f}s → {end_time:.2f}s (duration: {end_time - start_time:.2f}s)")
    
    cmd = [
        'ffmpeg',
        '-i', str(input_wav),
        '-ss', str(start_time),
        '-to', str(end_time),
        '-acodec', 'copy',
        '-y',
        str(output_wav)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def create_video_clip(image_path, audio_path, output_path):
    """Create video clip: static image with audio"""
    # Get audio duration
    probe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    
    cmd = [
        'ffmpeg',
        '-loop', '1',
        '-i', str(image_path),
        '-i', str(audio_path),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-vf', f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
        '-t', str(duration),
        '-shortest',
        '-y',
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def concatenate_videos(video_paths, output_path):
    """Concatenate multiple videos"""
    concat_file = TEMP_DIR / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video_path in video_paths:
            f.write(f"file '{os.path.abspath(video_path)}'\n")
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        '-y',
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    if 'text/html' in request.headers.get('Accept', ''):
        return """
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Shorts Builder v3.1</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #333; margin-bottom: 10px; }
        .version { color: #667eea; font-size: 14px; margin-bottom: 20px; }
        .status { 
            display: inline-block;
            background: #2ecc71;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
        }
        .feature {
            background: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid #2ecc71;
        }
        .feature h3 { color: #2ecc71; margin-bottom: 5px; }
        .new { background: #fff3cd; border-left-color: #ffc107; }
        .new h3 { color: #ffc107; }
        pre {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 YouTube Shorts Builder</h1>
        <p class="version">v3.1 - Optimized with SSML Cleaning</p>
        <p style="margin-bottom: 20px;"><span class="status">✓ RUNNING</span></p>
        
        <div class="feature new">
            <h3>✨ NEW in v3.1: SSML Tag Cleaning</h3>
            <p>Automatically removes emotion tags [past][somber] and break tags &lt;break time='0.6s'/&gt; from your scene texts for perfect matching!</p>
        </div>
        
        <div class="feature">
            <h3>🎯 How It Works</h3>
            <p>Upload ONE full audio file with scene texts (including SSML tags). Builder cleans tags automatically and splits audio by scene boundaries using Whisper speech recognition.</p>
        </div>
        
        <div class="feature">
            <h3>📝 Example Input</h3>
            <pre>{
  "title": "My Video",
  "full_audio_url": "https://drive.google.com/...",
  "scenes": [
    {
      "text": "[past][somber]A cargo ship vanished&lt;break time='0.6s'/&gt; in 1803.",
      "image_url": "https://drive.google.com/..."
    }
  ]
}</pre>
        </div>
        
        <div class="feature">
            <h3>🎯 Endpoints</h3>
            <p><strong>POST /build</strong> - Build video with audio splitting</p>
            <p><strong>GET /health</strong> - Health check</p>
        </div>
    </div>
</body>
</html>
        """
    else:
        return jsonify({
            "service": "YouTube Shorts Builder",
            "version": "3.1",
            "features": ["Audio splitting", "Whisper transcription", "SSML cleaning", "Robust matching"],
            "status": "running"
        }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    try:
        import whisper
        whisper_available = True
    except:
        whisper_available = False
    
    return jsonify({
        "status": "healthy",
        "version": "3.1",
        "ffmpeg": shutil.which('ffmpeg') is not None,
        "ffprobe": shutil.which('ffprobe') is not None,
        "whisper": whisper_available,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/build', methods=['POST'])
def build_video():
    """Main endpoint with audio splitting and SSML cleaning"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON payload"}), 400
        
        log("=" * 60)
        log("🎬 NEW VIDEO BUILD REQUEST (v3.1 - SSML Cleaning)")
        log("=" * 60)
        
        title = data.get('title', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        full_audio_url = data.get('full_audio_url')
        scenes = data.get('scenes', [])
        
        if not full_audio_url:
            return jsonify({"success": False, "error": "full_audio_url required"}), 400
        
        if not scenes:
            return jsonify({"success": False, "error": "No scenes provided"}), 400
        
        log(f"📝 Title: {title}")
        log(f"📊 Scenes: {len(scenes)}")
        log(f"🎵 Full audio URL: {full_audio_url[:60]}...")
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]
        
        # Create working directory
        work_dir = TEMP_DIR / f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        work_dir.mkdir(exist_ok=True)
        
        # Step 1: Download full audio
        log("\n" + "=" * 60)
        log("STEP 1: DOWNLOAD FULL AUDIO")
        log("=" * 60)
        
        full_audio_pcm = work_dir / "full_audio.pcm"
        full_audio_wav = work_dir / "full_audio.wav"
        
        download_file(full_audio_url, full_audio_pcm)
        pcm_to_wav(full_audio_pcm, full_audio_wav)
        
        # Step 2: Transcribe with Whisper
        log("\n" + "=" * 60)
        log("STEP 2: TRANSCRIBE AUDIO")
        log("=" * 60)
        
        transcribed_words, full_transcript = transcribe_audio_with_whisper(full_audio_wav)
        
        log(f"\n📄 FULL TRANSCRIPT:")
        log(f"   {full_transcript}")
        log(f"\n   (Total characters: {len(full_transcript)})")
        log(f"   (Total words: {len(transcribed_words)})")
        
        # Step 3: Align scenes to timestamps (with SSML cleaning!)
        log("\n" + "=" * 60)
        log("STEP 3: ALIGN SCENES (with SSML cleaning)")
        log("=" * 60)
        
        scene_texts = [scene.get('text', '') for scene in scenes]
        scenes_timing = align_scenes_to_timestamps(transcribed_words, scene_texts)
        
        if len(scenes_timing) != len(scenes):
            log(f"⚠️  Warning: Found {len(scenes_timing)} timings for {len(scenes)} scenes")
            log(f"   Some scenes may have been skipped due to matching issues")
        
        # Step 4: Process each scene
        log("\n" + "=" * 60)
        log("STEP 4: PROCESS SCENES")
        log("=" * 60)
        
        video_clips = []
        skipped_scenes = []
        
        for timing in scenes_timing:
            scene_idx = timing['scene_index']
            scene = scenes[scene_idx - 1]  # Convert to 0-based index
            
            log(f"\n🎬 SCENE {scene_idx}/{len(scenes)}")
            log(f"   Text: {scene.get('text', '')[:60]}...")
            log(f"   Time: {timing['start']:.2f}s → {timing['end']:.2f}s ({timing['duration']:.2f}s)")
            
            # Skip scenes with very short or zero duration
            if timing['duration'] < 0.5:
                log(f"   ⚠️  Duration too short ({timing['duration']:.2f}s), skipping scene")
                skipped_scenes.append(scene_idx)
                continue
            
            image_url = scene.get('image_url')
            if not image_url:
                log(f"   ⚠️  No image URL, skipping")
                skipped_scenes.append(scene_idx)
                continue
            
            # Download image
            image_path = work_dir / f"scene_{scene_idx}_image.jpg"
            log(f"   📥 Downloading image...")
            download_file(image_url, image_path)
            
            # Extract audio chunk
            scene_audio_path = work_dir / f"scene_{scene_idx}_audio.wav"
            log(f"   ✂️  Extracting audio chunk...")
            extract_audio_chunk(full_audio_wav, scene_audio_path, timing['start'], timing['end'])
            
            # Create video clip
            clip_path = work_dir / f"scene_{scene_idx}_clip.mp4"
            log(f"   🎥 Creating video clip...")
            create_video_clip(image_path, scene_audio_path, clip_path)
            
            video_clips.append(str(clip_path))
            log(f"   ✅ Scene {scene_idx} complete!")
        
        if skipped_scenes:
            log(f"\n   ⚠️  Skipped scenes: {skipped_scenes}")
        
        if not video_clips:
            error_msg = "No video clips created! "
            if skipped_scenes:
                error_msg += f"All {len(skipped_scenes)} scenes were skipped. "
            error_msg += "This usually means scene texts don't match the audio content. "
            error_msg += "Check the transcription in the logs above."
            raise Exception(error_msg)
        
        # Step 5: Concatenate
        log("\n" + "=" * 60)
        log(f"STEP 5: CONCATENATE {len(video_clips)} CLIPS")
        log("=" * 60)
        
        final_output = OUTPUT_DIR / f"{safe_title}.mp4"
        concatenate_videos(video_clips, str(final_output))
        
        # Cleanup
        log("\n🧹 Cleaning up temporary files...")
        shutil.rmtree(work_dir)
        
        file_size_mb = round(final_output.stat().st_size / 1024 / 1024, 2)
        
        log("\n" + "=" * 60)
        log("✅ VIDEO COMPLETE!")
        log("=" * 60)
        log(f"📁 Output: {final_output}")
        log(f"📊 Size: {file_size_mb} MB")
        log(f"🎬 Scenes: {len(video_clips)}")
        
        return jsonify({
            "success": True,
            "version": "3.1",
            "title": title,
            "output_path": str(final_output),
            "scenes_processed": len(video_clips),
            "file_size_mb": file_size_mb,
            "transcript_preview": full_transcript[:200]
        }), 200
        
    except Exception as e:
        log(f"\n❌ BUILD FAILED: {str(e)}")
        log(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    # Check dependencies
    if not shutil.which('ffmpeg'):
        log("⚠️  WARNING: FFmpeg not found!")
    else:
        log("✅ FFmpeg found")
    
    if not shutil.which('ffprobe'):
        log("⚠️  WARNING: FFprobe not found!")
    else:
        log("✅ FFprobe found")
    
    try:
        import whisper
        log("✅ Whisper found")
    except:
        log("⚠️  WARNING: Whisper not installed!")
        log("   Install with: pip install openai-whisper")
    
    log("=" * 60)
    log("🚀 YouTube Shorts Builder v3.1 - OPTIMIZED")
    log("   ✨ SSML tag cleaning enabled")
    log("   ✨ Robust text matching")
    log("=" * 60)
    log(f"📁 Temp: {TEMP_DIR}")
    log(f"📁 Output: {OUTPUT_DIR}")
    log("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)