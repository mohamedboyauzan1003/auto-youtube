import os, asyncio, random, requests, numpy as np, textwrap, json, time, wave, tempfile
import logging, hashlib, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate

# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
W, H       = 1080, 1920
FPS        = 30
NUM_SCENES = 7
MIN_AUDIO_S        = 1.5
MIN_IMAGE_KB       = 15
MIN_VIDEO_DURATION = 20
MAX_VIDEO_DURATION = 45
IMAGE_RETRIES      = 4
SCRIPT_RETRIES     = 5
UPLOAD_RETRIES     = 3
TTS_RETRIES        = 4

VOICE_POOL = [
    {"voice": "en-US-GuyNeural",         "rate": "-5%",  "pitch": "-10Hz", "volume": "+30%"},
    {"voice": "en-US-ChristopherNeural", "rate": "+0%",  "pitch": "-8Hz",  "volume": "+25%"},
    {"voice": "en-US-EricNeural",        "rate": "+5%",  "pitch": "-12Hz", "volume": "+30%"},
    {"voice": "en-GB-RyanNeural",        "rate": "-3%",  "pitch": "-6Hz",  "volume": "+25%"},
    {"voice": "en-US-DavisNeural",       "rate": "+8%",  "pitch": "-5Hz",  "volume": "+30%"},
]
FALLBACK_VOICE = {"voice": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz", "volume": "+25%"}

SUBTITLE_THEMES = [
    {"name": "blood_red",    "highlight": (220,15,15,230),   "accent": (220,15,15,255),  "label": (220,20,20,255)},
    {"name": "toxic_green",  "highlight": (40,200,90,230),   "accent": (40,200,90,255),  "label": (50,220,100,255)},
    {"name": "electric_blue","highlight": (30,140,240,230),  "accent": (30,140,240,255), "label": (50,160,255,255)},
    {"name": "violet",       "highlight": (160,40,220,230),  "accent": (160,40,220,255), "label": (180,60,240,255)},
    {"name": "gold",         "highlight": (230,170,20,230),  "accent": (230,170,20,255), "label": (240,190,40,255)},
]

_chosen_voice = random.choice(VOICE_POOL)
_chosen_theme = random.choice(SUBTITLE_THEMES)
VOICE        = _chosen_voice["voice"]
VOICE_RATE   = _chosen_voice["rate"]
VOICE_PITCH  = _chosen_voice["pitch"]
VOICE_VOLUME = _chosen_voice["volume"]
THEME        = _chosen_theme
_ZOOM_INTENSITY = random.uniform(0.04, 0.08)

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
    COLORS = {"DEBUG":"\033[37m","INFO":"\033[36m","WARNING":"\033[33m","ERROR":"\033[31m","SUCCESS":"\033[32m"}
    RESET = "\033[0m"
    def format(self, record):
        c = self.COLORS.get(record.levelname, "")
        record.msg = f"{c}[{record.levelname}]{self.RESET} {record.msg}"
        return super().format(record)

logging.SUCCESS = 25
logging.addLevelName(25, "SUCCESS")
def log_success(self, msg, *a, **kw):
    if self.isEnabledFor(25): self._log(25, msg, a, **kw)
logging.Logger.success = log_success

log = logging.getLogger("bot")
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(ColorLog("%(message)s"))
log.addHandler(sh)
fh = logging.FileHandler(LOG_DIR / f"{time.strftime('%Y-%m-%d')}.log")
fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(message)s"))
log.addHandler(fh)

log.info(f"Voice: {VOICE} (rate={VOICE_RATE}, pitch={VOICE_PITCH})")
log.info(f"Theme: {THEME['name']}")

# ═══════════════════════════════════════════════════════════
#  UPLOAD GUARD
# ═══════════════════════════════════════════════════════════
UPLOAD_GUARD_FILE = CACHE_DIR / "last_upload.json"

def check_upload_guard():
    try:
        if not UPLOAD_GUARD_FILE.exists():
            return True
        data = json.loads(UPLOAD_GUARD_FILE.read_text())
        last_ts = data.get("timestamp", 0)
        elapsed = time.time() - last_ts
        if elapsed < 55 * 60:
            mins_left = int((55*60 - elapsed) / 60)
            log.warning(f"Upload guard: last upload was {int(elapsed/60)}min ago ({mins_left}min remaining). Skipping.")
            return False
        return True
    except Exception:
        return True

def update_upload_guard(video_id):
    try:
        UPLOAD_GUARD_FILE.write_text(json.dumps({
            "timestamp": time.time(),
            "video_id": video_id,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        }))
    except Exception as e:
        log.warning(f"Could not update upload guard: {e}")

# ═══════════════════════════════════════════════════════════
#  TOPICS & HOOKS
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
    "how anchoring bias controls every purchase you make",
    "the dark reason you cannot stop scrolling",
    "why your brain remembers insults more than compliments",
    "how mirror neurons make you copy people without knowing",
    "the sunk cost trap that ruins lives silently",
]

DOPAMINE_HOOKS = [
    "Stop. Your brain is doing this right now.",
    "Most people realize this too late.",
    "This happens to you every single day.",
    "The second you understand this, everything changes.",
    "You have been doing this your whole life without knowing.",
    "Nobody warns you about this one.",
    "This will make you question everything you think you know.",
    "Your brain hides this from you on purpose.",
    "Watch what your brain does in the next 30 seconds.",
    "You are not going to like this, but you need to hear it.",
    "This is the reason you feel stuck, and you never knew.",
    "Pay attention. This changes after you see it.",
]

# ═══════════════════════════════════════════════════════════
#  GROQ SCRIPT GENERATOR
# ═══════════════════════════════════════════════════════════
def generate_script():
    api_key = os.environ.get("GROQ_API_KEY", "")
    history_file = CACHE_DIR / "topic_history.json"
    try:
        recent = json.loads(history_file.read_text()) if history_file.exists() else []
    except Exception:
        recent = []
    available = [t for t in TOPICS if t not in recent[-10:]] or TOPICS
    topic = random.choice(available)
    recent.append(topic)
    history_file.write_text(json.dumps(recent[-30:]))
    hook = random.choice(DOPAMINE_HOOKS)
    log.info(f"Topic: {topic}")
    log.info(f"Hook: {hook}")

    prompt = (
        "You are a viral dark psychology YouTube Shorts scriptwriter. "
        "Your videos get 70%+ retention because every second creates tension that PULLS the viewer forward.\n\n"
        f"Topic: {topic}\n"
        f"Scene 1 must open with exactly: '{hook}'\n\n"
        "STRUCTURE — 7 scenes, one tight connected story:\n"
        "- Scene 1: HOOK — the opening line above, then immediately state something shocking\n"
        "- Scene 2: THE MECHANISM — explain WHY this happens (one sentence, very specific)\n"
        "- Scene 3: THE MOMENT — describe the exact real-life moment the viewer has experienced this\n"
        "- Scene 4: THE HIDDEN CAUSE — the deeper psychological reason most people never realize\n"
        "- Scene 5: THE COST — what it is silently taking from them right now\n"
        "- Scene 6: THE SHIFT — the one thing that changes once they see this clearly\n"
        "- Scene 7: THE HOOK CLOSE — end with a question that pulls them to comment OR rewatch\n\n"
        "RULES:\n"
        "- Each line: 6-12 words MAX\n"
        "- Use ... for spoken pauses\n"
        "- Use YOU/YOUR constantly\n"
        "- Each image prompt: specific vivid dark anime scene matching that line's emotion\n"
        "- Title: under 55 chars, no emojis\n\n"
        "Return ONLY raw JSON:\n"
        "{\n"
        '  "title": "...",\n'
        '  "description": "...",\n'
        '  "tags": ["darkpsychology","psychology","mindcontrol","manipulation","shorts","brain","facts","awareness","secrets","mindset"],\n'
        '  "scenes": [\n'
        '    {"text": "...", "prompt": "dark anime art, [specific scene], dramatic chiaroscuro, 8k, no text, no watermark"},\n'
        "    ... (exactly 7 scenes)\n"
        "  ]\n"
        "}"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 2000
    }

    for attempt in range(SCRIPT_RETRIES):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers=headers, json=payload, timeout=30)
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
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end <= start:
                log.warning("No JSON found, retrying...")
                continue
            script = json.loads(raw[start:end])
            if "scenes" not in script or len(script["scenes"]) < 5:
                log.warning(f"Only {len(script.get('scenes', []))} scenes, retrying...")
                continue
            while len(script["scenes"]) < NUM_SCENES:
                script["scenes"].append(random.choice(script["scenes"]).copy())
            script["scenes"] = script["scenes"][:NUM_SCENES]
            script["_topic"] = topic
            log.success(f"Script OK: {script['title']} ({len(script['scenes'])} scenes)")
            return script
        except json.JSONDecodeError as e:
            log.error(f"JSON error attempt {attempt+1}: {e}")
            time.sleep(5)
        except Exception as e:
            log.error(f"Groq attempt {attempt+1}: {e}")
            time.sleep(5)

    log.warning("Groq failed — using fallback")
    fb = fallback_script()
    fb["_topic"] = topic
    return fb

def fallback_script():
    return {
        "title": "Your Brain Hides This From You Every Day",
        "description": "The hidden psychological loop that quietly controls your every decision.",
        "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
        "scenes": [
            {"text": "Stop. Your brain is doing this right now.", "prompt": "dark anime art, glowing human brain with shadowy hand pulling hidden levers inside it, dramatic red light, 8k, no text"},
            {"text": "It filters reality... to protect your ego.", "prompt": "dark anime art, person looking through keyhole seeing distorted version of world outside, 8k, no text"},
            {"text": "Remember the last time you were proven wrong... and refused to believe it.", "prompt": "dark anime art, figure standing in denial as dark truth hovers visibly behind them, 8k, no text"},
            {"text": "Your brain rewrites that memory... to make you the hero.", "prompt": "dark anime art, film reel being secretly edited by shadow hands, frames changing mid-roll, 8k, no text"},
            {"text": "This costs you every relationship... every opportunity.", "prompt": "dark anime art, person surrounded by doors all closing simultaneously, lone figure in center, 8k, no text"},
            {"text": "The moment you question your own story... reality comes into focus.", "prompt": "dark anime art, cracked mirror revealing true clear reflection underneath the distortion, 8k, no text"},
            {"text": "So when did your brain last lie to you... and you just let it?", "prompt": "dark anime art, warrior facing their own shadow self in golden confrontational light, epic cinematic, 8k, no text"},
        ],
    }

# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION
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
]

def validate_image(path):
    try:
        p = Path(path)
        if not p.exists(): return False, "not found"
        if p.stat().st_size < MIN_IMAGE_KB * 1024: return False, "too small"
        img = Image.open(path).convert("RGB")
        arr = np.array(img)
        if arr.mean() < 5: return False, "black"
        if arr.std() < 3: return False, "no contrast"
        return True, "ok"
    except Exception as e:
        return False, str(e)

def generate_image(prompt, index):
    key = hashlib.md5(prompt.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / "images" / f"{key}.jpg"
    if cache_path.exists():
        ok, _ = validate_image(str(cache_path))
        if ok:
            import shutil
            out = f"img_{index}.jpg"
            shutil.copy(str(cache_path), out)
            log.info(f"Image {index+1} from cache")
            return out

    style = random.choice(ANIME_STYLES)
    full_prompt = (
        f"{style}, {prompt}, masterpiece, best quality, ultra detailed, 8k, "
        "dramatic cinematic lighting, deep rich shadows, professional digital art, "
        "no watermark, no text, no signature, vertical portrait composition"
    )
    seed = int(time.time()) * (index+1) + random.randint(10000, 99999)

    for attempt in range(IMAGE_RETRIES):
        model = ["flux", "turbo", "flux-realism"][attempt % 3]
        path = _try_pollinations(full_prompt, index, seed + attempt*1337, model)
        if path:
            ok, reason = validate_image(path)
            if ok:
                import shutil
                shutil.copy(path, str(cache_path))
                log.success(f"Image {index+1} OK ({model}, attempt {attempt+1})")
                return path
            log.warning(f"Image {index+1} invalid ({reason})")
        wait = 4 * (attempt+1)
        log.warning(f"Image {index+1} retry in {wait}s...")
        time.sleep(wait)

    log.error(f"Image {index+1} all failed — gradient")
    return _dark_gradient_fallback(index)

def _try_pollinations(prompt, index, seed, model="flux"):
    try:
        encoded = requests.utils.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1080&height=1920&seed={seed}&model={model}&nologo=true&enhance=true"
        )
        r = requests.get(url, timeout=90, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://pollinations.ai/"
        })
        if r.status_code == 200 and len(r.content) > MIN_IMAGE_KB*1024:
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
        log.warning(f"  pollinations({model}): {r.status_code}, {len(r.content)//1024}KB")
    except Exception as e:
        log.warning(f"  pollinations({model}): {e}")
    return None

def _dark_gradient_fallback(index):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    c = random.choice([(5,2,12),(15,5,25),(8,3,18),(20,8,35)])
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(c[0]+40*(y/H)), int(c[1]+10*(y/H)), int(c[2]+60*(y/H))))
    path = f"img_{index}.jpg"
    img.save(path)
    return path

# ═══════════════════════════════════════════════════════════
#  VIGNETTE / GLITCH / FONTS
# ═══════════════════════════════════════════════════════════
def add_vignette(img):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    steps = min(w, h) // 2
    for i in range(steps):
        draw.ellipse([i, i, w-i, h-i], fill=int(255*(i/steps)**0.55))
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
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for fp in paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, 72), ImageFont.truetype(fp, 38)
            except:
                pass
    d = ImageFont.load_default()
    return d, d

# ═══════════════════════════════════════════════════════════
#  TEXT RENDERER — word by word like TikTok/CapCut
# ═══════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, word_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size

    # Top gradient
    gt = Image.new("RGBA", (w, h), (0,0,0,0))
    gd = ImageDraw.Draw(gt)
    for y in range(int(h*0.42)):
        gd.line([(0,y),(w,y)], fill=(0,0,0,int(190*(1-y/(h*0.42))**1.15)))
    img = Image.alpha_composite(img, gt)

    # Bottom gradient
    gb = Image.new("RGBA", (w, h), (0,0,0,0))
    gd2 = ImageDraw.Draw(gb)
    bh = int(h*0.18)
    for y in range(h-bh, h):
        gd2.line([(0,y),(w,y)], fill=(0,0,0,int(215*((y-(h-bh))/bh)**1.0)))
    img = Image.alpha_composite(img, gb)

    draw = ImageDraw.Draw(img)
    font_main, font_label = get_fonts()
    accent = THEME["accent"]
    highlight = THEME["highlight"]
    label_color = THEME["label"]

    # Top accent bar
    bar_y = 85
    draw.rectangle([(50, bar_y), (w-50, bar_y+7)], fill=accent)

    # Word by word text
    words = text.split()
    shown = words[:word_progress]
    lines = textwrap.wrap(" ".join(shown), width=14)
    line_h = 88
    text_y = bar_y + 26
    last_line = len(lines) - 1

    for li, line in enumerate(lines):
        line_words = line.split()
        total_w_px = sum(
            draw.textbbox((0,0), ww+" ", font=font_main)[2] -
            draw.textbbox((0,0), ww+" ", font=font_main)[0]
            for ww in line_words
        )
        x = (w - total_w_px) // 2
        y = text_y + li * line_h
        for wi, ww in enumerate(line_words):
            bb = draw.textbbox((0,0), ww+" ", font=font_main)
            ww_str = ww + " "
            ww_w = bb[2] - bb[0]
            is_last = (li == last_line and wi == len(line_words)-1 and word_progress <= len(words))
            if is_last:
                pad = 6
                draw.rounded_rectangle(
                    [x-pad, y-pad, x+ww_w-bb[0]+pad, y+line_h-12+pad],
                    radius=8, fill=highlight
                )
                for ox, oy in [(3,3),(2,2)]:
                    draw.text((x+ox, y+oy), ww_str, font=font_main, fill=(0,0,0,180))
                draw.text((x, y), ww_str, font=font_main, fill=(255,255,255,255))
            else:
                for ox, oy in [(5,5),(3,3),(1,1)]:
                    draw.text((x+ox, y+oy), ww_str, font=font_main, fill=(0,0,0,180))
                draw.text((x, y), ww_str, font=font_main, fill=(255,255,255,255))
            x += ww_w

    # Bottom branding
    draw.rectangle([(50, h-158),(w-50, h-151)], fill=accent[:3]+(200,))
    label = "DARK PSYCHOLOGY"
    bb = draw.textbbox((0,0), label, font=font_label)
    lx = (w-(bb[2]-bb[0])) // 2
    draw.text((lx+3, h-128+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx, h-128), label, font=font_label, fill=label_color)

    # Progress dots
    dd = 12
    sp = 26
    dx = (w - total_scenes*sp) // 2
    dy = h - 72
    for s in range(total_scenes):
        cx_ = dx + s*sp
        if s == scene_num:
            draw.ellipse([cx_-2, dy-2, cx_+dd+2, dy+dd+2], fill=accent)
            draw.ellipse([cx_, dy, cx_+dd, dy+dd], fill=accent)
        else:
            draw.ellipse([cx_, dy, cx_+dd, dy+dd], fill=(70,70,70,150))

    return np.array(img.convert("RGB"))

# ═══════════════════════════════════════════════════════════
#  ZOOM + PAN
# ═══════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + _ZOOM_INTENSITY * (t / duration)
    pan_x = 0.015 * np.sin(2*np.pi*t/duration)
    pan_y = 0.008 * np.cos(2*np.pi*t/duration)
    w, h = base_img.size
    nw = int(w / zoom)
    nh = int(h / zoom)
    left = max(0, min(int((w-nw)/2 + pan_x*w), w-nw))
    top  = max(0, min(int((h-nh)/2 + pan_y*h), h-nh))
    return base_img.crop((left, top, left+nw, top+nh)).resize((w, h), Image.LANCZOS)

# ═══════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════
def _ensure_signed(v):
    return v if v.startswith(("+", "-")) else f"+{v}"

VOICE_RATE   = _ensure_signed(VOICE_RATE)
VOICE_PITCH  = _ensure_signed(VOICE_PITCH)
VOICE_VOLUME = _ensure_signed(VOICE_VOLUME)

async def _synth(text, path, voice=None, rate=None, pitch=None, volume=None):
    tts = Communicate(
        text,
        voice=voice or VOICE,
        rate=rate or VOICE_RATE,
        pitch=pitch or VOICE_PITCH,
        volume=volume or VOICE_VOLUME
    )
    await tts.save(path)

def _audio_duration_ok(path, text):
    try:
        clip = AudioFileClip(path)
        dur = clip.duration
        clip.close()
        return (dur >= max(MIN_AUDIO_S, len(text.split())/4.0)*0.5), dur
    except:
        return False, 0

def synth_one(text, index):
    key = hashlib.md5(text.encode()).hexdigest()[:12]
    cache_path = str(CACHE_DIR / "audio" / f"{key}.mp3")
    out_path = f"audio_{index}.mp3"
    min_bytes = 8000
    if Path(cache_path).exists() and Path(cache_path).stat().st_size > min_bytes:
        ok, dur = _audio_duration_ok(cache_path, text)
        if ok:
            import shutil
            shutil.copy(cache_path, out_path)
            log.info(f"Audio {index+1} from cache ({dur:.1f}s)")
            return out_path
    for attempt in range(TTS_RETRIES):
        use_fallback = attempt >= 2
        try:
            if Path(out_path).exists():
                os.remove(out_path)
            if use_fallback:
                v = FALLBACK_VOICE
                asyncio.run(_synth(text, out_path, voice=v["voice"], rate=v["rate"], pitch=v["pitch"], volume=v["volume"]))
            else:
                asyncio.run(_synth(text, out_path))
            p = Path(out_path)
            if not p.exists() or p.stat().st_size < min_bytes:
                log.warning(f"Audio {index+1} too small, retry {attempt+1}...")
                time.sleep(2+attempt)
                continue
            ok, dur = _audio_duration_ok(out_path, text)
            if ok:
                import shutil
                shutil.copy(out_path, cache_path)
                log.success(f"Audio {index+1} OK ({p.stat().st_size//1024}KB, {dur:.1f}s)")
                return out_path
            log.warning(f"Audio {index+1} too short ({dur:.1f}s), retry {attempt+1}...")
        except Exception as e:
            log.warning(f"Audio {index+1} attempt {attempt+1}: {e}")
        time.sleep(2+attempt)
    log.error(f"Audio {index+1} failed — silence")
    _make_silence(out_path, 3.0)
    return out_path

def synth_all_sequential(scenes):
    paths = {}
    for i, scene in enumerate(scenes):
        paths[i] = synth_one(scene["text"], i)
        time.sleep(0.5)
    return paths

def _make_silence(path, duration=3.0):
    import struct, wave as wv
    sr = 44100
    samples = int(sr * duration)
    data = struct.pack("<" + "h"*samples, *([0]*samples))
    with wv.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data)

# ═══════════════════════════════════════════════════════════
#  MUSIC
# ═══════════════════════════════════════════════════════════
MUSIC_MOODS = ["tense", "ethereal", "ominous"]
_chosen_mood = random.choice(MUSIC_MOODS)
log.info(f"Music mood: {_chosen_mood}")

FREESOUND_QUERIES = {
    "tense":    ["dark tense ambient loop","horror tension drone","suspense cinematic loop"],
    "ethereal": ["ethereal ambient pad","dreamy atmosphere loop","soft dark ambient"],
    "ominous":  ["ominous drone loop","dark cinematic ambient","horror ambient pad"],
}

def try_freesound_music(duration, mood):
    api_key = os.environ.get("FREESOUND_API_KEY", "")
    if not api_key:
        log.warning("FREESOUND_API_KEY not set — synthetic fallback")
        return None
    queries = FREESOUND_QUERIES.get(mood, FREESOUND_QUERIES["ominous"])[:]
    random.shuffle(queries)
    for query in queries:
        try:
            params = {
                "query": query,
                "token": api_key,
                "filter": 'duration:[20 TO 300] license:("Creative Commons 0" OR "Attribution")',
                "fields": "id,name,previews,duration,license",
                "sort": "rating_desc",
                "page_size": 10
            }
            r = requests.get("https://freesound.org/apiv2/search/text/", params=params, timeout=20)
            if r.status_code != 200:
                continue
            results = r.json().get("results", [])
            if not results:
                continue
            random.shuffle(results)
            for sound in results[:5]:
                preview_url = sound.get("previews", {}).get("preview-hq-mp3")
                if not preview_url:
                    continue
                ar = requests.get(preview_url, timeout=30)
                if ar.status_code == 200 and len(ar.content) > 50000:
                    path = "freesound_music.mp3"
                    with open(path, "wb") as f:
                        f.write(ar.content)
                    log.success(f"Freesound OK: {sound.get('name','?')} ({query})")
                    return path
        except Exception as e:
            log.warning(f"  Freesound '{query}': {e}")
    log.warning("Freesound: no track found — synthetic fallback")
    return None

def _lowpass_noise(length, sr, cutoff_hz=300, std=0.02):
    raw = np.random.normal(0, std, length).astype(np.float32)
    fft = np.fft.rfft(raw)
    freqs = np.fft.rfftfreq(length, 1/sr)
    fft[freqs > cutoff_hz] = 0
    return np.fft.irfft(fft, n=length).astype(np.float32)

def generate_music(duration=60, mood=None):
    mood = mood or _chosen_mood
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
        pulse_rate = {"tense": random.uniform(0.12,0.18), "ethereal": random.uniform(0.03,0.06)}.get(mood, random.uniform(0.06,0.10))
        music *= 0.45 + 0.55*np.sin(2*np.pi*pulse_rate*t)
        shz = random.choice([220, 277, 330, 370, 415])
        music += 0.03*np.sin(2*np.pi*shz*t)*np.sin(2*np.pi*random.uniform(0.18,0.28)*t)
        music += 0.09*np.sin(2*np.pi*25*t)*(0.4+0.6*np.sin(2*np.pi*0.04*t))
        music += _lowpass_noise(len(t), sr) * (0.4+0.6*np.sin(2*np.pi*0.05*t))
        fade = int(sr*3)
        music[:fade] *= np.linspace(0, 1, fade)
        music[-fade:] *= np.linspace(1, 0, fade)
        music = music / (np.max(np.abs(music)) + 1e-9) * 0.32
        wav = "bg_music.wav"
        with wave.open(wav, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes((music*32767).astype(np.int16).tobytes())
        log.success(f"Synthetic music OK ({duration}s, mood={mood})")
        return wav
    except Exception as e:
        log.error(f"Music error: {e}")
        return None

def get_background_music(duration, mood=None):
    mood = mood or _chosen_mood
    real = try_freesound_music(duration, mood)
    if real:
        return real, "freesound"
    return generate_music(duration=duration, mood=mood), "synthetic"

# ═══════════════════════════════════════════════════════════
#  BUILD SCENE
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration + 0.8, MIN_AUDIO_S + 1)
    total_frames = int(duration * FPS)
    words = text.split()
    total_words = len(words)
    reveal_frames = int(FPS * 1.3)
    log.info(f"  Scene {scene_idx+1}: {total_frames}f / {duration:.1f}s / {total_words}w")
    frames = []
    for f in range(total_frames):
        t = f / FPS
        zoomed = zoom_frame(base_img, t, duration)
        base_arr = np.array(zoomed)
        wp = min(total_words, int(total_words*(f/reveal_frames))) if f < reveal_frames else total_words
        frame = render_text_frame(base_arr, text, wp, f, scene_idx, total_scenes)
        if f < 5:
            frame = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))
    def make_frame(t):
        return frames[min(int(t*FPS), len(frames)-1)]
    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    return clip.fadein(0.3).fadeout(0.3)

# ═══════════════════════════════════════════════════════════
#  VIDEO VALIDATION
# ═══════════════════════════════════════════════════════════
def validate_video(path, title, description, tags):
    errors = []
    try:
        from moviepy.editor import VideoFileClip
        vc = VideoFileClip(path)
        d = vc.duration
        has_audio = vc.audio is not None
        vc.close()
        if d < MIN_VIDEO_DURATION: errors.append(f"Too short: {d:.1f}s")
        if d > MAX_VIDEO_DURATION: errors.append(f"Too long: {d:.1f}s")
        if not has_audio: errors.append("No audio track")
    except Exception as e:
        errors.append(f"Cannot open: {e}")
    if not Path(path).exists(): errors.append("File missing")
    elif Path(path).stat().st_size < 500_000: errors.append("File too small")
    if len(title) > 60: errors.append(f"Title too long ({len(title)})")
    if not description: errors.append("No description")
    if len(tags) < 5: errors.append("Not enough tags")
    if errors:
        for e in errors: log.error(f"CHECKLIST FAIL: {e}")
        return False
    log.success("Checklist passed")
    return True

# ═══════════════════════════════════════════════════════════
#  BUILD VIDEO
# ═══════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)
    log.info("Generating images sequentially...")
    img_paths = {}
    for i, scene in enumerate(scenes):
        img_paths[i] = generate_image(scene["prompt"], i)
        time.sleep(1.5)

    log.info("Generating audio sequentially...")
    audio_paths = synth_all_sequential(scenes)

    clips = []
    for i, scene in enumerate(scenes):
        log.info(f"Building scene {i+1}/{total}: {scene['text'][:40]}...")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clips.append(build_scene(base_img, audio_paths[i], scene["text"], i, total))

    final = concatenate_videoclips(clips, method="compose")
    final_duration = final.duration
    log.info(f"Total duration: {final_duration:.1f}s")

    voice_only = "viral_short_voice_only.mp4"
    log.info("Rendering voice-only video...")
    final.write_videofile(
        voice_only, fps=FPS, codec="libx264", audio_codec="aac",
        bitrate="12000k", preset="fast", threads=4,
        ffmpeg_params=["-crf","18"], logger=None
    )

    music_path, music_source = get_background_music(duration=int(final_duration)+8)
    output = "viral_short.mp4"
    if music_path and Path(music_path).exists():
        try:
            probe = subprocess.run(
                ["ffprobe","-v","error","-show_entries","format=duration",
                 "-of","default=noprint_wrappers=1:nokey=1", music_path],
                capture_output=True, text=True, timeout=20
            )
            if float(probe.stdout.strip() or 0) < 1.0:
                log.warning("Music invalid, regenerating...")
                music_path = generate_music(int(final_duration)+8)
                music_source = "synthetic"
            music_volume = 0.35 if music_source == "freesound" else 0.45
            cmd = [
                "ffmpeg","-y","-i",voice_only,"-i",music_path,
                "-filter_complex",
                f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{final_duration},volume={music_volume}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",output
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and Path(output).stat().st_size > 500_000:
                log.success(f"Music mixed OK ({music_source}, vol={music_volume})")
            else:
                log.warning(f"ffmpeg mix failed: {result.stderr[-300:]}")
                import shutil; shutil.copy(voice_only, output)
        except Exception as e:
            log.warning(f"Music mix error: {e}")
            import shutil; shutil.copy(voice_only, output)
    else:
        log.warning("No music — voice only")
        import shutil; shutil.copy(voice_only, output)
    return output

# ═══════════════════════════════════════════════════════════
#  YOUTUBE UPLOAD
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
        creds = Credentials.from_authorized_user_file(
            token_path, scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = yt_build("youtube", "v3", credentials=creds)
        for attempt in range(UPLOAD_RETRIES):
            try:
                response = youtube.videos().insert(
                    part="snippet,status",
                    body={
                        "snippet": {
                            "title": title,
                            "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation #brain #mindset",
                            "tags": tags,
                            "categoryId": "22"
                        },
                        "status": {"privacyStatus": "public"},
                    },
                    media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
                ).execute()
                vid = response["id"]
                log.success(f"UPLOADED: https://www.youtube.com/watch?v={vid}")
                return vid
            except Exception as e:
                log.error(f"Upload attempt {attempt+1}: {e}")
                if attempt < UPLOAD_RETRIES-1:
                    time.sleep(15*(attempt+1))
    finally:
        os.unlink(token_path)
    return None

# ═══════════════════════════════════════════════════════════
#  METADATA LOG
# ═══════════════════════════════════════════════════════════
def log_video_metadata(video_id, script, duration):
    import csv
    csv_path = CACHE_DIR / "video_log.csv"
    is_new = not csv_path.exists()
    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["date","video_id","url","title","topic","voice","theme","mood","duration_s","scenes"])
            w.writerow([
                time.strftime("%Y-%m-%d %H:%M"),
                video_id or "FAILED",
                f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                script["title"],
                script.get("_topic", ""),
                VOICE, THEME["name"], _chosen_mood,
                f"{duration:.1f}",
                len(script.get("scenes", []))
            ])
        log.success("Metadata logged")
    except Exception as e:
        log.warning(f"Metadata error: {e}")

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  AUTO YOUTUBE BOT V4 — DARK PSYCHOLOGY SHORTS")
    log.info("=" * 55)

    if not check_upload_guard():
        log.info("Upload guard active — exiting cleanly")
        exit(0)

    script = generate_script()
    log.info(f"Title  : {script['title']}")
    log.info(f"Scenes : {len(script['scenes'])}")

    video = build_video(script["scenes"])

    try:
        from moviepy.editor import VideoFileClip
        _vc = VideoFileClip(video)
        video_duration = _vc.duration
        _vc.close()
    except:
        video_duration = 0.0

    if not validate_video(video, script["title"], script["description"], script["tags"]):
        log.error("Checklist failed — aborting upload")
        log_video_metadata(None, script, video_duration)
        exit(1)

    video_id = upload_to_youtube(video, script["title"], script["description"], script["tags"])
    if video_id:
        update_upload_guard(video_id)
    log_video_metadata(video_id, script, video_duration)

    log.info("=" * 55)
    log.success("DONE!")
    log.info("=" * 55)
