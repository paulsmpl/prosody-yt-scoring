from pydantic import BaseModel, Field, HttpUrl
from typing import List


class AnalyzeItem(BaseModel):
    url: HttpUrl
    start_minute: int = Field(default=10, ge=0, le=600)


class AnalyzeRequest(BaseModel):
    items: List[AnalyzeItem] = Field(min_length=1, max_length=20)


class AnalyzeResult(BaseModel):
    url: HttpUrl
    start_minute: int
    end_minute: int
    melody_score: float
    frequency_score: float
    combined_score: float
    audio_url: str


class AnalyzeResponse(BaseModel):
    results: List[AnalyzeResult]
