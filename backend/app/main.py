import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.database import redis_client, mongo_client

app = FastAPI(
    title="Production Hybrid RAG Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup():
    logging.info("Hybrid RAG Backend Started")

@app.get("/health")
async def health():
    redis_status = True
    mongo_status = True
    try:
        await redis_client.ping()
    except Exception:
        redis_status = False

    try:
        await mongo_client.admin.command("ping")
    except Exception:
        mongo_status = False

    return {
        "status": "healthy",
        "redis": redis_status,
        "mongodb": mongo_status,
        "llm": True
    }
