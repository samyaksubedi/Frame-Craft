from pydantic import BaseModel
from typing import Optional


class ThumbnailResponse(BaseModel):
    id: str
    style_name: str
    status: str
    imagekit_url: Optional[str] = None
    error_message: Optional[str] = None
    variants: Optional[dict] = None
