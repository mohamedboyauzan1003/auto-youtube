import os, asyncio, random, requests, numpy as np, textwrap, json, time, wave, tempfile
import logging, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate
from concurrent.futures import ThreadPoolExecutor

# ═══════════════════════════════════════════════════════════
#  CONFIG CENTRAL
# ═══════════════════════════════════════════════════════════
W, H       = 1080, 1920
FPS        = 30
NUM_SCENES = 10          # minimo 10 escenas = ~35-45s
MIN_AUDIO_S       = 1.5
MIN_IMAGE_KB      = 15
MIN_VIDEO_DURATION = 30
MAX_VIDEO_DURATION = 60
VOICE              = "en-US-GuyNeural"
VOICE_RATE         = "-5%"
VOICE_PITCH        = "-10Hz"
VOICE_VOLUME       = "+30%"
IMAGE_RETRIES      = 5
SCRIPT_RETRIES     = 5
UPLOAD_RETRIES     = 3

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
(CACHE_DIR / "images").mkdir(exist_ok=True)
(CACHE_DIR / "audio").mkdir(exist_ok=True)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════
class ColorLog(logging.Formatter):
    COLORS = {
        "DEBUG":   "\033[37m",
        "INFO":    "\033[36m",
        "WARNING": "\033[33m",
        "ERROR":   "\033[31m",
        "SUCCESS": "\033[32m",
    }
    RESET = "\033[0m"
    def format(self, record):
        c = self.COLORS.get(record.levelname, "")
        record.msg = f"{c}[{record.levelname}]{self.RESET} {record.msg}"
        return super().format(record)

logging.SUCCESS = 25
logging.addLevelName(25, "SUCCESS")
def log_success(self, msg, *args, **kw):
    if self.isEnabledFor(25):
        self._log(25, msg, args, **kw)
logging.Logger.success = log_success

log = logging.getLogger("bot")
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(ColorLog("%(message)s"))
log.addHandler(sh)
fh = logging.FileHandler(LOG_DIR / f"{time.strftime('%Y-%m-%d')}.log")
fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(message)s"))
log.addHandler(fh)

# ═══════════════════════════════════════════════════════════
#  GROQ SCRIPT GENERATOR
# ═══════════════════════════════════════════════════════════
TOPICS = [
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
    "why your brain secretly craves drama",
    "how dopamine addiction is engineered to control you",
    "the psychology behind why people obey authority",
    "dark reason why you care what strangers think",
    "how silence is used as a weapon of control",
    "psychological signs someone secretly envies you",
    "why your brain sabotages your own happiness",
    "dark truth about why people lie to themselves",
]

HOOKS = [
    "Nobody tells you this...",
    "99 percent of people never realize...",
    "The biggest lie you believe every day...",
    "They never want you to know this...",
    "This will change how you see everything...",
    "You have been manipulated your entire life...",
    "What they do not teach you in school...",
    "The dark truth nobody talks about...",
]

def generate_script():
    api_key = os.environ.get("GROQ_API_KEY", "")
    topic   = random.choice(TOPICS)
    hook    = random.choice(HOOKS)
    log.info(f"Topic: {topic}")

    prompt = (
        "You are a viral dark psychology YouTube Shorts scriptwriter.\n"
        f"Topic: {topic}\n"
        f"Opening hook: start scene 1 with: '{hook}'\n\n"
        "Rules:\n"
        "- Exactly 10 scenes\n"
        "- Each text: 8-14 words, dramatic dark tone, use ... for pauses\n"
        "- Last scene must end with a question to boost engagement\n"
        "- Each image prompt: very specific unique dark anime cinematic scene, no repeated scenes\n"
        "- Title: under 60 chars, no emojis, scroll-stopping\n\n"
        "Return ONLY raw JSON, no markdown, no backticks:\n"
        "{\n"
        '  "title": "...",\n'
        '  "description": "...",\n'
        '  "tags": ["darkpsychology","psychology","mindcontrol","manipulation","shorts","brain","facts","awareness","secrets","mindset"],\n'
        '  "scenes": [\n'
        '    {"text": "...", "prompt": "dark anime art, [unique scene], dramatic chiaroscuro, 8k, no text, no watermark"},\n'
        "    ... (10 total)\n"
        "  ]\n"
        "}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens":  2500,
    }

    for attempt in range(SCRIPT_RETRIES):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=30,
            )
            log.info(f"Groq status: {r.status_code} (attempt {attempt+1})")
            if r.status_code == 429:
                wait = 15 * (2 ** attempt)
                log.warning(f"Rate limit — waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                log.error(f"Groq error: {r.text[:200]}")
                time.sleep(5)
                continue
            raw = r.json()["choices"][0]["message"]["content"].strip()
            # Strip any markdown fences
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end <= start:
                log.warning("No JSON found, retrying...")
                continue
            raw    = raw[start:end]
            script = json.loads(raw)
            # Validate
            if "scenes" not in script or len(script["scenes"]) < 5:
                log.warning(f"Only {len(script.get('scenes',[]))} scenes, retrying...")
                continue
            # Pad to NUM_SCENES if needed
            while len(script["scenes"]) < NUM_SCENES:
                script["scenes"].append(random.choice(script["scenes"]).copy())
            script["scenes"] = script["scenes"][:NUM_SCENES]
            log.success(f"Script OK: {script['title']} ({len(script['scenes'])} scenes)")
            return script
        except json.JSONDecodeError as e:
            log.error(f"JSON parse error attempt {attempt+1}: {e}")
            time.sleep(5)
        except Exception as e:
            log.error(f"Groq attempt {attempt+1}: {e}")
            time.sleep(5)

    log.warning("All Groq attempts failed — using fallback")
    return fallback_script()

def fallback_script():
    base = {
        "title": "Dark Tricks Used to Manipulate You Every Day",
        "description": "The hidden manipulation tactics controlling your life right now.",
        "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
        "scenes": [
            {"text": "Nobody tells you this... you are being manipulated daily.", "prompt": "dark anime art, shadowy puppet master pulling strings on glowing human silhouette, blood red volumetric fog, 8k, no text"},
            {"text": "Every decision you make... has already been influenced.", "prompt": "dark anime art, massive chess board with human pieces moved by invisible hand, dramatic lighting, 8k, no text"},
            {"text": "Foot in the door... makes you agree to anything they want.", "prompt": "dark anime art, ancient massive door opening into endless crimson void, eerie glow, 8k, no text"},
            {"text": "Scarcity triggers panic... bypassing all your rational thought.", "prompt": "dark anime art, cracked hourglass glowing crimson sand draining fast, deep shadows, 8k, no text"},
            {"text": "Social proof hijacks you... making you copy others blindly.", "prompt": "dark anime art, vast crowd of shadowy identical figures, one different glowing silhouette, 8k, no text"},
            {"text": "Reciprocity traps you... one favor creates lifelong debt.", "prompt": "dark anime art, golden chains made of wrapped gifts binding figure, dark background, 8k, no text"},
            {"text": "Authority bias makes you... obey without ever questioning why.", "prompt": "dark anime art, towering dark authority figure casting shadow over crowd, 8k, no text"},
            {"text": "Anchoring warps your perception... the first number controls all.", "prompt": "dark anime art, giant anchor crushing human mind, distorted numbers floating, 8k, no text"},
            {"text": "Loss aversion is stronger... than any desire for gain.", "prompt": "dark anime art, figure gripping crumbling treasure while standing on edge of abyss, 8k, no text"},
            {"text": "Now you see the tricks... can you protect your mind? Comment below.", "prompt": "dark anime art, warrior breaking dark chains into explosive golden light, epic cinematic scale, 8k, no text"},
        ],
    }
    return base

# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION — Pollinations FLUX + validation
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

def validate_image(path):
    try:
        p = Path(path)
        if not p.exists():
            return False, "not found"
        if p.stat().st_size < MIN_IMAGE_KB * 1024:
            return False, f"too small ({p.stat().st_size//1024}KB)"
        img = Image.open(path).convert("RGB")
        arr = np.array(img)
        if arr.mean() < 5:
            return False, "image is black"
        if arr.std() < 3:
            return False, "no contrast"
        return True, "ok"
    except Exception as e:
        return False, str(e)

def generate_image(prompt, index):
    # Check cache first
    key       = hashlib.md5(prompt.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / "images" / f"{key}.jpg"
    if cache_path.exists():
        ok, reason = validate_image(str(cache_path))
        if ok:
            log.info(f"Image {index+1} from cache")
            return str(cache_path)

    style       = random.choice(ANIME_STYLES)
    full_prompt = (
        f"{style}, {prompt}, "
        "masterpiece, best quality, ultra detailed, 8k resolution, "
        "dramatic cinematic lighting, deep rich shadows, "
        "professional digital art, "
        "no watermark, no text, no signature, vertical portrait composition"
    )
    seed = int(time.time()) * (index + 1) + random.randint(10000, 99999)

    for attempt in range(IMAGE_RETRIES):
        for model in ["flux", "flux-realism", "turbo"]:
            path = _try_pollinations(full_prompt, index, seed + attempt * 1337, model)
            if path:
                ok, reason = validate_image(path)
                if ok:
                    import shutil
                    shutil.copy(path, str(cache_path))
                    log.success(f"Image {index+1} OK ({model}, attempt {attempt+1})")
                    return path
                else:
                    log.warning(f"Image {index+1} invalid ({reason}), retrying...")
        time.sleep(3 * (attempt + 1))

    log.error(f"Image {index+1} all attempts failed — using gradient")
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer":    "https://pollinations.ai/",
        }
        r = requests.get(url, timeout=120, headers=headers)
        if r.status_code == 200 and len(r.content) > MIN_IMAGE_KB * 1024:
            path = f"img_{index}.jpg"
            with open(path, "wb") as f:
                f.write(r.content)
            img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Color(img).enhance(1.1)
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
            img.save(path, quality=98, optimize=True)
            return path
        log.warning(f"  {model}: status={r.status_code}, size={len(r.content)//1024}KB")
    except Exception as e:
        log.warning(f"  {model} error: {e}")
    return None

def _dark_gradient_fallback(index):
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    c    = random.choice([(5,2,12),(15,5,25),(8,3,18),(20,8,35)])
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(c[0]+40*(y/H)), int(c[1]+10*(y/H)), int(c[2]+60*(y/H))))
    path = f"img_{index}.jpg"
    img.save(path)
    return path

# ═══════════════════════════════════════════════════════════
#  VIGNETTE
# ═══════════════════════════════════════════════════════════
def add_vignette(img):
    w, h  = img.size
    mask  = Image.new("L", (w, h), 0)
    draw  = ImageDraw.Draw(mask)
    steps = min(w, h) // 2
    for i in range(steps):
        draw.ellipse([i,i,w-i,h-i], fill=int(255*(i/steps)**0.55))
    return Image.composite(img, Image.new("RGB",(w,h),(0,0,0)), mask)

# ═══════════════════════════════════════════════════════════
#  GLITCH
# ═══════════════════════════════════════════════════════════
def glitch_frame(arr, intensity=4):
    img  = arr.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y     = random.randint(0, h-10)
        shift = random.randint(-12, 12)
        sh    = random.randint(2, 8)
        strip = img[y:y+sh, :].copy()
        if 0 < shift < w:
            img[y:y+sh, shift:] = strip[:, :-shift]
        elif -w < shift < 0:
            img[y:y+sh, :shift] = strip[:, -shift:]
    s = random.randint(2, 5)
    img[:,:,0] = np.roll(img[:,:,0],  s, axis=1)
    img[:,:,2] = np.roll(img[:,:,2], -s, axis=1)
    return img

# ═══════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════
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
                    ImageFont.truetype(fp, 72),  # main
                    ImageFont.truetype(fp, 38),  # label
                )
            except:
                pass
    d = ImageFont.load_default()
    return d, d

# ═══════════════════════════════════════════════════════════
#  TEXT RENDERER — estilo TikTok/CapCut
#  Palabra por palabra resaltada, no bloques grandes
# ═══════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, word_progress, frame_idx, scene_num, total_scenes):
    img  = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size

    # Top gradient
    gt = Image.new("RGBA", (w,h), (0,0,0,0))
    gd = ImageDraw.Draw(gt)
    gh = int(h*0.42)
    for y in range(gh):
        a = int(190*(1-y/gh)**1.15)
        gd.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, gt)

    # Bottom gradient
    gb  = Image.new("RGBA", (w,h), (0,0,0,0))
    gd2 = ImageDraw.Draw(gb)
    bh  = int(h*0.20)
    for y in range(h-bh, h):
        a = int(215*((y-(h-bh))/bh)**1.0)
        gd2.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, gb)

    draw             = ImageDraw.Draw(img)
    font_main, font_label = get_fonts()

    # ── TOP: barra roja + título palabra a palabra estilo TikTok ──
    bar_y = 85
    draw.rectangle([(50,bar_y),(w-50,bar_y+7)], fill=(220,15,15,255))

    words    = text.split()
    shown    = words[:word_progress]
    lines    = textwrap.wrap(" ".join(shown), width=14)
    line_h   = 88
    text_y   = bar_y + 26
    last_word_line = len(lines) - 1

    for li, line in enumerate(lines):
        line_words = line.split()
        # Calculate total line width for centering
        total_w_px = 0
        for ww in line_words:
            bb = draw.textbbox((0,0), ww+" ", font=font_main)
            total_w_px += bb[2]-bb[0]
        x = (w - total_w_px) // 2
        y = text_y + li * line_h

        for wi, ww in enumerate(line_words):
            bb  = draw.textbbox((0,0), ww+" ", font=font_main)
            ww_ = ww + " "
            ww_w = bb[2]-bb[0]

            # Is this the last revealed word? Highlight it
            is_last = (li == last_word_line and wi == len(line_words)-1 and word_progress <= len(words))

            if is_last:
                # Yellow highlight box behind last word
                pad = 6
                draw.rounded_rectangle(
                    [x-pad, y-pad, x+ww_w-bb[0]+pad, y+line_h-12+pad],
                    radius=8, fill=(220,15,15,230)
                )
                # Shadow
                for ox,oy in [(3,3),(2,2)]:
                    draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            else:
                # Normal word with shadow
                for ox,oy in [(5,5),(3,3),(1,1)]:
                    draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            x += ww_w

    # ── BOTTOM: branding ──
    draw.rectangle([(50,h-158),(w-50,h-151)], fill=(220,15,15,200))
    label = "DARK PSYCHOLOGY"
    bb    = draw.textbbox((0,0), label, font=font_label)
    lx    = (w-(bb[2]-bb[0]))//2
    draw.text((lx+3,h-128+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx,  h-128),   label, font=font_label, fill=(220,20,20,255))

    # ── Progress dots ──
    dd  = 12
    sp  = 26
    tw  = total_scenes * sp
    dx  = (w-tw)//2
    dy  = h-72
    for s in range(total_scenes):
        cx_ = dx + s*sp
        if s == scene_num:
            draw.ellipse([cx_-2,dy-2,cx_+dd+2,dy+dd+2], fill=(180,10,10,255))
            draw.ellipse([cx_,dy,cx_+dd,dy+dd],          fill=(220,20,20,255))
        else:
            draw.ellipse([cx_,dy,cx_+dd,dy+dd], fill=(70,70,70,150))

    return np.array(img.convert("RGB"))

# ═══════════════════════════════════════════════════════════
#  ZOOM + PAN (Ken Burns)
# ═══════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom  = 1.0 + 0.06*(t/duration)
    pan_x = 0.015 * np.sin(2*np.pi*t/duration)
    pan_y = 0.008 * np.cos(2*np.pi*t/duration)
    w, h  = base_img.size
    nw    = int(w/zoom)
    nh    = int(h/zoom)
    left  = max(0, min(int((w-nw)/2 + pan_x*w), w-nw))
    top   = max(0, min(int((h-nh)/2 + pan_y*h), h-nh))
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)

# ═══════════════════════════════════════════════════════════
#  TTS + validation
# ═══════════════════════════════════════════════════════════
async def _synth(text, path):
    tts = Communicate(text, voice=VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH, volume=VOICE_VOLUME)
    await tts.save(path)

def synth_sync(text, index):
    key        = hashlib.md5(text.encode()).hexdigest()[:12]
    cache_path = str(CACHE_DIR / "audio" / f"{key}.mp3")
    out_path   = f"audio_{index}.mp3"

    # Use cache if valid
    if Path(cache_path).exists() and Path(cache_path).stat().st_size > 20000:
        import shutil
        shutil.copy(cache_path, out_path)
        log.info(f"Audio {index+1} from cache")
        return out_path

    for attempt in range(3):
        try:
            asyncio.run(_synth(text, out_path))
            p = Path(out_path)
            if p.exists() and p.stat().st_size > 20000:
                import shutil
                shutil.copy(out_path, cache_path)
                log.success(f"Audio {index+1} OK")
                return out_path
            log.warning(f"Audio {index+1} too small, retrying...")
        except Exception as e:
            log.error(f"TTS attempt {attempt+1}: {e}")
        time.sleep(2)

    log.error(f"Audio {index+1} failed — creating silence")
    _make_silence(out_path, 3.0)
    return out_path

def _make_silence(path, duration=3.0):
    import struct, wave as wv
    sr      = 44100
    samples = int(sr * duration)
    data    = struct.pack("<" + "h"*samples, *([0]*samples))
    with wv.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data)

# ═══════════════════════════════════════════════════════════
#  DARK AMBIENT MUSIC
# ═══════════════════════════════════════════════════════════
def generate_music(duration=60):
    try:
        sr      = 44100
        t       = np.linspace(0, duration, int(sr*duration), dtype=np.float32)
        base_hz = random.choice([41.2, 43.65, 46.25, 55.0, 49.0, 36.71])

        music  = 0.30 * np.sin(2*np.pi*base_hz*t)
        music += 0.18 * np.sin(2*np.pi*base_hz*1.498*t)
        music += 0.12 * np.sin(2*np.pi*base_hz*1.782*t)
        music += 0.08 * np.sin(2*np.pi*base_hz*2.0*t)
        music += 0.05 * np.sin(2*np.pi*base_hz*2.997*t)
        music += 0.04 * np.sin(2*np.pi*base_hz*0.5*t)

        pulse   = 0.45 + 0.55*np.sin(2*np.pi*random.uniform(0.06,0.10)*t)
        music  *= pulse
        shz     = random.choice([220,277,330,370,415])
        music  += 0.04 * np.sin(2*np.pi*shz*t) * np.sin(2*np.pi*random.uniform(0.18,0.28)*t)
        music  += 0.09 * np.sin(2*np.pi*25*t) * (0.4+0.6*np.sin(2*np.pi*0.04*t))
        noise   = np.random.normal(0, 0.012, len(t)).astype(np.float32)
        music  += noise * (0.4+0.6*np.sin(2*np.pi*0.05*t))

        fade    = int(sr*3)
        music[:fade]  *= np.linspace(0,1,fade)
        music[-fade:] *= np.linspace(1,0,fade)
        music   = music / (np.max(np.abs(music))+1e-9) * 0.32
        ai      = (music*32767).astype(np.int16)

        wav = "bg_music.wav"
        with wave.open(wav,"w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2)
            wf.setframerate(sr); wf.writeframes(ai.tobytes())
        log.success(f"Music generated ({duration}s)")
        return wav
    except Exception as e:
        log.error(f"Music error: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#  BUILD SCENE
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio         = AudioFileClip(audio_path)
    duration      = max(audio.duration + 0.8, MIN_AUDIO_S + 1)
    total_frames  = int(duration * FPS)
    words         = text.split()
    total_words   = len(words)
    reveal_frames = int(FPS * 1.5)  # Faster word reveal for TikTok pace

    log.info(f"  Scene {scene_idx+1}: {total_frames}f / {duration:.1f}s / {total_words}w")
    frames = []
    for f in range(total_frames):
        t          = f / FPS
        zoomed     = zoom_frame(base_img, t, duration)
        base_arr   = np.array(zoomed)
        wp         = min(total_words, int(total_words*(f/reveal_frames))) if f < reveal_frames else total_words
        frame      = render_text_frame(base_arr, text, wp, f, scene_idx, total_scenes)
        if f < 5:
            frame  = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))

    def make_frame(t):
        return frames[min(int(t*FPS), len(frames)-1)]

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    return clip.fadein(0.4).fadeout(0.4)

# ═══════════════════════════════════════════════════════════
#  CHECKLIST before upload
# ═══════════════════════════════════════════════════════════
def validate_video(path, title, description, tags):
    errors = []
    try:
        from moviepy.editor import VideoFileClip
        vc = VideoFileClip(path)
        d  = vc.duration
        vc.close()
        if d < MIN_VIDEO_DURATION:
            errors.append(f"Too short: {d:.1f}s < {MIN_VIDEO_DURATION}s")
        if d > MAX_VIDEO_DURATION:
            errors.append(f"Too long: {d:.1f}s > {MAX_VIDEO_DURATION}s")
    except Exception as e:
        errors.append(f"Cannot open video: {e}")

    if not Path(path).exists():
        errors.append("Video file missing")
    elif Path(path).stat().st_size < 500_000:
        errors.append("Video file too small (<500KB)")

    if len(title) > 60:
        errors.append(f"Title too long: {len(title)} chars")
    if not description:
        errors.append("Description empty")
    if len(tags) < 5:
        errors.append(f"Not enough tags: {len(tags)}")

    if errors:
        for e in errors:
            log.error(f"CHECKLIST FAIL: {e}")
        return False
    log.success("Checklist passed — video ready to upload")
    return True

# ═══════════════════════════════════════════════════════════
#  BUILD VIDEO
# ═══════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)

    # Parallel image generation
    log.info("Generating images in parallel...")
    def gen_img(args):
        i, prompt = args
        return i, generate_image(prompt, i)
    with ThreadPoolExecutor(max_workers=3) as ex:
        results   = list(ex.map(gen_img, [(i,s["prompt"]) for i,s in enumerate(scenes)]))
    img_paths = {i:p for i,p in results}

    # Parallel TTS
    log.info("Generating audio in parallel...")
    def gen_audio(args):
        i, text = args
        return i, synth_sync(text, i)
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(gen_audio, [(i,s["text"]) for i,s in enumerate(scenes)]))

    # Build clips
    clips = []
    for i, scene in enumerate(scenes):
        log.info(f"Building scene {i+1}/{total}: {scene['text'][:40]}...")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clip     = build_scene(base_img, f"audio_{i}.mp3", scene["text"], i, total)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    # Music
    music_path = generate_music(duration=int(final.duration)+5)
    if music_path and Path(music_path).exists():
        try:
            music = AudioFileClip(music_path)
            music = music.subclip(0, min(final.duration, music.duration)).volumex(0.13)
            mixed = CompositeAudioClip([final.audio, music])
            final = final.set_audio(mixed)
            log.success("Music mixed OK")
        except Exception as e:
            log.warning(f"Music mix failed: {e} — continuing without music")

    output = "viral_short.mp4"
    log.info("Rendering final video...")
    final.write_videofile(
        output, fps=FPS, codec="libx264",
        audio_codec="aac", bitrate="12000k",
        preset="fast", threads=4,
        ffmpeg_params=["-crf","18"],
        logger=None,
    )
    return output

# ═══════════════════════════════════════════════════════════
#  YOUTUBE UPLOAD with retry
# ═══════════════════════════════════════════════════════════
def upload_to_youtube(video_path, title, description, tags):
    log.info("Uploading to YouTube...")
    from googleapiclient.discovery import build as yt_build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tf.write(os.environ["TOKEN_JSON"])
        token_path = tf.name

    try:
        creds   = Credentials.from_authorized_user_file(
            token_path, scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = yt_build("youtube", "v3", credentials=creds)
        for attempt in range(UPLOAD_RETRIES):
            try:
                response = youtube.videos().insert(
                    part="snippet,status",
                    body={
                        "snippet": {
                            "title":       title,
                            "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation #brain #mindset",
                            "tags":        tags,
                            "categoryId":  "22",
                        },
                        "status": {"privacyStatus": "public"},
                    },
                    media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
                ).execute()
                log.success(f"UPLOADED: https://www.youtube.com/watch?v={response['id']}")
                return
            except Exception as e:
                log.error(f"Upload attempt {attempt+1}: {e}")
                if attempt < UPLOAD_RETRIES - 1:
                    time.sleep(15 * (attempt+1))
    finally:
        os.unlink(token_path)

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("="*55)
    log.info("  AUTO YOUTUBE BOT V2 — DARK PSYCHOLOGY SHORTS")
    log.info("="*55)

    # 1. Generate script
    script = generate_script()
    log.info(f"Title  : {script['title']}")
    log.info(f"Scenes : {len(script['scenes'])}")

    # 2. Build video
    video = build_video(script["scenes"])

    # 3. Validate before upload
    if not validate_video(video, script["title"], script["description"], script["tags"]):
        log.error("Video failed checklist — aborting upload")
        exit(1)

    # 4. Upload
    upload_to_youtube(video, script["title"], script["description"], script["tags"])

    log.info("="*55)
    log.success("DONE!")
    log.info("="*55)
