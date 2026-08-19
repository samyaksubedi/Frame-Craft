# import os
# import asyncio
import logging
from pathlib import Path as FilePath
import re
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    BackgroundTasks,
    UploadFile,
    File,
    Path,
    HTTPException,
    status,
)
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel

from sqlmodel import Session
from Configs.sql import get_session
from Configs.env import ALLOWED_HEADSHOT_HOSTS, MAX_UPLOAD_SIZE_MB
from Models.models import Job, Thumbnail
from Services.thumbnail_service import process_job, STYLE_ORDER
from Services.imagekit_service import upload_file, get_variants
from Schemas.job_schema import (
    CreateJobResponse,
    CreateJobRequest,
    GetJobResponse,
)
from Schemas.thumbnail_schema import ThumbnailResponse


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _has_valid_image_signature(contents: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return contents.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return contents.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return contents.startswith(b"RIFF") and contents[8:12] == b"WEBP"
    return False


async def _read_limited_upload(file: UploadFile) -> bytes:
    contents = bytearray()
    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        contents.extend(chunk)
        if len(contents) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image must be {MAX_UPLOAD_SIZE_MB} MB or smaller",
            )
    return bytes(contents)


def _validate_headshot_url(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HEADSHOT_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="headshot_url must be an uploaded Cloudinary image URL",
        )


@router.post(
    "/upload-headshot",
)
async def upload_headshot(file: UploadFile = File(...)):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are supported",
        )

    try:
        contents = await _read_limited_upload(file)
    finally:
        await file.close()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty"
        )
    if not _has_valid_image_signature(contents, content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File contents do not match the declared image type",
        )

    original_stem = FilePath(file.filename or "headshot").stem
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", original_stem).strip("-_")[:50]
    safe_stem = safe_stem or "headshot"
    file_name = f"{uuid4().hex}-{safe_stem}"
    try:
        url = upload_file(
            file_bytes=contents,
            file_name=file_name,
            folder="headshots",
            content_type=content_type,
        )
    except Exception:
        logger.exception("Headshot upload failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not upload the headshot",
        )
    return {"url": url}


@router.post("/job", response_model=CreateJobResponse)
async def create_jobs(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    headshot_url = str(request.headshot_url)
    _validate_headshot_url(headshot_url)
    job = Job(
        prompt=request.prompt,
        num_thumbnails=request.num_thumbnails,
        headshot_url=headshot_url,
    )
    session.add(job)
    styles = STYLE_ORDER[: request.num_thumbnails]
    for style in styles:
        thumbnail = Thumbnail(job_id=job.id, style_name=style)
        session.add(thumbnail)
    #  Fire and forget style generation
    session.commit()
    # asyncio.create_task(process_job(job.id))
    background_tasks.add_task(process_job, job.id)
    return CreateJobResponse(job_id=job.id)


@router.get("/job/{job_id}", response_model=GetJobResponse)
async def get_job(job_id: str = Path(...), session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    thumbnails = job.thumbnails

    # id: str
    # style_name: str
    # status: str
    # imagekit_url: Optional[str] = None
    # error_message: Optional[str] = None
    # variants: Optional[str] = None
    thumbnail_responses = [
        ThumbnailResponse(
            id=t.id,
            style_name=t.style_name,
            imagekit_url=t.imagekit_url,
            status=t.status,
            error_message=t.error_message,
            variants=get_variants(t.imagekit_url),
        )
        for t in thumbnails
    ]
    return GetJobResponse(
        id=job.id,
        prompt=job.prompt,
        num_thumbnails=job.num_thumbnails,
        status=job.status,
        thumbnails=thumbnail_responses,
        headshot_url=job.headshot_url,
    )
