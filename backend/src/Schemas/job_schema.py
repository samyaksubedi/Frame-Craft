from pydantic import BaseModel, Field
from Schemas.thumbnail_schema import ThumbnailResponse


class CreateJobRequest(BaseModel):
    prompt: str = Field(...)
    num_thumbnails: int = Field(..., le=3, ge=1)
    headshot_url: str = Field(...)


class CreateJobResponse(BaseModel):
    job_id: str = Field(...)


# class GetJobRequest(BaseModel):
#     job_id: str = Field(...)


class GetJobResponse(BaseModel):
    id: str
    prompt: str
    num_thumbnails: int = Field(default=1, ge=0, le=3)
    headshot_url: str
    status: str
    thumbnails: list[ThumbnailResponse]
