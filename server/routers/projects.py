"""Project router — exposes the OSS default Project's project-scoped fields.

Mirrors the hosted platform's ``client.project.update(...)`` surface
(`retrieval_criteria`, `custom_instructions`, `custom_categories`, `multilingual`,
`decay`) over a ``GET /project`` + ``PATCH /project`` pair. The OSS server is
single-tenant single-default-project today; the schema is multi-row from day
one so a future ``/projects/{id}`` surface does not require a migration.
"""

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from auth import verify_auth
from server_state import PROJECT_FIELDS, get_project, update_project

router = APIRouter(tags=["project"])


class ProjectResponse(BaseModel):
    """Current state of the default project's scoped fields."""

    custom_instructions: Optional[str] = None
    custom_categories: Optional[List[Union[str, Dict[str, Any]]]] = None
    retrieval_criteria: Optional[List[Dict[str, Any]]] = None
    multilingual: bool = False
    decay: bool = False


class ProjectUpdateBody(BaseModel):
    """Partial-update body for ``PATCH /project``.

    Same five fields as the hosted ``Project.update``. At least one must be set.
    """

    custom_instructions: Optional[str] = Field(None, description="Free-form fact-extraction guidance.")
    custom_categories: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None,
        description=(
            "Project-scoped categories. Each entry may be a bare name string or a "
            "{name, description} dict."
        ),
    )
    retrieval_criteria: Optional[List[Dict[str, Any]]] = Field(
        None,
        description=(
            "Weighted criteria used by criteria-based search scoring. Each entry "
            "must contain {name, description, weight?}."
        ),
    )
    multilingual: Optional[bool] = Field(
        None, description="Use the input language for memory storage and retrieval."
    )
    decay: Optional[bool] = Field(
        None,
        description=(
            "Toggle Memory Decay. When True, search-time ranking boosts recently-used "
            "memories and gently dampens stale ones."
        ),
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _at_least_one(self) -> "ProjectUpdateBody":
        if all(getattr(self, field) is None for field in PROJECT_FIELDS):
            raise ValueError("At least one project field must be provided.")
        return self


def _to_response(project: Dict[str, Any]) -> ProjectResponse:
    return ProjectResponse(
        custom_instructions=project.get("custom_instructions"),
        custom_categories=project.get("custom_categories"),
        retrieval_criteria=project.get("retrieval_criteria"),
        multilingual=bool(project.get("multilingual", False)),
        decay=bool(project.get("decay", False)),
    )


@router.get("/project", summary="Get the default project's scoped fields", response_model=ProjectResponse)
def get_project_endpoint(_auth=Depends(verify_auth)) -> ProjectResponse:
    return _to_response(get_project())


@router.patch("/project", summary="Update the default project", response_model=ProjectResponse)
def patch_project(body: ProjectUpdateBody, _auth=Depends(verify_auth)) -> ProjectResponse:
    payload = body.model_dump(exclude_unset=True)
    try:
        update_project(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _to_response(get_project())
