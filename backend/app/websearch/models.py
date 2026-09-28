from pydantic import BaseModel, Field

class WebResult(BaseModel):
    title: str
    url: str
    description: str = ""
    provider: str = "duckduckgo"
    provider_rank: int = 0
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    rank_signals: list[str] = Field(default_factory=list)
    verification: dict = Field(default_factory=dict)
