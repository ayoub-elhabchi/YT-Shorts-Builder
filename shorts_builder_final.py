#!/usr/bin/env python3
"""
YouTube Shorts Builder - Flask Webhook Server
Complete solution with BASE64 decoding fix
"""

import os
import json
import struct
import subprocess
import requests
import base64
from flask import Flask, request, jsonify
from pathlib import Path
import shutil
from datetime import datetime
import traceback

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
    log(f"Downloading: {url[:80]}...")
    
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
        log(f"Downloaded: {file_size} bytes")
        
        # Check if file is base64-encoded (common with Gemini TTS audio)
        with open(temp_path, 'rb') as f:
            first_bytes = f.read(200)
        
        # Detect base64: only contains A-Z, a-z, 0-9, +, /, =, and whitespace
        is_base64 = False
        if len(first_bytes) > 0:
            # Check if it's printable ASCII (base64 characteristic)
            printable_count = sum(1 for b in first_bytes if 32 <= b <= 126 or b in (9, 10, 13))
            if printable_count > len(first_bytes) * 0.95:  # 95% printable = likely base64
                log("⚠️  File appears to be base64-encoded")
                is_base64 = True
        
        if is_base64:
            log("🔄 Decoding base64...")
            # Read entire file
            with open(temp_path, 'rb') as f:
                encoded_data = f.read()
            
            # Clean up whitespace
            encoded_data = encoded_data.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
            
            # Decode base64
            try:
                decoded_data = base64.b64decode(encoded_data)
                log(f"✅ Decoded: {len(encoded_data)} bytes → {len(decoded_data)} bytes")
                
                # Write decoded data to final path
                with open(output_path, 'wb') as f:
                    f.write(decoded_data)
                
                # Remove temp file
                os.remove(temp_path)
                
            except Exception as e:
                log(f"❌ Base64 decode failed: {e}")
                # If decode fails, use original file
                os.rename(temp_path, output_path)
        else:
            # Not base64, just rename
            log("✅ File is binary (not base64)")
            os.rename(temp_path, output_path)
        
        final_size = os.path.getsize(output_path)
        log(f"📁 Final file: {final_size} bytes")
        
        return output_path
        
    except Exception as e:
        log(f"❌ Download failed: {str(e)}")
        # Clean up
        temp_path = str(output_path) + ".temp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def pcm_to_wav(pcm_path, wav_path, sample_rate=SAMPLE_RATE, channels=CHANNELS, bits_per_sample=BITS_PER_SAMPLE):
    """Convert raw PCM to WAV using FFmpeg"""
    try:
        log("🔊 Converting PCM to WAV with FFmpeg...")
        
        # Use FFmpeg to convert
        cmd = [
            'ffmpeg',
            '-f', 's16le',  # signed 16-bit little-endian PCM
            '-ar', str(sample_rate),
            '-ac', str(channels),
            '-i', str(pcm_path),
            '-acodec', 'pcm_s16le',  # PCM codec
            '-y',
            str(wav_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Check output
        if not os.path.exists(wav_path):
            raise Exception("WAV file not created")
        
        wav_size = os.path.getsize(wav_path)
        if wav_size < 1000:
            raise Exception(f"WAV file too small: {wav_size} bytes")
        
        log(f"✅ WAV created: {wav_size} bytes")
        return wav_path
        
    except subprocess.CalledProcessError as e:
        log(f"❌ FFmpeg error: {e.stderr}")
        raise Exception(f"PCM to WAV conversion failed: {e.stderr}")
    except Exception as e:
        log(f"❌ Conversion error: {str(e)}")
        raise


def get_audio_duration(audio_path):
    """Get exact audio duration using FFprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    return duration


def create_video_clip(image_path, audio_path, output_path, duration):
    """Create video clip: static image with audio"""
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
    return output_path


def cleanup_temp_files(scene_dir):
    """Remove temporary files"""
    if scene_dir.exists():
        shutil.rmtree(scene_dir)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    if 'text/html' in request.headers.get('Accept', ''):
        return """
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Shorts Builder API</title>
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
        .status { 
            display: inline-block;
            background: #2ecc71;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
        }
        .endpoint {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .endpoint h3 { color: #667eea; margin-bottom: 10px; }
        .method { 
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }
        .method.get { background: #2ecc71; }
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
        <h1>🎬 YouTube Shorts Builder API</h1>
        <p style="margin: 10px 0 20px 0;">
            <span class="status">✓ RUNNING</span>
        </p>
        
        <div class="endpoint">
            <h3><span class="method">POST</span> /build</h3>
            <p>Build YouTube Shorts video from scenes</p>
            <pre>{
  "title": "My Video",
  "scenes": [
    {
      "image_url": "https://drive.google.com/...",
      "audio_url": "https://drive.google.com/..."
    }
  ]
}</pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /health</h3>
            <p>Health check</p>
        </div>
    </div>
</body>
</html>
        """
    else:
        return jsonify({
            "service": "YouTube Shorts Builder API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "POST /build": "Build video",
                "GET /health": "Health check"
            }
        }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "ffmpeg": shutil.which('ffmpeg') is not None,
        "ffprobe": shutil.which('ffprobe') is not None,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/build', methods=['POST'])
def build_video():
    """Main endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON payload"}), 400
        
        log("=" * 60)
        log("🎬 NEW VIDEO BUILD REQUEST")
        log("=" * 60)
        
        title = data.get('title', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        scenes = data.get('scenes', [])
        
        if not scenes:
            return jsonify({"success": False, "error": "No scenes provided"}), 400
        
        log(f"📝 Title: {title}")
        log(f"📊 Scenes: {len(scenes)}")
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]
        
        video_clips = []
        
        # Process each scene
        for idx, scene in enumerate(scenes, 1):
            log(f"\n{'='*60}")
            log(f"🎬 SCENE {idx}/{len(scenes)}")
            log(f"{'='*60}")
            
            image_url = scene.get('image_url') or scene.get('webViewLink') or scene.get('webContentLink')
            audio_url = scene.get('audio_url') or scene.get('webViewLink') or scene.get('webContentLink')
            
            if not image_url or not audio_url:
                return jsonify({
                    "success": False,
                    "error": f"Scene {idx} missing URLs"
                }), 400
            
            scene_dir = TEMP_DIR / f"scene_{idx}"
            scene_dir.mkdir(exist_ok=True)
            
            image_path = scene_dir / "image.jpg"
            audio_path = scene_dir / "audio.pcm"
            wav_path = scene_dir / "audio.wav"
            clip_path = scene_dir / "clip.mp4"
            
            try:
                # Download
                log("📥 Downloading image...")
                download_file(image_url, image_path)
                
                log("📥 Downloading audio...")
                download_file(audio_url, audio_path)
                
                # Convert audio
                pcm_to_wav(audio_path, wav_path)
                
                # Get duration
                duration = get_audio_duration(wav_path)
                log(f"⏱️  Duration: {duration:.2f}s")
                
                # Create clip
                log("🎥 Creating video clip...")
                create_video_clip(image_path, wav_path, clip_path, duration)
                
                video_clips.append(str(clip_path))
                log(f"✅ Scene {idx} complete!")
                
            except Exception as e:
                log(f"❌ Scene {idx} failed: {str(e)}")
                log(traceback.format_exc())
                return jsonify({
                    "success": False,
                    "error": f"Scene {idx} failed: {str(e)}"
                }), 500
        
        # Concatenate
        log(f"\n{'='*60}")
        log(f"🔗 CONCATENATING {len(video_clips)} CLIPS")
        log(f"{'='*60}")
        
        final_output = OUTPUT_DIR / f"{safe_title}.mp4"
        concatenate_videos(video_clips, str(final_output))
        
        # Cleanup
        log("🧹 Cleaning up...")
        for idx in range(1, len(scenes) + 1):
            cleanup_temp_files(TEMP_DIR / f"scene_{idx}")
        
        file_size_mb = round(final_output.stat().st_size / 1024 / 1024, 2)
        
        log(f"\n{'='*60}")
        log(f"✅ VIDEO COMPLETE!")
        log(f"{'='*60}")
        log(f"📁 Output: {final_output}")
        log(f"📊 Size: {file_size_mb} MB")
        
        return jsonify({
            "success": True,
            "title": title,
            "output_path": str(final_output),
            "scenes_processed": len(scenes),
            "file_size_mb": file_size_mb
        }), 200
        
    except Exception as e:
        log(f"❌ BUILD FAILED: {str(e)}")
        log(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    # Check FFmpeg
    if not shutil.which('ffmpeg'):
        log("⚠️  WARNING: FFmpeg not found!")
    else:
        log("✅ FFmpeg found")
    
    if not shutil.which('ffprobe'):
        log("⚠️  WARNING: FFprobe not found!")
    else:
        log("✅ FFprobe found")
    
    log("=" * 60)
    log("🚀 YouTube Shorts Builder Server v2.0")
    log("=" * 60)
    log(f"📁 Temp: {TEMP_DIR}")
    log(f"📁 Output: {OUTPUT_DIR}")
    log(f"🎵 Format: {SAMPLE_RATE}Hz, {BITS_PER_SAMPLE}-bit, {CHANNELS}ch")
    log("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)