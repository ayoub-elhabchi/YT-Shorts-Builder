import re
from pathlib import Path

shorts_file = Path("c:/Users/Just a PC/Desktop/youtube-shorts-builder/shorts_builder_app.py")
simple_file = Path("c:/Users/Just a PC/Desktop/youtube-shorts-builder/simple_routes_fixed.py")

with open(simple_file, "r", encoding="utf-8") as f:
    simple_content = f.read()

# Extract blocks
def get_block(name, kind="def "):
    pattern = rf"^{kind}{name}\b.*?(?=\n\n(?:def |@app\.\S))"
    match = re.search(pattern, simple_content, re.MULTILINE | re.DOTALL)
    if not match:
        pattern = rf"^{kind}{name}\b.*"
        match = re.search(pattern, simple_content, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else f"# Missing {name}"

load_retro_config = get_block("load_retro_config")
load_default_retro_config = get_block("load_default_retro_config")
get_scene_text_n8n = get_block("get_scene_text_n8n")
expand_scenes_to_frames_n8n = get_block("expand_scenes_to_frames_n8n")
build_video_n8n_async = get_block("build_video_n8n_async")

route1_match = re.search(r'(@app\.route\("/retro/build".*?(?=\n@app\.route|\nif __name__))', simple_content, re.MULTILINE | re.DOTALL)
route1 = route1_match.group(1).strip() if route1_match else "# missing retro/build"

route2_match = re.search(r'(@app\.route\("/retro/status/<job_id>".*?(?=\n@app\.route|\nif __name__))', simple_content, re.MULTILINE | re.DOTALL)
route2 = route2_match.group(1).strip() if route2_match else "# missing retro/status"

# Modify ken burns config usage
build_video_n8n_async = re.sub(
    r'use_ken_burns = data\.get\("ken_burns", RETRO_CONFIG\["video"\].*?\)',
    r'use_ken_burns = RETRO_CONFIG["video"].get("ken_burns_movement", False)',
    build_video_n8n_async
)

# Fix shake effect applying to pil_img
shake_replacement = """                # Apply shake_zoom effect if enabled
                if shake_zoom_enabled and apply_shake_zoom_effect:
                    progress = 0.5  # Mid-point for shake effect
                    raw_img = apply_shake_zoom_effect(
                        raw_img,
                        progress,
                        shake_intensity=shake_intensity,
                        zoom_out_factor=zoom_out_factor
                    )
                    pil_img = apply_shake_zoom_effect(
                        pil_img,
                        progress,
                        shake_intensity=shake_intensity,
                        zoom_out_factor=zoom_out_factor
                    )
"""
build_video_n8n_async = re.sub(
    r'# Apply shake_zoom effect if enabled.*?zoom_out_factor=zoom_out_factor\n\s*\)',
    shake_replacement,
    build_video_n8n_async,
    flags=re.DOTALL
)

retro_chunk = f"""
# ============================================================
# RETRO / N8N LOGIC (MERGED FROM SIMPLE_ROUTES_FIXED)
# ============================================================
RETRO_CONFIG_PATH = Path("./retro_config.json")
RETRO_BGM_DIR = Path("./assets/retro_bgm")

try:
    from effects_shake import apply_shake_zoom_effect
except ImportError:
    apply_shake_zoom_effect = None

{load_default_retro_config}

{load_retro_config}

RETRO_CONFIG = load_retro_config()
RETRO_BGM_DIR.mkdir(parents=True, exist_ok=True)

{get_scene_text_n8n}

{expand_scenes_to_frames_n8n}

{build_video_n8n_async}

{route1}

{route2}

"""

with open(shorts_file, "r", encoding="utf-8") as f:
    shorts_content = f.read()

shorts_content = shorts_content.replace('if __name__ == "__main__":', retro_chunk + '\nif __name__ == "__main__":')

with open(shorts_file, "w", encoding="utf-8") as f:
    f.write(shorts_content)

print("Merge completed successfully!")
