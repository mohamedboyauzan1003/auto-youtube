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

# Voces en español nativas
VOICE_POOL = [
    {"voice": "es-ES-AlvaroNeural", "rate": "+15%", "pitch": "-5Hz",  "volume": "+30%"},
    {"voice": "es-ES-AlvaroNeural", "rate": "+20%", "pitch": "-8Hz",  "volume": "+30%"},
    {"voice": "es-ES-AlvaroNeural", "rate": "+12%", "pitch": "-3Hz",  "volume": "+28%"},
]
FALLBACK_VOICE = {"voice": "es-ES-AlvaroNeural", "rate": "+15%", "pitch": "-5Hz", "volume": "+30%"}

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
sh = logging.StreamHandler(); sh.setFormatter(ColorLog("%(message)s")); log.addHandler(sh)
fh = logging.FileHandler(LOG_DIR / f"{time.strftime('%Y-%m-%d')}.log")
fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(message)s")); log.addHandler(fh)

log.info(f"Voz: {VOICE} (rate={VOICE_RATE})")
log.info(f"Tema: {THEME['name']}")

# ═══════════════════════════════════════════════════════════
#  UPLOAD GUARD
# ═══════════════════════════════════════════════════════════
UPLOAD_GUARD_FILE = CACHE_DIR / "last_upload.json"

def check_upload_guard():
    if os.environ.get("FORCE_UPLOAD", "").lower() == "true":
        log.info("FORCE_UPLOAD=true — publicando ahora")
        return True
    try:
        if not UPLOAD_GUARD_FILE.exists():
            return True
        data = json.loads(UPLOAD_GUARD_FILE.read_text())
        elapsed = time.time() - data.get("timestamp", 0)
        if elapsed < 55 * 60:
            log.warning(f"Guard activo: ultimo upload hace {int(elapsed/60)}min.")
            return False
        return True
    except Exception:
        return True

def update_upload_guard(video_id):
    try:
        UPLOAD_GUARD_FILE.write_text(json.dumps({
            "timestamp": time.time(), "video_id": video_id,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        }))
    except Exception as e:
        log.warning(f"No se pudo actualizar guard: {e}")

# ═══════════════════════════════════════════════════════════
#  TEMAS — psicologia para jovenes 16-24
# ═══════════════════════════════════════════════════════════
TOPICS = [
    "por que la gente pierde el interes en ti",
    "por que no puedes dejar de pensar en una persona",
    "como las personas atractivas manipulan sin hablar",
    "por que tu cerebro se vuelve adicto a las personas toxicas",
    "la psicologia detras del ghosting",
    "por que alguien ignora tus mensajes a proposito",
    "como los narcisistas hacen que te sientas culpable",
    "por que pensar demasiado destruye tu confianza",
    "como las redes sociales reprograman tu cerebro",
    "la psicologia de los celos",
    "por que algunas personas fingen que no les importas",
    "como los manipuladores consiguen tu confianza",
    "por que tu crush actua de forma tan confusa",
    "por que tu cerebro recuerda momentos vergonzosos durante anos",
    "como el silencio puede ser una forma de manipulacion",
    "por que la confianza intimida a las personas inseguras",
    "la psicologia de la popularidad",
    "como la gente te manipula usando cumplidos",
    "la psicologia de dejarte en visto",
    "por que tu ex vuelve cuando ya lo habias superado",
    "por que las relaciones toxicas son tan dificiles de dejar",
    "como tu cerebro se vuelve adicto a la aprobacion de los demas",
    "por que el rechazo duele tanto",
    "la psicologia de la primera impresion",
    "como la falsa confianza engana a todos",
    "por que las personas solitarias confian demasiado rapido",
    "como tu movil controla muchas de tus decisiones",
    "por que siempre dejas todo para despues",
    "la psicologia del miedo a perderte algo",
    "como los influencers manipulan tu atencion",
    "la psicologia de la venganza",
    "por que no puedes olvidar a ciertas personas",
    "como el lenguaje corporal revela emociones ocultas",
    "la psicologia de la ansiedad social",
    "por que tu mente se cree sus propias mentiras",
    "como funciona realmente la manipulacion emocional",
    "como tu cerebro se vuelve adicto al scroll infinito",
    "la psicologia de la adiccion a la dopamina",
    "por que tu confianza desaparece cerca de algunas personas",
    "como la gente te juzga sin que te des cuenta",
    "por que ser misterioso hace que los demas piensen mas en ti",
    "la psicologia de la dependencia emocional",
    "por que tu cerebro sabotea tus propios objetivos",
    "como los amigos toxicos manipulan sin que lo notes",
    "por que algunas personas se obsesionan cuando las rechazan",
    "la psicologia de las amistades falsas",
    "como otras personas pueden controlar tus emociones",
    "por que tu cerebro teme tanto ser ignorado",
    "la psicologia oscura del coqueteo",
    "como el contacto visual cambia lo que los demas piensan de ti",
    "por que algunas personas siempre parecen tener el control",
    "la psicologia de pensar demasiado por la noche",
    "como la manipulacion se esconde detras de la amabilidad",
    "por que tu cerebro se obsesiona con las relaciones imposibles",
    "la psicologia del autosabotaje en jovenes",
    "por que compararte con otros en redes te hace sentir menos",
    "como detectar cuando alguien te usa emocionalmente",
    "por que algunos te tratan bien en publico y mal en privado",
    "la psicologia de la zona de amistad",
    "como tu cerebro inventa conversaciones que nunca ocurrieron",
]

DOPAMINE_HOOKS = [
    "Si haces esto... ya te estan manipulando.",
    "Tu cerebro te esta enganando ahora mismo.",
    "La mayoria descubre esto demasiado tarde.",
    "Hay una razon por la que no puedes olvidarle.",
    "Lo que voy a decir puede cambiar como ves a la gente.",
    "Si alguien hace esto contigo... alejate.",
    "Esto explica por que siempre vuelves a cometer el mismo error.",
    "Tu mente hace esto todos los dias sin que lo notes.",
    "No confies en alguien que haga esto.",
    "Puede que hayas vivido esto hoy mismo.",
    "Hay personas que saben controlar tu mente... y tu ni lo notas.",
    "Si te cuesta decir que no... escucha esto.",
    "La persona que mas te manipula no siempre es quien imaginas.",
    "Nunca ignores esta senal.",
    "Tu cerebro esta programado para caer en esta trampa.",
    "Esto explica por que algunas personas tienen tanto poder sobre ti.",
    "Probablemente estas haciendo esto sin darte cuenta.",
    "Despues de saber esto... veras a la gente diferente.",
    "Lo mas peligroso de un manipulador es esto.",
    "Nadie te avisa de este truco psicologico.",
    "Si alguien hace esto... desconfia.",
    "Esto explica por que algunas personas parecen irresistibles.",
    "Hay una razon por la que no puedes dejar de pensar en esa persona.",
    "Este error esta arruinando tus relaciones.",
    "Tu cerebro prefiere una mentira antes que esta verdad.",
    "La gente inteligente tambien cae en esta trampa.",
    "Puede que estes confundiendo amor con manipulacion.",
    "Esto ocurre en casi todas las relaciones toxicas.",
    "Hay una tecnica que usan para controlarte sin hablar.",
    "Si siempre acabas decepcionado... escucha esto.",
]

# ═══════════════════════════════════════════════════════════
#  GROQ — genera guion + prompts de imagen ricos
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
    log.info(f"Tema: {topic}")
    log.info(f"Hook: {hook}")

    # El prompt esta DENTRO de la funcion (bug corregido)
    prompt = (
        "Eres el mejor guionista del mundo para YouTube Shorts sobre psicologia, manipulacion, "
        "comportamiento humano y relaciones. "
        "Tu objetivo NO es informar: tu objetivo es conseguir la maxima retencion posible. "
        "Cada frase debe hacer que el espectador NECESITE escuchar la siguiente. "
        "Tu publico son jovenes de 16 a 24 anos. Habla como un amigo, no como un profesor.\n\n"
        f"TEMA: {topic}\n"
        f"LA PRIMERA ESCENA DEBE EMPEZAR EXACTAMENTE CON: '{hook}'\n\n"
        "ESTRUCTURA OBLIGATORIA:\n"
        "- ESCENA 1 (GANCHO): empieza con el hook, luego afirmacion sorprendente\n"
        "- ESCENA 2 (EL PORQUE): que ocurre psicologicamente, muy simple\n"
        "- ESCENA 3 (IDENTIFICACION): situacion cotidiana que el espectador haya vivido\n"
        "- ESCENA 4 (REVELACION): la verdad que la mayoria desconoce, como un secreto\n"
        "- ESCENA 5 (CONSECUENCIAS): como afecta a su vida ahora mismo\n"
        "- ESCENA 6 (CAMBIO): reflexion que cambia su forma de pensar\n"
        "- ESCENA 7 (FINAL): pregunta muy potente que invite a comentar\n\n"
        "REGLAS DEL GUION:\n"
        "- TODO en espanol\n"
        "- Usa siempre 'tu' y 'tu'\n"
        "- Cada escena: entre 6 y 12 palabras\n"
        "- Frases cortas y faciles de entender\n"
        "- Sin lenguaje academico\n"
        "- Cada frase debe dejar una pregunta sin responder\n"
        "- Tono misterioso, intenso y emocional\n"
        "- Usa '...' para pausas dramaticas\n"
        "- No uses emojis\n"
        "- No pongas introducciones ni despedidas\n\n"
        "REGLAS DE LAS IMAGENES (MUY IMPORTANTE):\n"
        "Los prompts de imagen SIEMPRE en ingles.\n"
        "Para cada escena genera un prompt cinematografico de 40-60 palabras.\n"
        "El protagonista SIEMPRE debe ser un joven de 16 a 24 anos con ropa moderna "
        "(hoodie, streetwear, ropa casual actual).\n"
        "Los escenarios deben ser actuales: habitacion con luz de pantalla, ciudad nocturna, "
        "transporte publico, instituto, universidad, cafeteria, parque urbano.\n"
        "Cada imagen debe incluir UN simbolo psicologico visual poderoso relacionado con la escena.\n"
        "Estilo visual: cinematografico, como una escena de serie de Netflix o HBO.\n"
        "NO uses el mismo tipo de composicion dos veces seguidas.\n"
        "Alterna entre: primer plano de cara, plano medio, plano general, plano picado.\n"
        "Iluminacion: dramatica, volumetrica, con luces de neon, pantallas, farolas.\n"
        "Siempre incluye: ultra detailed, masterpiece, 8k, cinematic lighting, no text, no watermark.\n\n"
        "EJEMPLOS DE PROMPTS DE CALIDAD:\n"
        "- 'Young man 20 years old in hoodie surrounded by floating phone notifications "
        "one red message glowing bright, cinematic lighting, emotional, ultra detailed, 8k, no text'\n"
        "- 'Teenage girl standing alone in crowded high school hallway people wearing identical "
        "white masks one mask cracking, Netflix thriller aesthetic, dramatic lighting, masterpiece'\n"
        "- 'Young person lying in dark bedroom face lit only by phone screen giant invisible "
        "hands pulling strings attached to their head, cinematic, ultra detailed, 8k'\n\n"
        "Devuelve UNICAMENTE JSON valido con este formato exacto:\n"
        "{\n"
        "  \"title\": \"...\",\n"
        "  \"description\": \"...\",\n"
        "  \"tags\": [\"psicologia\",\"psicologia oscura\",\"mente\",\"cerebro\","
        "\"manipulacion\",\"relaciones\",\"curiosidades\",\"shorts\",\"viral\",\"jovenes\"],\n"
        "  \"scenes\": [\n"
        "    {\"text\": \"...\", \"prompt\": \"...\"},\n"
        "    ... (exactamente 7 escenas)\n"
        "  ]\n"
        "}\n\n"
        "No escribas explicaciones. No uses markdown. No pongas ```. Solo el JSON."
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile",
               "messages": [{"role": "user", "content": prompt}],
               "temperature": 1.0, "max_tokens": 2500}

    for attempt in range(SCRIPT_RETRIES):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers=headers, json=payload, timeout=30)
            log.info(f"Groq status: {r.status_code} (intento {attempt+1})")
            if r.status_code == 429:
                wait = 15 * (2 ** attempt)
                log.warning(f"Rate limit — esperando {wait}s..."); time.sleep(wait); continue
            if r.status_code != 200:
                log.error(f"Groq error: {r.text[:200]}"); time.sleep(5); continue
            raw = r.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json","").replace("```","").strip()
            start = raw.find("{"); end = raw.rfind("}") + 1
            if start == -1 or end <= start:
                log.warning("JSON no encontrado, reintentando..."); continue
            script = json.loads(raw[start:end])
            if "scenes" not in script or len(script["scenes"]) < 5:
                log.warning(f"Solo {len(script.get('scenes',[]))} escenas, reintentando..."); continue
            while len(script["scenes"]) < NUM_SCENES:
                script["scenes"].append(random.choice(script["scenes"]).copy())
            script["scenes"] = script["scenes"][:NUM_SCENES]
            script["_topic"] = topic
            log.success(f"Script OK: {script['title']} ({len(script['scenes'])} escenas)")
            return script
        except json.JSONDecodeError as e:
            log.error(f"JSON error intento {attempt+1}: {e}"); time.sleep(5)
        except Exception as e:
            log.error(f"Groq intento {attempt+1}: {e}"); time.sleep(5)

    log.warning("Groq fallo — usando fallback")
    fb = fallback_script(); fb["_topic"] = topic; return fb

def fallback_script():
    options = [
        {
            "title": "La verdad que tu cerebro te oculta",
            "description": "El mecanismo psicologico que influye en tus decisiones sin que lo sepas.",
            "tags": ["psicologia","psicologia oscura","mente","cerebro","manipulacion","relaciones","curiosidades","shorts","viral","jovenes"],
            "scenes": [
                {"text": "Tu cerebro te esta enganando ahora mismo.",
                 "prompt": "Young man 19 years old in dark hoodie sitting alone in bedroom face lit only by blue phone screen, giant shadowy hands controlling invisible strings attached to his head, cinematic psychological thriller, ultra detailed, 8k, no text, no watermark"},
                {"text": "Filtra la realidad... para proteger tu ego.",
                 "prompt": "Teenage girl looking through a cracked phone screen at distorted version of reality outside, one eye seeing truth one eye seeing lies, cinematic lighting, Netflix aesthetic, ultra detailed, 8k, no text"},
                {"text": "Recuerda la ultima vez que te equivocaste... y no lo quisiste admitir.",
                 "prompt": "Young person 20 years old standing in high school hallway while floating memory bubble shows embarrassing moment only they can see, dramatic cinematic lighting, emotional, masterpiece, 8k, no text"},
                {"text": "Tu cerebro reescribe ese recuerdo... para hacerte el heroe.",
                 "prompt": "Film reel being secretly edited by shadow hands in dark cinema, each frame showing different version of same memory, psychological thriller aesthetic, dramatic lighting, ultra detailed, 8k, no text"},
                {"text": "Eso afecta a tus relaciones sin que lo notes.",
                 "prompt": "Young couple 18-22 years old in park at night transparent wall of distorted perception growing between them while they smile unaware, cinematic, dramatic neon lighting, masterpiece, 8k, no text"},
                {"text": "Todo cambia cuando cuestionas tu propia historia.",
                 "prompt": "Young woman 21 years old looking at cracked mirror in dark bathroom true clear reflection emerging beneath the distortion, dramatic single light, emotional, cinematic, ultra detailed, 8k, no text"},
                {"text": "Cuantas veces tu mente te ha mentido... solo hoy?",
                 "prompt": "Young person standing at crossroads in dark urban street shadow self facing them in confrontation golden dawn breaking behind them, epic cinematic, emotional, masterpiece, 8k, no text"},
            ],
        },
        {
            "title": "Por que no puedes dejar de pensar en esa persona",
            "description": "La trampa psicologica que hace que alguien ocupe tu mente constantemente.",
            "tags": ["psicologia","psicologia oscura","mente","cerebro","amor","obsesion","relaciones","shorts","viral","jovenes"],
            "scenes": [
                {"text": "Hay una razon por la que no puedes olvidarle.",
                 "prompt": "Young person 19 years old lying in dark bedroom ceiling covered in floating glowing memories of one specific person, emotional, cinematic, dramatic blue lighting, ultra detailed, 8k, no text"},
                {"text": "Tu cerebro lo etiqueta como... una recompensa no completada.",
                 "prompt": "Brain cross-section with one glowing pathway obsessively activated surrounded by darkness, psychological scientific thriller aesthetic, dramatic lighting, masterpiece, 8k, no text"},
                {"text": "Recuerdas cuando te dejaba en visto... y lo comprobabas cada minuto.",
                 "prompt": "Young woman 20 years old in bed at 2am checking phone repeatedly message says delivered not read dramatic phone glow on face anxious expression, cinematic, ultra detailed, 8k, no text"},
                {"text": "Cuanto mas te ignora... mas lo deseas.",
                 "prompt": "Young man 21 years old reaching toward fading silhouette that keeps moving away in dark park neon lights reflecting in puddles below, psychological thriller, cinematic, masterpiece, 8k, no text"},
                {"text": "Eso te roba tiempo... energia... y paz mental.",
                 "prompt": "Hourglass draining not sand but hours and memories young person watching exhausted unable to stop it, symbolic psychological art, dramatic lighting, ultra detailed, 8k, no text"},
                {"text": "Cuando entiendes el truco... el hechizo se rompe.",
                 "prompt": "Young person 20 years old breaking invisible mental chains in dark urban setting light breaking through cracks dramatic liberation, cinematic, emotional, masterpiece, 8k, no text"},
                {"text": "En quien estas pensando ahora mismo mientras escuchas esto?",
                 "prompt": "Young person alone on rooftop at night city lights below looking directly at viewer calm but knowing expression cinematic portrait, ultra detailed, 8k, dramatic lighting, no text"},
            ],
        },
        {
            "title": "Lo que tu crush no te dice pero su cuerpo si",
            "description": "Senales del lenguaje corporal que revelan lo que alguien realmente siente.",
            "tags": ["psicologia","lenguaje corporal","relaciones","amor","shorts","viral","jovenes","crush","signos","mente"],
            "scenes": [
                {"text": "Si alguien hace esto contigo... no es casualidad.",
                 "prompt": "Two young people 18-20 years old in university cafeteria one subtly mirroring the other posture and gestures without realizing, cinematic overhead shot, dramatic warm lighting, ultra detailed, 8k, no text"},
                {"text": "El cuerpo revela lo que la boca nunca dira.",
                 "prompt": "Close up of young woman 19 years old face pupils dilated talking to someone off camera unconscious smile forming, psychological observation, cinematic macro photography aesthetic, masterpiece, 8k, no text"},
                {"text": "Recuerdas cuando alguien te tocaba el brazo sin razon.",
                 "prompt": "Young couple 20 years old in school hallway casual arm touch that lingers both pretending it means nothing dramatic lighting from window, cinematic, emotional, ultra detailed, 8k, no text"},
                {"text": "Ese gesto no fue accidental... fue una senal.",
                 "prompt": "Slow motion visual of hand touch with glowing energy transfer between two young people symbolic psychological moment, dramatic neon lighting, artistic cinematic, masterpiece, 8k, no text"},
                {"text": "Ignorar esas senales te ha costado oportunidades reales.",
                 "prompt": "Young man 21 years old watching chance disappear through window of bus while person he liked walks away unaware dramatic urban rain scene, cinematic, emotional, ultra detailed, 8k, no text"},
                {"text": "Cuando sabes leer el cuerpo... nadie puede mentirte.",
                 "prompt": "Young person 20 years old in crowded party seeing through everyones social masks seeing their true emotions as glowing auras, psychological surrealism, cinematic, masterpiece, 8k, no text"},
                {"text": "Que gestos ves cuando alguien te gusta de verdad?",
                 "prompt": "Young person looking directly at camera with slight knowing smile in dark urban street neon lights reflecting off wet pavement, cinematic portrait, emotional, ultra detailed, 8k, no text"},
            ],
        },
    ]
    return random.choice(options)

# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION — estilos cinematograficos para jovenes
# ═══════════════════════════════════════════════════════════

# Estilos visuales que funcionan para publico 16-24
IMAGE_STYLES = [
    "cinematic digital art, ultra detailed, masterpiece, dramatic lighting, emotional, 8k",
    "realistic cinematic illustration, psychological thriller, Netflix movie poster style, ultra detailed",
    "modern anime MAPPA style, dramatic cinematic lighting, ultra detailed, emotional, masterpiece",
    "Arcane style digital painting, vibrant dramatic lighting, cinematic, masterpiece, ultra detailed",
    "cyberpunk psychological atmosphere, neon lights, cinematic, ultra detailed, dramatic shadows",
    "dark surrealism, symbolic psychology, dreamlike, emotional, cinematic lighting, masterpiece",
    "high-end concept art, realistic faces, dramatic shadows, cinematic composition, masterpiece, 8k",
    "Netflix psychological thriller scene, ultra detailed, cinematic, dramatic lighting, masterpiece",
    "Spider-Verse inspired digital illustration, vibrant dramatic lighting, cinematic composition",
    "photorealistic cinematic portrait, psychological tension, dramatic lighting, 8k, masterpiece",
]

HF_MODELS = ["stabilityai/stable-diffusion-xl-base-1.0", "cagliostrolab/animagine-xl-3.1"]

def validate_image(path):
    try:
        p = Path(path)
        if not p.exists(): return False, "no encontrada"
        if p.stat().st_size < MIN_IMAGE_KB * 1024: return False, "muy pequena"
        img = Image.open(path).convert("RGB"); arr = np.array(img)
        if arr.mean() < 5: return False, "negra"
        if arr.std() < 3: return False, "sin contraste"
        return True, "ok"
    except Exception as e: return False, str(e)

def generate_image(prompt, index):
    key = hashlib.md5(prompt.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / "images" / f"{key}.jpg"
    if cache_path.exists():
        ok, _ = validate_image(str(cache_path))
        if ok:
            import shutil; out = f"img_{index}.jpg"
            shutil.copy(str(cache_path), out); log.info(f"Imagen {index+1} desde cache"); return out

    # El prompt ya viene enriquecido desde Groq
    # Solo anadimos el estilo visual por encima
    style = random.choice(IMAGE_STYLES)
    full_prompt = (
        f"{prompt}, {style}, "
        "young protagonist 16-24 years old modern clothing streetwear hoodie, "
        "contemporary urban setting, psychological symbolism, "
        "no watermark, no text, no signature, vertical portrait composition 9:16"
    )
    seed = int(time.time()) * (index+1) + random.randint(10000, 99999)

    for attempt in range(IMAGE_RETRIES):
        model = ["flux","turbo","flux-realism"][attempt % 3]
        path = _try_pollinations(full_prompt, index, seed + attempt*1337, model)
        if path:
            ok, reason = validate_image(path)
            if ok:
                import shutil; shutil.copy(path, str(cache_path))
                log.success(f"Imagen {index+1} OK ({model}, intento {attempt+1})"); return path
            log.warning(f"Imagen {index+1} invalida ({reason})")
        wait = 4*(attempt+1); log.warning(f"Imagen {index+1} reintento en {wait}s..."); time.sleep(wait)

    hf_token = os.environ.get("HF_API_KEY","")
    if hf_token:
        for hf_model in HF_MODELS:
            path = _try_huggingface(full_prompt, index, hf_model, hf_token)
            if path:
                ok, _ = validate_image(path)
                if ok:
                    import shutil; shutil.copy(path, str(cache_path))
                    log.success(f"Imagen {index+1} OK (HuggingFace)"); return path
            time.sleep(3)

    log.error(f"Imagen {index+1} todos fallaron — degradado")
    return _dark_gradient_fallback(index)

def _try_pollinations(prompt, index, seed, model="flux"):
    try:
        encoded = requests.utils.quote(prompt)
        url = (f"https://image.pollinations.ai/prompt/{encoded}"
               f"?width=1080&height=1920&seed={seed}&model={model}&nologo=true&enhance=true")
        r = requests.get(url, timeout=90, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://pollinations.ai/"})
        if r.status_code == 200 and len(r.content) > MIN_IMAGE_KB*1024:
            path = f"img_{index}.jpg"
            with open(path,"wb") as f: f.write(r.content)
            img = Image.open(path).convert("RGB").resize((W,H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.25)
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Color(img).enhance(1.15)
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
            img.save(path, quality=98, optimize=True); return path
        log.warning(f"  pollinations({model}): {r.status_code}, {len(r.content)//1024}KB")
    except Exception as e: log.warning(f"  pollinations({model}): {e}")
    return None

def _try_huggingface(prompt, index, model, token):
    try:
        r = requests.post(f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": prompt, "parameters": {
                "negative_prompt": "lowres, bad anatomy, blurry, watermark, text, old, ugly",
                "width": 832, "height": 1216, "num_inference_steps": 28, "guidance_scale": 7.5},
                "options": {"wait_for_model": True}}, timeout=90)
        if r.status_code == 200 and len(r.content) > MIN_IMAGE_KB*1024:
            path = f"img_{index}.jpg"
            with open(path,"wb") as f: f.write(r.content)
            img = Image.open(path).convert("RGB").resize((W,H), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.15); img = ImageEnhance.Sharpness(img).enhance(1.3)
            img.save(path, quality=98, optimize=True); return path
    except Exception as e: log.warning(f"  huggingface: {e}")
    return None

def _dark_gradient_fallback(index):
    img = Image.new("RGB",(W,H)); draw = ImageDraw.Draw(img)
    c = random.choice([(5,2,12),(15,5,25),(8,3,18),(20,8,35)])
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(c[0]+40*(y/H)), int(c[1]+10*(y/H)), int(c[2]+60*(y/H))))
    path = f"img_{index}.jpg"; img.save(path); return path

# ═══════════════════════════════════════════════════════════
#  VIGNETTE / GLITCH / FONTS
# ═══════════════════════════════════════════════════════════
def add_vignette(img):
    w,h = img.size; mask = Image.new("L",(w,h),0); draw = ImageDraw.Draw(mask)
    steps = min(w,h)//2
    for i in range(steps): draw.ellipse([i,i,w-i,h-i], fill=int(255*(i/steps)**0.55))
    return Image.composite(img, Image.new("RGB",(w,h),(0,0,0)), mask)

def glitch_frame(arr, intensity=4):
    img = arr.copy(); h,w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0,h-10); shift = random.randint(-12,12); sh = random.randint(2,8)
        strip = img[y:y+sh,:].copy()
        if 0 < shift < w: img[y:y+sh,shift:] = strip[:,:-shift]
        elif -w < shift < 0: img[y:y+sh,:shift] = strip[:,-shift:]
    s = random.randint(2,5)
    img[:,:,0] = np.roll(img[:,:,0],s,axis=1); img[:,:,2] = np.roll(img[:,:,2],-s,axis=1)
    return img

def get_fonts():
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]
    for fp in paths:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp,72), ImageFont.truetype(fp,38)
            except: pass
    d = ImageFont.load_default(); return d,d

# ═══════════════════════════════════════════════════════════
#  TEXT RENDERER — subtitulos estilo TikTok/CapCut
# ═══════════════════════════════════════════════════════════
def render_text_frame(base_arr, text, word_progress, frame_idx, scene_num, total_scenes):
    img = Image.fromarray(base_arr.astype(np.uint8)).convert("RGBA")
    w,h = img.size

    gt = Image.new("RGBA",(w,h),(0,0,0,0)); gd = ImageDraw.Draw(gt)
    for y in range(int(h*0.42)):
        gd.line([(0,y),(w,y)], fill=(0,0,0,int(190*(1-y/(h*0.42))**1.15)))
    img = Image.alpha_composite(img, gt)

    gb = Image.new("RGBA",(w,h),(0,0,0,0)); gd2 = ImageDraw.Draw(gb); bh = int(h*0.18)
    for y in range(h-bh,h):
        gd2.line([(0,y),(w,y)], fill=(0,0,0,int(215*((y-(h-bh))/bh)**1.0)))
    img = Image.alpha_composite(img, gb)

    draw = ImageDraw.Draw(img)
    font_main, font_label = get_fonts()
    accent = THEME["accent"]; highlight = THEME["highlight"]; label_color = THEME["label"]

    bar_y = 85
    draw.rectangle([(50,bar_y),(w-50,bar_y+7)], fill=accent)

    words = text.split(); shown = words[:word_progress]
    lines = textwrap.wrap(" ".join(shown), width=14)
    line_h = 88; text_y = bar_y + 26; last_line = len(lines)-1

    for li, line in enumerate(lines):
        line_words = line.split()
        total_w_px = sum(draw.textbbox((0,0), ww+" ", font=font_main)[2]-draw.textbbox((0,0), ww+" ", font=font_main)[0] for ww in line_words)
        x = (w-total_w_px)//2; y = text_y + li*line_h
        for wi, ww in enumerate(line_words):
            bb = draw.textbbox((0,0), ww+" ", font=font_main)
            ww_ = ww+" "; ww_w = bb[2]-bb[0]
            is_last = (li == last_line and wi == len(line_words)-1 and word_progress <= len(words))
            if is_last:
                pad = 6
                draw.rounded_rectangle([x-pad,y-pad,x+ww_w-bb[0]+pad,y+line_h-12+pad], radius=8, fill=highlight)
                for ox,oy in [(3,3),(2,2)]: draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            else:
                for ox,oy in [(5,5),(3,3),(1,1)]: draw.text((x+ox,y+oy), ww_, font=font_main, fill=(0,0,0,180))
                draw.text((x,y), ww_, font=font_main, fill=(255,255,255,255))
            x += ww_w

    draw.rectangle([(50,h-158),(w-50,h-151)], fill=accent[:3]+(200,))
    label = "PSICOLOGIA OSCURA"
    bb = draw.textbbox((0,0), label, font=font_label); lx = (w-(bb[2]-bb[0]))//2
    draw.text((lx+3,h-128+3), label, font=font_label, fill=(0,0,0,200))
    draw.text((lx,h-128), label, font=font_label, fill=label_color)

    dd=12; sp=26; dx=(w-total_scenes*sp)//2; dy=h-72
    for s in range(total_scenes):
        cx_ = dx+s*sp
        if s == scene_num:
            draw.ellipse([cx_-2,dy-2,cx_+dd+2,dy+dd+2], fill=accent)
            draw.ellipse([cx_,dy,cx_+dd,dy+dd], fill=accent)
        else:
            draw.ellipse([cx_,dy,cx_+dd,dy+dd], fill=(70,70,70,150))

    return np.array(img.convert("RGB"))

# ═══════════════════════════════════════════════════════════
#  ZOOM + PAN
# ═══════════════════════════════════════════════════════════
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + _ZOOM_INTENSITY*(t/duration)
    pan_x = 0.015*np.sin(2*np.pi*t/duration); pan_y = 0.008*np.cos(2*np.pi*t/duration)
    w,h = base_img.size; nw = int(w/zoom); nh = int(h/zoom)
    left = max(0,min(int((w-nw)/2+pan_x*w),w-nw)); top = max(0,min(int((h-nh)/2+pan_y*h),h-nh))
    return base_img.crop((left,top,left+nw,top+nh)).resize((w,h), Image.LANCZOS)

# ═══════════════════════════════════════════════════════════
#  TTS ESPANOL
# ═══════════════════════════════════════════════════════════
def _ensure_signed(v):
    return v if v.startswith(("+","-")) else f"+{v}"

VOICE_RATE = _ensure_signed(VOICE_RATE)
VOICE_PITCH = _ensure_signed(VOICE_PITCH)
VOICE_VOLUME = _ensure_signed(VOICE_VOLUME)

async def _synth(text, path, voice=None, rate=None, pitch=None, volume=None):
    tts = Communicate(text, voice=voice or VOICE, rate=rate or VOICE_RATE,
                      pitch=pitch or VOICE_PITCH, volume=volume or VOICE_VOLUME)
    await tts.save(path)

def _audio_duration_ok(path, text):
    try:
        clip = AudioFileClip(path); dur = clip.duration; clip.close()
        return (dur >= max(MIN_AUDIO_S, len(text.split())/4.0)*0.5), dur
    except: return False, 0

def synth_one(text, index):
    key = hashlib.md5(text.encode()).hexdigest()[:12]
    cache_path = str(CACHE_DIR / "audio" / f"{key}.mp3")
    out_path = f"audio_{index}.mp3"; min_bytes = 8000
    if Path(cache_path).exists() and Path(cache_path).stat().st_size > min_bytes:
        ok, dur = _audio_duration_ok(cache_path, text)
        if ok:
            import shutil; shutil.copy(cache_path, out_path)
            log.info(f"Audio {index+1} desde cache ({dur:.1f}s)"); return out_path
    for attempt in range(TTS_RETRIES):
        use_fallback = attempt >= 2
        try:
            if Path(out_path).exists(): os.remove(out_path)
            if use_fallback:
                v = FALLBACK_VOICE
                asyncio.run(_synth(text, out_path, voice=v["voice"], rate=v["rate"], pitch=v["pitch"], volume=v["volume"]))
            else:
                asyncio.run(_synth(text, out_path))
            p = Path(out_path)
            if not p.exists() or p.stat().st_size < min_bytes:
                log.warning(f"Audio {index+1} muy pequeno, reintento {attempt+1}..."); time.sleep(2+attempt); continue
            ok, dur = _audio_duration_ok(out_path, text)
            if ok:
                import shutil; shutil.copy(out_path, cache_path)
                log.success(f"Audio {index+1} OK ({p.stat().st_size//1024}KB, {dur:.1f}s)"); return out_path
            log.warning(f"Audio {index+1} muy corto ({dur:.1f}s), reintento {attempt+1}...")
        except Exception as e:
            log.warning(f"Audio {index+1} intento {attempt+1}: {e}")
        time.sleep(2+attempt)
    log.error(f"Audio {index+1} fallo — silencio"); _make_silence(out_path, 3.0); return out_path

def synth_all_sequential(scenes):
    paths = {}
    for i,scene in enumerate(scenes):
        paths[i] = synth_one(scene["text"], i); time.sleep(0.5)
    return paths

def _make_silence(path, duration=3.0):
    import struct, wave as wv
    sr = 44100; samples = int(sr*duration)
    data = struct.pack("<"+"h"*samples, *([0]*samples))
    with wv.open(path,"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(data)

# ═══════════════════════════════════════════════════════════
#  MUSICA
# ═══════════════════════════════════════════════════════════
MUSIC_MOODS = ["tense","ethereal","ominous"]
_chosen_mood = random.choice(MUSIC_MOODS)
log.info(f"Mood musical: {_chosen_mood}")

FREESOUND_QUERIES = {
    "tense":    ["dark trap beat loop","horror tension cinematic loop","dark suspense music loop","thriller psychological background"],
    "ethereal": ["dark lofi chill background","cinematic dark ambient pad loop","mysterious psychological atmosphere","soft dark cinematic drone"],
    "ominous":  ["dark ominous cinematic loop","horror psychological ambient","dark mystery background music","sinister atmospheric drone"],
}

def try_freesound_music(duration, mood):
    api_key = os.environ.get("FREESOUND_API_KEY","")
    if not api_key:
        log.warning("FREESOUND_API_KEY no configurada — musica sintetica"); return None
    queries = FREESOUND_QUERIES.get(mood, FREESOUND_QUERIES["ominous"])[:]
    random.shuffle(queries)
    for query in queries:
        try:
            params = {"query": query, "token": api_key,
                      "filter": 'duration:[20 TO 300] license:("Creative Commons 0" OR "Attribution")',
                      "fields": "id,name,previews,duration,license", "sort": "rating_desc", "page_size": 10}
            r = requests.get("https://freesound.org/apiv2/search/text/", params=params, timeout=20)
            if r.status_code != 200: continue
            results = r.json().get("results", [])
            if not results: continue
            random.shuffle(results)
            for sound in results[:5]:
                preview_url = sound.get("previews",{}).get("preview-hq-mp3")
                if not preview_url: continue
                ar = requests.get(preview_url, timeout=30)
                if ar.status_code == 200 and len(ar.content) > 50000:
                    path = "freesound_music.mp3"
                    with open(path,"wb") as f: f.write(ar.content)
                    log.success(f"Freesound OK: {sound.get('name','?')} ({query})"); return path
        except Exception as e: log.warning(f"  Freesound '{query}': {e}")
    log.warning("Freesound: no encontrado — musica sintetica"); return None

def _lowpass_noise(length, sr, cutoff_hz=300, std=0.02):
    raw = np.random.normal(0, std, length).astype(np.float32)
    fft = np.fft.rfft(raw); freqs = np.fft.rfftfreq(length, 1/sr)
    fft[freqs > cutoff_hz] = 0
    return np.fft.irfft(fft, n=length).astype(np.float32)

def generate_music(duration=60, mood=None):
    mood = mood or _chosen_mood
    try:
        sr = 44100; t = np.linspace(0, duration, int(sr*duration), dtype=np.float32)
        base_hz = random.choice([41.2,43.65,46.25,55.0,49.0,36.71])
        music  = 0.30*np.sin(2*np.pi*base_hz*t)
        music += 0.18*np.sin(2*np.pi*base_hz*1.498*t)
        music += 0.12*np.sin(2*np.pi*base_hz*1.782*t)
        music += 0.08*np.sin(2*np.pi*base_hz*2.0*t)
        music += 0.05*np.sin(2*np.pi*base_hz*2.997*t)
        music += 0.04*np.sin(2*np.pi*base_hz*0.5*t)
        pulse_rate = {"tense": random.uniform(0.12,0.18), "ethereal": random.uniform(0.03,0.06)}.get(mood, random.uniform(0.06,0.10))
        music *= 0.45 + 0.55*np.sin(2*np.pi*pulse_rate*t)
        shz = random.choice([220,277,330,370,415])
        music += 0.03*np.sin(2*np.pi*shz*t)*np.sin(2*np.pi*random.uniform(0.18,0.28)*t)
        music += 0.09*np.sin(2*np.pi*25*t)*(0.4+0.6*np.sin(2*np.pi*0.04*t))
        music += _lowpass_noise(len(t), sr)*(0.4+0.6*np.sin(2*np.pi*0.05*t))
        fade = int(sr*3); music[:fade] *= np.linspace(0,1,fade); music[-fade:] *= np.linspace(1,0,fade)
        music = music/(np.max(np.abs(music))+1e-9)*0.32
        wav = "bg_music.wav"
        with wave.open(wav,"w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes((music*32767).astype(np.int16).tobytes())
        log.success(f"Musica sintetica OK ({duration}s, mood={mood})"); return wav
    except Exception as e: log.error(f"Error musica: {e}"); return None

def get_background_music(duration, mood=None):
    mood = mood or _chosen_mood
    real = try_freesound_music(duration, mood)
    if real: return real, "freesound"
    return generate_music(duration=duration, mood=mood), "synthetic"

# ═══════════════════════════════════════════════════════════
#  BUILD SCENE
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration+0.8, MIN_AUDIO_S+1)
    total_frames = int(duration*FPS); words = text.split(); total_words = len(words)
    reveal_frames = int(FPS*1.3)
    log.info(f"  Escena {scene_idx+1}: {total_frames}f / {duration:.1f}s / {total_words}p")
    frames = []
    for f in range(total_frames):
        t = f/FPS; zoomed = zoom_frame(base_img, t, duration); base_arr = np.array(zoomed)
        wp = min(total_words, int(total_words*(f/reveal_frames))) if f < reveal_frames else total_words
        frame = render_text_frame(base_arr, text, wp, f, scene_idx, total_scenes)
        if f < 5: frame = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))
    def make_frame(t): return frames[min(int(t*FPS), len(frames)-1)]
    clip = VideoClip(make_frame, duration=duration); clip = clip.set_audio(audio)
    return clip.fadein(0.3).fadeout(0.3)

# ═══════════════════════════════════════════════════════════
#  CHECKLIST
# ═══════════════════════════════════════════════════════════
def validate_video(path, title, description, tags):
    errors = []
    try:
        from moviepy.editor import VideoFileClip
        vc = VideoFileClip(path); d = vc.duration; has_audio = vc.audio is not None; vc.close()
        if d < MIN_VIDEO_DURATION: errors.append(f"Demasiado corto: {d:.1f}s")
        if d > MAX_VIDEO_DURATION: errors.append(f"Demasiado largo: {d:.1f}s")
        if not has_audio: errors.append("Sin audio")
    except Exception as e: errors.append(f"No se puede abrir: {e}")
    if not Path(path).exists(): errors.append("Archivo no encontrado")
    elif Path(path).stat().st_size < 500_000: errors.append("Archivo muy pequeno")
    if len(title) > 60: errors.append(f"Titulo muy largo ({len(title)})")
    if not description: errors.append("Sin descripcion")
    if len(tags) < 5: errors.append("Pocos tags")
    if errors:
        for e in errors: log.error(f"CHECKLIST FALLO: {e}")
        return False
    log.success("Checklist superado"); return True

# ═══════════════════════════════════════════════════════════
#  BUILD VIDEO
# ═══════════════════════════════════════════════════════════
def build_video(scenes):
    total = len(scenes)
    log.info("Generando imagenes...")
    img_paths = {}
    for i,scene in enumerate(scenes):
        img_paths[i] = generate_image(scene["prompt"], i); time.sleep(1.5)
    log.info("Generando audio...")
    audio_paths = synth_all_sequential(scenes)
    clips = []
    for i,scene in enumerate(scenes):
        log.info(f"Construyendo escena {i+1}/{total}: {scene['text'][:40]}...")
        base_img = add_vignette(Image.open(img_paths[i]).convert("RGB"))
        clips.append(build_scene(base_img, audio_paths[i], scene["text"], i, total))
    final = concatenate_videoclips(clips, method="compose")
    final_duration = final.duration
    log.info(f"Duracion total: {final_duration:.1f}s")

    voice_only = "viral_short_voice_only.mp4"
    log.info("Renderizando video con voz...")
    final.write_videofile(voice_only, fps=FPS, codec="libx264", audio_codec="aac",
                          bitrate="12000k", preset="fast", threads=4,
                          ffmpeg_params=["-crf","18"], logger=None)

    music_path, music_source = get_background_music(duration=int(final_duration)+8)
    output = "viral_short.mp4"
    if music_path and Path(music_path).exists():
        try:
            probe = subprocess.run(
                ["ffprobe","-v","error","-show_entries","format=duration",
                 "-of","default=noprint_wrappers=1:nokey=1", music_path],
                capture_output=True, text=True, timeout=20)
            if float(probe.stdout.strip() or 0) < 1.0:
                log.warning("Musica invalida, regenerando..."); music_path = generate_music(int(final_duration)+8); music_source = "synthetic"
            music_volume = 0.35 if music_source == "freesound" else 0.45
            cmd = ["ffmpeg","-y","-i",voice_only,"-i",music_path,
                   "-filter_complex",
                   f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{final_duration},volume={music_volume}[music];"
                   f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                   "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",output]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and Path(output).stat().st_size > 500_000:
                log.success(f"Musica mezclada OK ({music_source}, vol={music_volume})")
            else:
                log.warning(f"ffmpeg mix fallo: {result.stderr[-300:]}"); import shutil; shutil.copy(voice_only, output)
        except Exception as e:
            log.warning(f"Error mezcla musica: {e}"); import shutil; shutil.copy(voice_only, output)
    else:
        log.warning("Sin musica — solo voz"); import shutil; shutil.copy(voice_only, output)
    return output

# ═══════════════════════════════════════════════════════════
#  YOUTUBE UPLOAD
# ═══════════════════════════════════════════════════════════
def upload_to_youtube(video_path, title, description, tags):
    log.info("Subiendo a YouTube...")
    from googleapiclient.discovery import build as yt_build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tf.write(os.environ["TOKEN_JSON"]); token_path = tf.name
    try:
        creds = Credentials.from_authorized_user_file(token_path, scopes=["https://www.googleapis.com/auth/youtube.upload"])
        youtube = yt_build("youtube","v3",credentials=creds)
        for attempt in range(UPLOAD_RETRIES):
            try:
                response = youtube.videos().insert(
                    part="snippet,status",
                    body={"snippet": {"title": title,
                                      "description": description + "\n\n#psicologia #psicologiaoscura #mente #shorts #viral #cerebro #manipulacion #jovenes #relaciones",
                                      "tags": tags, "categoryId": "22"},
                          "status": {"privacyStatus": "public"}},
                    media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
                ).execute()
                vid = response["id"]
                log.success(f"SUBIDO: https://www.youtube.com/watch?v={vid}"); return vid
            except Exception as e:
                log.error(f"Intento upload {attempt+1}: {e}")
                if attempt < UPLOAD_RETRIES-1: time.sleep(15*(attempt+1))
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
        with open(csv_path,"a",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new: w.writerow(["fecha","video_id","url","titulo","tema","voz","tema_visual","mood","duracion_s","escenas"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M"), video_id or "FALLO",
                        f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                        script["title"], script.get("_topic",""),
                        VOICE, THEME["name"], _chosen_mood, f"{duration:.1f}", len(script.get("scenes",[]))])
        log.success("Metadata guardada")
    except Exception as e: log.warning(f"Error metadata: {e}")

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("="*55)
    log.info("  BOT YOUTUBE V6 — PSICOLOGIA EN ESPANOL")
    log.info("="*55)

    if not check_upload_guard():
        log.info("Guard activo — saliendo sin duplicar")
        exit(0)

    script = generate_script()
    log.info(f"Titulo : {script['title']}")
    log.info(f"Escenas: {len(script['scenes'])}")

    video = build_video(script["scenes"])

    try:
        from moviepy.editor import VideoFileClip
        _vc = VideoFileClip(video); video_duration = _vc.duration; _vc.close()
    except: video_duration = 0.0

    if not validate_video(video, script["title"], script["description"], script["tags"]):
        log.error("Checklist fallo — abortando upload")
        log_video_metadata(None, script, video_duration); exit(1)

    video_id = upload_to_youtube(video, script["title"], script["description"], script["tags"])
    if video_id:
        update_upload_guard(video_id)
    log_video_metadata(video_id, script, video_duration)

    log.info("="*55)
    log.success("HECHO!")
    log.info("="*55)
