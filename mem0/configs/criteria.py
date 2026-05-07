from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CriterionConfig(BaseModel):
    """A single retrieval criterion used by criteria-based search scoring.

    `name` is the key the LLM scorer returns; `description` is the natural-language
    instruction interpreted by the LLM; `weight` controls how strongly this criterion
    influences the final weighted score relative to other criteria.
    """

    name: str = Field(description="Criterion name; used as the JSON key in scorer output.")
    description: str = Field(description="Natural-language definition the LLM uses to score memories.")
    weight: float = Field(default=1.0, description="Relative weight of this criterion in the weighted sum.")

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def _name_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Criterion name must be non-empty.")
        return stripped

    @field_validator("description")
    @classmethod
    def _description_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Criterion description must be non-empty.")
        return stripped

    @field_validator("weight")
    @classmethod
    def _weight_nonneg(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Criterion weight must be non-negative.")
        return value


def coerce_criteria(value: Optional[List]) -> Optional[List[CriterionConfig]]:
    """Accept either a list of dicts or a list of CriterionConfig instances."""
    if value is None:
        return None
    coerced: List[CriterionConfig] = []
    for item in value:
        if isinstance(item, CriterionConfig):
            coerced.append(item)
        elif isinstance(item, dict):
            coerced.append(CriterionConfig(**item))
        else:
            raise TypeError(f"retrieval_criteria entries must be dicts or CriterionConfig, got {type(item).__name__}")
    return coerced
