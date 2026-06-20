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

# ═══════════════════════════════════════════════════════════
#  CONFIG CENTRAL
# ═══════════════════════════════════════════════════════════
W, H       = 1080, 1920
FPS        = 30
NUM_SCENES = 10
MIN_AUDIO_S        = 1.5
MIN_IMAGE_KB       = 15
MIN_VIDEO_DURATION = 30
MAX_VIDEO_DURATION = 60
VOICE_POOL = [
    {"voice": "en-US-GuyNeural",      "rate": "-5%",  "pitch": "-10Hz", "volume": "+30%"},
    {"voice": "en-US-ChristopherNeural", "rate": "+0%",  "pitch": "-8Hz",  "volume": "+25%"},
    {"voice": "en-US-EricNeural",     "rate": "+5%",  "pitch": "-12Hz", "volume": "+30%"},
    {"voice": "en-GB-RyanNeural",     "rate": "-3%",  "pitch": "-6Hz",  "volume": "+25%"},
    {"voice": "en-US-DavisNeural",    "rate": "+8%",  "pitch": "-5Hz",  "volume": "+30%"},
]

SUBTITLE_THEMES = [
    {"name": "blood_red",   "highlight": (220, 15, 15, 230),  "accent": (220, 15, 15, 255), "label": (220, 20, 20, 255)},
    {"name": "toxic_green", "highlight": (40, 200, 90, 230),  "accent": (40, 200, 90, 255), "label": (50, 220, 100, 255)},
    {"name": "electric_blue","highlight": (30, 140, 240, 230),"accent": (30, 140, 240, 255),"label": (50, 160, 255, 255)},
    {"name": "violet",      "highlight": (160, 40, 220, 230), "accent": (160, 40, 220, 255),"label": (180, 60, 240, 255)},
    {"name": "gold",        "highlight": (230, 170, 20, 230), "accent": (230, 170, 20, 255),"label": (240, 190, 40, 255)},
]

# Se eligen UNA VEZ por ejecución para que todo el video sea consistente
_chosen_voice = random.choice(VOICE_POOL)
_chosen_theme = random.choice(SUBTITLE_THEMES)

VOICE        = _chosen_voice["voice"]
VOICE_RATE   = _chosen_voice["rate"]
VOICE_PITCH  = _chosen_voice["pitch"]
VOICE_VOLUME = _chosen_voice["volume"]
THEME        = _chosen_theme
IMAGE_RETRIES      = 4
SCRIPT_RETRIES     = 5
UPLOAD_RETRIES     = 3
TTS_RETRIES        = 4

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

log.info(f"Voice this run: {VOICE} (rate={VOICE_RATE}, pitch={VOICE_PITCH})")
log.info(f"Subtitle theme this run: {THEME['name']}")

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
    "Nobody tells you this, but the reason is...",
    "Here is the exact moment your brain betrays you...",
    "Scientists found the real reason, and it is not what you think...",
    "Watch what happens in your brain right before you fail...",
    "This one decision is sabotaging you without you knowing...",
    "There is a specific moment where this always starts...",
    "Your brain does this on purpose, and here is why...",
    "Most people never connect these two things...",
    "This pattern repeats every single time, watch closely...",
    "The real reason is hiding in plain sight...",
    "Here is what is actually happening when this occurs...",
    "One study found something disturbing about this...",
]

def generate_script():
    api_key = os.environ.get("GROQ_API_KEY", "")
    history_file = CACHE_DIR / "topic_history.json"
    try:
        recent = json.loads(history_file.read_text()) if history_file.exists() else []
    except Exception:
        recent = []
    available = [t for t in TOPICS if t not in recent[-8:]] or TOPICS
    topic   = random.choice(available)
    recent.append(topic)
    history_file.write_text(json.dumps(recent[-20:]))

    hook    = random.choice(HOOKS)
    log.info(f"Topic: {topic}")

    prompt = (
        "You are a viral dark psychology YouTube Shorts scriptwriter. "
        "You write tight, connected mini-essays — NOT a list of random disconnected facts.\n\n"
        f"Topic: {topic}\n"
        f"Opening hook: scene 1 must start with: '{hook}'\n\n"
        "STRUCTURE (this is mandatory, follow it exactly):\n"
        "- Scene 1: the HOOK — grab attention, state the problem\n"
        "- Scene 2: explain WHY this happens (the real mechanism, in plain words)\n"
        "- Scenes 3-4: give ONE concrete example or story that shows it in action\n"
        "- Scenes 5-6: explain the deeper psychological cause behind it\n"
        "- Scenes 7-8: show the consequence — what it costs the viewer if they ignore this\n"
        "- Scene 9: the turning point — what changes once you see it clearly\n"
        "- Scene 10: a direct question to the viewer that calls back to scene 1\n\n"
        "RULES:\n"
        "- Every single scene must flow logically from the one before it, like sentences in one paragraph, "
        "not like 10 separate quotes. Read them in order — they must sound like ONE story, not 10 facts.\n"
        "- Talk directly to the viewer using 'you'. Make it feel personal, like you are speaking to one person.\n"
        "- Each text: 8-16 words, dramatic dark tone, use ... for natural spoken pauses\n"
        "- NEVER use vague filler like 'they never teach you this' more than once total\n"
        "- Each image prompt: vivid, specific, unique dark anime cinematic scene matching that exact scene's meaning\n"
        "- Title: under 60 chars, no emojis, scroll-stopping, matches the actual content\n\n"
        "Return ONLY raw JSON, no markdown, no backticks:\n"
        "{\n"
        '  "title": "...",\n'
        '  "description": "...",\n'
        '  "tags": ["darkpsychology","psychology","mindcontrol","manipulation","shorts","brain","facts","awareness","secrets","mindset"],\n'
        '  "scenes": [\n'
        '    {"text": "...", "prompt": "dark anime art, [specific scene matching this line], dramatic chiaroscuro, 8k, no text, no watermark"},\n'
        "    ... (exactly 10, in narrative order)\n"
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
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end <= start:
                log.warning("No JSON found, retrying...")
                continue
            raw    = raw[start:end]
            script = json.loads(raw)
            if "scenes" not in script or len(script["scenes"]) < 5:
                log.warning(f"Only {len(script.get('scenes',[]))} scenes, retrying...")
                continue
            while len(script["scenes"]) < NUM_SCENES:
                script["scenes"].append(random.choice(script["scenes"]).copy())
            script["scenes"] = script["scenes"][:NUM_SCENES]
            log.success(f"Script OK: {script['title']} ({len(script['scenes'])} scenes)")
            script["_topic"] = topic
            return script
        except json.JSONDecodeError as e:
            log.error(f"JSON parse error attempt {attempt+1}: {e}")
            time.sleep(5)
        except Exception as e:
            log.error(f"Groq attempt {attempt+1}: {e}")
            time.sleep(5)

    log.warning("All Groq attempts failed — using fallback")
    fb = fallback_script()
    fb["_topic"] = topic
    return fb

def fallback_script():
    base = {
        "title": "Why You Keep Sabotaging Your Own Success",
        "description": "The hidden psychological loop that quietly destroys your progress.",
        "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
        "scenes": [
            {"text": "Nobody tells you this... you sabotage yourself right before you win.", "prompt": "dark anime art, figure reaching for glowing trophy then pulling back into shadow, dramatic lighting, 8k, no text"},
            {"text": "Your brain protects you from failure... by making you fail on purpose.", "prompt": "dark anime art, glowing brain with one dark hand secretly pulling levers, 8k, no text"},
            {"text": "Picture someone who quits a job... two weeks before their big promotion.", "prompt": "dark anime art, figure walking away from glowing office tower into darkness, 8k, no text"},
            {"text": "It feels random... but their mind planned this exact moment.", "prompt": "dark anime art, chess board where one piece secretly knocks itself down, 8k, no text"},
            {"text": "Deep down... success feels more dangerous than staying small.", "prompt": "dark anime art, person standing at edge of bright doorway, hesitating in shadow, 8k, no text"},
            {"text": "If you succeed... you risk being seen, judged, and losing it all.", "prompt": "dark anime art, glowing spotlight surrounded by judging shadow eyes, 8k, no text"},
            {"text": "So your mind chooses comfort... a slow, quiet failure feels safer.", "prompt": "dark anime art, person curled inside a dim comfortable cage, 8k, no text"},
            {"text": "Every year you wait... is a year you hand to that fear.", "prompt": "dark anime art, hourglass draining years instead of sand, dark background, 8k, no text"},
            {"text": "The moment you name this pattern... it starts losing its power over you.", "prompt": "dark anime art, figure breaking chains as shadow self dissolves into light, 8k, no text"},
            {"text": "So tell me honestly... where in your life are you sabotaging yourself right now?", "prompt": "dark anime art, warrior standing in golden dawn light looking directly forward, epic cinematic, 8k, no text"},
        ],
    }
    return base

# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION
#  Pollinations (secuencial, sin saturar) + Hugging Face fallback real
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

HF_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "cagliostrolab/animagine-xl-3.1",
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
    key        = hashlib.md5(prompt.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / "images" / f"{key}.jpg"
    if cache_path.exists():
        ok, _ = validate_image(str(cache_path))
        if ok:
            log.info(f"Image {index+1} from cache")
            import shutil
            out = f"img_{index}.jpg"
            shutil.copy(str(cache_path), out)
            return out

    style       = random.choice(ANIME_STYLES)
    full_prompt = (
        f"{style}, {prompt}, "
        "masterpiece, best quality, ultra detailed, 8k resolution, "
        "dramatic cinematic lighting, deep rich shadows, "
        "professional digital art, "
        "no watermark, no text, no signature, vertical portrait composition"
    )
    seed = int(time.time()) * (index + 1) + random.randint(10000, 99999)

    # 1) Pollinations — secuencial, un modelo a la vez, con backoff real
    for attempt in range(IMAGE_RETRIES):
        model = ["flux", "turbo", "flux-realism"][attempt % 3]
        path = _try_pollinations(full_prompt, index, seed + attempt * 1337, model)
        if path:
            ok, reason = validate_image(path)
            if ok:
                import shutil
                shutil.copy(path, str(cache_path))
                log.success(f"Image {index+1} OK ({model}, attempt {attempt+1})")
                return path
            log.warning(f"Image {index+1} invalid ({reason})")
        wait = 4 * (attempt + 1)
        log.warning(f"Image {index+1} retry in {wait}s...")
        time.sleep(wait)

    # 2) Hugging Face Inference API — respaldo real con SDXL/animagine
    hf_token = os.environ.get("HF_API_KEY", "")
    if hf_token:
        for hf_model in HF_MODELS:
            path = _try_huggingface(full_prompt, index, hf_model, hf_token)
            if path:
                ok, reason = validate_image(path)
                if ok:
                    import shutil
                    shutil.copy(path, str(cache_path))
                    log.success(f"Image {index+1} OK (HuggingFace {hf_model})")
                    return path
            time.sleep(3)
    else:
        log.warning("HF_API_KEY not set — skipping Hugging Face fallback")

    log.error(f"Image {index+1} all sources failed — using gradient")
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
        r = requests.get(url, timeout=90, headers=headers)
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
        log.warning(f"  pollinations({model}): status={r.status_code}, size={len(r.content)//1024}KB")
    except Exception as e:
        log.warning(f"  pollinations({model}) error: {e}")
    return None

def _try_huggingface(prompt, index, model, token):
    try:
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": "lowres, bad anatomy, blurry, watermark, text, signature, deformed",
                "width": 832,
                "height": 1216,
                "num_inference_steps": 28,
                "guidance_scale": 7.0,
            },
            "options": {"wait_for_model": True},
        }
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        if r.status_code == 200 and len(r.content) > MIN_IMAGE_KB * 1024:
            path = f"img_{index}.jpg"
            with open(path, "wb") as f:
                f.write(r.content)
            img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Sharpness(img).enhance(1.3)
            img.save(path, quality=98, optimize=True)
            return path
        log.warning(f"  huggingface({model}): status={r.status_code}")
    except Exception as e:
        log.warning(f"  huggingface({model}) error: {e}")
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
                    ImageFont.truetype(fp, 72),
                    ImageFont.truetype(fp, 38),
                )
            except:
                pass
    d = ImageFont.load_default()
    return d, d

# ═══════════════════════════════════════════════════════════
#  TEXT RENDERER — estilo TikTok/CapCut
# ═══════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, word_progress, frame_idx, scene_num, total_scenes):
    img  = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w, h = img.size

    gt = Image.new("RGBA", (w,h), (0,0,0,0))
    gd = ImageDraw.Draw(gt)
    gh = int(h*0.42)
    for y in range(gh):
        a = int(190*(1-y/gh)**1.15)
        gd.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, gt)

    gb  = Image.new("RGBA", (w,h), (0,0,0,0))
    gd2 = ImageDraw.Draw(gb)
    bh  = int(h*0.20)
    for y in range(h-bh, h):
        a = int(215*((y-(h-bh))/bh)**1.0)
        gd2.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, gb)

    draw                   = ImageDraw.Draw(img)
    font_main, font_label  = get_fonts()
    accent  = THEME["accent"]
    highlight = THEME["highlight"]
    label_color = THEME["label"]

    bar_y = 85
    draw.rectangle([(50,bar_y),(w-50,bar_y+7)], fill=accent)

    words    = text.split()
    shown    = words[:word_progress]
    lines    = textwrap.wrap(" ".join(shown), width=14)
    line_h   = 88
    text_y   = bar_y + 26
    last_word_line = len(lines) - 1

    for li, line in enumerate(lines):
        line_words = line.split()
        total_w_px = 0
        for ww in line_words:
            bb = draw.textbbox((0,0), ww+" ", font=font_main)
            total_w_px += bb[2]-bb[0]
        x = (w - total_w_px) // 2
        y = text_y + li * line_h

        for wi, ww in enumerate(line_words):
            bb   = draw.textbbox((0,0), ww+" ", font=font_main)
            ww_  = ww + " "
            ww_w = bb[2]-bb[0]
            is_last = (li == last_word_line and wi == len(line_words)-1 and word_progress <= len(words))

            if is_last:
                pad = 6
                draw.rounded_rectangle(
                    [x-pad, y-pad, x+ww_w-bb[0]+pad, y+line_h-12+pad],
                    radius=8, fill=highlight
                )
                for ox,oy in [(3,3),(2,2)]:
                    draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            else:
                for ox,oy in [(5,5),(3,3),(1,1)]:
                    draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            x += ww_w

    draw.rectangle([(50,h-158),(w-50,h-151)], fill=accent[:3]+(200,))
    label = "DARK PSYCHOLOGY"
    bb    = draw.textbbox((0,0), label, font=font_label)
    lx    = (w-(bb[2]-bb[0]))//2
    draw.text((lx+3,h-128+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx,  h-128),   label, font=font_label, fill=label_color)

    dd  = 12
    sp  = 26
    tw  = total_scenes * sp
    dx  = (w-tw)//2
    dy  = h-72
    for s in range(total_scenes):
        cx_ = dx + s*sp
        if s == scene_num:
            draw.ellipse([cx_-2,dy-2,cx_+dd+2,dy+dd+2], fill=accent)
            draw.ellipse([cx_,dy,cx_+dd,dy+dd],          fill=accent)
        else:
            draw.ellipse([cx_,dy,cx_+dd,dy+dd], fill=(70,70,70,150))

    return np.array(img.convert("RGB"))

# ═══════════════════════════════════════════════════════════
#  ZOOM + PAN — intensidad variable por video
# ═══════════════════════════════════════════════════════════
_ZOOM_INTENSITY = random.uniform(0.05, 0.10)  # mas alto = mas dinamico/rapido

def zoom_frame(base_img, t, duration):
    zoom  = 1.0 + _ZOOM_INTENSITY*(t/duration)
    pan_x = 0.015 * np.sin(2*np.pi*t/duration)
    pan_y = 0.008 * np.cos(2*np.pi*t/duration)
    w, h  = base_img.size
    nw    = int(w/zoom)
    nh    = int(h/zoom)
    left  = max(0, min(int((w-nw)/2 + pan_x*w), w-nw))
    top   = max(0, min(int((h-nh)/2 + pan_y*h), h-nh))
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)

# ═══════════════════════════════════════════════════════════
#  TTS — SECUENCIAL (Edge TTS no soporta bien paralelismo)
# ═══════════════════════════════════════════════════════════
def _ensure_signed(value):
    """Edge TTS exige signo explicito (+0% no 0%). Normaliza por seguridad."""
    if not value.startswith(("+", "-")):
        return f"+{value}"
    return value

VOICE_RATE   = _ensure_signed(VOICE_RATE)
VOICE_PITCH  = _ensure_signed(VOICE_PITCH)
VOICE_VOLUME = _ensure_signed(VOICE_VOLUME)

async def _synth(text, path):
    tts = Communicate(text, voice=VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH, volume=VOICE_VOLUME)
    await tts.save(path)

def _audio_duration_ok(path, text):
    """Valida por duración real, no por peso de archivo (mucho más fiable)."""
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(path)
        dur  = clip.duration
        clip.close()
        word_count   = max(1, len(text.split()))
        expected_min = max(MIN_AUDIO_S, word_count / 4.0)
        if dur < expected_min * 0.5:
            return False, dur
        return True, dur
    except Exception:
        return False, 0

def synth_one(text, index):
    key        = hashlib.md5(text.encode()).hexdigest()[:12]
    cache_path = str(CACHE_DIR / "audio" / f"{key}.mp3")
    out_path   = f"audio_{index}.mp3"
    min_bytes  = 8000  # ~3KB/s es el mínimo plausible para MP3 de voz

    if Path(cache_path).exists() and Path(cache_path).stat().st_size > min_bytes:
        ok, dur = _audio_duration_ok(cache_path, text)
        if ok:
            import shutil
            shutil.copy(cache_path, out_path)
            log.info(f"Audio {index+1} from cache ({dur:.1f}s)")
            return out_path

    for attempt in range(TTS_RETRIES):
        try:
            if Path(out_path).exists():
                os.remove(out_path)
            asyncio.run(_synth(text, out_path))
            p = Path(out_path)
            if not p.exists() or p.stat().st_size < min_bytes:
                log.warning(f"Audio {index+1} too small ({p.stat().st_size if p.exists() else 0}B), retry {attempt+1}...")
                time.sleep(2 + attempt)
                continue
            ok, dur = _audio_duration_ok(out_path, text)
            if ok:
                import shutil
                shutil.copy(out_path, cache_path)
                log.success(f"Audio {index+1} OK ({p.stat().st_size//1024}KB, {dur:.1f}s)")
                return out_path
            log.warning(f"Audio {index+1} duration too short ({dur:.1f}s for {len(text.split())} words), retry {attempt+1}...")
        except Exception as e:
            log.warning(f"Audio {index+1} attempt {attempt+1} error: {e}")
        time.sleep(2 + attempt)

    log.error(f"Audio {index+1} failed after {TTS_RETRIES} attempts — creating silence")
    _make_silence(out_path, 3.0)
    return out_path

def synth_all_sequential(scenes):
    """Genera todo el audio uno detrás de otro — Edge TTS falla si se paraleliza."""
    paths = {}
    for i, scene in enumerate(scenes):
        paths[i] = synth_one(scene["text"], i)
        time.sleep(0.5)  # pequeño respiro entre llamadas
    return paths

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
MUSIC_MOODS = ["tense", "ethereal", "ominous"]
_chosen_mood = random.choice(MUSIC_MOODS)
log.info(f"Music mood this run: {_chosen_mood}")

def generate_music(duration=60, mood=None):
    mood = mood or _chosen_mood
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

        if mood == "tense":
            pulse_rate = random.uniform(0.12, 0.18)  # mas rapido = mas tension
        elif mood == "ethereal":
            pulse_rate = random.uniform(0.03, 0.06)  # mas lento = mas etereo
        else:  # ominous
            pulse_rate = random.uniform(0.06, 0.10)

        pulse   = 0.45 + 0.55*np.sin(2*np.pi*pulse_rate*t)
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
        log.success(f"Music generated ({duration}s, mood={mood})")
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
    reveal_frames = int(FPS * 1.5)

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
#  CHECKLIST
# ═══════════════════════════════════════════════════════════
def validate_video(path, title, description, tags):
    errors = []
    try:
        from moviepy.editor import VideoFileClip
        vc = VideoFileClip(path)
        d  = vc.duration
        has_audio = vc.audio is not None
        vc.close()
        if d < MIN_VIDEO_DURATION:
            errors.append(f"Too short: {d:.1f}s < {MIN_VIDEO_DURATION}s")
        if d > MAX_VIDEO_DURATION:
            errors.append(f"Too long: {d:.1f}s > {MAX_VIDEO_DURATION}s")
        if not has_audio:
            errors.append("No audio track in final video")
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

    # Imágenes: secuencial con pequeño respiro entre cada una
    # (Pollinations rate-limita fuerte si se llama en paralelo)
    log.info("Generating images sequentially...")
    img_paths = {}
    for i, scene in enumerate(scenes):
        img_paths[i] = generate_image(scene["prompt"], i)
        time.sleep(1.5)

    # Audio: secuencial obligatorio (Edge TTS falla en paralelo)
    log.info("Generating audio sequentially...")
    audio_paths = synth_all_sequential(scenes)

    # Construir clips
    clips = []
    for i, scene in enumerate(scenes):
        log.info(f"Building scene {i+1}/{total}: {scene['text'][:40]}...")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clip     = build_scene(base_img, audio_paths[i], scene["text"], i, total)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    final_duration = final.duration
    log.info(f"Final video duration before music: {final_duration:.1f}s")

    music_path = generate_music(duration=int(final_duration) + 8)
    if music_path and Path(music_path).exists():
        try:
            # Verify the music file actually has audible signal
            with wave.open(music_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                peak = max(abs(int.from_bytes(frames[i:i+2], "little", signed=True))
                           for i in range(0, min(len(frames), 200000), 2))
            if peak < 500:
                log.warning(f"Music file seems silent (peak={peak}) — regenerating once")
                music_path = generate_music(duration=int(final_duration) + 8)

            voice_fps = final.audio.fps if final.audio else 44100
            log.info(f"Voice audio fps: {voice_fps}")

            music = AudioFileClip(music_path)
            # Loop or trim music to match video exactly
            if music.duration < final_duration:
                try:
                    from moviepy.audio.fx.all import audio_loop
                    music = audio_loop(music, duration=final_duration)
                except Exception:
                    from moviepy.editor import concatenate_audioclips
                    loops = int(final_duration // music.duration) + 1
                    music = concatenate_audioclips([music] * loops).subclip(0, final_duration)
            else:
                music = music.subclip(0, final_duration)

            # CRITICAL FIX: igualar el fps de audio entre voz y musica.
            # Edge TTS suele exportar a 24000Hz mientras la musica generada va a 44100Hz.
            # CompositeAudioClip puede silenciar/recortar mal una pista si los fps no coinciden.
            music = music.set_fps(voice_fps)
            music = music.volumex(0.30)  # subido de 0.22 -> 0.30

            mixed = CompositeAudioClip([final.audio, music]).set_duration(final_duration)
            mixed = mixed.set_fps(voice_fps)
            final = final.set_audio(mixed)

            # Sanity check: exportar el audio mezclado a un wav y comprobar que tiene señal real
            check_wav = "mixed_check.wav"
            mixed.write_audiofile(check_wav, fps=voice_fps, logger=None)
            with wave.open(check_wav, "rb") as wf:
                fr = wf.readframes(min(wf.getnframes(), 100000))
                mixed_peak = max(abs(int.from_bytes(fr[i:i+2], "little", signed=True))
                                  for i in range(0, len(fr)-1, 2)) if len(fr) > 1 else 0
            log.success(f"Music mixed OK (music_peak={peak}, mixed_peak={mixed_peak}, volume=0.30)")
            if mixed_peak < 200:
                log.warning("Mixed audio peak suspiciously low — music may not be audible")
        except Exception as e:
            log.warning(f"Music mix failed: {e} — continuing without music")
    else:
        log.warning("No music file generated — video will have voice only")

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
                video_id = response["id"]
                log.success(f"UPLOADED: https://www.youtube.com/watch?v={video_id}")
                return video_id
            except Exception as e:
                log.error(f"Upload attempt {attempt+1}: {e}")
                if attempt < UPLOAD_RETRIES - 1:
                    time.sleep(15 * (attempt+1))
    finally:
        os.unlink(token_path)
    return None

# ═══════════════════════════════════════════════════════════
#  REGISTRO DE METADATOS — para analizar despues que funciona mejor
# ═══════════════════════════════════════════════════════════
def log_video_metadata(video_id, script, duration):
    """
    Guarda un CSV con cada video subido: tema, hook, voz, color, mood, duracion.
    Mas adelante puedes cruzar esto con las vistas reales de YouTube Studio
    para ver que combinaciones funcionan mejor, en vez de adivinar.
    """
    import csv
    csv_path = CACHE_DIR / "video_log.csv"
    is_new   = not csv_path.exists()
    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow([
                    "date", "video_id", "url", "title", "topic",
                    "first_scene_text", "voice", "rate", "pitch",
                    "subtitle_theme", "music_mood", "duration_s", "num_scenes",
                ])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M"),
                video_id or "FAILED",
                f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                script["title"],
                script.get("_topic", ""),
                script["scenes"][0]["text"] if script.get("scenes") else "",
                VOICE, VOICE_RATE, VOICE_PITCH,
                THEME["name"], _chosen_mood,
                f"{duration:.1f}",
                len(script.get("scenes", [])),
            ])
        log.success(f"Metadata logged to {csv_path}")
    except Exception as e:
        log.warning(f"Could not log metadata: {e}")


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("="*55)
    log.info("  AUTO YOUTUBE BOT V3 — DARK PSYCHOLOGY SHORTS")
    log.info("="*55)

    script = generate_script()
    log.info(f"Title  : {script['title']}")
    log.info(f"Scenes : {len(script['scenes'])}")

    video = build_video(script["scenes"])

    try:
        from moviepy.editor import VideoFileClip
        _vc = VideoFileClip(video)
        video_duration = _vc.duration
        _vc.close()
    except Exception:
        video_duration = 0.0

    if not validate_video(video, script["title"], script["description"], script["tags"]):
        log.error("Video failed checklist — aborting upload")
        log_video_metadata(None, script, video_duration)
        exit(1)

    video_id = upload_to_youtube(video, script["title"], script["description"], script["tags"])
    log_video_metadata(video_id, script, video_duration)

    log.info("="*55)
    log.success("DONE!")
    log.info("="*55)
