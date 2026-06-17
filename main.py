import os, asyncio, random, requests, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip, vfx
)
from edge_tts import Communicate

RESOLUTION = (1080, 1920)
FPS = 30

# ── SCRIPTS ──────────────────────────────────────────────────────────────────
SCRIPTS = [
    {
        "title": "3 Dark Psychology Tricks Used Against You Daily",
        "description": "Discover the hidden manipulation tactics used on you every single day.",
        "tags": ["darkpsychology","manipulation","mindcontrol","psychology","shorts","facts","brain","mindset","secrets","awareness"],
        "scenes": [
            {"text": "Every day, someone manipulates your decisions without you even noticing.", "prompt": "dark anime cinematic, shadowy figure controlling puppet strings, ultra detailed, 4k, dramatic red lighting, psychological thriller"},
            {"text": "The 'foot-in-the-door' trick makes you say yes to big things after small ones.", "prompt": "dark anime, door opening into void, eerie glow, ultra realistic, cinematic shadows, psychological horror style"},
            {"text": "Scarcity makes your brain panic and override rational thinking instantly.", "prompt": "dark anime style, hourglass with blood dripping, dramatic lighting, ultra detailed, cinematic, 4k"},
            {"text": "Social proof hijacks your mind — you copy others without realizing it.", "prompt": "dark anime, crowd of shadowy figures all looking same direction, eerie atmosphere, ultra detailed, 4k cinematic"},
            {"text": "Now that you know these tricks, you can protect your mind from them.", "prompt": "dark anime, single figure breaking free from chains in dramatic light, ultra detailed, 4k, epic cinematic shot"}
        ]
    },
    {
        "title": "Signs Someone Is Secretly Manipulating You",
        "description": "These subtle signs reveal when someone is using dark psychology against you.",
        "tags": ["manipulation","darkpsychology","toxicpeople","mindcontrol","psychology","awareness","shorts","mentalhealth","brain","secrets"],
        "scenes": [
            {"text": "Manipulators make you feel guilty for things that are not your fault.", "prompt": "dark anime, person under heavy shadow with guilt written across their face, cinematic, ultra detailed, 4k"},
            {"text": "They isolate you slowly so you become fully dependent on them.", "prompt": "dark anime, lone figure trapped inside a glass prison, dramatic lighting, ultra detailed, psychological thriller, 4k"},
            {"text": "Gaslighting makes you question your own memory and sanity.", "prompt": "dark anime, shattered mirror reflecting distorted face, eerie red glow, ultra detailed, cinematic, 4k"},
            {"text": "They use love bombing first then withdraw affection as punishment.", "prompt": "dark anime, roses turning to thorns, dramatic contrast lighting, ultra detailed, 4k cinematic horror"},
            {"text": "Recognizing these signs is the first step to reclaiming your power.", "prompt": "dark anime, figure stepping out of darkness into bright light, epic dramatic shot, ultra detailed, 4k"}
        ]
    },
    {
        "title": "Why Your Brain Lies To You Every Morning",
        "description": "Your brain is not as honest as you think. Here is what it hides from you.",
        "tags": ["brain","psychology","mindcontrol","darkpsychology","facts","shorts","mindset","consciousness","awareness","secrets"],
        "scenes": [
            {"text": "Your brain filters out 99 percent of reality to keep you from going insane.", "prompt": "dark anime, human brain floating in space with static electricity, ultra detailed, cinematic, 4k dramatic"},
            {"text": "Confirmation bias makes you only see what you already believe is true.", "prompt": "dark anime, eye with tunnel vision, shadowy figures outside the vision, ultra detailed, 4k cinematic"},
            {"text": "Your memories are not recordings — your brain rewrites them every time.", "prompt": "dark anime, film reel melting and distorting, dark atmosphere, ultra detailed, 4k psychological"},
            {"text": "The Dunning-Kruger effect makes incompetent people feel the most confident.", "prompt": "dark anime, figure standing on peak unaware of the void below, dramatic lighting, ultra detailed, 4k"},
            {"text": "Understanding your brain's lies is the only way to think clearly.", "prompt": "dark anime, figure meditating with glowing mind breaking free from chains, epic shot, ultra detailed, 4k"}
        ]
    },
    {
        "title": "The Hidden Reason You Cannot Say No",
        "description": "Dark psychology explains why saying no feels almost impossible for most people.",
        "tags": ["psychology","darkpsychology","boundaries","manipulation","mindcontrol","shorts","brain","mindset","selfhelp","secrets"],
        "scenes": [
            {"text": "People pleasing is not kindness. It is a trauma response your brain learned.", "prompt": "dark anime, figure bowing under invisible heavy weight, dramatic shadow lighting, ultra detailed, 4k cinematic"},
            {"text": "The fear of rejection triggers the same pain response as physical injury.", "prompt": "dark anime, heart cracking like glass in darkness, blood red glow, ultra detailed, 4k psychological thriller"},
            {"text": "Manipulators sense people pleasers and target them deliberately.", "prompt": "dark anime, predator watching prey in shadows, eerie atmosphere, ultra detailed, 4k cinematic horror"},
            {"text": "Saying yes when you mean no slowly destroys your self worth.", "prompt": "dark anime, figure dissolving into nothing while smiling, dark surreal art, ultra detailed, 4k"},
            {"text": "Your no is a complete sentence. You owe no one an explanation.", "prompt": "dark anime, single figure standing tall breaking free from puppet strings, epic dramatic lighting, ultra detailed, 4k"}
        ]
    },
    {
        "title": "Dark Tricks Your Subconscious Uses Against You",
        "description": "Your own subconscious mind is working against you in ways you cannot see.",
        "tags": ["subconscious","darkpsychology","brain","mindcontrol","psychology","shorts","facts","mindset","awareness","secrets"],
        "scenes": [
            {"text": "Your subconscious makes 95 percent of your decisions before you are aware.", "prompt": "dark anime, shadowy figure pulling levers inside human head, ultra detailed, cinematic, 4k dramatic lighting"},
            {"text": "The negativity bias makes your brain remember pain ten times more than joy.", "prompt": "dark anime, scales heavily tipped toward darkness, dramatic contrast, ultra detailed, 4k cinematic"},
            {"text": "Self-sabotage is your subconscious protecting you from the fear of success.", "prompt": "dark anime, figure destroying their own path forward, surreal dark atmosphere, ultra detailed, 4k"},
            {"text": "Your comfort zone feels safe but it is actually a psychological prison.", "prompt": "dark anime, golden cage in darkness that looks comfortable inside, ultra detailed, 4k cinematic thriller"},
            {"text": "Awareness of these patterns is the key that unlocks your true potential.", "prompt": "dark anime, figure breaking out of mental prison into blazing light, epic cinematic shot, ultra detailed, 4k"}
        ]
    }
]

# ── IMAGE GENERATION ─────────────────────────────────────────────────────────
def generate_image(prompt, index):
    print(f"  Generating image {index+1}...")
    enhanced = prompt + ", no text, no watermark, vertical 9:16 format"
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(enhanced)}&width=1080&height=1920&nologo=true"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and len(r.content) > 10000:
                path = f"img_{index}.jpg"
                with open(path, "wb") as f:
                    f.write(r.content)
                img = Image.open(path).convert("RGB").resize((1080, 1920), Image.LANCZOS)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)
                img.save(path, quality=95)
                return path
        except Exception as e:
            print(f"  Retry {attempt+1}: {e}")
    # fallback dark image
    img = Image.new("RGB", (1080, 1920), (10, 5, 20))
    path = f"img_{index}.jpg"
    img.save(path)
    return path

# ── TEXT OVERLAY ─────────────────────────────────────────────────────────────
def add_animated_text_frames(base_img_path, text, total_frames, fps):
    base = Image.open(base_img_path).convert("RGB")
    w, h = base.size

    # dark gradient overlay at bottom
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for y in range(h // 2, h):
        alpha = int(180 * ((y - h // 2) / (h // 2)))
        draw_ov.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    base_rgba = base.convert("RGBA")
    base_with_grad = Image.alpha_composite(base_rgba, overlay).convert("RGB")

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    except:
        font_large = ImageFont.load_default()
        font_small = font_large

    # wrap text
    import textwrap
    words = text.split()
    lines = textwrap.wrap(text, width=22)

    frames = []
    chars_total = len(text)
    reveal_frames = int(fps * 1.5)  # 1.5 seconds to reveal text

    for f in range(total_frames):
        frame = base_with_grad.copy()
        draw = ImageDraw.Draw(frame)

        # typewriter effect
        chars_shown = min(chars_total, int(chars_total * (f / reveal_frames))) if f < reveal_frames else chars_total
        partial_text = text[:chars_shown]
        partial_lines = textwrap.wrap(partial_text, width=22)

        line_h = 70
        total_text_h = len(lines) * line_h
        y_start = h - total_text_h - 120

        for i, line in enumerate(partial_lines):
            bbox = draw.textbbox((0, 0), line, font=font_large)
            tw = bbox[2] - bbox[0]
            x = (w - tw) // 2
            y = y_start + i * line_h
            # shadow
            draw.text((x + 3, y + 3), line, font=font_large, fill=(0, 0, 0, 200))
            # main text in white
            draw.text((x, y), line, font=font_large, fill=(255, 255, 255))

        # red accent line
        draw.rectangle([(80, y_start - 20), (w - 80, y_start - 14)], fill=(200, 20, 20))

        frames.append(np.array(frame))

    return frames

# ── ZOOM EFFECT ──────────────────────────────────────────────────────────────
def make_zoom_clip(img_path, duration, fps, zoom_start=1.0, zoom_end=1.08):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    total_frames = int(duration * fps)
    frames = []
    for f in range(total_frames):
        t = f / total_frames
        zoom = zoom_start + (zoom_end - zoom_start) * t
        new_w = int(w / zoom)
        new_h = int(h / zoom)
        left = (w - new_w) // 2
        top = (h - new_h) // 2
        cropped = img.crop((left, top, left + new_w, top + new_h))
        resized = cropped.resize((w, h), Image.LANCZOS)
        frames.append(np.array(resized))
    return frames

# ── FADE TRANSITION ───────────────────────────────────────────────────────────
def make_fade_frames(fps, duration=0.4):
    n = int(fps * duration)
    frames = []
    for i in range(n):
        alpha = i / n
        black = np.zeros((1920, 1080, 3), dtype=np.uint8)
        frames.append(black)
    return frames

# ── TTS ───────────────────────────────────────────────────────────────────────
async def synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural", rate="-5%", pitch="-8Hz")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(synth(text, path))

# ── BUILD VIDEO ───────────────────────────────────────────────────────────────
def build_video(scenes):
    all_clips = []

    for i, scene in enumerate(scenes):
        print(f"\n Scene {i+1}/{len(scenes)}: {scene['text'][:40]}...")

        img_path = generate_image(scene["prompt"], i)

        audio_path = f"audio_{i}.mp3"
        synth_sync(scene["text"], audio_path)
        audio = AudioFileClip(audio_path)
        duration = audio.duration + 0.5

        total_frames = int(duration * FPS)

        # zoom frames
        zoom_frames = make_zoom_clip(img_path, duration, FPS)

        # text overlay on zoom frames
        text_frames = add_animated_text_frames(img_path, scene["text"], total_frames, FPS)

        # composite: zoom base + text
        composite_frames = []
        for f in range(total_frames):
            base = Image.fromarray(zoom_frames[f])
            txt_layer = Image.fromarray(text_frames[f])
            # blend
            blended = Image.blend(base, txt_layer, alpha=0.85)
            composite_frames.append(np.array(blended))

        def make_frame_func(frames):
            def get_frame(t):
                idx = min(int(t * FPS), len(frames) - 1)
                return frames[idx]
            return get_frame

        clip = ImageClip(composite_frames[0], duration=duration)
        clip = clip.set_make_frame(make_frame_func(composite_frames))
        clip = clip.set_audio(audio)
        all_clips.append(clip)

        # fade to black between scenes
        if i < len(scenes) - 1:
            fade_frames = make_fade_frames(FPS)
            fade_clip = ImageClip(fade_frames[0], duration=len(fade_frames)/FPS)
            fade_clip = fade_clip.set_make_frame(make_frame_func(fade_frames))
            all_clips.append(fade_clip)

    final = concatenate_videoclips(all_clips, method="compose")
    output = "viral_short.mp4"
    print("\n Rendering final video...")
    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        preset="medium",
        threads=4
    )
    return output

# ── YOUTUBE UPLOAD ────────────────────────────────────────────────────────────
def upload_to_youtube(video_path, title, description, tags):
    print("\n Uploading to YouTube...")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    TOKEN_JSON = os.environ["TOKEN_JSON"]
    with open("token.json", "w") as f:
        f.write(TOKEN_JSON)

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
                "description": description + "\n\n#darkpsychology #psychology #shorts #mindcontrol #manipulation",
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    )

    response = request.execute()
    print(f" UPLOADED: https://www.youtube.com/watch?v={response['id']}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(" AUTO YOUTUBE BOT STARTING...")
    script = random.choice(SCRIPTS)
    print(f" Title: {script['title']}")
    video = build_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])
    print(" DONE!")
