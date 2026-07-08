from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models
from ..database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total_employees = db.query(func.count(models.Employee.id)).scalar()
    total_seats = db.query(func.count(models.Seat.id)).scalar()
    occupied = db.query(func.count(models.Seat.id)).filter(
        models.Seat.status == models.SeatStatus.occupied
    ).scalar()
    available = db.query(func.count(models.Seat.id)).filter(
        models.Seat.status == models.SeatStatus.available
    ).scalar()
    reserved = db.query(func.count(models.Seat.id)).filter(
        models.Seat.status == models.SeatStatus.reserved
    ).scalar()
    maintenance = db.query(func.count(models.Seat.id)).filter(
        models.Seat.status == models.SeatStatus.maintenance
    ).scalar()
    pending = db.query(func.count(models.Employee.id)).filter(
        models.Employee.status == models.EmployeeStatus.pending_allocation
    ).scalar()

    return {
        "total_employees": total_employees,
        "total_seats": total_seats,
        "occupied_seats": occupied,
        "available_seats": available,
        "reserved_seats": reserved,
        "maintenance_seats": maintenance,
        "new_joiners_pending_allocation": pending,
    }


@router.get("/project-utilization")
def project_utilization(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Project.name,
            func.count(models.SeatAllocation.id).label("occupied_seats"),
            func.count(models.Employee.id.distinct()).label("employees"),
        )
        .outerjoin(models.Employee, models.Employee.project_id == models.Project.id)
        .outerjoin(
            models.SeatAllocation,
            (models.SeatAllocation.project_id == models.Project.id)
            & (models.SeatAllocation.allocation_status == models.AllocationStatus.active),
        )
        .group_by(models.Project.name)
        .all()
    )
    return [
        {"project": name, "occupied_seats": occ, "employees": emp}
        for name, occ, emp in rows
    ]


@router.get("/floor-utilization")
def floor_utilization(db: Session = Depends(get_db)):
    floors = db.query(models.Seat.floor).distinct().all()
    result = []
    for (floor,) in floors:
        total = db.query(func.count(models.Seat.id)).filter(models.Seat.floor == floor).scalar()
        occupied = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == floor, models.Seat.status == models.SeatStatus.occupied
        ).scalar()
        available = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == floor, models.Seat.status == models.SeatStatus.available
        ).scalar()
        result.append({
            "floor": floor,
            "total_seats": total,
            "occupied": occupied,
            "available": available,
            "occupancy_pct": round((occupied / total * 100), 1) if total else 0,
        })
    return sorted(result, key=lambda r: r["floor"])
