import pytest
from datetime import datetime, date, time

from pawpal_system import Owner, Pet, Scheduler


def test_task_completion():
    owner = Owner(name="Test")
    pet = Pet(name="Buddy", species="Dog", age_years=3)
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    task = scheduler.add_task("Walk", "Buddy", "Walk", 30, 1, preferred_time=time(8, 0), scheduled_time=datetime.combine(date.today(), time(8, 0)))
    assert not task.completed

    task.mark_complete()
    assert task.completed


def test_task_addition_to_pet():
    owner = Owner(name="Test")
    pet = Pet(name="Coco", species="Cat", age_years=2)
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    assert len(pet.tasks) == 0
    scheduler.add_task("Play", "Coco", "Playtime", 20, 2, preferred_time=time(18, 0), scheduled_time=datetime.combine(date.today(), time(18, 0)))
    assert len(pet.tasks) == 1
