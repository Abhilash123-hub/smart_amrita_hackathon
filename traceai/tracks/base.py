"""Base track interface for multimodal fingerprinting and matching engines."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from traceai.schemas.asset import AssetInput, TrackType


class MatchCandidate(BaseModel):
    """Candidate match retrieved during recall."""
    source_id: str
    source_title: str
    similarity_score: float
    stage: str = "recall"


class MatchResult(BaseModel):
    """Resolution output of a track evaluation."""

    is_match: bool = Field(description="True if copyrighted work matched above threshold")
    matched_source: Optional[str] = Field(default=None, description="Identified source of copyright")
    similarity_score: Optional[float] = Field(default=None, description="Confidence or similarity score")
    details: Optional[str] = Field(default=None, description="Diagnostic info on matching stages")
    candidates: list[MatchCandidate] = Field(default_factory=list, description="Retrieved candidate matches")


class BaseTrack(ABC):
    """Abstract base class for modal fingerprinting tracks."""

    @property
    @abstractmethod
    def track_type(self) -> TrackType:
        """Supported track modality."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        asset: AssetInput,
        index_dir: Optional[Path] = None,
    ) -> MatchResult:
        """Fingerprint asset and match against indexed copyrighted works."""
        pass
