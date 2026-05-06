import logging
from fastapi import FastAPI
from Routes import job_router
from Configs.sql import create_tables
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # everything BEFORE yield → runs on startup
    logger.info("server starting...")
    create_tables()

    yield  # ← server is running, handling requests

    # everything AFTER yield → runs on shutdown
    logger.info("server shutting down...")


app = FastAPI(title="Youtube Thumbnail Generator", lifespan=lifespan)
