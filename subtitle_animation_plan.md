# Centered 3-Word Pop-Up Subtitles (Hormozi Style) — Implementation Plan

## Objective
Implement a centered 3-word-at-a-time subtitle style where the active spoken word is large and centered, the previous word appears above it smaller, and the next word appears below it smaller. This runs independently from the standard subtitle mode.

## Layout Breakdown (from screenshots)
```
[Previous Word]   ← small, centered, above
[ACTIVE WORD]     ← BIG, centered, middle
[Next Word]       ← small, centered, below
```
All three words are **center-aligned (`\an5`)**, stacked vertically, with different `\pos(x,y)` offset for each row:
- Previous word: `\pos(540, 840)` (above center)
- Active word: `\pos(540, 960)` (dead center) + `\fscx140\fscy140`
- Next word: `\pos(540, 1080)` (below center)

> [!NOTE]
> Each word triplet generates **3 separate concurrent ASS `Dialogue` events** sharing the exact same Start/End timestamp.

## Proposed Strategy

### 1. Create a Dedicated Subtitle Generator Method
Inside [shorts_builder_app.py](file:///c:/Users/Just%20a%20PC/Desktop/youtube-shorts-builder/shorts_builder_app.py), we will write a brand new isolated function: `generate_diagonal_pop_subtitles()`.

This function will loop through `word_timestamps` exactly like the old function, but for every current word frame, it will explicitly calculate and append up to **3 simultaneous dialogue lines**:

1.  **Previous Word (Context):** 
    - Rendered explicitly at Top-Left: `\pos(350, 750)`
    - Scaled down: `\fscx60\fscy60`
    - Muted color to fade into background context.
2.  **Active Word (Current Spoken):**
    - Rendered explicitly at Dead Center: `\pos(540, 960)`
    - Scaled up aggressively: `\fscx140\fscy140`
    - High-contrast Primary Color (e.g., Bright Yellow/Cyan)
3.  **Next Word (Context):**
    - Rendered explicitly at Bottom-Right: `\pos(730, 1170)`
    - Scaled down: `\fscx60\fscy60`
    - Muted color to match Previous Word.

### 2. Isolate via [retro_config.json](file:///c:/Users/Just%20a%20PC/Desktop/youtube-shorts-builder/retro_config.json) Parameter
To guarantee the old subtitles never break, we will append a new trigger property strictly inside the [retro_config.json](file:///c:/Users/Just%20a%20PC/Desktop/youtube-shorts-builder/retro_config.json) subtitle dictionary.

**Config Example:**
```json
"subtitles": {
   "layout_mode": "diagonal_pop",
   "font_name": "Georgia",
   "font_size_word": 90
}
```

### 3. Implement the Branching Pipeline
During the Subtitles Step in [build_video_n8n_async](file:///c:/Users/Just%20a%20PC/Desktop/youtube-shorts-builder/shorts_builder_app.py#1881-2166), the script will read the config string. If it discovers `diagonal_pop`, it safely diverges the workload to the new generator, otherwise it uses the standard generator natively.

```python
# STEP 6: SUBTITLES (N8N)
if subtitles_enabled and transcribed_words:
    retro_style = RETRO_CONFIG.get("subtitles", {})
    layout = retro_style.get("layout_mode", "standard")
    
    if layout == "diagonal_pop":
        generate_diagonal_pop_subtitles(
            transcribed_words, str(ass_path), style=retro_style
        )
    else:
        # Falls back to old style natively
        generate_word_subtitles(
            transcribed_words, str(ass_path), style=retro_style
        )
```

## Review Status
This architecture is purely additive. [generate_word_subtitles](file:///c:/Users/Just%20a%20PC/Desktop/youtube-shorts-builder/shorts_builder_app.py#932-980) will remain completely untouched, ensuring total stability for your classic engine routes.
