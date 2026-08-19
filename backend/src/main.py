import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.job_router import router as job_router
from Configs.sql import create_tables
from Configs.env import CORS_ORIGINS
from Services.thumbnail_service import recover_interrupted_jobs
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # everything BEFORE yield → runs on startup
    logger.info("server starting...")
    create_tables()
    recover_interrupted_jobs()

    yield  # ← server is running, handling requests

    # everything AFTER yield → runs on shutdown
    logger.info("server shutting down...")


app = FastAPI(title="Youtube Thumbnail Generator", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(job_router)
