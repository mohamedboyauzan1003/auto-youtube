import os, asyncio, random, requests, numpy as np, textwrap, json, time, wave, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate
from concurrent.futures import ThreadPoolExecutor

W, H = 1080, 1920
FPS = 30

# ═══════════════════════════════════════════════════════════
#  GROQ SCRIPT GENERATOR (gratis, llama-3.3-70b)
#  Obtén tu key gratis en: https://console.groq.com
# ═══════════════════════════════════════════════════════════
def generate_script():
    api_key = os.environ.get("GROQ_API_KEY", "")

    topics = [
        "manipulation tactics people use daily",
        "dark cognitive biases controlling your decisions",
        "subconscious mind tricks you never knew about",
        "body language secrets manipulators exploit",
        "dark persuasion techniques in advertising",
        "psychological reasons you cannot say no",
        "signs someone is gaslighting you right now",
        "how your ego blinds you from truth",
        "dark truths about human nature nobody says",
        "hidden reasons people self sabotage success",
        "psychological tricks narcissists use on you",
        "how fear silently controls every decision",
        "dark side of social media on your brain",
        "why your brain is hardwired for negativity",
        "psychological power moves of influential leaders",
        "why intelligent people stay in toxic relationships",
        "how childhood trauma silently shapes you today",
        "dark secrets of the world most persuasive people",
        "why your brain secretly craves drama",
        "how dopamine addiction is engineered to control you",
        "the psychology behind why people obey authority",
        "dark reason why you care what strangers think",
        "how silence is used as a weapon of control",
        "psychological signs someone secretly envies you",
        "why your brain sabotages your own happiness",
    ]

    topic = random.choice(topics)
    print(f"  Topic: {topic}")

    prompt = f"""You are a viral dark psychology YouTube Shorts scriptwriter.
Write about: {topic}

Rules:
- Each scene text: max 12 words, dramatic, dark, with "..." pauses
- Each image prompt: vivid dark anime art scene, very specific, unique per scene
- Title: under 60 chars, no emojis, makes people stop scrolling

Return ONLY this raw JSON (no markdown, no backticks, no explanation):
{{
  "title": "...",
  "description": "...",
  "tags": ["darkpsychology","psychology","mindcontrol","manipulation","shorts","brain","facts","awareness","secrets","mindset"],
  "scenes": [
    {{"text": "...", "prompt": "dark anime art, [unique specific scene], dramatic chiaroscuro, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark anime art, [unique specific scene], moody atmosphere, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark anime art, [unique specific scene], cinematic, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark anime art, [unique specific scene], epic scale, ultra detailed, 8k, no text"}},
    {{"text": "...", "prompt": "dark anime art, [unique epic final scene], blazing light breaking darkness, ultra detailed, 8k, no text"}}
  ]
}}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 1500,
    }

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            print(f"  Groq status: {r.status_code}")
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"  Rate limit — waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                print(f"  Groq error: {r.text[:200]}")
                break
            raw = r.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            # Extraer solo el JSON si hay texto extra
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]
            script = json.loads(raw)
            print(f"  Groq OK: {script['title']}")
            return script
        except Exception as e:
            print(f"  Groq attempt {attempt+1}: {e}")
            time.sleep(5)

    print("  Using fallback script.")
    return fallback_script()


def fallback_script():
    options = [
        {
            "title": "3 Dark Tricks Used to Manipulate You Daily",
            "description": "Discover the hidden manipulation tactics used on you every single day.",
            "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
            "scenes": [
                {"text": "Every day... someone hijacks your decisions silently.", "prompt": "dark anime art, shadowy puppet master pulling strings on human silhouette, blood red and black, volumetric fog, ultra detailed 8k, no text"},
                {"text": "Foot-in-the-door... gets you to agree to anything.", "prompt": "dark anime art, massive ancient door opening into infinite void, eerie crimson glow from within, ultra detailed 8k, no text"},
                {"text": "Artificial scarcity... triggers your deepest panic response.", "prompt": "dark anime art, cracked hourglass with glowing crimson sand draining, dramatic shadows, ultra detailed 8k, no text"},
                {"text": "Social proof... makes you copy others like a puppet.", "prompt": "dark anime art, vast crowd of shadowy identical figures, one single glowing silhouette standing apart, ultra detailed 8k, no text"},
                {"text": "Now you see the trick... you can finally break free.", "prompt": "dark anime art, lone warrior figure shattering dark chains, explosive golden light breaking through darkness, epic cinematic, ultra detailed 8k, no text"},
            ],
        },
        {
            "title": "Signs Someone Is Secretly Manipulating You",
            "description": "These hidden signs reveal dark psychology being used against you.",
            "tags": ["manipulation","darkpsychology","toxicpeople","mindcontrol","psychology","awareness","shorts","mentalhealth","brain","secrets"],
            "scenes": [
                {"text": "They make you feel guilty... for their mistakes.", "prompt": "dark anime art, cloaked figure placing invisible crushing weight on kneeling person, dark crimson energy, ultra detailed 8k, no text"},
                {"text": "Slowly they isolate you... cutting every connection.", "prompt": "dark anime art, person reaching out through glass prison walls, hands of shadows pulling them back, ultra detailed 8k, no text"},
                {"text": "Gaslighting rewrites your reality... making you doubt yourself.", "prompt": "dark anime art, infinite hall of cracked mirrors each showing different distorted reflection, violet and red glow, ultra detailed 8k, no text"},
                {"text": "Love bombing then silence... the cycle of control.", "prompt": "dark anime art, beautiful roses blooming then violently transforming to black thorns with crimson drops, ultra detailed 8k, no text"},
                {"text": "Recognizing this pattern... is your first act of freedom.", "prompt": "dark anime art, figure standing tall breaking invisible puppet strings, brilliant golden dawn light behind them, ultra detailed 8k, no text"},
            ],
        },
        {
            "title": "Your Brain Deceives You Every Single Day",
            "description": "The hidden lies your brain tells you that shape your entire reality.",
            "tags": ["brain","psychology","mindcontrol","darkpsychology","facts","shorts","mindset","consciousness","awareness","secrets"],
            "scenes": [
                {"text": "Your brain filters 99 percent of reality... to protect you.", "prompt": "dark anime art, glowing translucent human brain suspended in cosmic void, electric synapses firing like lightning, ultra detailed 8k, no text"},
                {"text": "Confirmation bias... traps you in a prison of false beliefs.", "prompt": "dark anime art, massive eye with narrow tunnel vision, shadowy distorted figures lurking outside the view, ultra detailed 8k, no text"},
                {"text": "Your memories are fiction... rewritten every time you recall them.", "prompt": "dark anime art, antique film reel melting and distorting, frames changing as they fall into darkness, ultra detailed 8k, no text"},
                {"text": "Dunning-Kruger... the less you know, the more confident you feel.", "prompt": "dark anime art, arrogant figure standing triumphantly at peak, completely unaware of endless abyss below, ultra detailed 8k, no text"},
                {"text": "See the lies clearly... and your mind becomes truly free.", "prompt": "dark anime art, figure meditating with glowing aura, mental chains dissolving into pure cosmic light, ultra detailed 8k, no text"},
            ],
        },
        {
            "title": "How Fear Controls Every Decision You Make",
            "description": "Fear is silently running your life. Here is how to take back control.",
            "tags": ["fear","darkpsychology","psychology","mindcontrol","shorts","brain","mindset","facts","awareness","secrets"],
            "scenes": [
                {"text": "Fear was never meant... to control your entire life.", "prompt": "dark anime art, massive shadowy fear entity looming over tiny human figure, blood red sky, ultra detailed 8k, no text"},
                {"text": "Your amygdala fires... before your logic can respond.", "prompt": "dark anime art, glowing brain cross-section, one section burning red overriding all others, ultra detailed 8k, no text"},
                {"text": "Fear of rejection... keeps you small and silent forever.", "prompt": "dark anime art, person frozen in place surrounded by judging shadow crowd, ultra detailed 8k, no text"},
                {"text": "Comfort zone is a prison... built entirely from fear.", "prompt": "dark anime art, person inside transparent sphere watching free world outside, crimson chains on wrists, ultra detailed 8k, no text"},
                {"text": "Face the fear once... and it loses all its power.", "prompt": "dark anime art, warrior walking fearlessly into storm of shadow monsters, golden aura shield, ultra detailed 8k, no text"},
            ],
        },
        {
            "title": "Why Narcissists Always Target the Strongest People",
            "description": "Narcissists do not pick weak targets. They pick the most empathetic ones.",
            "tags": ["narcissist","darkpsychology","toxicpeople","manipulation","psychology","shorts","mentalhealth","awareness","brain","secrets"],
            "scenes": [
                {"text": "Narcissists do not want weak prey... they want your strength.", "prompt": "dark anime art, elegant predator circling glowing empathetic figure in darkness, ultra detailed 8k, no text"},
                {"text": "Your empathy is the weapon... they use against you.", "prompt": "dark anime art, glowing heart being slowly drained by dark tendrils, ultra detailed 8k, no text"},
                {"text": "Love bombing is their trap... set before you see it.", "prompt": "dark anime art, beautiful golden cage with roses outside, dark figure watching from shadows, ultra detailed 8k, no text"},
                {"text": "Devaluation begins... the moment they feel secure.", "prompt": "dark anime art, bright star being slowly dimmed by encroaching dark clouds, ultra detailed 8k, no text"},
                {"text": "Leaving a narcissist... is the strongest thing you do.", "prompt": "dark anime art, person breaking free from invisible chains into brilliant sunrise, ultra detailed 8k, no text"},
            ],
        },
    ]
    return random.choice(options)


# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION — Pollinations FLUX
# ═══════════════════════════════════════════════════════════
ANIME_STYLES = [
    "makoto shinkai anime style",
    "studio mappa dark anime art",
    "demon slayer kimetsu no yaiba art style",
    "attack on titan dark cinematic anime",
    "jujutsu kaisen dark aesthetic",
    "dark fantasy anime illustration",
    "cinematic anime concept art",
    "yoji shinkawa dark illustration style",
    "dark anime oil painting style",
]

def generate_image(prompt, index):
    print(f"  Image {index+1}...")
    style = random.choice(ANIME_STYLES)
    seed = int(time.time()) * (index+1) + random.randint(10000, 99999)

    full_prompt = (
        f"{style}, {prompt}, "
        f"masterpiece, best quality, ultra detailed, 8k resolution, "
        f"dramatic cinematic lighting, deep rich shadows, "
        f"professional digital art, "
        f"no watermark, no text, no signature, vertical portrait composition"
    )

    for model in ["flux", "flux-realism", "turbo"]:
        path = _try_pollinations(full_prompt, index, seed, model)
        if path:
            return path
        seed += 1337
        time.sleep(2)

    return _dark_gradient_fallback(index)

def _try_pollinations(prompt, index, seed, model="flux"):
    try:
        encoded = requests.utils.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1080&height=1920&seed={seed}"
            f"&model={model}&nologo=true&enhance=true"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pollinations.ai/",
        }
        r = requests.get(url, timeout=120, headers=headers)
        if r.status_code == 200 and len(r.content) > 15000:
            path = f"img_{index}.jpg"
            with open(path, "wb") as f:
                f.write(r.content)
            img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            img = ImageEnhance.Color(img).enhance(1.1)
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
            img.save(path, quality=98, optimize=True)
            print(f"  Image {index+1} OK ({model})")
            return path
        else:
            print(f"  {model}: status={r.status_code}, size={len(r.content)}")
    except Exception as e:
        print(f"  {model} error: {e}")
    return None

def _dark_gradient_fallback(index):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    colors = [(5,2,12),(15,5,25),(8,3,18),(20,8,35)]
    c = random.choice(colors)
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(c[0]+40*(y/H)), int(c[1]+10*(y/H)), int(c[2]+60*(y/H))))
    path = f"img_{index}.jpg"
    img.save(path)
    return path


# ═══════════════════════════════════════════════════════════
#  VIGNETTE
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


# ═══════════════════════════════════════════════════════════
#  GLITCH
# ═══════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════
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
                    ImageFont.truetype(fp, 76),
                    ImageFont.truetype(fp, 40),
                    ImageFont.truetype(fp, 34),
                )
            except:
                pass
    d = ImageFont.load_default()
    return d, d, d


# ═══════════════════════════════════════════════════════════
#  TEXT RENDERER
# ═══════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, char_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size

    # Top gradient
    grad_top = Image.new("RGBA", (w, h), (0,0,0,0))
    gd = ImageDraw.Draw(grad_top)
    top_h = int(h * 0.45)
    for y in range(top_h):
        a = int(200 * (1 - y/top_h) ** 1.1)
        gd.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad_top)

    # Bottom gradient
    grad_bot = Image.new("RGBA", (w, h), (0,0,0,0))
    gd2 = ImageDraw.Draw(grad_bot)
    bot_h = int(h * 0.18)
    for y in range(h - bot_h, h):
        a = int(220 * ((y-(h-bot_h))/bot_h) ** 1.0)
        gd2.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad_bot)

    draw = ImageDraw.Draw(img)
    font_big, font_label, font_small = get_fonts()

    # Top red bar
    bar_y = 90
    draw.rectangle([(50, bar_y),(w-50, bar_y+8)], fill=(220,15,15,255))

    # Typewriter text
    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=15)
    line_h = 95
    text_y = bar_y + 28

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font_big)
        tw = bbox[2]-bbox[0]
        x = (w-tw)//2
        y = text_y + i*line_h
        for ox,oy,alpha in [(8,8,140),(5,5,160),(3,3,180),(1,1,200)]:
            draw.text((x+ox,y+oy), line, font=font_big, fill=(0,0,0,alpha))
        draw.text((x,y), line, font=font_big, fill=(255,255,255,255))

    # Blinking cursor
    if char_progress < len(text) and (frame_idx//7)%2==0 and lines:
        bbox = draw.textbbox((0,0), lines[-1], font=font_big)
        cx = (w-(bbox[2]-bbox[0]))//2 + (bbox[2]-bbox[0]) + 7
        cy = text_y + (len(lines)-1)*line_h
        draw.rectangle([cx,cy,cx+7,cy+74], fill=(220,15,15,255))

    # Bottom branding
    draw.rectangle([(50,h-160),(w-50,h-153)], fill=(220,15,15,200))
    label = "DARK PSYCHOLOGY"
    bbox = draw.textbbox((0,0), label, font=font_label)
    lw = bbox[2]-bbox[0]
    lx = (w-lw)//2
    draw.text((lx+3,h-130+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx,h-130), label, font=font_label, fill=(220,20,20,255))

    # Progress dots
    dot_d = 12
    spacing = 28
    total_w = total_scenes * spacing
    dx = (w-total_w)//2
    dy = h-75
    for s in range(total_scenes):
        cx_ = dx + s*spacing
        if s == scene_num:
            draw.ellipse([cx_-2,dy-2,cx_+dot_d+2,dy+dot_d+2], fill=(180,10,10,255))
            draw.ellipse([cx_,dy,cx_+dot_d,dy+dot_d], fill=(220,20,20,255))
        else:
            draw.ellipse([cx_,dy,cx_+dot_d,dy+dot_d], fill=(80,80,80,160))

    return np.array(img.convert("RGB"))


# ═══════════════════════════════════════════════════════════
#  ZOOM (Ken Burns)
# ═══════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + 0.07*(t/duration)
    pan_x = 0.02 * np.sin(2*np.pi*t/duration)
    w, h = base_img.size
    nw, nh = int(w/zoom), int(h/zoom)
    left = max(0, min(int((w-nw)/2 + pan_x*w), w-nw))
    top = (h-nh)//2
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)


# ═══════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════
async def _synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-12%", pitch="-14Hz", volume="+30%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(_synth(text, path))


# ═══════════════════════════════════════════════════════════
#  DARK AMBIENT MUSIC
# ═══════════════════════════════════════════════════════════
def generate_music(duration=120):
    try:
        sr = 44100
        t = np.linspace(0, duration, int(sr*duration), dtype=np.float32)
        base_hz = random.choice([41.2, 43.65, 46.25, 55.0, 49.0, 36.71])

        music  = 0.30 * np.sin(2*np.pi*base_hz*t)
        music += 0.18 * np.sin(2*np.pi*base_hz*1.498*t)
        music += 0.12 * np.sin(2*np.pi*base_hz*1.782*t)
        music += 0.08 * np.sin(2*np.pi*base_hz*2.0*t)
        music += 0.05 * np.sin(2*np.pi*base_hz*2.997*t)
        music += 0.04 * np.sin(2*np.pi*base_hz*0.5*t)

        pulse = 0.45 + 0.55*np.sin(2*np.pi*random.uniform(0.06,0.10)*t)
        music *= pulse

        shimmer_hz = random.choice([220,277,330,370,415])
        music += 0.04 * np.sin(2*np.pi*shimmer_hz*t) * np.sin(2*np.pi*random.uniform(0.18,0.28)*t)
        music += 0.09 * np.sin(2*np.pi*25*t) * (0.4+0.6*np.sin(2*np.pi*0.04*t))

        noise = np.random.normal(0, 0.015, len(t)).astype(np.float32)
        music += noise * (0.4+0.6*np.sin(2*np.pi*0.05*t))

        fade_s = int(sr*4)
        music[:fade_s] *= np.linspace(0,1,fade_s)
        music[-fade_s:] *= np.linspace(1,0,fade_s)
        music = music / (np.max(np.abs(music))+1e-9) * 0.32
        audio_int = (music*32767).astype(np.int16)

        wav_path = "bg_music.wav"
        with wave.open(wav_path,"w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int.tobytes())
        print(f"  Music generated OK ({duration}s)")
        return wav_path
    except Exception as e:
        print(f"  Music error: {e}")
        return None


# ═══════════════════════════════════════════════════════════
#  BUILD SCENE
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1.0
    total_frames = int(duration * FPS)
    reveal_frames = int(FPS * 1.8)

    print(f"    Rendering {total_frames} frames...")
    frames = []
    for f in range(total_frames):
        t = f / FPS
        zoomed = zoom_frame(base_img, t, duration)
        base_arr = np.array(zoomed)
        cp = min(len(text), int(len(text)*(f/reveal_frames))) if f < reveal_frames else len(text)
        frame = render_text_frame(base_arr, text, cp, f, scene_idx, total_scenes)
        if f < 6:
            frame = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))

    def make_frame(t):
        return frames[min(int(t*FPS), len(frames)-1)]

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    return clip.fadein(0.5).fadeout(0.5)


# ═══════════════════════════════════════════════════════════
#  BUILD VIDEO
# ═══════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)

    print("\n  Generating images in parallel...")
    def gen_img(args):
        i, prompt = args
        return i, generate_image(prompt, i)
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(gen_img, [(i,s["prompt"]) for i,s in enumerate(scenes)]))
    img_paths = {i:p for i,p in results}

    print("  Generating audio in parallel...")
    def gen_audio(args):
        i, text = args
        path = f"audio_{i}.mp3"
        synth_sync(text, path)
        return i, path
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(gen_audio, [(i,s["text"]) for i,s in enumerate(scenes)]))

    clips = []
    for i, scene in enumerate(scenes):
        print(f"\n  Scene {i+1}/{total}: {scene['text'][:45]}...")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clip = build_scene(base_img, f"audio_{i}.mp3", scene["text"], i, total)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    music_path = generate_music(duration=int(final.duration)+5)
    if music_path:
        try:
            music = AudioFileClip(music_path)
            music = music.subclip(0, min(final.duration, music.duration)).volumex(0.13)
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
        ffmpeg_params=["-crf","17"],
    )
    return output


# ═══════════════════════════════════════════════════════════
#  YOUTUBE UPLOAD
# ═══════════════════════════════════════════════════════════
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
        response = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation #brain #mindset",
                    "tags": tags,
                    "categoryId": "22",
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
        ).execute()
        print(f"  UPLOADED: https://www.youtube.com/watch?v={response['id']}")
    finally:
        os.unlink(token_path)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("="*55)
    print("  AUTO YOUTUBE BOT — DARK PSYCHOLOGY SHORTS")
    print("="*55)

    script = generate_script()
    print(f"\n  Title  : {script['title']}")
    print(f"  Scenes : {len(script['scenes'])}")

    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])

    print("\n"+"="*55)
    print("  DONE!")
    print("="*55)

Learn more(opens in new tab)

|███████▍ | 586/794 [00:23<00:14, 14.73it/s, now=None] t: 74%|███████▍ | 588/794 [00:23<00:13,
