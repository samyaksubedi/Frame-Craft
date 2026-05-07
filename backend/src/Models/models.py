# # src/models/models.py
# from __future__ import annotations
# from datetime import datetime
# from typing import List, Optional
# from uuid import uuid4
# from sqlmodel import Field, SQLModel, Relationship


# def _uuid() -> str:
#     return str(uuid4())


# def _now() -> datetime:
#     return datetime.now()


# class Job(SQLModel, table=True):
#     id: str = Field(default_factory=_uuid, primary_key=True)
#     prompt: str = Field(default="")
#     num_thumbnails: int = Field(default=1, ge=0, le=3)
#     status: str = Field(default="pending")
#     created_at: datetime = Field(default_factory=_now)
#     headshot_url: str = Field(default="")
#     thumbnails: List[Thumbnail] = Relationship(back_populates="job")


# class Thumbnail(SQLModel, table=True):
#     id: str = Field(default_factory=_uuid, primary_key=True)
#     job_id: str = Field(foreign_key="job.id")
#     style_name: str = Field(default="")
#     imagekit_url: Optional[str] = Field(default=None)
#     status: str = Field(default="pending")
#     error_message: Optional[str] = Field(default=None)
#     created_at: datetime = Field(default_factory=_now)

#     job: Optional[Job] = Relationship(back_populates="thumbnails")
# ← remove from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy.orm import Mapped


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now()


class Job(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    prompt: str = Field(default="")
    num_thumbnails: int = Field(default=1, ge=0, le=3)
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=_now)
    headshot_url: str = Field(default="")
    thumbnails: Mapped[List["Thumbnail"]] = Relationship(back_populates="job")
    #                       ↑ string here because Thumbnail isn't defined yet


class Thumbnail(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    style_name: str = Field(default="")
    imagekit_url: Optional[str] = Field(default=None)
    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
    job: Mapped[Optional["Job"]] = Relationship(back_populates="thumbnails")
