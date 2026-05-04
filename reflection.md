# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
<<<<<<< HEAD
- What classes did you include, and what responsibilities did you assign to each?

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
=======
my initial design is to assist users with staying consistent with pet care by providing them with 3 key options including
1. Add a pet
2. Schedule activities (add, update, remove tasks like walks, feeding, meds, grooming)
3. View current schedule and daily plan

- What classes did you include, and what responsibilities did you assign to each?

Owner
- Holds: owner name, email, list of pets, preferences
- Actions: add_pet, remove_pet

Pet
- Holds: name, species, age, care needs
- Actions: update_needs

Task
- Holds: id, title, pet_name, category, duration_minutes, priority, preferred_time, scheduled_time, completed
- Actions: mark_complete, reschedule

Scheduler
- Holds: associated owner, task list, internal next_task_id
- Actions: add_task, remove_task, find_task, get_tasks_for_date, generate_daily_plan

**b. Design changes**

- Did your design change during implementation?
Yes. I refined the domain model from just the three actions to a class-centric design (Owner, Pet, Task, Scheduler) and added a dedicated Scheduler class to keep scheduling methods separate from data objects.
- If yes, describe at least one change and why you made it.
I added `Scheduler` so the scheduling algorithm and task lifecycle can evolve independently from `Owner`/`Pet` data tracking.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
<<<<<<< HEAD
- How did you decide which constraints mattered most?
=======
  - Time: scheduled_time + target date
  - Priority: sort by priority (lower numeric is higher importance)
  - Owner/pet relationships: tasks are filtered by owner pets
- How did you decide which constraints mattered most?
  - I focused on priority first and date alignment; this matches core user need for high-priority feed/walk events.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
<<<<<<< HEAD
- Why is that tradeoff reasonable for this scenario?
=======
  - We detect conflicts based on exact timestamp matches only (same scheduled_time), not overlapping durations or soft windows.
  - We also keep sorting/filtering simple with `sorted()` and lambda keys rather than a full interval scheduling solver.
- Why is that tradeoff reasonable for this scenario?
  - It makes the scheduler easier to implement and test now, and covers the majority of typical user needs for a basic pet care planner.
  - A more advanced overlap solver can be added later without breaking the current model.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
<<<<<<< HEAD
- What kinds of prompts or questions were most helpful?
=======
  - used AI to generate class skeletons, methods, docstrings, and well-structured test concepts.
- What kinds of prompts or questions were most helpful?
  - prompts asking for “how should Scheduler retrieve owner tasks” and “format schedule output for terminal” were especially helpful.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
<<<<<<< HEAD
- How did you evaluate or verify what the AI suggested?
=======
  - I changed the task storage so tasks are stored both globally in Scheduler and per Pet, because that fits domain responsibilities better.
- How did you evaluate or verify what the AI suggested?
  - I ran the demo script and tests; and I manually inspected behavior in both `main.py` and `test_pawpal.py`.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
<<<<<<< HEAD
- Why were these tests important?
=======
  - `mark_complete` toggles a task to completed.
  - Adding a task to a pet increases the pet task list count.
- Why were these tests important?
  - They validate critical task lifecycle and owner/pet task relationship behavior.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

**b. Confidence**

- How confident are you that your scheduler works correctly?
<<<<<<< HEAD
- What edge cases would you test next if you had more time?
=======
  - Moderate: core paths are covered; scheduler sorts and queries tasks correctly. 2 tests pass.
- What edge cases would you test next if you had more time?
  - duplicate pet names, no scheduled_time tasks, date spans across days, conflicting time slots.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
<<<<<<< HEAD
=======
  - Designing a clean class model and getting a passing pytest suite end-to-end very quickly.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
<<<<<<< HEAD
=======
  - Add a dedicated `ScheduleSlot` class and constraint solver (time windows, duration packing, resource usage), plus more UI integration.
>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
<<<<<<< HEAD
=======
  - Start with simple, testable abstractions and improve incrementally; use AI for scaffolding but always verify with runtime tests.

>>>>>>> 850b4f4 (feat: implement sorting, filtering, recurring task and conflict detection)
