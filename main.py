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
NUM_SCENES = 5          # 5 escenas x ~2s = 10-12s total
MIN_AUDIO_S        = 1.2
MIN_IMAGE_KB       = 15
MIN_VIDEO_DURATION = 9
MAX_VIDEO_DURATION = 15
IMAGE_RETRIES      = 4
SCRIPT_RETRIES     = 5
UPLOAD_RETRIES     = 3
TTS_RETRIES        = 4

# Velocidad/tono variable por posicion de escena (estructura AGRT)
# 0=ALARMA: lenta y grave | 1=GAP: rapida | 2=REVELACION: la mas lenta y grave
# 3=CONSECUENCIA: normal  | 4=TRAMPA: pausa inicial + lenta
VOICE_CONFIG_BY_SCENE = {
    0: {"voice": "es-ES-AlvaroNeural", "rate": "+12%", "pitch": "-8Hz",  "volume": "+35%"},
    1: {"voice": "es-ES-AlvaroNeural", "rate": "+22%", "pitch": "-5Hz",  "volume": "+30%"},
    2: {"voice": "es-ES-AlvaroNeural", "rate": "+10%", "pitch": "-10Hz", "volume": "+32%"},
    3: {"voice": "es-ES-AlvaroNeural", "rate": "+20%", "pitch": "-5Hz",  "volume": "+30%"},
    4: {"voice": "es-ES-AlvaroNeural", "rate": "+12%", "pitch": "-6Hz",  "volume": "+33%"},
}
FALLBACK_VOICE = {"voice": "es-ES-AlvaroNeural", "rate": "+15%", "pitch": "-5Hz", "volume": "+30%"}

SUBTITLE_THEMES = [
    {"name": "blood_red",    "highlight": (220,15,15,230),   "accent": (220,15,15,255),  "label": (220,20,20,255)},
    {"name": "toxic_green",  "highlight": (40,200,90,230),   "accent": (40,200,90,255),  "label": (50,220,100,255)},
    {"name": "electric_blue","highlight": (30,140,240,230),  "accent": (30,140,240,255), "label": (50,160,255,255)},
    {"name": "violet",       "highlight": (160,40,220,230),  "accent": (160,40,220,255), "label": (180,60,240,255)},
    {"name": "gold",         "highlight": (230,170,20,230),  "accent": (230,170,20,255), "label": (240,190,40,255)},
]

_chosen_theme    = random.choice(SUBTITLE_THEMES)
VOICE            = "es-ES-AlvaroNeural"
THEME            = _chosen_theme
_ZOOM_INTENSITY  = random.uniform(0.02, 0.04)   # sutil para videos cortos

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

log.info(f"Voz: {VOICE} (config variable por escena)")
log.info(f"Tema visual: {THEME['name']}")

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
#  TEMAS
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

# 100 hooks clasificados por categoria
HOOKS_BY_CATEGORY = {
    "relaciones": [
        "Tu ex no te queria. Te necesitaba.",
        "Esa persona te esta usando y sonrie.",
        "Si te ignora a veces... ya te tiene.",
        "Lo que llamas amor, el lo llama control.",
        "Volvio cuando ya lo habias superado. No fue casualidad.",
        "El problema no eres tu. Es lo que toleras.",
        "Te quiere cuando le conviene. Eso tiene nombre.",
        "Hay personas que solo aparecen cuando te necesitan.",
        "La red flag mas grande no grita. Susurra.",
        "Si sientes que caminas sobre cascara de huevo... es senal.",
        "No te engano de golpe. Lo hizo poco a poco.",
        "Ese silencio no fue accidental.",
        "Te dejo en visto. No fue sin querer.",
        "Si siempre eres tu quien da... ya sabes la respuesta.",
        "Ese te quiero llego justo cuando ibas a irte.",
    ],
    "manipulacion": [
        "Alguien te esta manipulando ahora mismo sin saberlo.",
        "Los mejores manipuladores siempre parecen los mas amables.",
        "Te hicieron sentir culpable de algo que no hiciste.",
        "Si siempre acabas pidiendo perdon... algo falla.",
        "Te dieron un cumplido justo antes de pedirte algo.",
        "Hacerte sentir especial es la primera tecnica.",
        "La culpa que sientes... no es tuya.",
        "Alguien esta usando tu empatia en tu contra.",
        "Cuando dices no, esa persona se convierte en victima.",
        "Usan tus secretos como municion.",
        "El manipulador nunca empieza con una mentira grande.",
        "Antes de pedirte algo, siempre te hacen un favor.",
        "Te comparan con otros para que compitas.",
        "Siempre hay una excusa. Siempre.",
        "Si te hacen dudar de tu memoria, huye.",
    ],
    "narcisistas": [
        "Los narcisistas no cambian. Mejoran su actuacion.",
        "Te eligieron porque eres facil de moldear.",
        "El narcisista no te quiere. Te usa como espejo.",
        "Cuando los dejas, vuelven. No por amor. Por ego.",
        "El love bombing no es amor. Es anzuelo.",
        "Un narcisista te hace sentir elegido. Luego prescindible.",
        "Te destruyeron la autoestima para que los necesitaras mas.",
        "Te hicieron creer que sin ellos no eres nada.",
        "Sienten envidia de ti pero nunca lo admitiran.",
        "Si alguien necesita que siempre le des la razon... es senal.",
    ],
    "autoestima": [
        "Tu peor critico vive dentro de tu cabeza.",
        "Compararte en redes te esta costando tu paz.",
        "Cada vez que buscas su aprobacion, pierdes la tuya.",
        "La inseguridad no aparece sola. Alguien te la enseno.",
        "Tu cerebro recuerda el insulto y olvida el cumplido.",
        "Pides perdon por existir. Y eso es un problema.",
        "Si necesitas likes para sentirte bien... es mas grave.",
        "Sigues pensando en lo que dijo alguien hace anos.",
        "Tu miedo al rechazo esta tomando decisiones por ti.",
        "No te falta confianza. Te sobran criticas ajenas interiorizadas.",
    ],
    "cerebro": [
        "Tu cerebro te miente varias veces al dia.",
        "Hay un truco que usan para hacerte adicto a ellos.",
        "Tu mente reescribe los recuerdos para proteger tu ego.",
        "El cerebro trata el rechazo igual que el dolor fisico.",
        "Tu cerebro crea patrones donde no existen.",
        "Piensas que decides. Tu cerebro ya decidio.",
        "Por que no puedes olvidar ese momento vergonzoso.",
        "Tu mente busca lo que temes. Y eso lo empeora.",
        "Hay personas que activan tu dopamina a proposito.",
        "Eso que llamas intuicion... a veces es sesgo.",
    ],
    "ansiedad": [
        "Eso que sientes en el pecho tiene nombre.",
        "Analizas tanto que ya no puedes actuar.",
        "Tu mente inventa conversaciones que nunca ocurriran.",
        "Preparas respuestas para conversaciones que aun no han pasado.",
        "Si piensas demasiado por la noche... esto lo explica.",
        "Overpensar no es inteligencia. Es miedo disfrazado.",
        "Tu cuerpo avisa antes que tu mente.",
        "La verguenza de ayer sigue viva en tu cabeza hoy.",
        "El peor escenario que imaginas casi nunca pasa.",
        "La ansiedad no es debilidad. Es un sistema en alerta.",
    ],
    "dopamina": [
        "Tu cerebro esta atrapado en un casino invisible.",
        "Cada notificacion activa lo mismo que una droga.",
        "Por que vuelves a mirar el perfil de alguien que te hace dano.",
        "El scroll infinito fue disenado para enganar a tu cerebro.",
        "Esperar su mensaje activa exactamente lo mismo que apostar.",
    ],
    "redes": [
        "Llevas tres horas mirando vidas que no son reales.",
        "Silenciaste sus historias pero sigues mirando de incognito.",
        "Compararte con alguien en redes es compararte con su actuacion.",
        "Por que sientes vacio despues de dos horas de scroll.",
        "Esa foto tuya perfecta esconde algo que no dijiste.",
    ],
    "ghosting": [
        "No desaparecio sin razon. Calculo el momento.",
        "El ghosting no es cobardía. Es un mensaje sin palabras.",
        "Enviaste el ultimo mensaje. Y ahi sigue.",
        "No te merecio una explicacion porque te necesitaba disponible.",
        "El ghosting duele mas porque tu cerebro no puede cerrar el bucle.",
    ],
    "lenguaje_corporal": [
        "Su boca dijo que si. Su cuerpo dijo otra cosa.",
        "Hay un gesto que delata a alguien que te miente.",
        "Cuando alguien te copia los gestos... no es coincidencia.",
        "Sus pies te dicen lo que sus palabras ocultan.",
        "El contacto visual que te sostiene tres segundos de mas.",
    ],
}

TOPIC_TO_CATEGORY = {
    "ghosting": "ghosting",
    "narcisist": "narcisistas",
    "redes": "redes",
    "dopamina": "dopamina",
    "manipulac": "manipulacion",
    "autoestima": "autoestima",
    "ansiedad": "ansiedad",
    "cerebro": "cerebro",
    "lenguaje": "lenguaje_corporal",
    "relacion": "relaciones",
    "ex ": "relaciones",
    "amor": "relaciones",
    "crush": "relaciones",
    "celos": "relaciones",
    "toxico": "relaciones",
    "toxicas": "relaciones",
    "scroll": "dopamina",
    "movil": "dopamina",
}

def get_hook_for_topic(topic):
    topic_lower = topic.lower()
    for key, cat in TOPIC_TO_CATEGORY.items():
        if key in topic_lower:
            pool = HOOKS_BY_CATEGORY.get(cat, [])
            if pool:
                return random.choice(pool)
    all_hooks = [h for hooks in HOOKS_BY_CATEGORY.values() for h in hooks]
    return random.choice(all_hooks)

# ═══════════════════════════════════════════════════════════
#  GROQ — guion AGRT de 5 escenas para Short de 10-12s
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
    hook = get_hook_for_topic(topic)
    log.info(f"Tema: {topic}")
    log.info(f"Hook: {hook}")

    prompt = (
        "Eres el mejor creador de Shorts de psicologia del mundo.\n"
        "Escribes para jovenes de 16 a 24 anos.\n"
        "Tu unico objetivo es que el video se vea completo y se repita en bucle.\n\n"
        f"TEMA: {topic}\n"
        f"LA FRASE 1 DEBE SER EXACTAMENTE: '{hook}'\n\n"
        "FORMATO OBLIGATORIO: 5 frases, estructura AGRT.\n\n"
        "FRASE 1 - ALARMA: usa el hook exacto de arriba.\n"
        "Crea incomodidad inmediata. El espectador debe parar el scroll.\n\n"
        "FRASE 2 - GAP (6-8 palabras):\n"
        "Amplia el gancho pero NO lo expliques.\n"
        "El espectador debe pensar: como? por que? a mi?\n\n"
        "FRASE 3 - REVELACION (7-9 palabras):\n"
        "La verdad inesperada. Contradice lo que el espectador creia.\n"
        "Empieza con: Tu cerebro... / Lo llaman... / La razon es... / Eso se llama...\n"
        "Usa '...' en esta frase para la pausa dramatica.\n\n"
        "FRASE 4 - CONSECUENCIA (6-8 palabras):\n"
        "Conecta la revelacion con la vida del espectador AHORA MISMO.\n"
        "Usa: cada vez que / hoy mismo / en este momento / sin que lo notes.\n\n"
        "FRASE 5 - TRAMPA (5-8 palabras):\n"
        "Elige UNA opcion:\n"
        "A) Pregunta directa y personal que solo se responde en comentarios.\n"
        "B) Afirmacion que genera disonancia y obliga a rebobinar.\n"
        "NUNCA termines con dale like ni sigueme.\n\n"
        "REGLAS ABSOLUTAS:\n"
        "- TODO en espanol, tutear siempre\n"
        "- Cada frase: 5-9 palabras MAXIMO\n"
        "- Total del guion: 30-42 palabras\n"
        "- Cero palabras academicas\n"
        "- Cero relleno: en realidad, de hecho, basicamente\n"
        "- Una sola idea por frase\n"
        "- Usa '...' solo en la frase 3, no en las demas\n\n"
        "REGLAS DE IMAGENES (prompts en ingles, 40-60 palabras):\n"
        "Composicion por frase (no repetir el mismo tipo):\n"
        "  Frase 1: Extreme close-up face\n"
        "  Frase 2: Medium shot torso up\n"
        "  Frase 3: Dutch angle medium shot\n"
        "  Frase 4: Over-the-shoulder or POV\n"
        "  Frase 5: Direct eye contact looking at camera\n"
        "Protagonista: joven 18-22 anos, streetwear, hoodie oversized.\n"
        "Escenario: bedroom con luz de pantalla, calle nocturna neon, metro vacio, instituto.\n"
        "Un simbolo psicologico distinto por imagen (no repetir):\n"
        "  manos invisibles tirando hilos, espejo con reflejo diferente,\n"
        "  notificaciones flotando, sombra que no coincide, cuerda en el pecho,\n"
        "  mascara cayendo, ojos multiples en el fondo, reloj derritiendose.\n"
        "Luz: azul frio=soledad, rojo=peligro, morado=poder, dorado=revelacion.\n"
        "Siempre incluir: cinematic, 8k, ultra detailed, masterpiece, no text, no watermark, 9:16 vertical.\n\n"
        "Devuelve UNICAMENTE JSON valido:\n"
        "{\n"
        "  \"title\": \"titulo llamativo maximo 55 caracteres\",\n"
        "  \"description\": \"una frase de 15-20 palabras\",\n"
        "  \"tags\": [\"psicologia\",\"mente\",\"cerebro\",\"manipulacion\",\"relaciones\",\"autoestima\",\"shorts\",\"viral\",\"jovenes\",\"comportamiento\"],\n"
        "  \"scenes\": [\n"
        "    {\"text\": \"frase 1\", \"prompt\": \"imagen 1 en ingles\"},\n"
        "    {\"text\": \"frase 2\", \"prompt\": \"imagen 2 en ingles\"},\n"
        "    {\"text\": \"frase 3\", \"prompt\": \"imagen 3 en ingles\"},\n"
        "    {\"text\": \"frase 4\", \"prompt\": \"imagen 4 en ingles\"},\n"
        "    {\"text\": \"frase 5\", \"prompt\": \"imagen 5 en ingles\"}\n"
        "  ]\n"
        "}\n\n"
        "No escribas nada mas. Solo JSON."
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 2000,
    }

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
            if "scenes" not in script or len(script["scenes"]) < 4:
                log.warning(f"Solo {len(script.get('scenes',[]))} escenas, reintentando..."); continue
            # Asegurar exactamente NUM_SCENES escenas
            while len(script["scenes"]) < NUM_SCENES:
                script["scenes"].append(random.choice(script["scenes"]).copy())
            script["scenes"] = script["scenes"][:NUM_SCENES]
            script["_topic"] = topic
            # Recortar frases que excedan 10 palabras
            for i, scene in enumerate(script["scenes"]):
                words = scene["text"].split()
                if len(words) > 10:
                    scene["text"] = " ".join(words[:9])
                    log.warning(f"Frase {i+1} recortada a 9 palabras")
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
            "title": "Tu cerebro te esta mintiendo ahora",
            "description": "El mecanismo psicologico que toma decisiones por ti sin que lo sepas.",
            "tags": ["psicologia","mente","cerebro","manipulacion","relaciones","autoestima","shorts","viral","jovenes","comportamiento"],
            "scenes": [
                {"text": "Tu cerebro te miente varias veces al dia.",
                 "prompt": "Extreme close-up young man 20yo face, eyes wide with sudden realization, invisible puppet strings glowing red attached to temples, dark bedroom lit only by cold blue phone screen, psychological thriller, cinematic, 8k, ultra detailed, masterpiece, no text, no watermark, 9:16 vertical"},
                {"text": "Y lo peor es que no puedes detectarlo.",
                 "prompt": "Medium shot young woman 19yo sitting on bed, hands covering face partially, distorted reflection in phone screen showing different expression, neon blue bedroom light, emotional, cinematic, ultra detailed, masterpiece, no text, 9:16 vertical"},
                {"text": "Tu mente reescribe los recuerdos... para protegerte.",
                 "prompt": "Dutch angle young person 21yo in dark corridor, film reel unspooling from their head with different memory frames visible, moody purple light, psychological surrealism, cinematic, 8k, masterpiece, no text, 9:16 vertical"},
                {"text": "Por eso siempre te ves como el heroe.",
                 "prompt": "Over-the-shoulder shot young man 20yo looking at group of friends, his shadow on wall shows him larger and central while real shadow is small, urban park night, neon street light, cinematic, ultra detailed, no text, 9:16 vertical"},
                {"text": "Cuantas veces te ha mentido solo hoy?",
                 "prompt": "Young woman 21yo direct intense eye contact with camera, calm knowing expression, slight half-smile, dark urban rooftop night, city lights blurred behind, dramatic single spotlight, masterpiece, 8k, cinematic, no text, 9:16 vertical"},
            ],
        },
        {
            "title": "El ghosting no es lo que crees",
            "description": "La verdad psicologica detras de desaparecer sin dar explicaciones.",
            "tags": ["psicologia","ghosting","relaciones","mente","cerebro","manipulacion","shorts","viral","jovenes","comportamiento"],
            "scenes": [
                {"text": "No desaparecio sin razon. Calculo el momento.",
                 "prompt": "Extreme close-up young woman 20yo eyes staring at phone screen showing last message sent days ago, cold blue light on face, clock hands visible faintly superimposed, cinematic, 8k, ultra detailed, masterpiece, no text, no watermark, 9:16 vertical"},
                {"text": "Y eso es mucho peor que el abandono.",
                 "prompt": "Medium shot young man 19yo at subway late night, empty car, ghost silhouette of person sitting next to him fading into air, purple moody light, psychological thriller, cinematic, masterpiece, no text, 9:16 vertical"},
                {"text": "El ghosting activa el mismo dolor... que una perdida real.",
                 "prompt": "Dutch angle young person 21yo clutching chest, visible heartbeat pulse radiating outward like sonar waves, dark apartment single overhead lamp, psychological symbolism, 8k, cinematic, ultra detailed, no text, 9:16 vertical"},
                {"text": "Tu cerebro busca el cierre que no llego.",
                 "prompt": "POV shot hands holding phone with unanswered conversation thread, cold screen light illuminating hands dramatically, urban cafe window rain outside, cinematic, ultra detailed, masterpiece, no text, 9:16 vertical"},
                {"text": "Cuantos dias llevas esperando esa respuesta?",
                 "prompt": "Young woman 20yo direct camera stare, calm but eyes holding back emotion, rooftop night city lights below, warm golden backlight contrasting cold blue phone glow, cinematic portrait, 8k, masterpiece, no text, 9:16 vertical"},
            ],
        },
        {
            "title": "Alguien te controla sin que lo notes",
            "description": "Las tecnicas de manipulacion silenciosa que se usan en relaciones cotidianas.",
            "tags": ["psicologia","manipulacion","relaciones","mente","cerebro","autoestima","shorts","viral","jovenes","comportamiento"],
            "scenes": [
                {"text": "Alguien te esta manipulando ahora mismo sin saberlo.",
                 "prompt": "Extreme close-up young man 20yo face, micro-expression of unease mixed with affection, invisible hand pressing gently on his chest from outside frame, dark bedroom warm amber light turning cold blue, cinematic, 8k, masterpiece, no text, no watermark, 9:16 vertical"},
                {"text": "Y probablemente lo llamas carino.",
                 "prompt": "Medium shot young couple 19-21yo, she smiling warmly at him, his shadow on wall behind forms controlling silhouette with strings, warm apartment light with cold edge, psychological thriller, cinematic, ultra detailed, no text, 9:16 vertical"},
                {"text": "Tu cerebro no distingue amor... de dependencia.",
                 "prompt": "Dutch angle young woman 20yo sitting alone at cafe table, brain cross-section glowing faintly visible through skull with two pathways labeled differently, purple neon light from window, surrealism, cinematic, 8k, no text, 9:16 vertical"},
                {"text": "Por eso vuelves aunque te haga dano.",
                 "prompt": "Over-the-shoulder young man 21yo walking toward same apartment door again, ghost version of himself walking away reflected in puddle below, neon street night rain, cinematic, ultra detailed, masterpiece, no text, 9:16 vertical"},
                {"text": "Cuantas veces has vuelto ya?",
                 "prompt": "Young woman 21yo direct confrontational eye contact with camera, quiet anger in calm face, dark minimal background, single dramatic overhead light, intense cinematic portrait, 8k, masterpiece, no text, 9:16 vertical"},
            ],
        },
    ]
    return random.choice(options)

# ═══════════════════════════════════════════════════════════
#  IMAGE GENERATION
# ═══════════════════════════════════════════════════════════
IMAGE_STYLES = [
    "cinematic digital art, ultra detailed, masterpiece, dramatic lighting, emotional, 8k",
    "realistic cinematic illustration, psychological thriller, Netflix movie poster style, ultra detailed",
    "photorealistic cinematic portrait, psychological tension, dramatic lighting, 8k, masterpiece",
    "Netflix psychological thriller scene, ultra detailed, cinematic, dramatic lighting, masterpiece",
    "high-end concept art, realistic faces, dramatic shadows, cinematic composition, masterpiece, 8k",
    "dark surrealism, symbolic psychology, dreamlike, emotional, cinematic lighting, masterpiece",
    "cyberpunk psychological atmosphere, neon lights, cinematic, ultra detailed, dramatic shadows",
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

    style = random.choice(IMAGE_STYLES)
    full_prompt = (
        f"{prompt}, {style}, "
        "young protagonist 18-22 years old modern streetwear hoodie oversized, "
        "contemporary urban setting, strong psychological symbolism, "
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
#  TEXT RENDERER
#  Highlight en palabra 2-3 segun la escena (no siempre la ultima)
# ═══════════════════════════════════════════════════════════
def get_emphasis_word_index(scene_idx, total_words):
    if scene_idx == 0 and total_words >= 3:
        return 2    # tercera palabra — la mas impactante del hook
    if scene_idx == 2 and total_words >= 4:
        return 3    # cuarta palabra — el dato clave de la revelacion
    return total_words - 1  # ultima para el resto

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
    total_words = len(words)
    emphasis_idx = get_emphasis_word_index(scene_num, total_words)
    lines = textwrap.wrap(" ".join(shown), width=14)
    line_h = 88; text_y = bar_y + 26

    global_word_idx = 0
    for li, line in enumerate(lines):
        line_words = line.split()
        total_w_px = sum(
            draw.textbbox((0,0), ww+" ", font=font_main)[2] -
            draw.textbbox((0,0), ww+" ", font=font_main)[0]
            for ww in line_words
        )
        x = (w-total_w_px)//2; y = text_y + li*line_h
        for wi, ww in enumerate(line_words):
            bb = draw.textbbox((0,0), ww+" ", font=font_main)
            ww_ = ww+" "; ww_w = bb[2]-bb[0]
            is_emphasis = (global_word_idx == emphasis_idx and word_progress > emphasis_idx)
            if is_emphasis:
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
            global_word_idx += 1

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
#  TTS — velocidad y tono variables por escena
# ═══════════════════════════════════════════════════════════
def _ensure_signed(v):
    return v if v.startswith(("+","-")) else f"+{v}"

async def _synth(text, path, rate, pitch, volume):
    tts = Communicate(
        text, voice=VOICE,
        rate=_ensure_signed(rate),
        pitch=_ensure_signed(pitch),
        volume=_ensure_signed(volume),
    )
    await tts.save(path)

def _prepend_silence(audio_path, silence_s=0.3):
    """Añade silencio al inicio del audio (para la escena trampa final)."""
    try:
        import struct, wave as wv
        sr = 44100; samples = int(sr * silence_s)
        silence_data = struct.pack("<" + "h" * samples, *([0] * samples))
        sil_path = audio_path + "_silence.wav"
        with wv.open(sil_path, "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(silence_data)
        out_path = audio_path + "_padded.mp3"
        cmd = ["ffmpeg", "-y",
               "-i", sil_path, "-i", audio_path,
               "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[aout]",
               "-map", "[aout]", "-c:a", "libmp3lame", out_path]
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        if result.returncode == 0:
            import shutil; shutil.move(out_path, audio_path)
        Path(sil_path).unlink(missing_ok=True)
    except Exception as e:
        log.warning(f"prepend_silence fallo: {e}")

def _audio_duration_ok(path, text):
    try:
        clip = AudioFileClip(path); dur = clip.duration; clip.close()
        return (dur >= max(MIN_AUDIO_S, len(text.split())/5.0)*0.5), dur
    except: return False, 0

def synth_one(text, index):
    config = VOICE_CONFIG_BY_SCENE.get(index, FALLBACK_VOICE)
    add_silence = (index == NUM_SCENES - 1)  # pausa de 0.3s en escena trampa

    key = hashlib.md5((text + str(index)).encode()).hexdigest()[:12]
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
            v = FALLBACK_VOICE if use_fallback else config
            asyncio.run(_synth(text, out_path, v["rate"], v["pitch"], v["volume"]))
            p = Path(out_path)
            if not p.exists() or p.stat().st_size < min_bytes:
                log.warning(f"Audio {index+1} muy pequeno, reintento {attempt+1}..."); time.sleep(2+attempt); continue
            ok, dur = _audio_duration_ok(out_path, text)
            if ok:
                if add_silence:
                    _prepend_silence(out_path, 0.3)
                import shutil; shutil.copy(out_path, cache_path)
                log.success(f"Audio {index+1} OK | rate={v['rate']} pitch={v['pitch']} | {dur:.1f}s")
                return out_path
            log.warning(f"Audio {index+1} muy corto ({dur:.1f}s), reintento {attempt+1}...")
        except Exception as e:
            log.warning(f"Audio {index+1} intento {attempt+1}: {e}")
        time.sleep(2+attempt)

    log.error(f"Audio {index+1} fallo — silencio"); _make_silence(out_path, 2.0); return out_path

def synth_all_sequential(scenes):
    paths = {}
    for i, scene in enumerate(scenes):
        paths[i] = synth_one(scene["text"], i); time.sleep(0.5)
    return paths

def _make_silence(path, duration=2.0):
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

def generate_music(duration=30, mood=None):
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
        fade = int(sr*2); music[:fade] *= np.linspace(0,1,fade); music[-fade:] *= np.linspace(1,0,fade)
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
#  BUILD SCENE — silencio visual +1.2s en escena final (loop)
# ═══════════════════════════════════════════════════════════
def build_scene(base_img, audio_path, text, scene_idx, total_scenes):
    audio = AudioFileClip(audio_path)
    # Escena trampa: +1.2s de imagen estática sin voz para favorecer el loop
    extra_silence = 1.2 if scene_idx == total_scenes - 1 else 0.0
    duration = max(audio.duration + 0.6 + extra_silence, MIN_AUDIO_S + 0.5)
    total_frames = int(duration*FPS)
    words = text.split(); total_words = len(words)
    reveal_frames = int(FPS * 0.9)   # revelacion de palabras mas rapida en shorts cortos
    log.info(f"  Escena {scene_idx+1}: {total_frames}f / {duration:.1f}s / {total_words}p")
    frames = []
    for f in range(total_frames):
        t = f/FPS; zoomed = zoom_frame(base_img, t, duration); base_arr = np.array(zoomed)
        wp = min(total_words, int(total_words*(f/reveal_frames))) if f < reveal_frames else total_words
        frame = render_text_frame(base_arr, text, wp, f, scene_idx, total_scenes)
        if f < 5: frame = glitch_frame(frame, intensity=5)
        frames.append(frame.astype(np.uint8))
    def make_frame(t): return frames[min(int(t*FPS), len(frames)-1)]
    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    return clip.fadein(0.2).fadeout(0.2)

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
    elif Path(path).stat().st_size < 300_000: errors.append("Archivo muy pequeno")
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
    for i, scene in enumerate(scenes):
        img_paths[i] = generate_image(scene["prompt"], i); time.sleep(1.5)
    log.info("Generando audio...")
    audio_paths = synth_all_sequential(scenes)
    clips = []
    for i, scene in enumerate(scenes):
        log.info(f"Construyendo escena {i+1}/{total}: {scene['text'][:50]}...")
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

    music_path, music_source = get_background_music(duration=int(final_duration)+5)
    output = "viral_short.mp4"
    if music_path and Path(music_path).exists():
        try:
            probe = subprocess.run(
                ["ffprobe","-v","error","-show_entries","format=duration",
                 "-of","default=noprint_wrappers=1:nokey=1", music_path],
                capture_output=True, text=True, timeout=20)
            if float(probe.stdout.strip() or 0) < 1.0:
                log.warning("Musica invalida, regenerando...")
                music_path = generate_music(int(final_duration)+5); music_source = "synthetic"
            music_volume = 0.35 if music_source == "freesound" else 0.45
            cmd = ["ffmpeg","-y","-i",voice_only,"-i",music_path,
                   "-filter_complex",
                   f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{final_duration},volume={music_volume}[music];"
                   f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                   "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",output]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and Path(output).stat().st_size > 300_000:
                log.success(f"Musica mezclada OK ({music_source}, vol={music_volume})")
            else:
                log.warning(f"ffmpeg mix fallo: {result.stderr[-300:]}")
                import shutil; shutil.copy(voice_only, output)
        except Exception as e:
            log.warning(f"Error mezcla musica: {e}")
            import shutil; shutil.copy(voice_only, output)
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
            if is_new:
                w.writerow(["fecha","video_id","url","titulo","tema","tema_visual","mood","duracion_s","escenas"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M"), video_id or "FALLO",
                        f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                        script["title"], script.get("_topic",""),
                        THEME["name"], _chosen_mood, f"{duration:.1f}", len(script.get("scenes",[]))])
        log.success("Metadata guardada")
    except Exception as e: log.warning(f"Error metadata: {e}")

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("="*55)
    log.info("  BOT YOUTUBE V7 — PSICOLOGIA SHORTS 10-12s")
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
