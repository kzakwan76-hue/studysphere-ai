"""API request and response shapes."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    """Note: no storage path and no hash. Those stay inside the server."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    kind: str
    size_bytes: int
    page_count: int
    char_count: int
    chunk_count: int
    created_at: datetime


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    page_number: int
    position: int
    text: str


class SearchHitOut(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    score: float
    coverage: float
    matched_terms: list[str]
    text: str


class SearchResponse(BaseModel):
    query: str
    terms: list[str]  # the words actually searched for, after filler words were removed
    results: list[SearchHitOut]