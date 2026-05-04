"""
eval_advisor.py — Deterministic reliability evaluation for PawPal+ AI Advisor.

Runs 15 checks across three categories without making any real API calls.
Each check has a clear pass/fail criterion and a reason on failure.

Usage:
    python eval_advisor.py
"""

from __future__ import annotations

from datetime import datetime, date, time
from pawpal_system import Owner, Pet, Scheduler
from ai_advisor import retrieve_care_context, PetCareAdvisor, CARE_KNOWLEDGE_BASE

PASS = "PASS"
FAIL = "FAIL"

results: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    status = PASS if passed else FAIL
    results.append({"name": name, "status": status, "detail": detail})
    marker = "+" if passed else "x"
    print(f"  [{marker}] {name}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Category 1: RAG Retrieval Quality  (6 checks)
# ---------------------------------------------------------------------------

print("\n-- Category 1: RAG Retrieval Quality --")

dog_adult = Pet("Rex", "Dog", 3.0)
cat_senior = Pet("Whiskers", "Cat", 11.0)
dog_puppy = Pet("Pip", "Dog", 0.4)
fish = Pet("Nemo", "Fish", 1.0)

ctx_dog = retrieve_care_context([dog_adult])
check(
    "Dog adult guidelines retrieved",
    "twice daily" in ctx_dog.lower() or "30-60" in ctx_dog,
    "expected adult feeding/exercise text",
)

ctx_cat = retrieve_care_context([cat_senior])
check(
    "Cat senior guidelines retrieved",
    "senior" in ctx_cat.lower(),
    "expected senior-specific text",
)

ctx_puppy = retrieve_care_context([dog_puppy])
check(
    "Dog puppy age group correctly classified",
    "puppy" in ctx_puppy.lower(),
    "expected puppy guideline, not adult",
)

ctx_fish = retrieve_care_context([fish])
check(
    "Unknown species returns empty (no hallucinated guidelines)",
    ctx_fish == "",
    f"got: {repr(ctx_fish[:60])}",
)

ctx_multi = retrieve_care_context([dog_adult, cat_senior])
check(
    "Multiple pets: both appear in context",
    "Rex" in ctx_multi and "Whiskers" in ctx_multi,
    "one or both pets missing from context",
)

check(
    "Knowledge base covers feeding and health for all species",
    all("feeding" in cats and "health" in cats for cats in CARE_KNOWLEDGE_BASE.values()),
    "a species entry is missing feeding or health",
)

# ---------------------------------------------------------------------------
# Category 2: Tool Handler Reliability  (5 checks)
# ---------------------------------------------------------------------------

print("\n-- Category 2: Tool Handler Reliability --")

owner = Owner(name="Test Owner")
owner.add_pet(Pet("Rex", "Dog", 3.0))
scheduler = Scheduler(owner=owner)

# Need to instantiate without hitting the real API
import unittest.mock as mock
with mock.patch("ai_advisor.OpenAI"):
    advisor = PetCareAdvisor(scheduler)

empty_result = advisor._handle_tool("get_schedule", {})
check(
    "get_schedule returns 'No tasks' when schedule is empty",
    "no tasks" in empty_result.lower(),
    f"got: {repr(empty_result[:80])}",
)

scheduler.add_task("Morning walk", "Rex", "Walk", 30, 1,
                   scheduled_time=datetime.combine(date.today(), time(7, 30)))
populated_result = advisor._handle_tool("get_schedule", {})
check(
    "get_schedule lists the task after it is added",
    "Morning walk" in populated_result and "Rex" in populated_result,
    f"got: {repr(populated_result[:80])}",
)

add_result = advisor._handle_tool("add_task", {
    "title": "Evening walk", "pet_name": "Rex",
    "category": "Walk", "duration_minutes": 30, "priority": 2,
})
check(
    "add_task succeeds for a known pet",
    "Evening walk" in add_result and "Error" not in add_result,
    f"got: {repr(add_result[:80])}",
)

bad_pet_result = advisor._handle_tool("add_task", {
    "title": "Walk", "pet_name": "Ghost",
    "category": "Walk", "duration_minutes": 20, "priority": 2,
})
check(
    "add_task rejects unknown pet with error message",
    "error" in bad_pet_result.lower() or "not found" in bad_pet_result.lower(),
    f"got: {repr(bad_pet_result[:80])}",
)

unknown_tool_result = advisor._handle_tool("teleport_dog", {})
check(
    "Unknown tool name returns graceful error (no crash)",
    "unknown tool" in unknown_tool_result.lower(),
    f"got: {repr(unknown_tool_result[:80])}",
)

# ---------------------------------------------------------------------------
# Category 3: Confidence Parsing  (4 checks)
# ---------------------------------------------------------------------------

print("\n-- Category 3: Confidence Extraction --")

import re
from ai_advisor import _CONFIDENCE_RE

sample_with_confidence = (
    "Rex needs feeding twice a day.\n\nConfidence: 5/5 — fully supported by adult dog guidelines."
)
match = _CONFIDENCE_RE.search(sample_with_confidence)
check(
    "Confidence line is detected in response",
    match is not None,
    "regex did not match",
)

if match:
    extracted = match.group(1).strip()
    body = sample_with_confidence[: match.start()].strip()
    check(
        "Confidence value extracted correctly",
        extracted.startswith("5/5"),
        f"got: {repr(extracted)}",
    )
    check(
        "Confidence line stripped from visible reply",
        "Confidence:" not in body,
        f"body still contains confidence: {repr(body[-40:])}",
    )
else:
    check("Confidence value extracted correctly", False, "no match to extract from")
    check("Confidence line stripped from visible reply", False, "no match to extract from")

sample_no_confidence = "Rex needs feeding twice a day."
check(
    "Response without confidence line handled gracefully",
    _CONFIDENCE_RE.search(sample_no_confidence) is None,
    "regex falsely matched a response with no confidence line",
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

total = len(results)
passed = sum(1 for r in results if r["status"] == PASS)
failed = total - passed

print("\n" + "-" * 60)
print(f"  Results: {passed}/{total} checks passed", end="")
if failed:
    print(f"  ({failed} failed)")
    print("\n  Failed checks:")
    for r in results:
        if r["status"] == FAIL:
            print(f"    x {r['name']}: {r['detail']}")
else:
    print(" -- all checks passed")

print(f"\n  RAG retrieval:      {sum(1 for r in results[:6] if r['status']==PASS)}/6 passed")
print(f"  Tool reliability:   {sum(1 for r in results[6:11] if r['status']==PASS)}/5 passed")
print(f"  Confidence parsing: {sum(1 for r in results[11:] if r['status']==PASS)}/4 passed")
print("-" * 60 + "\n")
