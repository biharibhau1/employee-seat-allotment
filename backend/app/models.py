import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


class EmployeeStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    pending_allocation = "pending_allocation"


class SeatStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    maintenance = "maintenance"


class AllocationStatus(str, enum.Enum):
    active = "active"
    released = "released"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, default="")
    manager_name = Column(String, default="")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="project")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    department = Column(String)
    role = Column(String)
    joining_date = Column(Date, default=date.today)
    status = Column(Enum(EmployeeStatus), default=EmployeeStatus.pending_allocation)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="employees")
    allocations = relationship("SeatAllocation", back_populates="employee")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("floor", "zone", "seat_number", name="uq_seat_location"),
    )

    id = Column(Integer, primary_key=True, index=True)
    floor = Column(Integer, nullable=False, index=True)
    zone = Column(String, nullable=False, index=True)
    bay = Column(String, nullable=False)
    seat_number = Column(String, nullable=False)
    status = Column(Enum(SeatStatus), default=SeatStatus.available, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    allocations = relationship("SeatAllocation", back_populates="seat")


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    allocation_status = Column(Enum(AllocationStatus), default=AllocationStatus.active, index=True)
    allocation_date = Column(DateTime, default=datetime.utcnow)
    released_date = Column(DateTime, nullable=True)

    employee = relationship("Employee", back_populates="allocations")
    seat = relationship("Seat", back_populates="allocations")
