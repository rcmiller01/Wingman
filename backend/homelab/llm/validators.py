"""Schema validators for LLM outputs."""

from pydantic import BaseModel, ConfigDict, Field


class NarrativeOutput(BaseModel):
    """Validated narrative output."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)


class SummaryOutput(BaseModel):
    """Validated summary output."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)

