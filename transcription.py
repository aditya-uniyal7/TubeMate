import json
import os
import re
import tempfile
from urllib.request import urlopen
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

load_dotenv()

MAX_WHISPER_FILE_BYTES = 25 * 1024 * 1024
TEXT_TRANSCRIPT_EXTENSIONS = {".txt", ".vtt", ".srt"}
MEDIA_EXTENSIONS = {".mp4", ".m4a", ".mp3", ".wav", ".webm", ".ogg", ".flac", ".mpeg", ".mpga"}
YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})")
BARE_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
SUBTITLE_RANGE_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}"
)
SPEAKER_TAG_RE = re.compile(r"<v\s+([^>]+)>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def extract_youtube_id(source: str) -> str | None:
    source = (source or "").strip()
    if BARE_YOUTUBE_ID_RE.fullmatch(source):
        return source
    match = YOUTUBE_ID_RE.search(source)
    return match.group(1) if match else None


class Transcription:
    @staticmethod
    def _fetch_youtube_transcript(vid: str) -> str | None:
        try:
            tracks = YouTubeTranscriptApi().list(vid)
            try:
                transcript = tracks.find_transcript(["en", "en-US", "en-GB"]).fetch()
            except Exception:
                try:
                    track = tracks.find_transcript(["hi"])
                except Exception:
                    track = next(iter(tracks))
                if getattr(track, "is_translatable", False):
                    try:
                        transcript = track.translate("en").fetch()
                    except Exception:
                        transcript = track.fetch()
                else:
                    transcript = track.fetch()

            text = " ".join(
                item["text"].strip()
                for item in transcript.to_raw_data()
                if item.get("text", "").strip()
            ).strip()
            return text or None
        except Exception as e:
            print(f"YouTube transcript unavailable ({e}). Falling back to Whisper...")
            return None

    @staticmethod
    def _download_audio(source_url: str, output_dir: str) -> tuple[str, dict]:
        ydl_opts = {
            "format": (
                "bestaudio[ext=m4a][filesize<25M]/"
                "bestaudio[ext=webm][filesize<25M]/"
                "bestaudio[ext=m4a][filesize_approx<25M]/"
                "bestaudio[ext=webm][filesize_approx<25M]/"
                "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
            ),
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            audio_path = ydl.prepare_filename(info)

        if not os.path.exists(audio_path):
            candidates = [
                os.path.join(output_dir, name)
                for name in os.listdir(output_dir)
                if not name.endswith(".part")
            ]
            if not candidates:
                raise FileNotFoundError("yt-dlp did not produce a media file.")
            audio_path = candidates[0]

        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise ValueError("Downloaded media file is empty.")
        if file_size > MAX_WHISPER_FILE_BYTES:
            raise ValueError(
                f"Downloaded media ({file_size / (1024 * 1024):.1f} MB) exceeds the 25 MB Whisper upload limit."
            )

        meta = {
            "title": (info or {}).get("title"),
            "author": (info or {}).get("uploader") or (info or {}).get("channel"),
        }
        return audio_path, meta

    @staticmethod
    def _transcribe_audio(audio_path: str) -> str:
        load_dotenv()
        errors = []
        providers = (
            ("GROQ_API_KEY", Groq, "whisper-large-v3-turbo", "Groq Whisper"),
            ("OPENAI_API_KEY", OpenAI, "whisper-1", "OpenAI Whisper"),
        )
        for env_key, client_cls, model_name, label in providers:
            if api_key := (os.getenv(env_key) or "").strip():
                try:
                    client = client_cls(api_key=api_key)
                    with open(audio_path, "rb") as audio_file:
                        response = client.audio.transcriptions.create(
                            file=audio_file,
                            model=model_name,
                        )
                    text = response if isinstance(response, str) else getattr(response, "text", "")
                    if text and text.strip():
                        return text.strip()
                except Exception as e:
                    errors.append(f"{label} failed: {e}")

        if errors:
            raise RuntimeError("; ".join(errors))
        raise RuntimeError("No GROQ_API_KEY or OPENAI_API_KEY found for Whisper transcription.")

    @staticmethod
    def _clean_subtitle_text(raw_text: str, ext: str) -> str:
        if ext == ".txt":
            return raw_text.strip()

        lines = []
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if (
                not line
                or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:"))
                or line.isdigit()
                or SUBTITLE_RANGE_RE.match(line)
            ):
                continue
            cleaned = HTML_TAG_RE.sub("", SPEAKER_TAG_RE.sub(r"\1: ", line)).strip()
            if cleaned and (not lines or lines[-1] != cleaned):
                lines.append(cleaned)
        return "\n".join(lines).strip()

    @staticmethod
    def transcribe_uploaded_file(
        file_bytes: bytes, filename: str
    ) -> tuple[str | None, str | None, str | None]:
        ext = os.path.splitext((filename or "").strip())[1].lower()
        if not file_bytes:
            return None, None, "Uploaded file is empty."

        if ext in TEXT_TRANSCRIPT_EXTENSIONS:
            text = Transcription._clean_subtitle_text(file_bytes.decode("utf-8", errors="replace"), ext)
            if not text:
                return None, None, "Uploaded transcript file contains no readable text."
            return text, "transcript_file", None

        if ext in MEDIA_EXTENSIONS:
            if len(file_bytes) > MAX_WHISPER_FILE_BYTES:
                size_mb = len(file_bytes) / (1024 * 1024)
                return (
                    None,
                    None,
                    f"Uploaded file ({size_mb:.1f} MB) exceeds the 25 MB Whisper upload limit. "
                    "Upload a smaller audio file (.m4a/.mp3) or a .vtt/.txt transcript instead.",
                )
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = os.path.join(tmpdir, f"upload{ext}")
                    with open(tmp_path, "wb") as f:
                        f.write(file_bytes)
                    text = Transcription._transcribe_audio(tmp_path)
                    if not text:
                        return None, None, "Whisper returned an empty transcript."
                    return text, "whisper", None
            except Exception as e:
                return None, None, str(e)

        return None, None, f"Unsupported file format '{ext or 'unknown'}'."

    @staticmethod
    def _transcribe_with_whisper(source_url: str) -> tuple[str | None, dict | None, str | None]:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path, meta = Transcription._download_audio(source_url, tmpdir)
                text = Transcription._transcribe_audio(audio_path)
                if not text:
                    return None, meta, "Whisper returned an empty transcript."
                return text, meta, None
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return None, None, str(e)

    @staticmethod
    def get_transcription_with_source(source: str) -> tuple[str | None, str | None, dict | None, str | None]:
        vid = extract_youtube_id(source)
        if not vid:
            return None, None, None, "Please enter a valid YouTube link."

        if text := Transcription._fetch_youtube_transcript(vid):
            return text, "youtube", None, None

        text, meta, err = Transcription._transcribe_with_whisper(f"https://www.youtube.com/watch?v={vid}")
        return text, ("whisper" if text else None), meta, err

    @staticmethod
    def get_transcription(vid: str) -> str | None:
        text, _, _, _ = Transcription.get_transcription_with_source(vid)
        return text

    @staticmethod
    def get_video_info(source: str) -> dict:
        vid = extract_youtube_id(source) or (source or "").strip()
        fallback = {"title": f"YouTube Video ({vid})", "author": "YouTube"}
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
            with urlopen(oembed_url, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {
                "title": data.get("title") or fallback["title"],
                "author": data.get("author_name") or fallback["author"],
            }
        except Exception:
            return fallback
