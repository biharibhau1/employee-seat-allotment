from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ---------- Project ----------
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    manager_name: Optional[str] = ""


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    manager_name: str
    status: str

    class Config:
        from_attributes = True


# ---------- Employee ----------
class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    email: EmailStr
    department: Optional[str] = None
    role: Optional[str] = None
    joining_date: Optional[date] = None
    project_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    project_id: Optional[int] = None


class EmployeeOut(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    department: Optional[str]
    role: Optional[str]
    joining_date: Optional[date]
    status: str
    project_id: Optional[int]

    class Config:
        from_attributes = True


# ---------- Seat ----------
class SeatCreate(BaseModel):
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: Optional[str] = "available"


class SeatOut(BaseModel):
    id: int
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: str

    class Config:
        from_attributes = True


class SeatAllocateRequest(BaseModel):
    employee_id: int
    seat_id: Optional[int] = None  # if omitted, auto-suggest a seat
    preferred_zone: Optional[str] = None


class SeatReleaseRequest(BaseModel):
    employee_id: int


class SeatAllocationOut(BaseModel):
    id: int
    employee_id: int
    seat_id: int
    project_id: Optional[int]
    allocation_status: str
    allocation_date: datetime

    class Config:
        from_attributes = True


# ---------- AI Assistant ----------
class AIQueryRequest(BaseModel):
    query: str
    email: Optional[str] = None


class AIQueryResponse(BaseModel):
    answer: str
