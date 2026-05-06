# import os
# import asyncio
import logging
from fastapi import (
    APIRouter,
    Depends,
    BackgroundTasks,
    UploadFile,
    File,
    Path,
    HTTPException,
)
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel

from sqlmodel import Session
from Configs.sql import get_session
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


@router.post(
    "/upload-headshot",
)
async def upload_headshot(file: UploadFile = File(...)):
    contents = await file.read()
    url = upload_file(
        file_bytes=contents,
        file_name=file.filename,
        folder="/headshots",
        content_type=file.content_type,
    )
    return {"url": url}


@router.post("/job", response_model=CreateJobResponse)
async def create_jobs(
    request: CreateJobRequest, session: Session = Depends(get_session)
):
    job = Job(
        prompt=request.prompt,
        num_thumbnails=request.num_thumbnails,
        headshot_url=request.headshot_url,
    )
    session.add(job)
    styles = STYLE_ORDER[: request.num_thumbnails]
    for style in styles:
        thumbnail = Thumbnail(job_id=job.id, style_name=style)
        session.add(thumbnail)
    #  Fire and forget style generation
    session.commit()
    # asyncio.create_task(process_job(job.id))
    BackgroundTasks.add_task(process_job, job.id)
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
