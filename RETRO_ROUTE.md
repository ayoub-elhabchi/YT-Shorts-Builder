# N8N AI Workflow Route

## Overview

A new isolated route has been added to `shorts_builder_app.py` for n8n AI workflows. This route accepts scenes with **1-5 frames per scene** (flexible, won't crash), uses music and transitions, but **NO overlays**.

## Endpoint

**POST** `/n8n/build`

## Input Schema

```json
{
  "title": "My Video Title",
  "full_audio_url": "https://example.com/audio.mp3",
  "scenes": [
    {
      "index": 1,
      "transition": "zoom",
      "frames": [
        {
          "frame": "A",
          "voice_text": "First text",
          "visual_prompt": "Image description",
          "image_url": "https://example.com/image1.jpg"
        },
        {
          "frame": "B",
          "voice_text": "Second text",
          "visual_prompt": "Image description",
          "image_url": "https://example.com/image2.jpg"
        }
      ]
    }
  ],
  "subtitles": true,
  "subtitle_style": "word_by_word",
  "transition": "fade",
  "transition_duration": 0.5,
  "add_bgm": true,
  "bgm_volume": 0.2,
  "ken_burns": true,
  "webhook_url": "https://your-webhook-url.com/notify",
  "base_url": "https://your-server.com"
}
```

## Validation Rules

- `full_audio_url`: Required
- `scenes`: Required, non-empty array
- Each scene must have `frames` array with 1-5 frames
- Each frame must have `voice_text` and `image_url`

## Response

```json
{
  "job_id": "uuid-string",
  "status": "queued",
  "message": "Video build started"
}
```

## Check Status

**GET** `/n8n/status/<job_id>`

## Features

| Feature | Supported |
|---------|-----------|
| Flexible frames (1-5 per scene) | ✅ |
| Music (BGM) | ✅ |
| Transitions | ✅ |
| Ken Burns effects | ✅ |
| Subtitles | ✅ |
| Overlays | ❌ No |
| Evidence cards | ❌ No |

## Example Usage

```bash
curl -X POST http://localhost:5000/n8n/build \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Video",
    "full_audio_url": "https://example.com/audio.mp3",
    "scenes": [
      {
        "index": 1,
        "transition": "zoom",
        "frames": [
          {
            "frame": "A",
            "voice_text": "Broke is a habit.",
            "visual_prompt": "1970s vintage comic",
            "image_url": "https://example.com/1.jpg"
          },
          {
            "frame": "B",
            "voice_text": "Wealth is a decision.",
            "visual_prompt": "1970s vintage comic",
            "image_url": "https://example.com/2.jpg"
          },
          {
            "frame": "C",
            "voice_text": "Quitting chooses poverty.",
            "visual_prompt": "1970s vintage comic",
            "image_url": "https://example.com/3.jpg"
          }
        ]
      }
    ],
    "subtitles": true,
    "add_bgm": true,
    "bgm_volume": 0.2,
    "transition": "fade",
    "transition_duration": 0.5,
    "ken_burns": true
  }'
```

## Differences from Main `/build` Route

| Feature | `/build` | `/n8n/build` |
|---------|----------|--------------|
| Frames per scene | Fixed 2 | 1-5 (flexible) |
| Overlays | ✅ Yes | ❌ No |
| Evidence cards | ✅ Yes | ❌ No |
| Input format | Legacy | New schema with frames array |
