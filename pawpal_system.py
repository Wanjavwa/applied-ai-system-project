from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Task:
    id: int
    title: str
    pet_name: str
    category: str
    duration_minutes: int
    priority: int
    preferred_time: Optional[time] = None
    scheduled_time: Optional[datetime] = None
    completed: bool = False
    frequency: Optional[str] = None  # 'daily', 'weekly', None

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.completed = True

    def reschedule(self, new_time: datetime) -> None:
        """Reschedule task to a new datetime."""
        self.scheduled_time = new_time


@dataclass
class Pet:
    name: str
    species: str
    age_years: float
    needs: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

    def update_needs(self, new_needs: List[str]) -> None:
        """Update the care needs for the pet."""
        self.needs = new_needs

    def add_task(self, task: Task) -> None:
        """Assign a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: int) -> None:
        """Remove a task from the pet by id."""
        self.tasks = [t for t in self.tasks if t.id != task_id]


@dataclass
class Owner:
    name: str
    email: Optional[str] = None
    pets: List[Pet] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's list."""
        if pet.name not in [p.name for p in self.pets]:
            self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def all_tasks(self) -> List[Task]:
        """Return all tasks across all pets."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.tasks: List[Task] = []
        self._next_task_id = 1

    def add_task(self, title: str, pet_name: str, category: str, duration_minutes: int, priority: int, preferred_time: Optional[time] = None, scheduled_time: Optional[datetime] = None, frequency: Optional[str] = None) -> Task:
        """Create and add a new task and assign it to the named pet."""
        if frequency not in (None, "daily", "weekly"):
            raise ValueError("frequency must be 'daily', 'weekly', or None")

        pet = next((p for p in self.owner.pets if p.name == pet_name), None)
        if pet is None:
            raise ValueError(f"Pet not found: {pet_name}")

        task = Task(
            id=self._next_task_id,
            title=title,
            pet_name=pet_name,
            category=category,
            duration_minutes=duration_minutes,
            priority=priority,
            preferred_time=preferred_time,
            scheduled_time=scheduled_time,
            frequency=frequency,
        )
        pet.add_task(task)
        self.tasks.append(task)
        self._next_task_id += 1
        logger.info("Task #%d added: '%s' for %s (priority=%d)", task.id, title, pet_name, priority)
        return task

    def get_all_owner_tasks(self) -> List[Task]:
        """Retrieve all tasks from the owner via pets."""
        return self.owner.all_tasks()

    def sort_by_time(self, target_date: Optional[date] = None) -> List[Task]:
        """Sort tasks by scheduled time; unscheduled tasks at the end."""
        tasks = self.get_all_owner_tasks() if target_date is None else self.get_tasks_for_date(target_date)
        scheduled = [t for t in tasks if t.scheduled_time is not None]
        unscheduled = [t for t in tasks if t.scheduled_time is None]
        scheduled_sorted = sorted(scheduled, key=lambda t: t.scheduled_time)
        return scheduled_sorted + unscheduled

    def filter_tasks(self, pet_name: Optional[str] = None, completed: Optional[bool] = None) -> List[Task]:
        """Filter tasks by pet name and/or completion status."""
        result = self.get_all_owner_tasks()
        if pet_name is not None:
            result = [t for t in result if t.pet_name == pet_name]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark a task complete; if recurring, create next occurrence."""
        task = self.find_task(task_id)
        if not task:
            return None

        task.mark_complete()
        logger.info("Task #%d '%s' marked complete", task.id, task.title)

        if task.frequency in {"daily", "weekly"} and task.scheduled_time is not None:
            interval = timedelta(days=1 if task.frequency == "daily" else 7)
            next_time = task.scheduled_time + interval
            return self.add_task(
                title=task.title,
                pet_name=task.pet_name,
                category=task.category,
                duration_minutes=task.duration_minutes,
                priority=task.priority,
                preferred_time=task.preferred_time,
                scheduled_time=next_time,
            )

        return task

    def detect_conflicts(self) -> List[str]:
        """Detect tasks scheduled at the exact same time and return warnings."""
        tasks = [t for t in self.get_all_owner_tasks() if t.scheduled_time is not None and not t.completed]
        conflicts: List[str] = []
        seen = {}
        for t in tasks:
            key = (t.scheduled_time, t.pet_name)
            if key in seen:
                conflicts.append(
                    f"Conflict: {t.pet_name} has multiple tasks at {t.scheduled_time.strftime('%Y-%m-%d %H:%M')} ({seen[key].title} and {t.title})"
                )
            seen[key] = t

        # cross-pet same-time conflict
        by_time = {}
        for t in tasks:
            by_time.setdefault(t.scheduled_time, []).append(t)
        for when, group in by_time.items():
            if len(group) > 1:
                pets = ", ".join(f"{g.pet_name}:{g.title}" for g in group)
                conflicts.append(f"Overlap: {when.strftime('%Y-%m-%d %H:%M')} has tasks for multiple pets: {pets}")

        if conflicts:
            logger.warning("%d scheduling conflict(s) detected", len(conflicts))
        return list(dict.fromkeys(conflicts))

    def get_tasks_for_date(self, target_date: date) -> List[Task]:
        """Return tasks assigned for a date."""
        return [t for t in self.get_all_owner_tasks() if t.scheduled_time and t.scheduled_time.date() == target_date]

    def generate_daily_plan(self, target_date: date) -> List[Task]:
        """Generate a plan for the day using priority and time slot ordering."""
        available = [t for t in self.get_all_owner_tasks() if not t.completed and (t.scheduled_time is None or t.scheduled_time.date() == target_date)]
        prioritized = sorted(available, key=lambda x: (x.priority, x.preferred_time or time(23, 59)))
        return prioritized

    def remove_task(self, task_id: int) -> None:
        """Remove task by its id from scheduler and pet."""
        self.tasks = [t for t in self.tasks if t.id != task_id]
        for pet in self.owner.pets:
            pet.remove_task(task_id)

    def find_task(self, task_id: int) -> Optional[Task]:
        """Find a task by id."""
        return next((t for t in self.get_all_owner_tasks() if t.id == task_id), None)
