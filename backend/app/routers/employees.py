from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=schemas.EmployeeOut, status_code=201)
def create_employee(payload: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    if db.query(models.Employee).filter(models.Employee.email == payload.email).first():
        raise HTTPException(400, "Duplicate employee email is not allowed")
    if db.query(models.Employee).filter(models.Employee.employee_code == payload.employee_code).first():
        raise HTTPException(400, "Duplicate employee_code")

    employee = models.Employee(
        employee_code=payload.employee_code,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        role=payload.role,
        joining_date=payload.joining_date,
        project_id=payload.project_id,
        status=models.EmployeeStatus.pending_allocation,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[schemas.EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="search by name/email/employee_code"),
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    query = db.query(models.Employee)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Employee.name.ilike(like),
                models.Employee.email.ilike(like),
                models.Employee.employee_code.ilike(like),
            )
        )
    if project_id:
        query = query.filter(models.Employee.project_id == project_id)
    if status:
        query = query.filter(models.Employee.status == status)
    return query.offset(offset).limit(limit).all()


@router.get("/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).get(employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    return employee


@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, payload: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).get(employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=204)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).get(employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    employee.status = models.EmployeeStatus.inactive
    db.commit()
    return None
