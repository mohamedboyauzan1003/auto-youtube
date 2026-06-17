import os, json, asyncio, random, time, logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests
from moviepy.editor import *
from moviepy.video.fx.all import zoom_in, crossfadein, crossfadeout, fadein, fadeout
from edge_tts import Communicate
import subprocess

# CONFIGURACIÓN INICIAL
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConfigLoader:
    def __init__(self):
        if os.path.exists("config.yaml"):
            # Cargar configuración simple
            self.config = {
                "resolution": (1080, 1920),
                "fps": 30,
                "duration": 4.0,
                "voice_type": "en-US-GuyNeural",
                "bgm_volume": 0.2,
                "subtitle_font_size": 40
            }
        else:
            self.config = {}

cfg = ConfigLoader()

# -------------------------
# GENERADOR DE GUION INTELIGENTE
# -------------------------
class ScriptGenerator:
    hooks = [
        "Lo que nunca te contaron sobre...",
        "La verdad incómoda sobre...",
        "Nunca volverás a ser el mismo después de esto...",
        "El secreto oculto que domina tu vida...",
        "Esto está pasando dentro de tu cerebro ahora mismo..."
    ]
    
    topics = [
        "sesgos cognitivos invisibles",
        "la psicología detrás de las compras impulsivas",
        "el lenguaje corporal que miente por ti",
        "técnicas de persuasión usadas por políticos",
        "cómo se manipulan tus decisiones diarias"
    ]

    @staticmethod
    def generate():
        hook = random.choice(ScriptGenerator.hooks)
        topic = random.choice(ScriptGenerator.topics)
        
        scenes = []
        for i in range(5):
            # Variación aleatoria para evitar repetición
            phrases = [
                f"{topic}. La mayoría ignora esto.",
                f"Tu cerebro actúa así inconscientemente.",
                f"Efecto demostrado en 80% de las personas.",
                f"Influencia subconsciente detectada.",
                f"Sistema psicológico activado."
            ]
            
            scenes.append({
                "text": f"{hook} {random.choice(phrases)}",
                "image_prompt": f"cine dramático, iluminación oscura, realista, hiperdetallado, {topic}, ángulo {i+1}, contraste alto"
            })
        return {"title": f"{hook[:30].strip()}...", "description": "Video generado por IA", "scenes": scenes}

# -------------------------
# VISUALS & IMAGEN
# -------------------------
def apply_zoom(clip):
    """Aplica efecto de Zoom lento estilo documental"""
    return clip.fxaa(zoom_in=1.1).fx(zoom_in, start=1.0, end=1.1, duration=clip.duration/2)

def add_subtitle_clip(text, image_path, font_size=40):
    """Crea un overlay de texto estilo viral"""
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    txt_layer = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(txt_layer)
    
    # Fuente negra con contorno blanco
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    pos = ((width - text_w) // 2, height - text_h - 50)
    
    # Texto blanco brillante con borde negro
    shadow_color = (0, 0, 0, 200)
    fill_color = (255, 255, 255, 255)
    stroke_width = 2
    draw.text(pos, text, font=font, fill=shadow_color, stroke_width=stroke_width)
    draw.text(pos, text, font=font, fill=fill_color, stroke_width=stroke_width)
    
    final_img = Image.alpha_composite(img.convert("RGBA"), txt_layer)
    return ImageClip(nparray(final_img)).set_duration(cfg.config.get("duration", 4))

# -------------------------
# AUDIO Y MÚSICA
# -------------------------
async def synthesize_audio(text, filename):
    tts = Communicate(text, voice="en-US-GuyNeural")
    await tts.save(filename)

def mix_audio(audio_clips, bgm_filename=None):
    """Mezcla voz y música de fondo"""
    if not bgm_filename or not os.path.exists(bgm_filename):
        return audio_clips[-1]
        
    bgm = AudioFileClip(bgm_filename)
    bgm = CompositeAudioClip([b.set_volume_range(cfg.config["bgm_volume"]) for b in [bgm]])
    
    # Ajustar duración BG al clip más largo
    max_dur = max(a.duration for a in audio_clips)
    bgm = bgm.subclipped(start=0, end=max_dur)
    return CompositeAudioClip([c for c in audio_clips] + [bgm])

# -------------------------
# RENDERIZADO FINAL
# -------------------------
def render_video(scenes, output_name="final.mp4"):
    clips = []
    for i, scene in enumerate(scenes):
        print(f"[{i+1}/{len(scenes)}] Renderizando escena...")
        
        # 1. Generar imagen
        prompt = requests.utils.quote(scene["image_prompt"])
        url = f"https://image.pollinations.ai/prompt/{prompt}"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            temp_img = f"/tmp/img_{i}.png"
            with open(temp_img, "wb") as f:
                f.write(resp.content)
            
            # Ajustar tamaño y aplicar zoom si configurado
            img = Image.open(temp_img).resize((1080, 1920))
            img.save(temp_img)
            img_clip = ImageClip(temp_img).set_duration(cfg.config.get("duration", 4))
            img_clip = img_clip.fx(crossfadein, 0.1).fx(crossfadeout, 0.1)
            
            if cfg.config.get("zoom_effect", True):
                img_clip = img_clip.fx(zoom_in, 1.1)

            # 2. Subtítulo
            sub_clip = add_subtitle_clip(scene["text"], temp_img)
            
            # 3. Audio TTS
            audio_file = f"aud_{i}.mp3"
            loop = asyncio.new_event_loop()
            loop.run_until_complete(synthesize_audio(scene["text"], audio_file))
            loop.close()
            audio = AudioFileClip(audio_file).set_duration(sub_clip.duration)
            
            # Ensamblar escena
            final_clip = img_clip.set_audio(audio).add_mask(alpha=sub_clip)
            final_clip = ImageClip(None).subclip(0, sub_clip.duration).set_image(Image.fromarray(sub_clip.to_image()))
            clips.append(final_clip)

    # Mezcla final
    final_audio = CompositeAudioClip([c.audio for c in clips])
    
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_fps(30).set_audio(final_audio)
    
    final_video.write_videofile(output_name, codec="libx264", audio_codec="aac", preset="slow")
    
    # Limpieza
    for f in [temp_img, audio_file]:
        try: os.remove(f)
        except: pass
        
    return output_name

# -------------------------
# MAIN EXECUTION
# -------------------------
if __name__ == "__main__":
    print("🚀 Iniciando Sistema Video Viral PRO...")
    
    # 1. Generar Script
    script = ScriptGenerator.generate()
    print(f"📝 Guion: {script['title']}")
    
    # 2. Renderizar
    output = render_video(script["scenes"], "viral_short.mp4")
    print(f"✅ Vídeo terminado: {output}")
    
    # 3. (Opcional) Upload a YouTube requeriría integrar API Keys en variables de entorno
    # upload_to_youtube(output, script)
