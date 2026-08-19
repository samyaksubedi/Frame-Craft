from pydantic import BaseModel, Field, HttpUrl, field_validator
from Schemas.thumbnail_schema import ThumbnailResponse


class CreateJobRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)
    num_thumbnails: int = Field(..., le=3, ge=1)
    headshot_url: HttpUrl = Field(...)

    @field_validator("prompt")
    @classmethod
    def prompt_must_have_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Prompt must contain at least 3 non-whitespace characters")
        return value


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
