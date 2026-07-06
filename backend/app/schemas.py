import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime: str
    size_bytes: int
    status: str
    error: str | None
    page_count: int | None
    tags: list[str]
    summary: str | None
    doc_date: datetime.date | None
    uploaded_at: datetime.datetime
    processed_at: datetime.datetime | None


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_no: int
    content_md: str


class DocumentDetail(DocumentOut):
    pages: list[PageOut]
