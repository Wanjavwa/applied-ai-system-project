from __future__ import annotations

import logging
import re
from typing import Optional

import anthropic

_CONFIDENCE_RE = re.compile(r"\n+Confidence:\s*(.+?)$", re.IGNORECASE | re.MULTILINE)

from pawpal_system import Scheduler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge base (RAG source)
# ---------------------------------------------------------------------------

CARE_KNOWLEDGE_BASE: dict = {
    "dog": {
        "feeding": {
            "puppy": "Puppies under 1 year need 3-4 small meals per day for healthy growth.",
            "adult": "Adult dogs (1-7 years) should be fed twice daily. Portion size depends on weight and breed.",
            "senior": "Senior dogs (7+ years) do well with smaller, more frequent meals and senior-formula food.",
        },
        "exercise": {
            "puppy": "Keep sessions short — 5 minutes per month of age, twice a day, to protect growing joints.",
            "adult": "Adult dogs need 30-60 minutes of exercise per day, ideally split into two sessions.",
            "senior": "Gentle daily walks of 20-30 minutes keep senior dogs mobile without overexertion.",
        },
        "grooming": {
            "general": "Most dogs need brushing weekly and bathing every 4-8 weeks. Trim nails monthly.",
        },
        "health": {
            "general": (
                "Annual vet checkups are essential. Core vaccines: rabies, distemper, parvovirus. "
                "Use monthly flea, tick, and heartworm prevention year-round."
            ),
            "dental": "Brush teeth 2-3 times per week or provide dental chews daily to prevent tartar build-up.",
        },
    },
    "cat": {
        "feeding": {
            "kitten": "Kittens under 1 year need 3-4 meals per day to support rapid growth.",
            "adult": "Adult cats (1-10 years) do well with 2 measured meals per day to prevent obesity.",
            "senior": "Senior cats (10+ years) often benefit from wet food for extra hydration and easier digestion.",
        },
        "exercise": {
            "general": "Cats need 15-30 minutes of interactive play daily using wands, feather toys, or laser pointers.",
        },
        "grooming": {
            "general": (
                "Short-haired cats self-groom but benefit from weekly brushing. "
                "Long-haired cats need daily brushing. Trim nails every 2-3 weeks."
            ),
        },
        "health": {
            "general": "Annual vet visits and core vaccines (rabies, FVRCP) are required even for indoor cats.",
            "litter": "Scoop litter boxes daily and do a full clean weekly to prevent odour and infection.",
        },
    },
}


def _age_group(species: str, age_years: float) -> str:
    s = species.lower()
    if s == "dog":
        if age_years < 1:
            return "puppy"
        if age_years >= 7:
            return "senior"
        return "adult"
    if s == "cat":
        if age_years < 1:
            return "kitten"
        if age_years >= 10:
            return "senior"
        return "adult"
    return "adult"


def retrieve_care_context(pets) -> str:
    """RAG step: pull relevant care guidelines for every pet in the household."""
    sections = []
    for pet in pets:
        kb = CARE_KNOWLEDGE_BASE.get(pet.species.lower())
        if not kb:
            logger.debug("No knowledge base entry for species: %s", pet.species)
            continue
        age_grp = _age_group(pet.species, pet.age_years)
        lines = [f"=== {pet.name} ({pet.species}, {pet.age_years}yr, {age_grp}) ==="]
        for category, content in kb.items():
            text = content.get(age_grp) or content.get("general", "")
            if text:
                lines.append(f"[{category.upper()}] {text}")
        sections.append("\n".join(lines))

    result = "\n\n".join(sections)
    logger.debug("RAG retrieved %d chars for %d pet(s)", len(result), len(pets))
    return result


# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

_TOOLS = [
    {
        "name": "get_schedule",
        "description": (
            "Return all current pet care tasks with their status, timing, and priority. "
            "Always call this before recommending new tasks to avoid duplicates."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_task",
        "description": "Add a new care task to the schedule for a specific pet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short task title"},
                "pet_name": {"type": "string", "description": "Exact name of the pet"},
                "category": {
                    "type": "string",
                    "description": "One of: Feeding, Walk, Grooming, Health, Play, Other",
                },
                "duration_minutes": {"type": "integer", "description": "Estimated duration in minutes"},
                "priority": {
                    "type": "integer",
                    "description": "1 = high, 2 = medium, 3 = low",
                },
            },
            "required": ["title", "pet_name", "category", "duration_minutes", "priority"],
        },
    },
]


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

class PetCareAdvisor:
    """Claude-powered advisor with RAG (knowledge base retrieval) and agentic tool use."""

    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.client = anthropic.Anthropic()
        self._history: list[dict] = []
        self.last_confidence: str = "N/A"
        logger.info("PetCareAdvisor initialised for owner '%s'", scheduler.owner.name)

    def _handle_tool(self, name: str, inputs: dict) -> str:
        if name == "get_schedule":
            tasks = self.scheduler.get_all_owner_tasks()
            if not tasks:
                return "No tasks currently in the schedule."
            lines = []
            for t in tasks:
                status = "done" if t.completed else "pending"
                when = t.scheduled_time.strftime("%Y-%m-%d %H:%M") if t.scheduled_time else "unscheduled"
                lines.append(
                    f"- [{status}] #{t.id} {t.pet_name}: {t.title} "
                    f"({t.category}, {t.duration_minutes}min, priority {t.priority}, {when})"
                )
            result = "\n".join(lines)
            logger.info("Tool get_schedule returned %d task(s)", len(tasks))
            return result

        if name == "add_task":
            known = [p.name for p in self.scheduler.owner.pets]
            if inputs["pet_name"] not in known:
                msg = f"Pet '{inputs['pet_name']}' not found. Available: {known}"
                logger.warning("Tool add_task rejected: %s", msg)
                return f"Error: {msg}"
            try:
                task = self.scheduler.add_task(
                    title=inputs["title"],
                    pet_name=inputs["pet_name"],
                    category=inputs["category"],
                    duration_minutes=int(inputs["duration_minutes"]),
                    priority=int(inputs["priority"]),
                )
                logger.info("Tool add_task created #%d '%s' for %s", task.id, task.title, task.pet_name)
                return f"Added task #{task.id}: '{task.title}' for {task.pet_name}."
            except ValueError as exc:
                logger.warning("Tool add_task error: %s", exc)
                return f"Error adding task: {exc}"

        return f"Unknown tool: {name}"

    def chat(self, user_message: str) -> str:
        """Send a message and return the advisor's reply. Handles tool-use internally."""
        owner = self.scheduler.owner
        pets = owner.pets

        # RAG: retrieve care guidelines relevant to this owner's pets
        care_context = retrieve_care_context(pets)
        pet_summary = (
            ", ".join(f"{p.name} ({p.species}, {p.age_years}yr)" for p in pets)
            or "No pets registered yet."
        )

        system_prompt = f"""You are PawPal AI, a concise and friendly pet care advisor integrated with a live scheduling system.

Owner: {owner.name or "the user"}
Pets: {pet_summary}

--- Retrieved Pet Care Guidelines ---
{care_context or "No guidelines available — no pets registered yet."}
-------------------------------------

Use the retrieved guidelines above when giving advice. You have two tools:
• get_schedule — inspect the live task list before making recommendations (always do this first).
• add_task — add a task directly to the schedule when the user says yes.

Keep replies short and specific. If you add a task, confirm what was added and its ID.

After your main response, on a new line write exactly:
Confidence: X/5 — [one short reason]
where X is 1–5 based on how well the retrieved guidelines and schedule data support your answer (5 = fully supported, 1 = mostly uncertain)."""

        self._history.append({"role": "user", "content": user_message})
        logger.info("User: %s", user_message[:120])

        # Copy history for this call; tool-call exchanges stay local to the turn
        messages = list(self._history)

        # Agentic loop — keep going until Claude stops calling tools
        while True:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                tools=_TOOLS,
                messages=messages,
            )
            logger.debug("Claude stop_reason=%s", response.stop_reason)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result_text = self._handle_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            else:
                raw = next(
                    (block.text for block in response.content if hasattr(block, "text")), ""
                )
                # Extract and strip the confidence line before storing/returning
                match = _CONFIDENCE_RE.search(raw)
                if match:
                    self.last_confidence = match.group(1).strip()
                    reply = raw[: match.start()].strip()
                else:
                    self.last_confidence = "N/A"
                    reply = raw.strip()
                logger.info("Advisor (confidence=%s): %s", self.last_confidence, reply[:120])
                self._history.append({"role": "assistant", "content": reply})
                return reply

    def reset(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        logger.info("Conversation history cleared")
