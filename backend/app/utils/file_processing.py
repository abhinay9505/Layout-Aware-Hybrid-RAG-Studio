import re
import unicodedata
from fastapi import HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter

class FileValidator:
    ALLOWED_EXTENSIONS = [
        # Documents
        ".pdf", ".docx",
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
        # Audio
        ".mp3", ".wav", ".m4a", ".ogg", ".flac",
        # Video
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
    ]

    # Max file sizes in bytes
    MAX_SIZES = {
        "document": 50 * 1024 * 1024,   # 50 MB
        "image": 20 * 1024 * 1024,       # 20 MB
        "audio": 100 * 1024 * 1024,      # 100 MB
        "video": 200 * 1024 * 1024,      # 200 MB
    }

    @classmethod
    def get_file_type(cls, filename):
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in {".pdf", ".docx"}:
            return "document"
        elif ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            return "image"
        elif ext in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
            return "audio"
        elif ext in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
            return "video"
        return None

    @classmethod
    async def validate(cls, file):
        valid = any([file.filename.endswith(ext) for ext in cls.ALLOWED_EXTENSIONS])
        if not valid:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

class TextCleaner:
    @staticmethod
    def clean(text):
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?:;\-\[\]\(\)\'\"/@#$%&*+=]', '', text)
        return text.strip()

class TextNormalizer:
    @staticmethod
    def normalize(text):
        # Don't lowercase for media — preserve proper nouns from transcriptions
        text = unicodedata.normalize('NFKD', text)
        return text.encode('ascii', 'ignore').decode('utf-8')

class RecursiveChunker:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def split(self, text):
        return self.splitter.create_documents([text])
