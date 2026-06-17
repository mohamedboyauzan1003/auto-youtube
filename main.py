import os, asyncio, random, requests, numpy as np, textwrap, json, time, wave, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate
from concurrent.futures import ThreadPoolExecutor

W, H = 1080, 1920
FPS = 30

# ═══════════════════════════════════════════════════════════════════
#  GEMINI — Script Generator con retry automático
# ═══════════════════════════════════════════════════════════════════
def generate_script_with_gemini():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    topics = [
        "manipulation tactics people use daily",
        "dark cognitive biases that control your decisions",
        "subconscious mind tricks you do not know about",
        "body language secrets manipulators use",
        "dark persuasion techniques used in advertising",
        "psychological reasons you cannot say no",
        "signs someone is gaslighting you",
        "how your ego blinds you from the truth",
        "dark truths about human nature nobody talks about",
        "hidden reasons people self sabotage",
        "psychological tricks used by narcissists",
        "how fear controls every decision you make",
        "the dark side of social media on your brain",
        "why your brain is wired for negativity",
        "psychological power moves used by leaders",
        "why people stay in toxic relationships",
        "how childhood trauma shapes adult behavior",
        "dark secrets of the most persuasive people",
        "why your brain craves drama and conflict",
        "how dopamine is used to control you",
    ]
    topic = random.choice(topics)
    print(f"  Topic: {topic}")

    prompt = f"""You are a viral YouTube Shorts scriptwriter for dark psychology content.
Create a script about: {topic}

IMPORTANT: Return ONLY raw JSON. No markdown. No backticks. No explanation. Just the JSON object.

{{
  "title": "catchy title under 60 characters no emojis",
  "description": "compelling description under 150 characters",
  "tags": ["darkpsychology","psychology","mindcontrol","manipulation","shorts","brain","mindset","facts","awareness","secrets"],
  "scenes": [
    {{"text": "short dramatic sentence max 12 words dark tone with pauses marked by ...", "prompt": "masterpiece best quality dark anime cinematic, specific unique detailed scene, dramatic chiaroscuro lighting, ultra detailed 8k"}},
    {{"text": "short dramatic sentence max 12 words dark tone with pauses marked by ...", "prompt": "masterpiece best quality dark anime cinematic, specific unique detailed scene different from scene 1, dramatic lighting, ultra detailed 8k"}},
    {{"text": "short dramatic sentence max 12 words dark tone with pauses marked by ...", "prompt": "masterpiece best quality dark anime cinematic, specific unique detailed scene, moody atmosphere, ultra detailed 8k"}},
    {{"text": "short dramatic sentence max 12 words dark tone with pauses marked by ...", "prompt": "masterpiece best quality dark anime cinematic, specific unique detailed scene, epic scale, ultra detailed 8k"}},
    {{"text": "short dramatic sentence max 12 words dark tone with pauses marked by ...", "prompt": "masterpiece best quality dark anime cinematic, epic final scene powerful emotion, blazing dramatic lighting, ultra detailed 8k"}}
  ]
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1500},
    }

    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=30)
            print(f"  Gemini status: {r.status_code}")
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"  Rate limit — waiting {wait}s...")
                time.sleep(wait)
                continue
            data = r.json()
            if "candidates" not in data:
                print(f"  Gemini error: {json.dumps(data)[:200]}")
                break
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            script = json.loads(raw)
            print(f"  Gemini OK: {script['title']}")
            return script
        except Exception as e:
            print(f"  Gemini attempt {attempt+1} error: {e}")
            time.sleep(5)

    print("  Using fallback script.")
    return get_fallback_script()


def get_fallback_script():
    scripts = [
        {
            "title": "3 Dark Psychology Tricks Used Against You Daily",
            "description": "The hidden manipulation tactics used on you every single day.",
            "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
            "scenes": [
                {"text": "Someone manipulates your decisions... every single day.", "prompt": "masterpiece best quality dark anime, shadowy puppet master controlling human silhouette, crimson black dramatic lighting, ultra detailed 8k"},
                {"text": "Foot-in-the-door... makes you agree to anything.", "prompt": "masterpiece best quality dark anime, massive ominous door opening into endless void, eerie crimson glow, ultra detailed 8k"},
                {"text": "Scarcity triggers panic... bypassing all rational thought.", "prompt": "masterpiece best quality dark anime, cracked hourglass with crimson sand, dramatic chiaroscuro lighting, ultra detailed 8k"},
                {"text": "Social proof hijacks your mind... without you knowing.", "prompt": "masterpiece best quality dark anime, crowd of shadowy identical figures one glowing different, ultra detailed 8k"},
                {"text": "Now you know these tricks... protect your mind forever.", "prompt": "masterpiece best quality dark anime, lone warrior breaking free from dark chains into blazing golden light, epic scale, ultra detailed 8k"},
            ],
        },
        {
            "title": "Signs Someone Is Secretly Manipulating You",
            "description": "Subtle signs that reveal when dark psychology is being used against you.",
            "tags": ["manipulation","darkpsychology","toxicpeople","mindcontrol","psychology","awareness","shorts","mentalhealth","brain","secrets"],
            "scenes": [
                {"text": "They make you feel guilty... for things not your fault.", "prompt": "masterpiece best quality dark anime, figure crushed under invisible dark weight, crimson energy, ultra detailed 8k"},
                {"text": "They isolate you slowly... until you depend on them.", "prompt": "masterpiece best quality dark anime, person trapped in glass sphere surrounded by endless darkness, ultra detailed 8k"},
                {"text": "Gaslighting makes you question... your own sanity.", "prompt": "masterpiece best quality dark anime, shattered mirror distorted reflection blood red violet glow, ultra detailed 8k"},
                {"text": "Love bombing first... then silence as punishment.", "prompt": "masterpiece best quality dark anime, roses transforming into black thorns dramatic contrast dark background, ultra detailed 8k"},
                {"text": "Recognizing these signs... is how you reclaim your power.", "prompt": "masterpiece best quality dark anime, figure rising from darkness into brilliant golden light, epic cinematic, ultra detailed 8k"},
            ],
        },
        {
            "title": "Your Brain Lies To You Every Single Day",
            "description": "Your brain is not as honest as you think. Here is what it hides.",
            "tags": ["brain","psychology","mindcontrol","darkpsychology","facts","shorts","mindset","consciousness","awareness","secrets"],
            "scenes": [
                {"text": "Your brain filters 99 percent of reality... to protect you.", "prompt": "masterpiece best quality dark anime, glowing human brain floating in cosmic space electric synapses, ultra detailed 8k"},
                {"text": "Confirmation bias... makes you see only what you believe.", "prompt": "masterpiece best quality dark anime, single eye extreme tunnel vision shadowy distorted world outside, ultra detailed 8k"},
                {"text": "Your memories are not recordings... your brain rewrites them.", "prompt": "masterpiece best quality dark anime, film reel melting distorting into darkness surreal, ultra detailed 8k"},
                {"text": "Dunning-Kruger... makes the least skilled feel most confident.", "prompt": "masterpiece best quality dark anime, figure standing on narrow peak unaware of void below, ultra detailed 8k"},
                {"text": "Know your brain's lies... and you unlock true clarity.", "prompt": "masterpiece best quality dark anime, mind shattering chains cosmos exploding into enlightened light, ultra detailed 8k"},
            ],
        },
    ]
    return random.choice(scripts)


# ═══════════════════════════════════════════════════════════════════
#  IMAGE GENERATION — Pollinations HD + retry + parallel ready
# ═══════════════════════════════════════════════════════════════════

ANIME_STYLES = [
    "makoto shinkai anime style",
    "studio mappa dark anime",
    "demon slayer anime art style",
    "attack on titan cinematic anime",
    "jujutsu kaisen dark aesthetic anime",
    "dark fantasy anime art",
    "cinematic anime illustration",
]

def build_image_prompt(raw_prompt):
    style = random.choice(ANIME_STYLES)
    return (
        f"{style}, {raw_prompt}, "
        f"masterpiece, best quality, ultra detailed, 8k, "
        f"dramatic cinematic lighting, deep shadows, "
        f"no watermark, no text, no logo, no signature, "
        f"vertical composition, portrait format"
    )

def generate_image(prompt, index):
    print(f"  Generating image {index+1}...")
    full_prompt = build_image_prompt(prompt)

    # 3 intentos con seeds distintas
    for attempt in range(3):
        path = try_pollinations(full_prompt, index, attempt)
        if path:
            return path
        time.sleep(3)

    # Fallback oscuro con degradado
    return make_dark_gradient(index)


def try_pollinations(full_prompt, index, attempt=0):
    try:
        seed = int(time.time()) + index * 7919 + attempt * 1337 + random.randint(0, 9999)
        encoded = requests.utils.quote(full_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1080&height=1920&seed={seed}"
            f"&model=flux&nologo=true&enhance=true"
        )
        r = requests.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 10000:
            path = f"img_{index}.jpg"
            with open(path, "wb") as f:
                f.write(r.content)
            img = Image.open(path).convert("RGB")
            img = img.resize((W, H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.25)
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Color(img).enhance(1.15)
            img.save(path, quality=97)
            print(f"  Pollinations OK (attempt {attempt+1})")
            return path
    except Exception as e:
        print(f"  Pollinations error attempt {attempt+1}: {e}")
    return None


def make_dark_gradient(index):
    img = Image.new("RGB", (W, H), (5, 2, 12))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / H
        r = int(5 + 30 * ratio)
        g = int(2 + 5 * ratio)
        b = int(12 + 40 * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    path = f"img_{index}.jpg"
    img.save(path)
    return path


# ═══════════════════════════════════════════════════════════════════
#  VIGNETTE
# ═══════════════════════════════════════════════════════════════════
def add_vignette(img):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    steps = min(w, h) // 2
    for i in range(steps):
        alpha = int(255 * (i / steps) ** 0.5)
        draw.ellipse([i, i, w - i, h - i], fill=alpha)
    vignette = Image.composite(img, Image.new("RGB", (w, h), (0, 0, 0)), mask)
    return vignette


# ═══════════════════════════════════════════════════════════════════
#  GLITCH
# ═══════════════════════════════════════════════════════════════════
def glitch_frame(img_array, intensity=3):
    img = img_array.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0, h - 10)
        shift = random.randint(-10, 10)
        strip_h = random.randint(2, 8)
        strip = img[y : y + strip_h, :].copy()
        if shift > 0 and shift < w:
            img[y : y + strip_h, shift:] = strip[:, :-shift]
        elif shift < 0 and -shift < w:
            img[y : y + strip_h, :shift] = strip[:, -shift:]
    shift = random.randint(1, 4)
    img[:, :, 0] = np.roll(img[:, :, 0], shift, axis=1)
    img[:, :, 2] = np.roll(img[:, :, 2], -shift, axis=1)
    return img


# ═══════════════════════════════════════════════════════════════════
#  TEXT RENDERER — texto arriba + branding mejorado
# ═══════════════════════════════════════════════════════════════════
def get_fonts():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return (
                    ImageFont.truetype(fp, 72),   # title big
                    ImageFont.truetype(fp, 42),   # label
                    ImageFont.truetype(fp, 36),   # small
                )
            except:
                pass
    default = ImageFont.load_default()
    return default, default, default


def render_text_frame(base_arr, text, char_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr).convert("RGBA")
    w, h = img.size

    # ── Gradiente superior (para texto arriba) ──
    grad_top = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad_top)
    grad_h_top = int(h * 0.38)
    for y in range(grad_h_top):
        a = int(200 * (1 - y / grad_h_top) ** 1.2)
        gd.line([(0, y), (w, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, grad_top)

    # ── Gradiente inferior (branding) ──
    grad_bot = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(grad_bot)
    grad_h_bot = int(h * 0.22)
    for y in range(h - grad_h_bot, h):
        a = int(210 * ((y - (h - grad_h_bot)) / grad_h_bot) ** 1.1)
        gd2.line([(0, y), (w, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, grad_bot)

    draw = ImageDraw.Draw(img)
    font_big, font_label, font_small = get_fonts()

    # ── Barra roja superior ──
    bar_top = 110
    draw.rectangle([(60, bar_top), (w - 60, bar_top + 7)], fill=(220, 15, 15, 255))

    # ── Texto principal ARRIBA ──
    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=16)
    line_h = 88
    text_start_y = bar_top + 28

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_big)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        y = text_start_y + i * line_h

        # Sombra doble para legibilidad máxima
        for ox, oy in [(6, 6), (4, 4), (2, 2), (-2, -2)]:
            draw.text((x + ox, y + oy), line, font=font_big, fill=(0, 0, 0, 210))
        # Texto blanco
        draw.text((x, y), line, font=font_big, fill=(255, 255, 255, 255))

    # ── Cursor parpadeante ──
    if char_progress < len(text) and (frame_idx // 8) % 2 == 0 and lines:
        last = lines[-1]
        bbox = draw.textbbox((0, 0), last, font=font_big)
        cx = (w - (bbox[2] - bbox[0])) // 2 + (bbox[2] - bbox[0]) + 6
        cy = text_start_y + (len(lines) - 1) * line_h
        draw.rectangle([cx, cy, cx + 6, cy + 68], fill=(220, 15, 15, 255))

    # ── Branding inferior ──
    label = "DARK PSYCHOLOGY"
    bbox = draw.textbbox((0, 0), label, font=font_label)
    lw = bbox[2] - bbox[0]
    lx = (w - lw) // 2
    # Sombra label
    draw.text((lx + 3, h - 110 + 3), label, font=font_label, fill=(0, 0, 0, 200))
    draw.text((lx, h - 110), label, font=font_label, fill=(200, 15, 15, 240))

    # ── Barra roja inferior ──
    draw.rectangle([(60, h - 140), (w - 60, h - 133)], fill=(220, 15, 15, 200))

    # ── Indicador de escena (puntos) ──
    dot_r = 8
    dot_spacing = 28
    total_dots_w = total_scenes * dot_spacing - (dot_spacing - dot_r * 2)
    dot_x_start = (w - total_dots_w) // 2
    dot_y = h - 68
    for s in range(total_scenes):
        cx_ = dot_x_start + s * dot_spacing
        if s == scene_num:
            draw.ellipse([cx_, dot_y, cx_ + dot_r * 2, dot_y + dot_r * 2], fill=(220, 15, 15, 255))
        else:
            draw.ellipse([cx_, dot_y, cx_ + dot_r * 2, dot_y + dot_r * 2], fill=(120, 120, 120, 160))

    return np.array(img.convert("RGB"))


# ═══════════════════════════════════════════════════════════════════
#  ZOOM suave
# ═══════════════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + 0.06 * (t / duration)
    w, h = base_img.size
    nw, nh = int(w / zoom), int(h / zoom)
    left = (w - nw) // 2
    top = (h - nh) // 2
    return base_img.crop((left, top, left + nw, top + nh)).resize((w, h), Image.LANCZOS)


# ═══════════════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════════════
async def _synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-10%", pitch="-12Hz", volume="+25%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(_synth(text, path))


# ═══════════════════════════════════════════════════════════════════
#  MÚSICA — dark ambient variada
# ═══════════════════════════════════════════════════════════════════
def get_music(duration=120):
    try:
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)

        # Variación aleatoria de tonalidad base
        base_hz = random.choice([41.2, 46.25, 55.0, 61.74, 36.71])

        # Drone base
        music = 0.28 * np.sin(2 * np.pi * base_hz * t)
        music += 0.14 * np.sin(2 * np.pi * base_hz * 1.5 * t)
        music += 0.09 * np.sin(2 * np.pi * base_hz * 2.0 * t)
        music += 0.05 * np.sin(2 * np.pi * base_hz * 3.0 * t)

        # Pulso lento
        pulse_hz = random.uniform(0.06, 0.11)
        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * pulse_hz * t)
        music = music * pulse

        # Shimmer tonal
        shimmer_hz = random.choice([220, 330, 440, 528])
        shimmer = 0.035 * np.sin(2 * np.pi * shimmer_hz * t) * np.sin(2 * np.pi * 0.2 * t)
        music += shimmer

        # Rumble
        music += 0.07 * np.sin(2 * np.pi * 28 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.04 * t))

        # Ruido suave (textura)
        noise = np.random.normal(0, 0.012, len(t)).astype(np.float32)
        noise_env = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)
        music += noise * noise_env

        # Fade in / fade out
        fade = int(sr * 3)
        music[:fade] *= np.linspace(0, 1, fade)
        music[-fade:] *= np.linspace(1, 0, fade)

        # Normalizar a 30% volumen
        music = music / np.max(np.abs(music) + 1e-9) * 0.30
        audio_int = (music * 32767).astype(np.int16)

        wav_path = "bg_music.wav"
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int.tobytes())

        print("  Music generated OK")
        return wav_path
    except Exception as e:
        print(f"  Music error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
#  BUILD SCENE — lazy frames (sin precalcular todo en memoria)
# ═══════════════════════════════════════════════════════════════════
def build_scene(scene, index, total_scenes=5):
    img_path = generate_image(scene["prompt"], index)
    base_img = add_vignette(Image.open(img_path).convert("RGB"))

    audio_path = f"audio_{index}.mp3"
    synth_sync(scene["text"], audio_path)
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1.0
    text = scene["text"]
    reveal_frames = int(FPS * 2.0)

    # Lazy frame maker — sin lista en RAM
    def make_frame(t):
        f = int(t * FPS)
        zoomed = zoom_frame(base_img, t, duration)
        base_arr = np.array(zoomed)
        char_progress = (
            min(len(text), int(len(text) * (f / reveal_frames)))
            if f < reveal_frames
            else len(text)
        )
        frame = render_text_frame(base_arr, text, char_progress, f, index, total_scenes)
        if f < 4:
            frame = glitch_frame(frame, intensity=5)
        return frame

    clip = ImageClip(make_frame, duration=duration, ismask=False)
    clip = clip.set_audio(audio)
    return clip.fadein(0.4).fadeout(0.4)


# ═══════════════════════════════════════════════════════════════════
#  BUILD VIDEO — escenas en paralelo
# ═══════════════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)

    # Generación de imágenes y TTS en paralelo (5x más rápido)
    print("\n  Generating all images in parallel...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        img_futures = {ex.submit(generate_image, s["prompt"], i): i for i, s in enumerate(scenes)}
    img_paths = {img_futures[f]: f.result() for f in img_futures}

    print("\n  Synthesizing all audio in parallel...")
    def synth_scene(args):
        i, text = args
        path = f"audio_{i}.mp3"
        synth_sync(text, path)
        return i, path
    with ThreadPoolExecutor(max_workers=5) as ex:
        audio_futures = list(ex.map(synth_scene, [(i, s["text"]) for i, s in enumerate(scenes)]))

    # Construir clips
    clips = []
    for i, scene in enumerate(scenes):
        print(f"\n  Building scene {i+1}/{total}")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        audio = AudioFileClip(f"audio_{i}.mp3")
        duration = audio.duration + 1.0
        text = scene["text"]
        reveal_frames = int(FPS * 2.0)

        def make_frame(t, _img=base_img, _text=text, _dur=duration, _idx=i):
            f = int(t * FPS)
            zoomed = zoom_frame(_img, t, _dur)
            base_arr = np.array(zoomed)
            cp = (
                min(len(_text), int(len(_text) * (f / reveal_frames)))
                if f < reveal_frames else len(_text)
            )
            frame = render_text_frame(base_arr, _text, cp, f, _idx, total)
            if f < 4:
                frame = glitch_frame(frame, intensity=5)
            return frame

        clip = ImageClip(make_frame, duration=duration, ismask=False)
        clip = clip.set_audio(audio)
        clips.append(clip.fadein(0.4).fadeout(0.4))

    final = concatenate_videoclips(clips, method="compose")

    # Música de fondo
    music_path = get_music(duration=int(final.duration) + 5)
    if music_path:
        try:
            music = AudioFileClip(music_path)
            music = music.subclip(0, min(final.duration, music.duration)).volumex(0.14)
            mixed = CompositeAudioClip([final.audio, music])
            final = final.set_audio(mixed)
            print("  Music mixed OK")
        except Exception as e:
            print(f"  Music mix error: {e}")

    output = "viral_short.mp4"
    print("\n  Rendering final video...")
    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="12000k",
        preset="slow",
        threads=4,
        ffmpeg_params=["-crf", "18"],
    )
    return output


# ═══════════════════════════════════════════════════════════════════
#  UPLOAD YOUTUBE
# ═══════════════════════════════════════════════════════════════════
def upload_to_youtube(video_path, title, description, tags):
    print("\n  Uploading to YouTube...")
    from googleapiclient.discovery import build as yt_build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    # Token seguro con tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tf.write(os.environ["TOKEN_JSON"])
        token_path = tf.name

    try:
        creds = Credentials.from_authorized_user_file(
            token_path,
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        youtube = yt_build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title,
                "description": (
                    description
                    + "\n\n#darkpsychology #psychology #shorts "
                    + "#mindcontrol #manipulation #brain #mindset #facts"
                ),
                "tags": tags,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        }
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
        )
        response = request.execute()
        print(f"  UPLOADED: https://www.youtube.com/watch?v={response['id']}")
    finally:
        os.unlink(token_path)


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  AUTO YOUTUBE BOT — DARK PSYCHOLOGY SHORTS")
    print("=" * 60)

    script = generate_script_with_gemini()
    print(f"\n  Title: {script['title']}")
    print(f"  Scenes: {len(script['scenes'])}")

    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)
