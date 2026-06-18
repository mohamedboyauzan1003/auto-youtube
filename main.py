import os
import asyncio
import random
import requests
import numpy as np
import textwrap
import json
import time
import wave
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

# Mantener compatibilidad con versiones modernas de Pillow
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate
from concurrent.futures import ThreadPoolExecutor

# Importaciones de Google API para la subida automática
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle

# Configuración de Lienzo Vertical Estándar (Shorts/Reels)
W, H = 1080, 1920
FPS = 30

# ═══════════════════════════════════════════════════════════
#  1. GENERACIÓN DE GUIONES (GROQ) CON REINTENTOS
# ═══════════════════════════════════════════════════════════
def generate_script():
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("⚠ GROQ_API_KEY no detectada. Usando guion de respaldo.")
        return fallback_script()

    topics = [
        "manipulation tactics people use daily",
        "dark cognitive biases controlling your decisions",
        "subconscious mind tricks you never knew about",
        "body language secrets manipulators exploit",
        "dark truths about human nature nobody says",
    ]
    topic = random.choice(topics)
    print(f"🧠 Generando guión en Groq para el tema: {topic}")

    prompt = f"""You are an educational psychology scriptwriter.
Write about: {topic}
Rules:
- Each scene text: max 12 words, dramatic, with "..." pauses
- Each image prompt: vivid dark art scene, very specific, unique per scene
- Title: under 60 chars, no emojis

Return ONLY this raw JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["psychology","mindset","facts","awareness"],
  "scenes": [
    {{"text": "...", "prompt": "dark style art, [unique specific scene], dramatic chiaroscuro, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark style art, [unique specific scene], moody atmosphere, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark style art, [unique specific scene], cinematic, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark style art, [unique specific scene], epic scale, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark style art, [unique epic final scene], blazing light breaking darkness, ultra detailed, 8k, no text"}}
  ]
}}"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1500,
    }

    for attempt in range(3):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"⏳ Rate limit en Groq. Esperando {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                break
            
            raw = r.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("
```", "").strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]
            return json.loads(raw)
        except Exception as e:
            print(f"⚠ Intento Groq {attempt+1} fallido: {e}")
            time.sleep(5)

    return fallback_script()

def fallback_script():
    return {
        "title": "Your Brain Deceives You Every Single Day",
        "description": "The hidden lies your brain tells you.",
        "tags": ["brain","psychology","facts"],
        "scenes": [
            {"text": "Your brain filters 99 percent of reality... to protect you.", "prompt": "dark art style, glowing human brain suspended in cosmic void, ultra detailed 8k"},
            {"text": "Confirmation bias... traps you in a prison of false beliefs.", "prompt": "dark art style, massive eye with narrow tunnel vision, ultra detailed 8k"},
            {"text": "Your memories are fiction... rewritten every time you recall them.", "prompt": "dark art style, antique film reel melting into darkness, ultra detailed 8k"},
            {"text": "The less you know... the more confident your brain feels.", "prompt": "dark art style, figure standing triumphantly at a peak, ultra detailed 8k"},
            {"text": "See the lies clearly... and your mind becomes truly free.", "prompt": "dark art style, figure breaking mental chains into pure light, ultra detailed 8k"},
        ],
    }

# ═══════════════════════════════════════════════════════════
#  2. GENERACIÓN DE IMÁGENES (POLLINATIONS) + POST-PROCESO
# ═══════════════════════════════════════════════════════════
ANIME_STYLES = ["attack on titan dark cinematic anime", "jujutsu kaisen dark aesthetic", "dark fantasy anime illustration"]

def generate_image(prompt, index):
    style = random.choice(ANIME_STYLES)
    seed = int(time.time()) * (index+1) + random.randint(10000, 99999)
    full_prompt = f"{style}, {prompt}, masterpiece, best quality, ultra detailed, 8k, no text, vertical composition"

    for model in ["flux", "flux-realism", "turbo"]:
        try:
            encoded = requests.utils.quote(full_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={seed}&model={model}&nologo=true&enhance=true"
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and len(r.content) > 15000:
                path = f"img_{index}.jpg"
                with open(path, "wb") as f:
                    f.write(r.content)
                
                # Post-procesado estético cinematográfico
                img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
                img = ImageEnhance.Contrast(img).enhance(1.2)
                img = ImageEnhance.Sharpness(img).enhance(1.5)
                img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
                img.save(path, quality=98, optimize=True)
                return path
        except Exception as e:
            print(f"⚠ Fallo con modelo {model} en imagen {index}: {e}")
        time.sleep(2)

    # Fallback si falla la API de imagen
    img = Image.new("RGB", (W, H), (15, 5, 25))
    path = f"img_{index}.jpg"
    img.save(path)
    return path

# ═══════════════════════════════════════════════════════════
#  3. EFECTOS VISUALES Y DISEÑO DE SUBTÍTULOS
# ═══════════════════════════════════════════════════════════
def add_vignette(img):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    steps = min(w, h) // 2
    for i in range(steps):
        alpha = int(255 * (i / steps) ** 0.55)
        draw.ellipse([i, i, w-i, h-i], fill=alpha)
    return Image.composite(img, Image.new("RGB", (w, h), (0,0,0)), mask)

def glitch_frame(arr, intensity=4):
    img = arr.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0, h-10)
        shift = random.randint(-12, 12)
        sh = random.randint(2, 8)
        strip = img[y:y+sh, :].copy()
        if 0 < shift < w:
            img[y:y+sh, shift:] = strip[:, :-shift]
        elif -w < shift < 0:
            img[y:y+sh, :shift] = strip[:, -shift:]
    s = random.randint(2, 5)
    img[:,:,0] = np.roll(img[:,:,0], s, axis=1)
    img[:,:,2] = np.roll(img[:,:,2], -s, axis=1)
    return img

def get_fonts():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, 76), ImageFont.truetype(fp, 40)
    d = ImageFont.load_default()
    return d, d

def render_text_frame(base_arr, text, char_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    font_big, font_label = get_fonts()

    # Barra roja superior estética
    bar_y = 90
    draw.rectangle([(50, bar_y),(w-50, bar_y+8)], fill=(220,15,15,255))

    # Efecto máquina de escribir en subtítulos
    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=15)
    text_y = bar_y + 28

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font_big)
        tw = bbox[2]-bbox[0]
        x = (w-tw)//2
        y = text_y + i*95
        draw.text((x+3,y+3), line, font=font_big, fill=(0,0,0,200)) # Sombra
        draw.text((x,y), line, font=font_big, fill=(255,255,255,255))

    return np.array(img.convert("RGB"))

def zoom_frame(base_img, t, duration):
    zoom = 1.0 + 0.07*(t/duration)
    w, h = base_img.size
    nw, nh = int(w/zoom), int(h/zoom)
    left = (w-nw)//2
    top = (h-nh)//2
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)

# ═══════════════════════════════════════════════════════════
#  4. SÍNTESIS DE AUDIO (VOZ Y MÚSICA DE FONDO)
# ═══════════════════════════════════════════════════════════
async def _synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-10%", pitch="-12Hz", volume="+30%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(_synth(text, path))

def generate_music(duration=120):
    sr = 44100
    t = np.linspace(0, duration, int(sr*duration), dtype=np.float32)
    music = 0.25 * np.sin(2*np.pi*43.65*t) # Tono oscuro de fondo (F1)
    pulse = 0.5 + 0.5*np.sin(2*np.pi*0.08*t)
    music *= pulse
    audio_int = (music*32767).astype(np.int16)
    wav_path = "bg_ambient_music.wav"
    with wave.open(wav_path,"w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int.tobytes())
    return wav_path

# ═══════════════════════════════════════════════════════════
#  5. COMPOSICIÓN MULTIMEDIA Y MONTAJE CON MOVIEPY
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 0.8
    total_frames = int(duration * FPS)
    reveal_frames = int(FPS * 1.5)

    frames = []
    for f in range(total_frames):
        t = f / FPS
        zoomed = zoom_frame(base_img, t, duration)
        cp = min(len(text), int(len(text)*(f/reveal_frames))) if f < reveal_frames else len(text)
        frame = render_text_frame(np.array(zoomed), text, cp, f, scene_idx, total_scenes)
        if f < 5: # Glitch inicial de transición
            frame = glitch_frame(frame, intensity=4)
        frames.append(frame.astype(np.uint8))

    clip = VideoClip(lambda t: frames[min(int(t*FPS), len(frames)-1)], duration=duration)
    return clip.set_audio(audio)

def build_video(scenes):
    total = len(scenes)
    print("🎨 Descargando imágenes y voces en paralelo...")
    
    with ThreadPoolExecutor(max_workers=3) as ex:
        img_results = list(ex.map(lambda x: (x[0], generate_image(x[1]["prompt"], x[0])), enumerate(scenes)))
    img_paths = {i:p for i,p in img_results}

    with ThreadPoolExecutor(max_workers=3) as ex:
        ex.map(lambda x: synth_sync(x[1]["text"], f"audio_{x[0]}.mp3"), enumerate(scenes))

    clips = []
    for i, scene in enumerate(scenes):
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clips.append(build_scene(base_img, f"audio_{i}.mp3", scene["text"], i, total))

    final = concatenate_videoclips(clips, method="compose")
    
    music_path = generate_music(duration=int(final.duration)+5)
    music = AudioFileClip(music_path).subclip(0, final.duration).volumex(0.12)
    final = final.set_audio(CompositeAudioClip([final.audio, music]))

    output = "final_short.mp4"
    final.write_videofile(output, fps=FPS, codec="libx264", audio_codec="aac", bitrate="8000k", preset="superfast", logger=None)
    return output

# ═══════════════════════════════════════════════════════════
#  6. AUTOMATIZACIÓN DE SUBIDA A YOUTUBE SHORTS
# ═══════════════════════════════════════════════════════════
def upload_to_youtube(video_path, metadata):
    print("🚀 Iniciando proceso de subida automática a YouTube...")
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                raise FileNotFoundError("❌ Falta 'client_secrets.json'. Consíguelo en Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.load(token) if False else pickle.dump(creds, token)

    youtube = build('youtube', 'v3', credentials=creds)

    title = metadata.get("title", "Psychology Fact")
    if "#shorts" not in title.lower():
        title = f"{title[:50]} #shorts"

    body = {
        'snippet': {
            'title': title,
            'description': metadata.get("description", "") + "\n\n#shorts #psychology #mindset",
            'tags': metadata.get("tags", ["shorts", "psychology"]),
            'categoryId': '27' # Categoría: Educación
        },
        'status': {
            'privacyStatus': 'public', # Cambiar a 'unlisted' o 'private' si quieres revisar antes
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

    print(f"📦 Subiendo '{title}'...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   -> Progreso: {int(status.progress() * 100)}%")
    
    print(f"🎉 ¡Vídeo subido con éxito! ID del vídeo: {response['id']}")
    return response['id']

# ═══════════════════════════════════════════════════════════
#  7. BLOQUE DE ORQUESTACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🤖 === INICIANDO PIPELINE TOTALMENTE AUTOMATIZADO ===")
    
    # Paso 1: Generar Guión Inteligente
    script = generate_script()
    print(f"📝 Guión listo: {script['title']}")
    
    # Paso 2: Crear el Archivo de Video Completo
    video_file = build_video(script["scenes"])
    print(f"✅ Video renderizado con éxito en: {video_file}")
    
    # Paso 3: Subir a YouTube Directamente
    try:
        upload_to_youtube(video_file, script)
    except Exception as e:
        print(f"❌ Error crítico al intentar subir a YouTube: {e}")
        print("💾 El vídeo se ha guardado localmente en 'final_short.mp4' para que no lo pierdas.")
