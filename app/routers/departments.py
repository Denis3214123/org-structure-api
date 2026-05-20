from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DepartmentCreate,
    DepartmentDetail,
    DepartmentPatch,
    DepartmentRead,
    EmployeeCreate,
    EmployeeRead,
)
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(db: DbSession, payload: DepartmentCreate) -> DepartmentRead:
    dept = department_service.create_department(db, payload)
    return DepartmentRead.model_validate(dept)


@router.post(
    "/{department_id}/employees/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    db: DbSession, department_id: int, payload: EmployeeCreate
) -> EmployeeRead:
    emp = department_service.create_employee(db, department_id, payload)
    return EmployeeRead.model_validate(emp)


@router.get("/{department_id}", response_model=DepartmentDetail)
def get_department(
    db: DbSession,
    department_id: int,
    depth: int = Query(default=1, ge=1, le=5),
    include_employees: bool = Query(default=True),
) -> DepartmentDetail:
    return department_service.get_department_detail(db, department_id, depth, include_employees)


@router.patch("/{department_id}", response_model=DepartmentRead)
def patch_department(
    db: DbSession, department_id: int, payload: DepartmentPatch
) -> DepartmentRead:
    dept = department_service.update_department(db, department_id, payload)
    return DepartmentRead.model_validate(dept)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    db: DbSession,
    department_id: int,
    mode: str = Query(..., description="cascade | reassign"),
    reassign_to_department_id: int | None = Query(default=None),
) -> None:
    department_service.delete_department(
        db,
        department_id,
        mode=mode,
        reassign_to_department_id=reassign_to_department_id,
    )
