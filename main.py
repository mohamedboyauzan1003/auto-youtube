import os, asyncio, random, requests, numpy as np, textwrap, json
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
)
from edge_tts import Communicate

W, H = 1080, 1920
FPS = 30

# ── GEMINI SCRIPT GENERATOR ───────────────────────────────────────────────────
def generate_script_with_gemini():
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    topic = random.choice([
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
        "psychological power moves used by leaders"
    ])

    prompt = f"""You are a viral YouTube Shorts scriptwriter specializing in dark psychology content.
Create a script about: {topic}

Return ONLY a valid JSON object with NO markdown, NO backticks, NO extra text. Just raw JSON:
{{
  "title": "catchy title under 60 characters, no emojis",
  "description": "compelling description under 150 characters",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],
  "scenes": [
    {{
      "text": "dramatic narrator sentence with pauses marked by three dots, max 20 words, in english, dark and intriguing tone",
      "prompt": "dark anime art style, specific cinematic scene description, ultra detailed, 4k, dramatic lighting, no text, no watermark"
    }},
    {{
      "text": "...",
      "prompt": "..."
    }},
    {{
      "text": "...",
      "prompt": "..."
    }},
    {{
      "text": "...",
      "prompt": "..."
    }},
    {{
      "text": "...",
      "prompt": "..."
    }}
  ]
}}

Rules:
- Exactly 5 scenes
- Each text must be in English, dark, adult, intriguing
- Each image prompt must be unique and vivid for anime dark art
- Title must make people stop scrolling instantly
- Never repeat topics from before"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        script = json.loads(raw.strip())
        print(f"  Gemini script: {script['title']}")
        return script
    except Exception as e:
        print(f"  Gemini error: {e}, using fallback")
        return get_fallback_script()

def get_fallback_script():
    fallbacks = [
        {
            "title": "3 Dark Psychology Tricks Used Against You Daily",
            "description": "Discover the hidden manipulation tactics used on you every single day.",
            "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
            "scenes": [
                {"text": "Every single day... someone manipulates your decisions without you even noticing.", "prompt": "dark anime art, shadowy puppet master controlling strings attached to human silhouette, crimson and black palette, ultra detailed, cinematic 4k, dramatic lighting, no text"},
                {"text": "The foot-in-the-door trick... makes you say yes to big things after tiny ones.", "prompt": "dark anime style, massive door opening into endless void, eerie green glow, ultra detailed cinematic, psychological horror atmosphere, 4k, no text"},
                {"text": "Scarcity makes your brain panic... and completely override rational thinking.", "prompt": "dark anime, cracked hourglass with crimson sand draining, dramatic chiaroscuro lighting, surreal psychological art, ultra detailed 4k, no text"},
                {"text": "Social proof hijacks your mind... you copy others without even realizing it.", "prompt": "dark anime cinematic, crowd of identical shadowy figures, one glowing figure different, eerie atmosphere ultra detailed 4k, no text"},
                {"text": "Now that you know these tricks... you can finally protect your mind.", "prompt": "dark anime epic, lone warrior breaking free from shadow chains into blazing light, ultra detailed cinematic 4k, no text"}
            ]
        },
        {
            "title": "Signs Someone Is Secretly Manipulating You",
            "description": "These subtle signs reveal when someone is using dark psychology against you.",
            "tags": ["manipulation","darkpsychology","toxicpeople","mindcontrol","psychology","awareness","shorts","mentalhealth","brain","secrets"],
            "scenes": [
                {"text": "Manipulators make you feel guilty... for things that are never your fault.", "prompt": "dark anime, figure crushed under invisible weight, guilt radiating as dark energy, ultra detailed cinematic 4k, no text"},
                {"text": "They isolate you slowly... until you become completely dependent on them.", "prompt": "dark anime, person trapped in glass sphere surrounded by darkness, ultra detailed psychological thriller 4k, no text"},
                {"text": "Gaslighting makes you question... your own memory and your own sanity.", "prompt": "dark anime, shattered mirror showing distorted fractured reflection, blood red and violet glow, ultra detailed 4k, no text"},
                {"text": "They use love bombing first... then withdraw affection as punishment.", "prompt": "dark anime, roses transforming into black thorns, dramatic contrast lighting, ultra detailed cinematic horror 4k, no text"},
                {"text": "Recognizing these signs... is the first step to reclaiming your power.", "prompt": "dark anime epic, figure stepping from absolute darkness into golden light, dramatic transformation, ultra detailed 4k, no text"}
            ]
        }
    ]
    return random.choice(fallbacks)

# ── IMAGE ─────────────────────────────────────────────────────────────────────
def generate_image(prompt, index):
    print(f"  Generating image {index+1}...")
    full_prompt = prompt + ", anime dark art style, ultra high quality, masterpiece, no watermark, no text, no logo, vertical format"
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}&width=1080&height=1920&nologo=true&enhance=true"
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
    vignette = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, vignette, mask)

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
    grad_draw = ImageDraw.Draw(grad)
    grad_h = int(h * 0.45)
    for y in range(h - grad_h, h):
        a = int(210 * ((y - (h - grad_h)) / grad_h) ** 1.4)
        grad_draw.line([(0,y),(w,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, grad)
    draw = ImageDraw.Draw(img)

    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        font_main = ImageFont.load_default()
        font_label = font_main

    bar_y = int(h * 0.72)
    draw.rectangle([(60, bar_y), (w-60, bar_y+5)], fill=(220, 15, 15, 240))

    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=20)
    all_lines = textwrap.wrap(text, width=20)
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
                return "bg_music.mp3"
        except:
            pass
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
            from moviepy.audio.AudioClip import CompositeAudioClip
            music = AudioFileClip(music_path)
            music = music.subclip(0, min(final.duration, music.duration)).volumex(0.12)
            mixed = CompositeAudioClip([final.audio, music])
            final = final.set_audio(mixed)
        except Exception as e:
            print(f"  Music error: {e}")

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
