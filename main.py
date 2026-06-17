import os, asyncio, random, requests, numpy as np, textwrap, json, time, wave, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, VideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate
from concurrent.futures import ThreadPoolExecutor

W, H = 1080, 1920
FPS = 30

# ═══════════════════════════════════════════════════════════════════
#  SCRIPT — Gemini con retry + fallback robusto
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
#  IMAGEN — Pollinations HD con retry
# ═══════════════════════════════════════════════════════════════════
ANIME_STYLES = [
    "makoto shinkai anime style",
    "studio mappa dark anime",
    "demon slayer anime art style",
    "attack on titan cinematic anime",
    "jujutsu kaisen dark aesthetic anime",
    "dark fantasy anime illustration",
    "cinematic anime art",
]

def generate_image(prompt, index):
    print(f"  Generating image {index+1}...")
    style = random.choice(ANIME_STYLES)
    full_prompt = (
        f"{style}, {prompt}, "
        f"masterpiece, best quality, ultra detailed, 8k, "
        f"dramatic cinematic lighting, deep shadows, "
        f"no watermark, no text, no logo, vertical composition"
    )
    for attempt in range(3):
        path = try_pollinations(full_prompt, index, attempt)
        if path:
            return path
        time.sleep(4)
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
            img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
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
        draw.line([(0, y), (W, y)], fill=(int(5+30*ratio), int(2+5*ratio), int(12+40*ratio)))
    path = f"img_{index}.jpg"
    img.save(path)
    print(f"  Using dark gradient fallback for image {index+1}")
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
        draw.ellipse([i, i, w-i, h-i], fill=alpha)
    return Image.composite(img, Image.new("RGB", (w, h), (0, 0, 0)), mask)


# ═══════════════════════════════════════════════════════════════════
#  GLITCH
# ═══════════════════════════════════════════════════════════════════
def glitch_frame(img_array, intensity=3):
    img = img_array.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0, h - 10)
        shift = random.randint(-10, 10)
        sh = random.randint(2, 8)
        strip = img[y:y+sh, :].copy()
        if shift > 0 and shift < w:
            img[y:y+sh, shift:] = strip[:, :-shift]
        elif shift < 0 and -shift < w:
            img[y:y+sh, :shift] = strip[:, -shift:]
    s = random.randint(1, 4)
    img[:,:,0] = np.roll(img[:,:,0], s, axis=1)
    img[:,:,2] = np.roll(img[:,:,2], -s, axis=1)
    return img


# ═══════════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════════
def get_fonts():
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for fp in paths:
        if os.path.exists(fp):
            try:
                return (
                    ImageFont.truetype(fp, 72),
                    ImageFont.truetype(fp, 42),
                )
            except:
                pass
    d = ImageFont.load_default()
    return d, d


# ═══════════════════════════════════════════════════════════════════
#  TEXT RENDERER — texto arriba, branding abajo
# ═══════════════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, char_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size

    # Gradiente superior oscuro
    grad_top = Image.new("RGBA", (w, h), (0,0,0,0))
    gd = ImageDraw.Draw(grad_top)
    gh = int(h * 0.40)
    for y in range(gh):
        a = int(195 * (1 - y/gh) ** 1.2)
        gd.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad_top)

    # Gradiente inferior oscuro
    grad_bot = Image.new("RGBA", (w, h), (0,0,0,0))
    gd2 = ImageDraw.Draw(grad_bot)
    gbh = int(h * 0.20)
    for y in range(h - gbh, h):
        a = int(210 * ((y-(h-gbh))/gbh) ** 1.1)
        gd2.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad_bot)

    draw = ImageDraw.Draw(img)
    font_big, font_label = get_fonts()

    # Barra roja superior
    bar_top = 100
    draw.rectangle([(60, bar_top), (w-60, bar_top+7)], fill=(220,15,15,255))

    # Texto arriba con typewriter
    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=16)
    line_h = 90
    text_y = bar_top + 30

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font_big)
        tw = bbox[2]-bbox[0]
        x = (w-tw)//2
        y = text_y + i*line_h
        for ox,oy in [(6,6),(4,4),(2,2),(-2,-2)]:
            draw.text((x+ox,y+oy), line, font=font_big, fill=(0,0,0,215))
        draw.text((x,y), line, font=font_big, fill=(255,255,255,255))

    # Cursor parpadeante
    if char_progress < len(text) and (frame_idx//8)%2==0 and lines:
        bbox = draw.textbbox((0,0), lines[-1], font=font_big)
        cx = (w-(bbox[2]-bbox[0]))//2 + (bbox[2]-bbox[0]) + 6
        cy = text_y + (len(lines)-1)*line_h
        draw.rectangle([cx, cy, cx+6, cy+70], fill=(220,15,15,255))

    # Branding DARK PSYCHOLOGY abajo
    label = "DARK PSYCHOLOGY"
    bbox = draw.textbbox((0,0), label, font=font_label)
    lw = bbox[2]-bbox[0]
    lx = (w-lw)//2
    draw.text((lx+3, h-115+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx, h-115), label, font=font_label, fill=(210,15,15,245))

    # Barra roja inferior
    draw.rectangle([(60, h-145),(w-60, h-138)], fill=(220,15,15,200))

    # Puntos de progreso
    dot_r = 9
    spacing = 30
    total_w = total_scenes * spacing
    dx = (w - total_w)//2
    dy = h - 70
    for s in range(total_scenes):
        cx_ = dx + s*spacing
        color = (220,15,15,255) if s == scene_num else (100,100,100,160)
        draw.ellipse([cx_, dy, cx_+dot_r*2, dy+dot_r*2], fill=color)

    return np.array(img.convert("RGB"))


# ═══════════════════════════════════════════════════════════════════
#  ZOOM
# ═══════════════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + 0.06*(t/duration)
    w, h = base_img.size
    nw, nh = int(w/zoom), int(h/zoom)
    left = (w-nw)//2
    top = (h-nh)//2
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)


# ═══════════════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════════════
async def _synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-10%", pitch="-12Hz", volume="+25%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(_synth(text, path))


# ═══════════════════════════════════════════════════════════════════
#  MÚSICA dark ambient variada
# ═══════════════════════════════════════════════════════════════════
def get_music(duration=120):
    try:
        sr = 44100
        t = np.linspace(0, duration, int(sr*duration), dtype=np.float32)
        base_hz = random.choice([41.2, 46.25, 55.0, 61.74, 36.71])

        music = 0.28 * np.sin(2*np.pi*base_hz*t)
        music += 0.14 * np.sin(2*np.pi*base_hz*1.5*t)
        music += 0.09 * np.sin(2*np.pi*base_hz*2.0*t)
        music += 0.05 * np.sin(2*np.pi*base_hz*3.0*t)

        pulse = 0.5 + 0.5*np.sin(2*np.pi*random.uniform(0.06,0.11)*t)
        music *= pulse

        shimmer_hz = random.choice([220,330,440,528])
        music += 0.035 * np.sin(2*np.pi*shimmer_hz*t) * np.sin(2*np.pi*0.2*t)
        music += 0.07 * np.sin(2*np.pi*28*t) * (0.5+0.5*np.sin(2*np.pi*0.04*t))

        noise = np.random.normal(0, 0.012, len(t)).astype(np.float32)
        music += noise * (0.5+0.5*np.sin(2*np.pi*0.07*t))

        fade = int(sr*3)
        music[:fade] *= np.linspace(0,1,fade)
        music[-fade:] *= np.linspace(1,0,fade)

        music = music / (np.max(np.abs(music))+1e-9) * 0.30
        audio_int = (music*32767).astype(np.int16)

        wav_path = "bg_music.wav"
        with wave.open(wav_path,"w") as wf:
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
#  BUILD SCENE — frames precalculados (compatible con MoviePy 1.x)
# ═══════════════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1.0
    total_frames = int(duration * FPS)
    reveal_frames = int(FPS * 2.0)

    print(f"    Rendering {total_frames} frames for scene {scene_idx+1}...")
    frames = []
    for f in range(total_frames):
        t = f / FPS
        zoomed = zoom_frame(base_img, t, duration)
        base_arr = np.array(zoomed)
        cp = min(len(text), int(len(text)*(f/reveal_frames))) if f < reveal_frames else len(text)
        frame = render_text_frame(base_arr, text, cp, f, scene_idx, total_scenes)
        if f < 5:
            frame = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))

    frames_arr = frames  # lista de arrays

    def make_frame(t):
        idx = min(int(t*FPS), len(frames_arr)-1)
        return frames_arr[idx]

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    return clip.fadein(0.4).fadeout(0.4)


# ═══════════════════════════════════════════════════════════════════
#  BUILD VIDEO
# ═══════════════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)

    # Imágenes en paralelo
    print("\n  Generating all images in parallel...")
    def gen_img(args):
        i, prompt = args
        return i, generate_image(prompt, i)
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(gen_img, [(i, s["prompt"]) for i,s in enumerate(scenes)]))
    img_paths = {i: p for i,p in results}

    # TTS en paralelo
    print("  Synthesizing all audio in parallel...")
    def gen_audio(args):
        i, text = args
        path = f"audio_{i}.mp3"
        synth_sync(text, path)
        return i, path
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(gen_audio, [(i, s["text"]) for i,s in enumerate(scenes)]))

    # Construir clips
    clips = []
    for i, scene in enumerate(scenes):
        print(f"\n  Building scene {i+1}/{total}")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clip = build_scene(base_img, f"audio_{i}.mp3", scene["text"], i, total)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    # Música
    music_path = get_music(duration=int(final.duration)+5)
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
        output, fps=FPS, codec="libx264",
        audio_codec="aac", bitrate="12000k",
        preset="slow", threads=4,
        ffmpeg_params=["-crf","18"],
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tf.write(os.environ["TOKEN_JSON"])
        token_path = tf.name

    try:
        creds = Credentials.from_authorized_user_file(
            token_path, scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = yt_build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation #brain",
                    "tags": tags,
                    "categoryId": "22",
                },
                "status": {"privacyStatus": "public"},
            },
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
    print("="*60)
    print("  AUTO YOUTUBE BOT — DARK PSYCHOLOGY SHORTS")
    print("="*60)

    script = generate_script_with_gemini()
    print(f"\n  Title: {script['title']}")
    print(f"  Scenes: {len(script['scenes'])}")

    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])

    print("\n"+"="*60)
    print("  DONE!")
    print("="*60)
