from datetime import datetime, date, time

from pawpal_system import Owner, Pet, Scheduler


def format_task(task):
    status = "✅" if task.completed else "🕒"
    scheduled = task.scheduled_time.strftime("%Y-%m-%d %H:%M") if task.scheduled_time else "unscheduled"
    return f"[{status}] (#{task.id}) {task.pet_name}: {task.title} - {task.category} - {task.duration_minutes}m - priority {task.priority} - {scheduled}"


def main():
    owner = Owner(name="Jamie", email="jamie@example.com")

    dog = Pet(name="Rex", species="Dog", age_years=4)
    cat = Pet(name="Mittens", species="Cat", age_years=2)

    owner.add_pet(dog)
    owner.add_pet(cat)

    scheduler = Scheduler(owner=owner)

    # add tasks out of order intentionally
    scheduler.add_task(title="Evening play", pet_name="Rex", category="Play", duration_minutes=25, priority=2, preferred_time=time(18, 0), scheduled_time=datetime.combine(date.today(), time(18, 0)))
    scheduler.add_task(title="Morning walk", pet_name="Rex", category="Walk", duration_minutes=30, priority=1, preferred_time=time(7, 30), scheduled_time=datetime.combine(date.today(), time(7, 30)))
    scheduler.add_task(title="Feeding", pet_name="Rex", category="Feeding", duration_minutes=15, priority=2, preferred_time=time(8, 0), scheduled_time=datetime.combine(date.today(), time(8, 0)), frequency="daily")
    scheduler.add_task(title="Litter cleaning", pet_name="Mittens", category="Grooming", duration_minutes=10, priority=1, preferred_time=time(9, 0), scheduled_time=datetime.combine(date.today(), time(9, 0)))
    scheduler.add_task(title="Vet check", pet_name="Mittens", category="Health", duration_minutes=30, priority=1, preferred_time=time(9, 0), scheduled_time=datetime.combine(date.today(), time(9, 0)))

    today_schedule = scheduler.sort_by_time(date.today())

    print("Today's Schedule:")
    for task in today_schedule:
        print(format_task(task))

    print("\nFiltered: Rex tasks not completed")
    for task in scheduler.filter_tasks(pet_name="Rex", completed=False):
        print(format_task(task))

    print("\nConflict checks:")
    for warning in scheduler.detect_conflicts():
        print(warning)

    # simulate completing a daily task
    completed_next = scheduler.complete_task(3)
    print("\nAfter completing task 3 and adding recurrence:")
    for task in scheduler.get_all_owner_tasks():
        print(format_task(task))


if __name__ == "__main__":
    main()
