import os, asyncio, random, requests, numpy as np, textwrap, json, time
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from edge_tts import Communicate

W, H = 1080, 1920
FPS = 30

# ── GEMINI ────────────────────────────────────────────────────────────────────
def generate_script_with_gemini():
    api_key = os.environ["GEMINI_API_KEY"]

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
        "how dopamine is used to control you"
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
    {{"text": "first scene narrator text, dramatic pauses with three dots, max 18 words, dark tone", "prompt": "dark anime art, specific unique scene, ultra detailed, 4k cinematic, dramatic lighting, no text no watermark"}},
    {{"text": "second scene narrator text, dramatic pauses with three dots, max 18 words, dark tone", "prompt": "dark anime art, specific unique scene different from first, ultra detailed, 4k cinematic, no text no watermark"}},
    {{"text": "third scene narrator text, dramatic pauses with three dots, max 18 words, dark tone", "prompt": "dark anime art, specific unique scene different from others, ultra detailed, 4k cinematic, no text no watermark"}},
    {{"text": "fourth scene narrator text, dramatic pauses with three dots, max 18 words, dark tone", "prompt": "dark anime art, specific unique scene different from others, ultra detailed, 4k cinematic, no text no watermark"}},
    {{"text": "fifth scene narrator text, dramatic pauses with three dots, max 18 words, dark tone", "prompt": "dark anime art, epic final scene different from all others, ultra detailed, 4k cinematic, no text no watermark"}}
  ]
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 1500
        }
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        print(f"  Gemini status: {r.status_code}")
        data = r.json()

        if "candidates" not in data:
            print(f"  Gemini response: {json.dumps(data)[:300]}")
            return get_fallback_script(topic)

        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        script = json.loads(raw)
        print(f"  Gemini OK: {script['title']}")
        return script

    except Exception as e:
        print(f"  Gemini error: {e}")
        return get_fallback_script(topic)

def get_fallback_script(topic="manipulation"):
    seed = int(time.time())
    random.seed(seed)

    all_scripts = [
        {
            "title": "3 Dark Psychology Tricks Used Against You Daily",
            "description": "The hidden manipulation tactics used on you every single day. Stay aware.",
            "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
            "scenes": [
                {"text": "Every single day... someone manipulates your decisions without you noticing.", "prompt": f"dark anime art, shadowy puppet master controlling strings on human silhouette, crimson black palette, ultra detailed cinematic 4k, seed{seed}1"},
                {"text": "The foot-in-the-door trick... makes you agree to big things after small ones.", "prompt": f"dark anime, massive door opening into endless void, eerie green glow, ultra detailed cinematic 4k, seed{seed}2"},
                {"text": "Scarcity makes your brain panic... and bypass all rational thinking instantly.", "prompt": f"dark anime, cracked hourglass crimson sand draining fast, chiaroscuro lighting, ultra detailed 4k, seed{seed}3"},
                {"text": "Social proof hijacks your mind... you copy others without realizing it.", "prompt": f"dark anime, crowd of identical shadowy figures one glowing different, eerie ultra detailed 4k, seed{seed}4"},
                {"text": "Now that you know these tricks... you can protect your mind forever.", "prompt": f"dark anime epic, warrior breaking free from shadow chains into blazing light, ultra detailed cinematic 4k, seed{seed}5"}
            ]
        },
        {
            "title": "Signs Someone Is Secretly Manipulating You",
            "description": "Subtle signs that reveal when dark psychology is being used against you.",
            "tags": ["manipulation","darkpsychology","toxicpeople","mindcontrol","psychology","awareness","shorts","mentalhealth","brain","secrets"],
            "scenes": [
                {"text": "Manipulators always make you feel guilty... for things that are never your fault.", "prompt": f"dark anime, figure crushed under invisible guilt weight, dark energy radiating, ultra detailed cinematic 4k, seed{seed}6"},
                {"text": "They isolate you slowly... until you depend on them completely.", "prompt": f"dark anime, person trapped in glass sphere surrounded by darkness, ultra detailed 4k psychological, seed{seed}7"},
                {"text": "Gaslighting makes you question... your own memory and your own sanity.", "prompt": f"dark anime, shattered mirror distorted fractured reflection blood red violet glow, ultra detailed 4k, seed{seed}8"},
                {"text": "Love bombing comes first... then affection is withdrawn as punishment.", "prompt": f"dark anime, roses transforming into black thorns dramatic contrast, ultra detailed cinematic horror 4k, seed{seed}9"},
                {"text": "Recognizing these signs... is the first step to reclaiming your power.", "prompt": f"dark anime epic, figure stepping from darkness into golden light transformation, ultra detailed 4k, seed{seed}10"}
            ]
        },
        {
            "title": "Your Brain Lies To You Every Single Day",
            "description": "Your brain is not as honest as you think. Here is what it hides from you.",
            "tags": ["brain","psychology","mindcontrol","darkpsychology","facts","shorts","mindset","consciousness","awareness","secrets"],
            "scenes": [
                {"text": "Your brain filters 99 percent of reality... just to keep you from going insane.", "prompt": f"dark anime, glowing human brain floating cosmic space electric synapses, ultra detailed cinematic 4k, seed{seed}11"},
                {"text": "Confirmation bias means... you only see what you already believe.", "prompt": f"dark anime, eye with extreme tunnel vision shadowy distorted world outside, ultra detailed 4k, seed{seed}12"},
                {"text": "Your memories are not recordings... your brain silently rewrites them.", "prompt": f"dark anime, film reel melting distorting into darkness surreal, ultra detailed psychological 4k, seed{seed}13"},
                {"text": "The Dunning-Kruger effect... makes the least competent feel most confident.", "prompt": f"dark anime, figure on peak unaware of void below dramatic lighting, ultra detailed 4k, seed{seed}14"},
                {"text": "Understanding your brain's lies... is the only path to true clarity.", "prompt": f"dark anime, mind breaking free from chains into enlightened cosmic light, epic cinematic 4k, seed{seed}15"}
            ]
        }
    ]
    return random.choice(all_scripts)

# ── IMAGE ─────────────────────────────────────────────────────────────────────
def generate_image(prompt, index, seed_extra=""):
    print(f"  Generating image {index+1}...")
    unique_seed = f"{int(time.time())}_{index}_{random.randint(1000,9999)}"
    full_prompt = f"{prompt}, anime dark art style, ultra high quality, masterpiece, no watermark, no text, no logo, vertical 9:16, unique{unique_seed}"
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}&width=1080&height=1920&nologo=true&enhance=true&seed={unique_seed}"

    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and len(r.content) > 5000:
                path = f"img_{index}.jpg"
                with open(path, "wb") as f:
                    f.write(r.content)
                img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
                img = ImageEnhance.Contrast(img).enhance(1.25)
                img = ImageEnhance.Sharpness(img).enhance(1.4)
                img = ImageEnhance.Color(img).enhance(1.15)
                img.save(path, quality=97)
                return path
        except Exception as e:
            print(f"  Retry {attempt+1}: {e}")
            time.sleep(2)

    img = Image.new("RGB", (W, H), (8, 4, 16))
    path = f"img_{index}.jpg"
    img.save(path)
    return path

# ── VIGNETTE ──────────────────────────────────────────────────────────────────
def add_vignette(img):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    for i in range(min(w, h) // 2):
        alpha = int(255 * (i / (min(w, h) / 2)) ** 0.6)
        draw.ellipse([i, i, w-i, h-i], fill=alpha)
    return Image.composite(img, Image.new("RGB", (w, h), (0,0,0)), mask)

# ── GLITCH ────────────────────────────────────────────────────────────────────
def glitch_frame(img_array, intensity=3):
    img = img_array.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0, h - 10)
        shift = random.randint(-8, 8)
        strip_h = random.randint(2, 6)
        strip = img[y:y+strip_h, :].copy()
        if shift > 0 and shift < w:
            img[y:y+strip_h, shift:] = strip[:, :-shift]
        elif shift < 0 and -shift < w:
            img[y:y+strip_h, :shift] = strip[:, -shift:]
    shift = random.randint(1, 3)
    img[:,:,0] = np.roll(img[:,:,0], shift, axis=1)
    img[:,:,2] = np.roll(img[:,:,2], -shift, axis=1)
    return img

# ── TEXT RENDERER ─────────────────────────────────────────────────────────────
def render_text_frame(base_arr, text, char_progress, frame_idx):
    img = Image.fromarray(base_arr).convert("RGBA")
    w, h = img.size

    grad = Image.new("RGBA", (w, h), (0,0,0,0))
    gd = ImageDraw.Draw(grad)
    grad_h = int(h * 0.45)
    for y in range(h - grad_h, h):
        a = int(210 * ((y - (h - grad_h)) / grad_h) ** 1.4)
        gd.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad)
    draw = ImageDraw.Draw(img)

    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        font_main = ImageFont.load_default()
        font_label = font_main

    bar_y = int(h * 0.72)
    draw.rectangle([(60, bar_y), (w-60, bar_y+5)], fill=(220,15,15,240))

    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=20)
    line_h = 68
    text_start_y = bar_y + 22

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font_main)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        y = text_start_y + i * line_h
        for ox, oy in [(4,4),(2,2),(-1,-1)]:
            draw.text((x+ox, y+oy), line, font=font_main, fill=(0,0,0,180))
        draw.text((x, y), line, font=font_main, fill=(255,255,255,255))

    if char_progress < len(text) and (frame_idx // 8) % 2 == 0 and lines:
        last = lines[-1]
        bbox = draw.textbbox((0,0), last, font=font_main)
        cx = (w-(bbox[2]-bbox[0]))//2 + (bbox[2]-bbox[0]) + 4
        cy = text_start_y + (len(lines)-1) * line_h
        draw.rectangle([cx, cy, cx+4, cy+52], fill=(220,15,15,255))

    label = "DARK PSYCHOLOGY"
    bbox = draw.textbbox((0,0), label, font=font_label)
    lw = bbox[2]-bbox[0]
    draw.text(((w-lw)//2, h-90), label, font=font_label, fill=(180,10,10,200))

    return np.array(img.convert("RGB"))

# ── ZOOM ──────────────────────────────────────────────────────────────────────
def zoom_frame(base_img, t, duration):
    zoom = 1.0 + 0.07 * (t / duration)
    w, h = base_img.size
    nw, nh = int(w / zoom), int(h / zoom)
    left = (w - nw) // 2
    top = (h - nh) // 2
    return base_img.crop((left, top, left+nw, top+nh)).resize((w, h), Image.LANCZOS)

# ── TTS ───────────────────────────────────────────────────────────────────────
async def synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-8%", pitch="-10Hz", volume="+20%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(synth(text, path))

# ── MUSIC ─────────────────────────────────────────────────────────────────────
def get_music():
    urls = [
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Broke_For_Free/Directionless_EP/Broke_For_Free_-_01_-_Night_Owl.mp3",
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Satin/Kai_Engel_-_09_-_Interlude.mp3",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 10000:
                with open("bg_music.mp3", "wb") as f:
                    f.write(r.content)
                print("  Music OK")
                return "bg_music.mp3"
        except:
            pass
    print("  No music")
    return None

# ── BUILD SCENE ───────────────────────────────────────────────────────────────
def build_scene(scene, index):
    img_path = generate_image(scene["prompt"], index)
    base_img = add_vignette(Image.open(img_path).convert("RGB"))

    audio_path = f"audio_{index}.mp3"
    synth_sync(scene["text"], audio_path)
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 0.8
    total_frames = int(duration * FPS)
    text = scene["text"]
    reveal_frames = int(FPS * 2.0)

    frames = []
    for f in range(total_frames):
        t = f / FPS
        zoomed = zoom_frame(base_img, t, duration)
        base_arr = np.array(zoomed)
        char_progress = min(len(text), int(len(text) * (f / reveal_frames))) if f < reveal_frames else len(text)
        frame = render_text_frame(base_arr, text, char_progress, f)
        if f < 3:
            frame = glitch_frame(frame, intensity=4)
        frames.append(frame)

    def make_frame(t):
        return frames[min(int(t * FPS), len(frames)-1)]

    clip = ImageClip(frames[0], duration=duration)
    clip = clip.set_make_frame(make_frame)
    clip = clip.set_audio(audio)
    return clip.fadein(0.3).fadeout(0.3)

# ── BUILD VIDEO ───────────────────────────────────────────────────────────────
def build_video(scenes):
    clips = []
    for i, scene in enumerate(scenes):
        print(f"\n  Scene {i+1}/{len(scenes)}")
        clips.append(build_scene(scene, i))

    final = concatenate_videoclips(clips, method="compose")

    music_path = get_music()
    if music_path:
        try:
            music = AudioFileClip(music_path)
            music = music.subclip(0, min(final.duration, music.duration)).volumex(0.12)
            mixed = CompositeAudioClip([final.audio, music])
            final = final.set_audio(mixed)
        except Exception as e:
            print(f"  Music mix error: {e}")

    output = "viral_short.mp4"
    print("\n  Rendering...")
    final.write_videofile(output, fps=FPS, codec="libx264", audio_codec="aac", bitrate="10000k", preset="slow", threads=4)
    return output

# ── UPLOAD ────────────────────────────────────────────────────────────────────
def upload_to_youtube(video_path, title, description, tags):
    print("\n  Uploading...")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    with open("token.json", "w") as f:
        f.write(os.environ["TOKEN_JSON"])

    creds = Credentials.from_authorized_user_file("token.json", scopes=["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation #brain",
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    )
    response = request.execute()
    print(f"  UPLOADED: https://www.youtube.com/watch?v={response['id']}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("AUTO YOUTUBE BOT STARTING...")
    script = generate_script_with_gemini()
    print(f"Title: {script['title']}")
    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])
    print("DONE!")
