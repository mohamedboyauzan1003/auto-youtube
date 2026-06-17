import os, asyncio, random, requests, numpy as np, textwrap, math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip, AudioClip
)
from moviepy.audio.AudioClip import AudioArrayClip
from edge_tts import Communicate

W, H = 1080, 1920
FPS = 30

# ── SCRIPTS ──────────────────────────────────────────────────────────────────
SCRIPTS = [
    {
        "title": "3 Dark Psychology Tricks Used Against You Daily",
        "description": "Discover the hidden manipulation tactics used on you every single day. Dark psychology exposed.",
        "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
        "scenes": [
            {"text": "Every single day... someone manipulates your decisions without you even noticing.", "prompt": "dark anime art, shadowy puppet master controlling strings attached to human silhouette, crimson and black palette, ultra detailed, cinematic 4k, dramatic volumetric lighting, no text"},
            {"text": "The foot-in-the-door trick... makes you say yes to big things after tiny ones.", "prompt": "dark anime style, massive door opening into endless void, eerie green glow, ultra detailed cinematic, psychological horror atmosphere, 4k, no text"},
            {"text": "Scarcity makes your brain panic... and completely override rational thinking.", "prompt": "dark anime, cracked hourglass with crimson sand, dramatic chiaroscuro lighting, surreal psychological art, ultra detailed 4k, no text"},
            {"text": "Social proof hijacks your mind... you copy others without even realizing it.", "prompt": "dark anime cinematic, crowd of identical shadowy figures, one person different glowing, eerie atmosphere ultra detailed 4k, no text"},
            {"text": "Now that you know these tricks... you can finally protect your mind.", "prompt": "dark anime epic, lone warrior figure breaking free from shadow chains into blazing light, ultra detailed cinematic 4k, no text"}
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
    },
    {
        "title": "Your Brain Lies To You Every Single Day",
        "description": "Your brain is not as honest as you think. Here is what it hides from you.",
        "tags": ["brain","psychology","mindcontrol","darkpsychology","facts","shorts","mindset","consciousness","awareness","secrets"],
        "scenes": [
            {"text": "Your brain filters out 99 percent of reality... just to keep you from going insane.", "prompt": "dark anime, glowing human brain floating in cosmic space, electric synapses firing, ultra detailed cinematic 4k, no text"},
            {"text": "Confirmation bias means... you only see what you already believe is true.", "prompt": "dark anime, eye with tunnel vision, shadowy distorted world outside the view, ultra detailed 4k cinematic, no text"},
            {"text": "Your memories are not recordings... your brain silently rewrites them every time.", "prompt": "dark anime, film reel melting and distorting into darkness, surreal psychological art, ultra detailed 4k, no text"},
            {"text": "The Dunning-Kruger effect... makes the least competent feel the most confident.", "prompt": "dark anime, figure standing on peak completely unaware of void below, dramatic lighting, ultra detailed 4k, no text"},
            {"text": "Understanding how your brain lies... is the only way to think with true clarity.", "prompt": "dark anime, mind breaking free from chains into enlightened light, epic cinematic shot, ultra detailed 4k, no text"}
        ]
    },
    {
        "title": "The Dark Reason You Cannot Say No",
        "description": "Dark psychology explains why saying no feels almost impossible for most people.",
        "tags": ["psychology","darkpsychology","boundaries","manipulation","mindcontrol","shorts","brain","mindset","selfhelp","secrets"],
        "scenes": [
            {"text": "People pleasing is not kindness... it is a trauma response your brain learned.", "prompt": "dark anime, figure bowing under crushing invisible force, shadows pressing down, ultra detailed cinematic 4k, no text"},
            {"text": "Rejection triggers the exact same pain response... as physical injury.", "prompt": "dark anime, heart shattering like glass in pitch darkness, blood red glow, ultra detailed psychological thriller 4k, no text"},
            {"text": "Manipulators can sense people pleasers... and they target them deliberately.", "prompt": "dark anime, predator watching vulnerable prey from deep shadows, eerie atmosphere ultra detailed 4k, no text"},
            {"text": "Saying yes when you mean no... slowly and silently destroys your self worth.", "prompt": "dark anime, figure dissolving into darkness while forcing a smile, surreal dark art, ultra detailed 4k, no text"},
            {"text": "Your no is a complete sentence... you owe absolutely no one an explanation.", "prompt": "dark anime epic, powerful figure cutting puppet strings with light blade, dramatic cinematic shot, ultra detailed 4k, no text"}
        ]
    },
    {
        "title": "Dark Tricks Your Subconscious Uses Against You",
        "description": "Your own subconscious mind works against you in ways you cannot see.",
        "tags": ["subconscious","darkpsychology","brain","mindcontrol","psychology","shorts","facts","mindset","awareness","secrets"],
        "scenes": [
            {"text": "Your subconscious makes 95 percent of your decisions... before you are even aware.", "prompt": "dark anime, shadowy hidden figure pulling levers deep inside glowing human head, ultra detailed cinematic 4k, no text"},
            {"text": "Negativity bias makes your brain remember pain... ten times stronger than joy.", "prompt": "dark anime, scales overwhelmingly tipped toward darkness and shadow, dramatic contrast, ultra detailed 4k, no text"},
            {"text": "Self sabotage is your subconscious... protecting you from the fear of success.", "prompt": "dark anime, figure destroying their own bridge forward, surreal dark psychological atmosphere, ultra detailed 4k, no text"},
            {"text": "Your comfort zone feels safe... but it is actually a psychological prison.", "prompt": "dark anime, golden comfortable cage surrounded by infinite darkness, ultra detailed cinematic thriller 4k, no text"},
            {"text": "Awareness of these hidden patterns... is the key that unlocks your true potential.", "prompt": "dark anime epic, figure shattering mental prison walls into blazing cosmic light, ultra detailed 4k, no text"}
        ]
    }
]

# ── IMAGE ─────────────────────────────────────────────────────────────────────
def generate_image(prompt, index):
    print(f"  Generating image {index+1}...")
    full_prompt = prompt + ", anime dark art style, ultra high quality, masterpiece, no watermark, no text, no logo"
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
    result = Image.composite(img, vignette, mask)
    return result

# ── GLITCH EFFECT ─────────────────────────────────────────────────────────────
def glitch_frame(img_array, intensity=3):
    img = img_array.copy()
    h, w = img.shape[:2]
    for _ in range(intensity):
        y = random.randint(0, h - 10)
        shift = random.randint(-8, 8)
        strip_h = random.randint(2, 6)
        strip = img[y:y+strip_h, :].copy()
        if shift > 0:
            img[y:y+strip_h, shift:] = strip[:, :-shift] if shift < w else strip
        elif shift < 0:
            img[y:y+strip_h, :shift] = strip[:, -shift:] if -shift < w else strip
    r, g, b = img[:,:,0].copy(), img[:,:,1].copy(), img[:,:,2].copy()
    shift = random.randint(1, 3)
    img[:,:,0] = np.roll(r, shift, axis=1)
    img[:,:,2] = np.roll(b, -shift, axis=1)
    return img

# ── TEXT FRAME RENDERER ───────────────────────────────────────────────────────
def render_text_frame(base_arr, text, char_progress, frame_idx, total_frames):
    img = Image.fromarray(base_arr).convert("RGBA")
    w, h = img.size

    # bottom gradient
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
        font_accent = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        font_main = ImageFont.load_default()
        font_accent = font_main

    # red top accent bar
    bar_y = int(h * 0.72)
    draw.rectangle([(60, bar_y), (w-60, bar_y+5)], fill=(220, 15, 15, 240))

    # typewriter text
    partial = text[:char_progress]
    lines = textwrap.wrap(partial, width=20)
    line_h = 68
    text_start_y = bar_y + 22

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font_main)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        y = text_start_y + i * line_h
        # shadow layers
        for ox, oy in [(4,4),(2,2),(-1,-1)]:
            draw.text((x+ox, y+oy), line, font=font_main, fill=(0,0,0,180))
        # main white text
        draw.text((x, y), line, font=font_main, fill=(255,255,255,255))

    # blinking cursor
    if char_progress < len(text) and (frame_idx // 8) % 2 == 0:
        if lines:
            last = lines[-1]
            bbox = draw.textbbox((0,0), last, font=font_main)
            cursor_x = (w - (bbox[2]-bbox[0]))//2 + (bbox[2]-bbox[0]) + 4
            cursor_y = text_start_y + (len(lines)-1) * line_h
            draw.rectangle([cursor_x, cursor_y, cursor_x+4, cursor_y+52], fill=(220,15,15,255))

    # bottom label
    label = "DARK PSYCHOLOGY"
    bbox = draw.textbbox((0,0), label, font=font_accent)
    lw = bbox[2]-bbox[0]
    draw.text(((w-lw)//2, h-90), label, font=font_accent, fill=(180,10,10,200))

    return np.array(img.convert("RGB"))

# ── ZOOM FRAME ────────────────────────────────────────────────────────────────
def zoom_frame(base_img, t, duration, zoom_start=1.0, zoom_end=1.07):
    progress = t / duration
    zoom = zoom_start + (zoom_end - zoom_start) * progress
    w, h = base_img.size
    nw, nh = int(w / zoom), int(h / zoom)
    left = (w - nw) // 2
    top = (h - nh) // 2
    cropped = base_img.crop((left, top, left+nw, top+nh))
    return cropped.resize((w, h), Image.LANCZOS)

# ── TTS ───────────────────────────────────────────────────────────────────────
async def synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-8%", pitch="-10Hz", volume="+20%")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(synth(text, path))

# ── MUSIC ─────────────────────────────────────────────────────────────────────
def get_background_music():
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
                print("  Music downloaded")
                return "bg_music.mp3"
        except:
            pass
    print("  No music available, continuing without")
    return None

# ── BUILD VIDEO ───────────────────────────────────────────────────────────────
def build_scene_clip(scene, index):
    img_path = generate_image(scene["prompt"], index)
    base_img = Image.open(img_path).convert("RGB")
    base_img = add_vignette(base_img)

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
        frame = render_text_frame(base_arr, text, char_progress, f, total_frames)

        # glitch on first 3 frames
        if f < 3:
            frame = glitch_frame(frame, intensity=4)

        frames.append(frame)

    def make_frame(t):
        idx = min(int(t * FPS), len(frames)-1)
        return frames[idx]

    clip = ImageClip(frames[0], duration=duration)
    clip = clip.set_make_frame(make_frame)
    clip = clip.set_audio(audio)
    return clip

def build_video(scenes):
    all_clips = []

    for i, scene in enumerate(scenes):
        print(f"\n  Scene {i+1}/{len(scenes)}")
        clip = build_scene_clip(scene, i)

        # fade in/out
        clip = clip.fadein(0.3).fadeout(0.3)
        all_clips.append(clip)

    final = concatenate_videoclips(all_clips, method="compose")

    # add background music
    music_path = get_background_music()
    if music_path:
        try:
            from moviepy.editor import CompositeAudioClip
            music = AudioFileClip(music_path).subclip(0, min(final.duration, AudioFileClip(music_path).duration))
            music = music.volumex(0.12)
            voice = final.audio
            from moviepy.audio.AudioClip import CompositeAudioClip
            mixed = CompositeAudioClip([voice, music])
            final = final.set_audio(mixed)
        except Exception as e:
            print(f"  Music mix error: {e}")

    output = "viral_short.mp4"
    print("\n  Rendering final video...")
    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="10000k",
        preset="slow",
        threads=4
    )
    return output

# ── YOUTUBE UPLOAD ────────────────────────────────────────────────────────────
def upload_to_youtube(video_path, title, description, tags):
    print("\n  Uploading to YouTube...")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    with open("token.json", "w") as f:
        f.write(os.environ["TOKEN_JSON"])

    creds = Credentials.from_authorized_user_file(
        "token.json",
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
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
    script = random.choice(SCRIPTS)
    print(f"Title: {script['title']}")
    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])
    print("DONE!")
