from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/seats", tags=["seats"])


@router.post("", response_model=schemas.SeatOut, status_code=201)
def create_seat(payload: schemas.SeatCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(models.Seat)
        .filter(
            models.Seat.floor == payload.floor,
            models.Seat.zone == payload.zone,
            models.Seat.seat_number == payload.seat_number,
        )
        .first()
    )
    if exists:
        raise HTTPException(400, "Duplicate seat number on same floor/zone")
    seat = models.Seat(**payload.model_dump())
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


@router.get("", response_model=list[schemas.SeatOut])
def list_seats(
    db: Session = Depends(get_db),
    floor: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
):
    query = db.query(models.Seat)
    if floor is not None:
        query = query.filter(models.Seat.floor == floor)
    if zone:
        query = query.filter(models.Seat.zone == zone)
    if status:
        query = query.filter(models.Seat.status == status)
    return query.offset(offset).limit(limit).all()


@router.get("/available", response_model=list[schemas.SeatOut])
def list_available_seats(
    db: Session = Depends(get_db),
    floor: Optional[int] = None,
    zone: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    query = db.query(models.Seat).filter(models.Seat.status == models.SeatStatus.available)
    if floor is not None:
        query = query.filter(models.Seat.floor == floor)
    if zone:
        query = query.filter(models.Seat.zone == zone)
    return query.limit(limit).all()


def _find_best_zone_for_project(db: Session, project_id: Optional[int]) -> Optional[str]:
    """Find the zone where most active teammates of this project already sit."""
    if not project_id:
        return None
    row = (
        db.query(models.Seat.zone, func.count(models.SeatAllocation.id).label("cnt"))
        .join(models.SeatAllocation, models.SeatAllocation.seat_id == models.Seat.id)
        .join(models.Employee, models.Employee.id == models.SeatAllocation.employee_id)
        .filter(
            models.Employee.project_id == project_id,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
        )
        .group_by(models.Seat.zone)
        .order_by(func.count(models.SeatAllocation.id).desc())
        .first()
    )
    return row[0] if row else None


@router.post("/allocate", response_model=schemas.SeatAllocationOut, status_code=201)
def allocate_seat(payload: schemas.SeatAllocateRequest, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).get(payload.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    existing = (
        db.query(models.SeatAllocation)
        .filter(
            models.SeatAllocation.employee_id == employee.id,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "Employee already has an active seat allocation")

    seat = None
    if payload.seat_id:
        seat = db.query(models.Seat).get(payload.seat_id)
        if not seat:
            raise HTTPException(404, "Seat not found")
        if seat.status != models.SeatStatus.available:
            raise HTTPException(400, f"Seat is not available (status={seat.status.value})")
    else:
        # Auto-suggest: preferred_zone param > project's dominant zone > any available seat
        zone_priority = [z for z in [
            payload.preferred_zone,
            _find_best_zone_for_project(db, employee.project_id),
        ] if z]

        for zone in zone_priority:
            seat = (
                db.query(models.Seat)
                .filter(models.Seat.status == models.SeatStatus.available, models.Seat.zone == zone)
                .first()
            )
            if seat:
                break

        if not seat:
            # Alternate zone fallback: any available seat, closest floor number if possible
            seat = (
                db.query(models.Seat)
                .filter(models.Seat.status == models.SeatStatus.available)
                .first()
            )

        if not seat:
            raise HTTPException(409, "No available seats in any zone")

    seat.status = models.SeatStatus.occupied
    allocation = models.SeatAllocation(
        employee_id=employee.id,
        seat_id=seat.id,
        project_id=employee.project_id,
        allocation_status=models.AllocationStatus.active,
        allocation_date=datetime.utcnow(),
    )
    employee.status = models.EmployeeStatus.active
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.post("/release", status_code=200)
def release_seat(payload: schemas.SeatReleaseRequest, db: Session = Depends(get_db)):
    allocation = (
        db.query(models.SeatAllocation)
        .filter(
            models.SeatAllocation.employee_id == payload.employee_id,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
        )
        .first()
    )
    if not allocation:
        raise HTTPException(404, "No active allocation found for this employee")

    seat = db.query(models.Seat).get(allocation.seat_id)
    seat.status = models.SeatStatus.available
    allocation.allocation_status = models.AllocationStatus.released
    allocation.released_date = datetime.utcnow()

    employee = db.query(models.Employee).get(payload.employee_id)
    if employee:
        employee.status = models.EmployeeStatus.pending_allocation

    db.commit()
    return {"message": "Seat released", "seat_id": seat.id}
