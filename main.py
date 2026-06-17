import os, json, asyncio, random, requests
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

TOKEN_JSON = os.environ["TOKEN_JSON"]

# -------------------------
# SCRIPT GENERATOR
# -------------------------
def generate_script():
    topics = [
        "psychological manipulation secrets",
        "dark persuasion techniques",
        "mind control tricks people use",
        "cognitive biases in daily life",
        "how body language reveals lies",
        "subconscious influence patterns",
        "how people get manipulated easily",
        "hidden psychology of behavior"
    ]

    topic = random.choice(topics)

    scenes = []
    for i in range(5):
        scenes.append({
            "text": f"Psychological insight {i+1}: {topic}. Most people never notice this hidden behavior control.",
            "image_prompt": f"{topic}, cinematic dark lighting, ultra realistic, dramatic, thriller style"
        })

    return {
        "title": f"The dark truth about {topic}",
        "description": "Psychology secrets explained in this short video.",
        "tags": ["psychology", "mind", "dark psychology", "behavior", "facts"],
        "scenes": scenes
    }

# -------------------------
# IMAGES
# -------------------------
def generate_image(prompt, index):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    r = requests.get(url, timeout=60)

    if r.status_code != 200:
        raise Exception("Image generation failed")

    path = f"scene_{index}.jpg"
    with open(path, "wb") as f:
        f.write(r.content)

    img = Image.open(path).resize((1080, 1920))
    img.save(path)

    return path

# -------------------------
# AUDIO
# -------------------------
async def generate_audio(text, index):
    path = f"audio_{index}.mp3"
    tts = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await tts.save(path)
    return path


def generate_audio_sync(text, index):
    return asyncio.run(generate_audio(text, index))

# -------------------------
# VIDEO
# -------------------------
def create_video(scenes):
    clips = []

    for i, scene in enumerate(scenes):
        print(f"Scene {i+1}")

        img = generate_image(scene["image_prompt"], i)
        audio_path = generate_audio_sync(scene["text"], i)

        if not audio_path or not os.path.exists(audio_path):
            continue

        audio = AudioFileClip(audio_path)

        clip = ImageClip(img, duration=audio.duration).set_audio(audio)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output = "output.mp4"
    final.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")

    # cleanup
    for c in clips:
        c.close()
    final.close()

    return output

# -------------------------
# YOUTUBE UPLOAD
# -------------------------
def upload_to_youtube(video_path, title, description, tags):
    with open("token.json", "w") as f:
        f.write(TOKEN_JSON)

    creds = Credentials.from_authorized_user_file(
        "token.json",
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27"
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = request.execute()
    print("Uploaded:", response["id"])

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    script = generate_script()
    video = create_video(script["scenes"])
    upload_to_youtube(video, script["title"], script["description"], script["tags"])
