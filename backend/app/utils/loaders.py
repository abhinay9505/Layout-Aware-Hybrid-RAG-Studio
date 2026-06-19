import os
import base64
import logging
import tempfile
import pdfplumber
import docx2txt
from groq import Groq
from app.core.config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)


class PDFLoader:
    async def load(self, file_path):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text


class DOCXLoader:
    async def load(self, file_path):
        text = docx2txt.process(file_path)
        return text


class ImageLoader:
    """Uses Groq's vision model to generate a detailed text description of an image."""

    SUPPORTED = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

    async def load(self, file_path):
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze this image in great detail. Describe:\n"
                                    "1. Every object, person, text, and element visible\n"
                                    "2. Colors, layout, and spatial relationships\n"
                                    "3. Any text or writing visible in the image (OCR)\n"
                                    "4. The overall context and purpose of the image\n"
                                    "5. Any data, charts, diagrams, or tables if present\n\n"
                                    "Be extremely thorough — this description will be used "
                                    "to answer questions about this image later."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            description = response.choices[0].message.content
            file_name = os.path.basename(file_path)
            return (
                f"[IMAGE FILE: {file_name}]\n\n"
                f"Detailed Image Description:\n{description}"
            )
        except Exception as e:
            logging.error(f"Image analysis failed: {e}")
            return f"[IMAGE FILE: {os.path.basename(file_path)}]\nImage analysis failed: {str(e)}"


class AudioLoader:
    """Uses Groq's Whisper API to transcribe audio files."""

    SUPPORTED = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}

    async def load(self, file_path):
        file_name = os.path.basename(file_path)
        try:
            with open(file_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=audio_file,
                    response_format="verbose_json",
                )

            text = transcription.text
            duration = getattr(transcription, "duration", None)
            duration_str = f" | Duration: {duration:.1f}s" if duration else ""

            return (
                f"[AUDIO FILE: {file_name}{duration_str}]\n\n"
                f"Full Transcription:\n{text}"
            )
        except Exception as e:
            logging.error(f"Audio transcription failed: {e}")
            return f"[AUDIO FILE: {file_name}]\nTranscription failed: {str(e)}"


class VideoLoader:
    """
    Extracts audio from video using moviepy, transcribes with Whisper,
    and optionally captures keyframes for vision analysis.
    """

    SUPPORTED = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

    async def load(self, file_path):
        file_name = os.path.basename(file_path)
        parts = []

        # ── 1. Extract & transcribe audio ──────────────────────────
        try:
            from moviepy.editor import VideoFileClip

            clip = VideoFileClip(file_path)
            duration = clip.duration

            # Extract audio to a temp WAV file
            temp_audio = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=tempfile.gettempdir()
            )
            temp_audio_path = temp_audio.name
            temp_audio.close()

            clip.audio.write_audiofile(temp_audio_path, logger=None)

            with open(temp_audio_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=audio_file,
                    response_format="verbose_json",
                )

            parts.append(
                f"[VIDEO FILE: {file_name} | Duration: {duration:.1f}s]\n\n"
                f"Audio Transcription:\n{transcription.text}"
            )

            # Cleanup
            os.unlink(temp_audio_path)

            # ── 2. Capture keyframes for visual analysis ───────────
            try:
                keyframe_descriptions = []
                # Capture up to 3 keyframes spread across the video
                timestamps = [
                    duration * frac
                    for frac in [0.1, 0.5, 0.9]
                    if duration * frac < duration
                ]

                for ts in timestamps[:3]:
                    frame = clip.get_frame(ts)
                    # Convert numpy array to image bytes
                    from PIL import Image
                    import io

                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=80)
                    img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    response = groq_client.chat.completions.create(
                        model="llama-3.2-90b-vision-preview",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            f"This is a frame captured at {ts:.1f}s from a video. "
                                            "Describe what you see concisely (2-3 sentences)."
                                        ),
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{img_b64}"
                                        },
                                    },
                                ],
                            }
                        ],
                        temperature=0.1,
                        max_tokens=300,
                    )
                    desc = response.choices[0].message.content
                    keyframe_descriptions.append(f"  [{ts:.1f}s]: {desc}")

                if keyframe_descriptions:
                    parts.append(
                        "\nVisual Keyframe Descriptions:\n"
                        + "\n".join(keyframe_descriptions)
                    )

            except Exception as e:
                logging.warning(f"Keyframe analysis skipped: {e}")

            clip.close()

        except ImportError:
            logging.warning("moviepy not installed — falling back to audio-only via direct file")
            # Try direct transcription (works for some video formats)
            try:
                with open(file_path, "rb") as vf:
                    transcription = groq_client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=vf,
                        response_format="verbose_json",
                    )
                parts.append(
                    f"[VIDEO FILE: {file_name}]\n\n"
                    f"Audio Transcription:\n{transcription.text}"
                )
            except Exception as e:
                logging.error(f"Video transcription failed: {e}")
                parts.append(
                    f"[VIDEO FILE: {file_name}]\n"
                    f"Processing failed: {str(e)}"
                )
        except Exception as e:
            logging.error(f"Video processing failed: {e}")
            parts.append(
                f"[VIDEO FILE: {file_name}]\n"
                f"Processing failed: {str(e)}"
            )

        return "\n\n".join(parts)
