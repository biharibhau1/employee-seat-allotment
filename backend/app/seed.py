"""
Seed script — generates sample data per assessment spec:
- 5,000 employees
- 5 floors, 10 zones
- 5,500 seats
- 10 projects
- >=500 available seats, >=100 reserved seats, >=50 employees pending allocation

Run: python -m app.seed  (from backend/ dir)
"""
import random
from datetime import date, timedelta

from faker import Faker

from .database import Base, engine, SessionLocal
from . import models

fake = Faker()
random.seed(42)

PROJECTS = [
    "Indigo", "Indreed", "Mydreed", "Preed", "Serfy",
    "Oreed", "Bedegreed", "Opreed", "Serry", "Kaary", "Mered",
]

FLOORS = [1, 2, 3, 4, 5]
ZONES = [f"Zone-{c}" for c in "ABCDEFGHIJ"]  # 10 zones
DEPARTMENTS = ["Engineering", "Product", "QA", "Design", "HR", "Finance", "Growth", "Support"]
ROLES = ["Software Engineer", "Senior Engineer", "QA Engineer", "Product Manager",
          "Designer", "HR Executive", "Team Lead", "Analyst"]


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed():
    reset_db()
    db = SessionLocal()
    try:
        # --- Projects ---
        projects = []
        for name in PROJECTS:
            p = models.Project(
                name=name,
                description=f"{name} client engagement",
                manager_name=fake.name(),
                status="active",
            )
            db.add(p)
            projects.append(p)
        db.commit()
        for p in projects:
            db.refresh(p)

        # --- Seats: 5 floors x 10 zones x ~110 seats = 5500 seats ---
        seats = []
        seats_per_zone = 110  # 5 floors * 10 zones * 110 = 5500
        reserved_target = 120
        maintenance_target = 30
        seat_count = 0
        for floor in FLOORS:
            for zone in ZONES:
                for i in range(seats_per_zone):
                    bay = f"Bay-{(i // 10) + 1}"
                    seat_number = f"{zone.split('-')[1]}{floor}-{i + 1:03d}"
                    seat = models.Seat(
                        floor=floor,
                        zone=zone,
                        bay=bay,
                        seat_number=seat_number,
                        status=models.SeatStatus.available,
                    )
                    db.add(seat)
                    seats.append(seat)
                    seat_count += 1
        db.commit()
        for s in seats:
            db.refresh(s)

        # Mark some seats reserved / maintenance before allocation
        random.shuffle(seats)
        for s in seats[:reserved_target]:
            s.status = models.SeatStatus.reserved
        for s in seats[reserved_target:reserved_target + maintenance_target]:
            s.status = models.SeatStatus.maintenance
        db.commit()

        available_seats = [s for s in seats if s.status == models.SeatStatus.available]
        random.shuffle(available_seats)

        # --- Employees: 5000 total, ~60 left pending allocation (no seat) ---
        total_employees = 5000
        pending_count = 60
        employees_to_seat = total_employees - pending_count  # will attempt allocation
        # Reserve at least 500 available seats unallocated -> only allocate up to (available - 500)
        allocatable_seats = available_seats[:max(0, len(available_seats) - 500)]

        employees = []
        used_emails = set()
        for i in range(total_employees):
            emp_code = f"ETH{i + 1:05d}"
            first_last = fake.unique.name()
            email_base = first_last.lower().replace(" ", ".").replace("'", "")
            email = f"{email_base}@ethara.ai"
            suffix = 1
            while email in used_emails:
                email = f"{email_base}{suffix}@ethara.ai"
                suffix += 1
            used_emails.add(email)

            joining_date = fake.date_between(start_date="-3y", end_date="today")
            project = random.choice(projects)

            emp = models.Employee(
                employee_code=emp_code,
                name=first_last,
                email=email,
                department=random.choice(DEPARTMENTS),
                role=random.choice(ROLES),
                joining_date=joining_date,
                project_id=project.id,
                status=models.EmployeeStatus.pending_allocation,
            )
            db.add(emp)
            employees.append(emp)

        db.commit()
        for e in employees:
            db.refresh(e)

        # Allocate seats to all but `pending_count` employees
        random.shuffle(employees)
        to_allocate = employees[:employees_to_seat]
        pending_employees = employees[employees_to_seat:]

        seat_idx = 0
        for emp in to_allocate:
            if seat_idx >= len(allocatable_seats):
                break
            seat = allocatable_seats[seat_idx]
            seat_idx += 1
            seat.status = models.SeatStatus.occupied
            allocation = models.SeatAllocation(
                employee_id=emp.id,
                seat_id=seat.id,
                project_id=emp.project_id,
                allocation_status=models.AllocationStatus.active,
                allocation_date=fake.date_time_between(start_date="-2y", end_date="now"),
            )
            emp.status = models.EmployeeStatus.active
            db.add(allocation)

        # Any employees left unallocated because seats ran out also count as pending
        for emp in to_allocate[seat_idx:]:
            emp.status = models.EmployeeStatus.pending_allocation
        for emp in pending_employees:
            emp.status = models.EmployeeStatus.pending_allocation

        db.commit()

        # --- Summary ---
        final_available = db.query(models.Seat).filter(
            models.Seat.status == models.SeatStatus.available
        ).count()
        final_occupied = db.query(models.Seat).filter(
            models.Seat.status == models.SeatStatus.occupied
        ).count()
        final_reserved = db.query(models.Seat).filter(
            models.Seat.status == models.SeatStatus.reserved
        ).count()
        final_pending = db.query(models.Employee).filter(
            models.Employee.status == models.EmployeeStatus.pending_allocation
        ).count()

        print(f"Seed complete: {seat_count} seats, {total_employees} employees")
        print(f"  Available: {final_available}, Occupied: {final_occupied}, Reserved: {final_reserved}")
        print(f"  Pending allocation: {final_pending}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
