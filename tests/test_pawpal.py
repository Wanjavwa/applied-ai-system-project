"""
Test suite for PawPal+.

Covers:
- Core scheduler logic (unit tests)
- RAG retrieval from the care knowledge base
- AI advisor tool handling (no real API calls)
- Reliability: consistent structured output from advisor tools
"""

import pytest
from datetime import datetime, date, time
from unittest.mock import MagicMock, patch

from pawpal_system import Owner, Pet, Scheduler
from ai_advisor import retrieve_care_context, PetCareAdvisor, CARE_KNOWLEDGE_BASE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_scheduler(pet_name="Buddy", species="Dog", age=3.0) -> tuple[Scheduler, Pet]:
    owner = Owner(name="Test Owner")
    pet = Pet(name=pet_name, species=species, age_years=age)
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)
    return scheduler, pet


# ---------------------------------------------------------------------------
# Core scheduler tests (existing + extended)
# ---------------------------------------------------------------------------

def test_task_completion():
    scheduler, pet = make_scheduler()
    task = scheduler.add_task(
        "Walk", pet.name, "Walk", 30, 1,
        preferred_time=time(8, 0),
        scheduled_time=datetime.combine(date.today(), time(8, 0)),
    )
    assert not task.completed
    task.mark_complete()
    assert task.completed


def test_task_addition_to_pet():
    scheduler, pet = make_scheduler(pet_name="Coco", species="Cat")
    assert len(pet.tasks) == 0
    scheduler.add_task(
        "Play", pet.name, "Playtime", 20, 2,
        preferred_time=time(18, 0),
        scheduled_time=datetime.combine(date.today(), time(18, 0)),
    )
    assert len(pet.tasks) == 1


def test_invalid_pet_raises():
    scheduler, _ = make_scheduler()
    with pytest.raises(ValueError, match="Pet not found"):
        scheduler.add_task("Walk", "Ghost", "Walk", 30, 1)


def test_invalid_frequency_raises():
    scheduler, pet = make_scheduler()
    with pytest.raises(ValueError, match="frequency"):
        scheduler.add_task("Walk", pet.name, "Walk", 30, 1, frequency="hourly")


def test_conflict_detection():
    scheduler, pet = make_scheduler()
    t = datetime.combine(date.today(), time(9, 0))
    scheduler.add_task("Feeding", pet.name, "Feeding", 15, 1, scheduled_time=t)
    scheduler.add_task("Grooming", pet.name, "Grooming", 10, 2, scheduled_time=t)
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) > 0


def test_recurring_task_creates_next_occurrence():
    scheduler, pet = make_scheduler()
    t = datetime.combine(date.today(), time(8, 0))
    task = scheduler.add_task("Feeding", pet.name, "Feeding", 10, 1, scheduled_time=t, frequency="daily")
    next_task = scheduler.complete_task(task.id)
    assert next_task is not None
    assert next_task.scheduled_time == t + __import__("datetime").timedelta(days=1)


def test_filter_by_pet():
    owner = Owner(name="Test")
    dog = Pet(name="Rex", species="Dog", age_years=2)
    cat = Pet(name="Mimi", species="Cat", age_years=1)
    owner.add_pet(dog)
    owner.add_pet(cat)
    scheduler = Scheduler(owner=owner)
    scheduler.add_task("Walk", "Rex", "Walk", 30, 1)
    scheduler.add_task("Play", "Mimi", "Play", 20, 2)

    rex_tasks = scheduler.filter_tasks(pet_name="Rex")
    assert all(t.pet_name == "Rex" for t in rex_tasks)
    assert len(rex_tasks) == 1


# ---------------------------------------------------------------------------
# RAG retrieval tests
# ---------------------------------------------------------------------------

def test_retrieve_care_context_dog_adult():
    pet = Pet(name="Rex", species="Dog", age_years=3)
    context = retrieve_care_context([pet])
    assert "Rex" in context
    assert "FEEDING" in context
    assert "EXERCISE" in context
    # Adult dog guideline should appear (not puppy copy)
    assert "twice daily" in context.lower() or "30-60" in context


def test_retrieve_care_context_cat_senior():
    pet = Pet(name="Whiskers", species="Cat", age_years=12)
    context = retrieve_care_context([pet])
    assert "Whiskers" in context
    assert "senior" in context.lower()


def test_retrieve_care_context_puppy():
    pet = Pet(name="Max", species="Dog", age_years=0.5)
    context = retrieve_care_context([pet])
    assert "puppy" in context.lower()


def test_retrieve_care_context_unknown_species():
    pet = Pet(name="Nemo", species="Fish", age_years=1)
    context = retrieve_care_context([pet])
    # No knowledge base entry for fish — should return empty
    assert context == ""


def test_retrieve_care_context_multiple_pets():
    pets = [
        Pet(name="Rex", species="Dog", age_years=3),
        Pet(name="Mimi", species="Cat", age_years=2),
    ]
    context = retrieve_care_context(pets)
    assert "Rex" in context
    assert "Mimi" in context


def test_knowledge_base_completeness():
    """Reliability: every species entry has feeding and health guidelines."""
    for species, categories in CARE_KNOWLEDGE_BASE.items():
        assert "feeding" in categories, f"{species} missing feeding"
        assert "health" in categories, f"{species} missing health"


# ---------------------------------------------------------------------------
# AI advisor tool-handling tests (no real API calls)
# ---------------------------------------------------------------------------

def test_advisor_get_schedule_empty():
    scheduler, _ = make_scheduler()
    advisor = PetCareAdvisor(scheduler)
    result = advisor._handle_tool("get_schedule", {})
    assert "No tasks" in result


def test_advisor_get_schedule_with_tasks():
    scheduler, pet = make_scheduler()
    scheduler.add_task("Morning walk", pet.name, "Walk", 30, 1)
    advisor = PetCareAdvisor(scheduler)
    result = advisor._handle_tool("get_schedule", {})
    assert "Morning walk" in result
    assert pet.name in result


def test_advisor_add_task_tool_success():
    scheduler, pet = make_scheduler()
    advisor = PetCareAdvisor(scheduler)
    result = advisor._handle_tool("add_task", {
        "title": "Evening walk",
        "pet_name": pet.name,
        "category": "Walk",
        "duration_minutes": 30,
        "priority": 1,
    })
    assert "Evening walk" in result
    tasks = scheduler.get_all_owner_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "Evening walk"


def test_advisor_add_task_unknown_pet():
    scheduler, _ = make_scheduler()
    advisor = PetCareAdvisor(scheduler)
    result = advisor._handle_tool("add_task", {
        "title": "Walk",
        "pet_name": "Ghost",
        "category": "Walk",
        "duration_minutes": 20,
        "priority": 2,
    })
    assert "Error" in result or "not found" in result


def test_advisor_unknown_tool():
    scheduler, _ = make_scheduler()
    advisor = PetCareAdvisor(scheduler)
    result = advisor._handle_tool("fly_to_moon", {})
    assert "Unknown tool" in result


# ---------------------------------------------------------------------------
# Reliability: mocked end-to-end chat
# ---------------------------------------------------------------------------

def _mock_text_response(text: str):
    """Build a minimal mock Claude response that looks like a final text reply."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def test_advisor_chat_returns_non_empty_string():
    scheduler, pet = make_scheduler()
    with patch("ai_advisor.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_response(
            "Rex needs feeding twice a day."
        )
        MockClient.return_value = mock_client

        advisor = PetCareAdvisor(scheduler)
        reply = advisor.chat("How often should I feed Rex?")

    assert isinstance(reply, str)
    assert len(reply) > 0


def test_advisor_chat_history_grows():
    scheduler, pet = make_scheduler()
    with patch("ai_advisor.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_response("Good question!")
        MockClient.return_value = mock_client

        advisor = PetCareAdvisor(scheduler)
        advisor.chat("Hello")
        advisor.chat("How are you?")
        # 2 user + 2 assistant turns
        assert len(advisor._history) == 4


def test_advisor_reset_clears_history():
    scheduler, _ = make_scheduler()
    with patch("ai_advisor.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_response("Sure!")
        MockClient.return_value = mock_client

        advisor = PetCareAdvisor(scheduler)
        advisor.chat("Hello")
        advisor.reset()
        assert advisor._history == []


def test_advisor_handles_tool_use_then_text():
    """Reliability: advisor correctly loops through a tool call before returning text."""
    scheduler, pet = make_scheduler()
    scheduler.add_task("Feeding", pet.name, "Feeding", 10, 1)

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "get_schedule"
    tool_block.input = {}
    tool_block.id = "tool_001"

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [tool_block]

    final_response = _mock_text_response("Your schedule looks good!")

    with patch("ai_advisor.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [tool_response, final_response]
        MockClient.return_value = mock_client

        advisor = PetCareAdvisor(scheduler)
        reply = advisor.chat("What's on the schedule?")

    assert reply == "Your schedule looks good!"
    # Claude was called twice: once returning tool_use, once returning text
    assert mock_client.messages.create.call_count == 2
