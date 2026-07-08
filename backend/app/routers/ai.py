"""
AI Assistant / Vibe Coding feature.

Default: rule-based / keyword intent parser (no external API key required,
works fully offline). If ANTHROPIC_API_KEY (or OPENAI_API_KEY) is set in the
environment, swap in a real LLM call here to handle free-form phrasing on
top of the same intent handlers below.
"""
import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import AIQueryRequest, AIQueryResponse

router = APIRouter(prefix="/ai", tags=["ai assistant"])


def _employee_seat_answer(db: Session, employee: models.Employee) -> str:
    allocation = (
        db.query(models.SeatAllocation)
        .filter(
            models.SeatAllocation.employee_id == employee.id,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
        )
        .first()
    )
    project_name = employee.project.name if employee.project else "no project assigned"
    if not allocation:
        return f"{employee.name} has not been allocated a seat yet. Assigned project: {project_name}."
    seat = db.query(models.Seat).get(allocation.seat_id)
    return (
        f"{employee.name} is seated on Floor {seat.floor}, Zone {seat.zone}, "
        f"Bay {seat.bay}, Seat {seat.seat_number}. Assigned to Project {project_name}."
    )


def _find_employee(db: Session, name: str = None, email: str = None):
    if email:
        return db.query(models.Employee).filter(models.Employee.email.ilike(email)).first()
    if name:
        return db.query(models.Employee).filter(models.Employee.name.ilike(f"%{name}%")).first()
    return None


@router.post("/query", response_model=AIQueryResponse)
def ai_query(payload: AIQueryRequest, db: Session = Depends(get_db)):
    q = payload.query.strip()
    q_lower = q.lower()

    # 1) "Where is employee <Name> seated?" / "where is my seat" + email
    name_match = re.search(
        r"employee\s+([A-Za-z][A-Za-z]*(?:\s+[A-Za-z]+)?)(?=\s+(?:is|seated|sit|located)\b|\s*\?|$)",
        q,
        re.IGNORECASE,
    )
    if name_match or ("my seat" in q_lower or "where is my" in q_lower):
        employee = None
        if payload.email:
            employee = _find_employee(db, email=payload.email)
        elif name_match:
            employee = _find_employee(db, name=name_match.group(1).strip())
        else:
            email_in_text = re.search(r"[\w\.-]+@[\w\.-]+", q)
            if email_in_text:
                employee = _find_employee(db, email=email_in_text.group(0))

        if not employee:
            return AIQueryResponse(answer="I couldn't find that employee. Please check the name or email.")
        return AIQueryResponse(answer=_employee_seat_answer(db, employee))

    # 2) "Which project am I assigned to?" / "which project is <name> assigned to"
    if "project" in q_lower and ("assigned" in q_lower or "which project" in q_lower) and "occupied" not in q_lower and "utilization" not in q_lower:
        assigned_name_match = re.search(
            r"is\s+([A-Za-z][A-Za-z]*(?:\s+[A-Za-z]+)?)\s+assigned", q, re.IGNORECASE
        )
        employee = None
        if payload.email:
            employee = _find_employee(db, email=payload.email)
        elif assigned_name_match:
            employee = _find_employee(db, name=assigned_name_match.group(1).strip())
        elif name_match:
            employee = _find_employee(db, name=name_match.group(1).strip())
        if employee:
            project_name = employee.project.name if employee.project else "no project"
            return AIQueryResponse(answer=f"{employee.name} is assigned to Project {project_name}.")
        return AIQueryResponse(answer="I couldn't find that employee to check their project.")

    # 3) "Show all available seats on Floor X"
    floor_match = re.search(r"floor\s*(\d+)", q_lower)
    if "available seat" in q_lower or ("available" in q_lower and "seat" in q_lower):
        query = db.query(models.Seat).filter(models.Seat.status == models.SeatStatus.available)
        if floor_match:
            query = query.filter(models.Seat.floor == int(floor_match.group(1)))
        seats = query.limit(10).all()
        if not seats:
            return AIQueryResponse(answer="No available seats found matching that criteria.")
        listing = ", ".join(f"{s.zone}-{s.seat_number} (Floor {s.floor})" for s in seats)
        return AIQueryResponse(answer=f"Available seats: {listing}.")

    # 4) "How many seats are occupied for Project X?"
    project_match = re.search(r"project\s+([A-Za-z][A-Za-z0-9\s]*)", q, re.IGNORECASE)
    if ("occupied" in q_lower or "utilization" in q_lower) and project_match:
        project_name = project_match.group(1).strip()
        project = db.query(models.Project).filter(models.Project.name.ilike(project_name)).first()
        if not project:
            return AIQueryResponse(answer=f"I couldn't find a project named {project_name}.")
        occupied_count = (
            db.query(models.SeatAllocation)
            .filter(
                models.SeatAllocation.project_id == project.id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active,
            )
            .count()
        )
        return AIQueryResponse(answer=f"{occupied_count} seat(s) are currently occupied for Project {project.name}.")

    # 5) "Who is sitting near me?" - same zone/floor as requester
    if "near me" in q_lower or "sitting near" in q_lower:
        employee = _find_employee(db, email=payload.email) if payload.email else None
        if not employee:
            return AIQueryResponse(answer="Please provide your email so I can find who is sitting near you.")
        allocation = (
            db.query(models.SeatAllocation)
            .filter(
                models.SeatAllocation.employee_id == employee.id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active,
            )
            .first()
        )
        if not allocation:
            return AIQueryResponse(answer="You don't have a seat allocated yet, so I can't find nearby colleagues.")
        my_seat = db.query(models.Seat).get(allocation.seat_id)
        neighbors = (
            db.query(models.Employee)
            .join(models.SeatAllocation, models.SeatAllocation.employee_id == models.Employee.id)
            .join(models.Seat, models.Seat.id == models.SeatAllocation.seat_id)
            .filter(
                models.Seat.floor == my_seat.floor,
                models.Seat.zone == my_seat.zone,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active,
                models.Employee.id != employee.id,
            )
            .limit(5)
            .all()
        )
        if not neighbors:
            return AIQueryResponse(answer="No one else is currently allocated in your zone.")
        names = ", ".join(n.name for n in neighbors)
        return AIQueryResponse(answer=f"Colleagues near you in Floor {my_seat.floor}, Zone {my_seat.zone}: {names}.")

    # 6) "Allocate a seat for a new employee joining today"
    if "allocate" in q_lower and ("new employee" in q_lower or "new joiner" in q_lower or "joining" in q_lower):
        return AIQueryResponse(
            answer="To allocate a seat for a new joiner, please use POST /employees to create the "
                   "employee record, then POST /seats/allocate with their employee_id. I can suggest "
                   "the best available seat automatically based on their project's team zone."
        )

    return AIQueryResponse(
        answer="I can help with: where an employee is seated, project assignment, available seats "
               "by floor, project seat utilization, and who's sitting nearby. Try rephrasing your question, "
               "e.g. 'Where is employee Amit seated?' or 'Show available seats on Floor 3'."
    )
