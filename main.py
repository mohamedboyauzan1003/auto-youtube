import os, asyncio, random, requests
from PIL import Image
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    vfx
)

from edge_tts import Communicate

# -------------------------
# CONFIG
# -------------------------
RESOLUTION = (1080, 1920)
FPS = 30
DURATION = 4

# -------------------------
# SCRIPT
# -------------------------
class ScriptGenerator:

    hooks = [
        "La verdad que nadie te dice:",
        "Esto controla tu mente sin que lo notes:",
        "Tu cerebro está siendo manipulado:",
        "Esto influye en cada decisión tuya:",
        "No estás pensando libremente:"
    ]

    topics = [
        "sesgos cognitivos invisibles",
        "psicología de la manipulación",
        "decisiones inconscientes humanas",
        "lenguaje corporal engañoso",
        "técnicas de persuasión modernas"
    ]

    @staticmethod
    def generate():
        hook = random.choice(ScriptGenerator.hooks)
        topic = random.choice(ScriptGenerator.topics)

        scenes = []
        for i in range(5):
            scenes.append({
                "text": f"{hook} {topic}. Punto {i+1}.",
                "image_prompt": f"{topic}, cinematic, dark, ultra realistic, shot {i+1}"
            })

        return {
            "title": hook,
            "description": "Video generado con IA",
            "tags": ["psychology", "mind"],
            "scenes": scenes
        }

# -------------------------
# TTS
# -------------------------
async def synth(text, path):
    tts = Communicate(text, voice="en-US-GuyNeural")
    await tts.save(path)

def synth_sync(text, path):
    asyncio.run(synth(text, path))

# -------------------------
# IMAGE
# -------------------------
def get_image(prompt, i):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    r = requests.get(url, timeout=60)

    path = f"img_{i}.jpg"
    with open(path, "wb") as f:
        f.write(r.content)

    return path

# -------------------------
# VIDEO
# -------------------------
def render_video(scenes):

    clips = []

    for i, scene in enumerate(scenes):
        print(f"🎬 Scene {i+1}")

        img_path = get_image(scene["image_prompt"], i)

        audio_path = f"audio_{i}.mp3"
        synth_sync(scene["text"], audio_path)

        audio = AudioFileClip(audio_path)

        clip = ImageClip(img_path).set_duration(audio.duration)

        # zoom suave
        clip = clip.fx(vfx.resize, lambda t: 1 + 0.03 * t)

        clip = clip.set_audio(audio)

        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output = "viral_short.mp4"

    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        preset="medium"
    )

    return output

# -------------------------
# UPLOAD (OBLIGATORIO)
# -------------------------
def upload_to_youtube(video_path, title, description, tags):
    print("📤 UPLOADING...")

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
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path)
    )

    response = request.execute()

    print("✅ UPLOADED:")
    print("https://www.youtube.com/watch?v=" + response["id"])

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":

    print("🚀 START")

    script = ScriptGenerator.generate()

    print("🎬 creating video...")

    video = render_video(script["scenes"])

    print("📤 uploading...")

    upload_to_youtube(
        video,
        script["title"],
        script["description"],
        script["tags"]
    )

    print("✅ DONE")
