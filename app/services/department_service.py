from __future__ import annotations

import logging
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Department, Employee
from app.schemas import (
    DepartmentCreate,
    DepartmentDetail,
    DepartmentPatch,
    DepartmentRead,
    EmployeeCreate,
    EmployeeRead,
)

log = logging.getLogger(__name__)


def get_department_or_404(db: Session, department_id: int) -> Department:
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


def _descendant_ids(db: Session, root_id: int) -> set[int]:
    """Subtree under root_id, excluding root_id."""
    found: set[int] = set()
    frontier: list[int] = [root_id]
    while frontier:
        pid = frontier.pop()
        rows = db.execute(select(Department.id).where(Department.parent_id == pid)).scalars().all()
        for cid in rows:
            if cid not in found:
                found.add(cid)
                frontier.append(cid)
    return found - {root_id}


def _would_create_cycle(db: Session, department_id: int, new_parent_id: int | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == department_id:
        return True
    return new_parent_id in _descendant_ids(db, department_id)


def _sibling_name_exists(
    db: Session, name: str, parent_id: int | None, exclude_id: int | None = None
) -> bool:
    conditions = [func.lower(Department.name) == name.lower()]
    if parent_id is None:
        conditions.append(Department.parent_id.is_(None))
    else:
        conditions.append(Department.parent_id == parent_id)
    if exclude_id is not None:
        conditions.append(Department.id != exclude_id)
    q = select(Department.id).where(and_(*conditions))
    return db.execute(q.limit(1)).scalar_one_or_none() is not None


def create_department(db: Session, payload: DepartmentCreate) -> Department:
    if payload.parent_id is not None:
        get_department_or_404(db, payload.parent_id)

    if _sibling_name_exists(db, payload.name, payload.parent_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name must be unique among siblings",
        )

    dept = Department(name=payload.name, parent_id=payload.parent_id)
    db.add(dept)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        log.warning("integrity error on department create: %s", e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create department",
        ) from e
    db.refresh(dept)
    return dept


def create_employee(db: Session, department_id: int, payload: EmployeeCreate) -> Employee:
    get_department_or_404(db, department_id)
    emp = Employee(
        department_id=department_id,
        full_name=payload.full_name,
        position=payload.position,
        hired_at=payload.hired_at,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def _sorted_employees(dept: Department) -> list[Employee]:
    return sorted(dept.employees, key=lambda e: (e.full_name.lower(), e.id))


def _sorted_children(db: Session, parent_id: int) -> Sequence[Department]:
    rows = db.execute(
        select(Department)
        .options(selectinload(Department.employees))
        .where(Department.parent_id == parent_id)
        .order_by(func.lower(Department.name), Department.id)
    ).scalars().all()
    return rows


def build_department_detail(
    db: Session, dept: Department, depth: int, include_employees: bool
) -> DepartmentDetail:
    employees_models = _sorted_employees(dept) if include_employees else []
    employees = [EmployeeRead.model_validate(e) for e in employees_models]

    children: list[DepartmentDetail] = []
    if depth > 0:
        for ch in _sorted_children(db, dept.id):
            children.append(build_department_detail(db, ch, depth - 1, include_employees))

    return DepartmentDetail(
        department=DepartmentRead.model_validate(dept),
        employees=employees,
        children=children,
    )


def get_department_detail(
    db: Session, department_id: int, depth: int, include_employees: bool
) -> DepartmentDetail:
    dept = db.execute(
        select(Department)
        .options(selectinload(Department.employees))
        .where(Department.id == department_id)
    ).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return build_department_detail(db, dept, depth, include_employees)


def update_department(db: Session, department_id: int, payload: DepartmentPatch) -> Department:
    dept = get_department_or_404(db, department_id)
    updates = payload.model_dump(exclude_unset=True)

    new_name = updates.get("name", dept.name)
    if "parent_id" in updates:
        new_parent: int | None = updates["parent_id"]
    else:
        new_parent = dept.parent_id

    if new_parent is not None:
        get_department_or_404(db, new_parent)

    if "parent_id" in updates and _would_create_cycle(db, department_id, new_parent):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot set parent: would create a cycle in the department tree",
        )

    if _sibling_name_exists(db, new_name, new_parent, exclude_id=department_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name must be unique among siblings",
        )

    dept.name = new_name
    dept.parent_id = new_parent
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        log.warning("integrity error on department update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update department",
        ) from e
    db.refresh(dept)
    return dept


def delete_department(
    db: Session,
    department_id: int,
    *,
    mode: str,
    reassign_to_department_id: int | None,
) -> None:
    dept = get_department_or_404(db, department_id)

    if mode == "cascade":
        db.delete(dept)
        db.commit()
        return

    if mode == "reassign":
        if reassign_to_department_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="reassign_to_department_id is required when mode=reassign",
            )
        if reassign_to_department_id == department_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="reassign_to_department_id must differ from the deleted department",
            )
        get_department_or_404(db, reassign_to_department_id)
        if reassign_to_department_id in _descendant_ids(db, department_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reassign into a descendant of the deleted department",
            )

        db.execute(
            update(Employee)
            .where(Employee.department_id == department_id)
            .values(department_id=reassign_to_department_id)
        )
        db.execute(
            update(Department)
            .where(Department.parent_id == department_id)
            .values(parent_id=reassign_to_department_id)
        )
        db.delete(dept)
        db.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="mode must be 'cascade' or 'reassign'",
    )