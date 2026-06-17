import os, asyncio, random, requests
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
    vfx
)

from edge_tts import Communicate

# -------------------------
# CONFIG PRO
# -------------------------
RESOLUTION = (1080, 1920)
FPS = 30
DURATION = 4

# -------------------------
# SCRIPT ENGINE (NO REPETITIVO)
# -------------------------
class ScriptGenerator:

    hooks = [
        "La verdad que nadie te dice:",
        "Esto controla tu mente sin que lo notes:",
        "Tu cerebro está siendo manipulado:",
        "Esto influye en cada decisión tuya:",
        "No estás pensando libremente:"
    ]

    topics = [
        "sesgos cognitivos invisibles",
        "psicología de la manipulación",
        "decisiones inconscientes humanas",
        "lenguaje corporal engañoso",
        "técnicas de persuasión modernas"
    ]

    @staticmethod
    def generate():
        hook = random.choice(ScriptGenerator.hooks)
        topic = random.choice(ScriptGenerator.topics)

        scenes = []
        for i in range(5):
            scenes.append({
                "text": f"{hook} {topic}. Punto {i+1}: impacto real en tu comportamiento diario.",
                "image_prompt": f"{topic}, cinematic dark, ultra realistic, dramatic lighting, depth of field, shot {i+1}"
            })

        return {
            "title": hook,
            "description": "Video generado automáticamente con IA",
            "scenes": scenes
        }

# -------------------------
# TTS (EDGE TTS)
# -------------------------
async def synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(synth(text, path))

# -------------------------
# IMAGE GENERATION
# -------------------------
def get_image(prompt, i):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    r = requests.get(url, timeout=60)

    path = f"img_{i}.jpg"
    with open(path, "wb") as f:
        f.write(r.content)

    img = Image.open(path).convert("RGB")
    img = img.resize(RESOLUTION)
    img.save(path)

    return path

# -------------------------
# VIDEO RENDER (PROFESIONAL Y ESTABLE)
# -------------------------
def render_video(scenes):

    clips = []

    for i, scene in enumerate(scenes):
        print(f"🎬 Scene {i+1}")

        # IMAGE
        img_path = get_image(scene["image_prompt"], i)

        # AUDIO
        audio_path = f"audio_{i}.mp3"
        synth_sync(scene["text"], audio_path)
        audio = AudioFileClip(audio_path)

        # CLIP BASE
        clip = ImageClip(img_path).set_duration(audio.duration)

        # 🔥 ZOOM SUAVE PRO (compatibilidad total)
        clip = clip.fx(vfx.resize, lambda t: 1 + 0.03 * t)

        # AUDIO
        clip = clip.set_audio(audio)

        clips.append(clip)

    # CONCAT FINAL
    final = concatenate_videoclips(clips, method="compose")

    # AUDIO MIX GLOBAL
    final_audio = CompositeAudioClip([c.audio for c in clips])
    final = final.set_audio(final_audio)

    # EXPORT FULL HD PRO
    output = "viral_short.mp4"
    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        preset="medium"
    )

    return output

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    print("🚀 Generando vídeo PRO Full HD...")

    script = ScriptGenerator.generate()

    print("🧠 TITLE:", script["title"])

    video = render_video(script["scenes"])

    print("✅ LISTO:", video)
