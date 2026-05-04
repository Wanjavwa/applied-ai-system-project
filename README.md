# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

This version ships with enhanced scheduler features:

- sort tasks by scheduled time using `Scheduler.sort_by_time`
- filter task lists by pet name and completion status with `Scheduler.filter_tasks`
- support recurring tasks (`daily`/`weekly`) via `Scheduler.complete_task`
- simple conflict detection for exact slot collisions with `Scheduler.detect_conflicts`
- demonstration script in `main.py` with out-of-order insertion and conflict handling

## Testing PawPal+

We have an automated test suite in `tests/test_pawpal.py` covering:

- Sorting correctness (`Scheduler.sort_by_time` returns tasks in chronological order)
- Recurrence logic (completing a `daily` task creates a next-day instance)
- Conflict detection (same-time tasks generate overlap warnings)
- Basic task lifecycle (completion state and pet list task tracking)

Run tests with:

```bash
python -m pytest
```

Confidence: ★★★★☆ (4/5)
