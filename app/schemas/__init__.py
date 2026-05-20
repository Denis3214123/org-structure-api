from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip_nonempty(v: str, field: str) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{field} must be a string")
    s = v.strip()
    if not s:
        raise ValueError(f"{field} must not be empty")
    if len(s) > 200:
        raise ValueError(f"{field} must be at most 200 characters")
    return s


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: object) -> str:
        if v is None:
            raise ValueError("name is required")
        return _strip_nonempty(str(v), "name")


class DepartmentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: object) -> str | None:
        if v is None:
            return None
        return _strip_nonempty(str(v), "name")

    @model_validator(mode="after")
    def reject_null_name(self) -> DepartmentPatch:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    created_at: datetime


class EmployeeCreate(BaseModel):
    full_name: str
    position: str
    hired_at: date | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, v: object) -> str:
        return _strip_nonempty(str(v), "full_name")

    @field_validator("position", mode="before")
    @classmethod
    def normalize_position(cls, v: object) -> str:
        return _strip_nonempty(str(v), "position")


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime


class DepartmentDetail(BaseModel):
    """Recursive department node for GET /departments/{id}."""

    department: DepartmentRead
    employees: list[EmployeeRead] = Field(default_factory=list)
    children: list[DepartmentDetail] = Field(default_factory=list)


DepartmentDetail.model_rebuild()
