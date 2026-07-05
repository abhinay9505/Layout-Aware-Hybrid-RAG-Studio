import os
# Set HF_HOME cache directory to D: drive due to low space on C: drive (only ~16MB free)
os.environ["HF_HOME"] = "D:\\huggingface_cache"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import logging
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env location relative to the config file path (app/.env)
config_dir = Path(__file__).resolve().parent
env_path = config_dir.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
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

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UPLOAD_DIR = str(BACKEND_DIR / "uploads")
FAISS_INDEX_DIR = str(BACKEND_DIR / os.getenv("FAISS_INDEX_DIR", "faiss_index"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

