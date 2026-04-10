import re
from pathlib import Path

shorts_file = Path("c:/Users/Just a PC/Desktop/youtube-shorts-builder/shorts_builder_app.py")
trans_file = Path("c:/Users/Just a PC/Desktop/youtube-shorts-builder/transitions.py")

with open(shorts_file, "r", encoding="utf-8") as f:
    sh = f.read()

# 1. Trigger shake_zoom advanced path
sh = re.sub(
    r'if transition_effect != "none" or use_ken_burns:\n\s*log\(f"\\n>>> \[N8N\] STEP 4: BUILD ADVANCED PATH"\)\n\s*# Check if shake_zoom effect is enabled\n\s*shake_zoom_enabled = RETRO_CONFIG\["video"\]\["effects"\]\["shake_zoom"\]\["enabled"\]\n\s*shake_intensity = RETRO_CONFIG\["video"\]\["effects"\]\["shake_zoom"\]\["shake_intensity"\]\n\s*zoom_out_factor = RETRO_CONFIG\["video"\]\["effects"\]\["shake_zoom"\]\["zoom_out_factor"\]\n\s*scenes_data = \[\]',
    '''shake_cfg = RETRO_CONFIG["video"].get("effects", {}).get("shake_zoom", {})
        shake_zoom_enabled = shake_cfg.get("enabled", False)

        if transition_effect != "none" or use_ken_burns or shake_zoom_enabled:
            log(f"\\n>>> [N8N] STEP 4: BUILD ADVANCED PATH")
            
            shake_intensity = shake_cfg.get("shake_intensity", 0.5)
            zoom_out_factor = shake_cfg.get("zoom_out_factor", 1.1)

            scenes_data = []''',
    sh, flags=re.MULTILINE
)

# 2. Remove static python shake_zoom from the loop
sh = re.sub(
    r'# Apply shake_zoom effect if enabled\n\s*if shake_zoom_enabled and apply_shake_zoom_effect:\n\s*progress = 0\.5  # Mid-point for shake effect\n\s*raw_img = apply_shake_zoom_effect\(\n\s*raw_img,\n\s*progress,\n\s*shake_intensity=shake_intensity,\n\s*zoom_out_factor=zoom_out_factor\n\s*\)\n\s*pil_img = apply_shake_zoom_effect\(\n\s*pil_img,\n\s*progress,\n\s*shake_intensity=shake_intensity,\n\s*zoom_out_factor=zoom_out_factor\n\s*\)\n\s*requested_fx = frame\.get\("ken_burns_effect"\)',
    'raw_img = Image.open(image_path).convert("RGB")\n                \n                requested_fx = frame.get("ken_burns_effect")',
    sh, flags=re.MULTILINE
)

# 3. Add shake_effect configuration back to scenes_data dict
sh = re.sub(
    r'"transition_duration": scene_dur,\n\s*\}\)',
    '"transition_duration": scene_dur,\n                    "shake_effect": shake_cfg if shake_zoom_enabled else None,\n                })',
    sh, flags=re.MULTILINE
)

with open(shorts_file, "w", encoding="utf-8") as f:
    f.write(sh)

with open(trans_file, "r", encoding="utf-8") as f:
    tr = f.read()

# Modify transitions.py to import apply_shake_zoom_effect
if "apply_shake_zoom_effect" not in tr:
    tr = tr.replace('from effects import apply_ken_burns', 'from effects import apply_ken_burns\n    from effects_shake import apply_shake_zoom_effect')

# Dynamically apply shake during blending:
kb1 = """if scenes_data[bi].get('kb_effect'):
                        p_out = (t - scenes_data[bi]['start']) / max(0.1, scenes_data[bi]['end'] - scenes_data[bi]['start'])
                        img_out = apply_ken_burns(scenes_data[bi]['raw_image'], max(0.0, min(1.0, p_out)), scenes_data[bi]['kb_effect'], width, height)"""
shk1 = """if scenes_data[bi].get('kb_effect'):
                        p_out = (t - scenes_data[bi]['start']) / max(0.1, scenes_data[bi]['end'] - scenes_data[bi]['start'])
                        img_out = apply_ken_burns(scenes_data[bi]['raw_image'], max(0.0, min(1.0, p_out)), scenes_data[bi]['kb_effect'], width, height)
                    elif scenes_data[bi].get('shake_effect'):
                        p_out = (t - scenes_data[bi]['start']) / max(0.1, scenes_data[bi]['end'] - scenes_data[bi]['start'])
                        shk = scenes_data[bi]['shake_effect']
                        img_out = apply_shake_zoom_effect(scenes_data[bi]['raw_image'], max(0.0, min(1.0, p_out)), shk.get("shake_intensity", 0.5), shk.get("zoom_out_factor", 1.1), width, height)"""
tr = tr.replace(kb1, shk1)

kb2 = """if scenes_data[bi + 1].get('kb_effect'):
                        p_in = (t - scenes_data[bi + 1]['start']) / max(0.1, scenes_data[bi + 1]['end'] - scenes_data[bi + 1]['start'])
                        img_in = apply_ken_burns(scenes_data[bi + 1]['raw_image'], max(0.0, min(1.0, p_in)), scenes_data[bi + 1]['kb_effect'], width, height)"""
shk2 = """if scenes_data[bi + 1].get('kb_effect'):
                        p_in = (t - scenes_data[bi + 1]['start']) / max(0.1, scenes_data[bi + 1]['end'] - scenes_data[bi + 1]['start'])
                        img_in = apply_ken_burns(scenes_data[bi + 1]['raw_image'], max(0.0, min(1.0, p_in)), scenes_data[bi + 1]['kb_effect'], width, height)
                    elif scenes_data[bi + 1].get('shake_effect'):
                        p_in = (t - scenes_data[bi + 1]['start']) / max(0.1, scenes_data[bi + 1]['end'] - scenes_data[bi + 1]['start'])
                        shk = scenes_data[bi + 1]['shake_effect']
                        img_in = apply_shake_zoom_effect(scenes_data[bi + 1]['raw_image'], max(0.0, min(1.0, p_in)), shk.get("shake_intensity", 0.5), shk.get("zoom_out_factor", 1.1), width, height)"""
tr = tr.replace(kb2, shk2)

kb3 = """if scenes_data[0].get('kb_effect'):
                        s_prog = (t - scenes_data[0]['start']) / max(0.1, scenes_data[0]['end'] - scenes_data[0]['start'])
                        img_target = apply_ken_burns(scenes_data[0]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[0]['kb_effect'], width, height)"""
shk3 = """if scenes_data[0].get('kb_effect'):
                        s_prog = (t - scenes_data[0]['start']) / max(0.1, scenes_data[0]['end'] - scenes_data[0]['start'])
                        img_target = apply_ken_burns(scenes_data[0]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[0]['kb_effect'], width, height)
                    elif scenes_data[0].get('shake_effect'):
                        s_prog = (t - scenes_data[0]['start']) / max(0.1, scenes_data[0]['end'] - scenes_data[0]['start'])
                        shk = scenes_data[0]['shake_effect']
                        img_target = apply_shake_zoom_effect(scenes_data[0]['raw_image'], max(0.0, min(1.0, s_prog)), shk.get("shake_intensity", 0.5), shk.get("zoom_out_factor", 1.1), width, height)"""
tr = tr.replace(kb3, shk3)

kb4 = """if scenes_data[-1].get('kb_effect'):
                        s_prog = (t - scenes_data[-1]['start']) / max(0.1, scenes_data[-1]['end'] - scenes_data[-1]['start'])
                        img_source = apply_ken_burns(scenes_data[-1]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[-1]['kb_effect'], width, height)"""
shk4 = """if scenes_data[-1].get('kb_effect'):
                        s_prog = (t - scenes_data[-1]['start']) / max(0.1, scenes_data[-1]['end'] - scenes_data[-1]['start'])
                        img_source = apply_ken_burns(scenes_data[-1]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[-1]['kb_effect'], width, height)
                    elif scenes_data[-1].get('shake_effect'):
                        s_prog = (t - scenes_data[-1]['start']) / max(0.1, scenes_data[-1]['end'] - scenes_data[-1]['start'])
                        shk = scenes_data[-1]['shake_effect']
                        img_source = apply_shake_zoom_effect(scenes_data[-1]['raw_image'], max(0.0, min(1.0, s_prog)), shk.get("shake_intensity", 0.5), shk.get("zoom_out_factor", 1.1), width, height)"""
tr = tr.replace(kb4, shk4)

kb5 = """if scenes_data[si].get('kb_effect'):
                        # --- GENERATE KEN BURNS FRAME ON THE FLY ---
                        s_prog = (t - scenes_data[si]['start']) / max(0.1, scenes_data[si]['end'] - scenes_data[si]['start'])
                        frame = apply_ken_burns(scenes_data[si]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[si]['kb_effect'], width, height)
                        process.stdin.write(frame.tobytes())
                    else:"""
shk5 = """if scenes_data[si].get('kb_effect'):
                        # --- GENERATE KEN BURNS FRAME ON THE FLY ---
                        s_prog = (t - scenes_data[si]['start']) / max(0.1, scenes_data[si]['end'] - scenes_data[si]['start'])
                        frame = apply_ken_burns(scenes_data[si]['raw_image'], max(0.0, min(1.0, s_prog)), scenes_data[si]['kb_effect'], width, height)
                        process.stdin.write(frame.tobytes())
                    elif scenes_data[si].get('shake_effect'):
                        # --- GENERATE SHAKE FRAME ON THE FLY ---
                        s_prog = (t - scenes_data[si]['start']) / max(0.1, scenes_data[si]['end'] - scenes_data[si]['start'])
                        shk = scenes_data[si]['shake_effect']
                        frame = apply_shake_zoom_effect(scenes_data[si]['raw_image'], max(0.0, min(1.0, s_prog)), shk.get("shake_intensity", 0.5), shk.get("zoom_out_factor", 1.1), width, height)
                        process.stdin.write(frame.tobytes())
                    else:"""
tr = tr.replace(kb5, shk5)

with open(trans_file, "w", encoding="utf-8") as f:
    f.write(tr)
print("done")
