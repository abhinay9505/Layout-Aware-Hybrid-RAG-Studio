import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "hybrid_rag")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UPLOAD_DIR = "uploads"
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "faiss_index")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

