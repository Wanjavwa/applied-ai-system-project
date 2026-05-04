# PawPal+ AI Pet Care Assistant

A conversational AI system that helps pet owners plan and manage daily pet care — powered by Retrieval-Augmented Generation (RAG) and an agentic Claude-based advisor that reads and writes a live schedule.

---

## Original Project (Modules 1–3)

This project evolves **PawPal+**, originally built during Modules 1–3 as a rule-based pet care scheduler. The original system let owners register pets, add care tasks with priorities and time slots, and generate a daily schedule sorted by priority and time. It included conflict detection for overlapping tasks and support for recurring daily and weekly tasks — but all logic was deterministic Python with no AI layer. The goal was to model the domain cleanly (Owner → Pet → Task → Scheduler) and prove that the scheduling rules worked through a pytest suite.

---

## What This Project Does

PawPal+ AI extends the original scheduler with a Claude-powered care advisor integrated directly into the Streamlit UI. The advisor:

- **Retrieves** species- and age-specific care guidelines from a built-in knowledge base before every response (RAG)
- **Reads the live schedule** via a tool call to avoid recommending tasks that already exist
- **Adds tasks directly** to the schedule when the owner agrees, closing the loop between conversation and action (Agentic)
- **Logs** every meaningful event — task creation, conflict warnings, RAG retrieval size, Claude tool calls — to `pawpal.log`

The result is a system where the AI is not a chatbot bolted on the side: every response is grounded in retrieved veterinary guidelines and the owner's actual current schedule.

---

## System Architecture

![Architecture Diagram](assets/architecture.png)

> If the image does not render, open `assets/architecture.md` and paste the Mermaid source into [mermaid.live](https://mermaid.live).

The system has four main layers:

| Layer | File | Role |
|---|---|---|
| **UI** | `app.py` | Two-column Streamlit interface — schedule management on the left, AI chat on the right |
| **AI Advisor** | `ai_advisor.py` | RAG retriever + prompt builder + Claude Haiku + tool handler |
| **Scheduler** | `pawpal_system.py` | In-memory domain model: Owner, Pet, Task, Scheduler |
| **Tests** | `tests/test_pawpal.py` | 22 tests — unit, RAG correctness, tool handling, mocked reliability |

**Data flow:**

```
Owner types question
  → RAG retriever looks up species/age group in CARE_KNOWLEDGE_BASE
  → Retrieved guidelines + pet summary injected into Claude system prompt
  → Claude calls get_schedule tool → reads live task list
  → Claude calls add_task tool (if owner agrees) → writes to Scheduler
  → Final text reply rendered in UI
  → All events logged to pawpal.log
```

Human checkpoints exist at two points: the owner reviews the AI's suggestion before any task is added, and the owner can also edit or remove tasks manually via the schedule panel without involving the AI.

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) (free tier works)

### 1. Clone the repo

```bash
git clone https://github.com/Wanjavwa/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2. Create and activate a virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 6. Run the tests (no API key required)

```bash
python -m pytest tests/ -v
```

All 22 tests run without hitting the Anthropic API — Claude calls are mocked.

---

## Sample Interactions

These are real outputs from the running system with an adult dog (Rex, 4yr) and a cat (Mittens, 2yr) registered.

---

### Example 1 — Checking whether a pet is fed enough

**User:** `Is Rex being fed enough? He only has one feeding task right now.`

**System (internally):**
- RAG retrieves adult dog feeding guideline: *"Adult dogs (1-7 years) should be fed twice daily."*
- Claude calls `get_schedule` → sees one `Feeding` task at 08:00

**PawPal AI:** 
> Based on care guidelines for adult dogs, Rex should be fed **twice daily** — once in the morning and once in the evening. I can see he currently has a morning feeding at 08:00. He's missing an evening meal. Would you like me to add an evening feeding task for him?

---

### Example 2 — Adding a task through conversation

**User:** `Yes, add an evening feeding for Rex at 6pm.`

**System (internally):**
- Claude calls `add_task` → title: "Evening feeding", pet: Rex, category: Feeding, duration: 15min, priority: 1

**PawPal AI:**
> Done! I've added **Evening feeding** for Rex (task #6, Feeding, 15 minutes, high priority). His feeding schedule now covers both morning and evening, which matches the twice-daily recommendation for adult dogs.

---

### Example 3 — Health gap detection

**User:** `Are there any health tasks I'm missing for my pets?`

**System (internally):**
- RAG retrieves: dog health guideline (*annual vet checkup, core vaccines, monthly flea/tick/heartworm*) and cat health guideline (*annual vet visit, FVRCP vaccine, daily litter scooping*)
- Claude calls `get_schedule` → no vet or health tasks found

**PawPal AI:**
> Looking at the schedule, neither Rex nor Mittens has any health-related tasks. A few things to consider:
>
> - **Rex (Dog):** Annual vet checkup due, plus monthly flea, tick, and heartworm prevention
> - **Mittens (Cat):** Annual vet visit needed (even for indoor cats), and litter should be scooped daily
>
> Would you like me to add a vet reminder task for either of them?

---

## Design Decisions and Trade-offs

### Why RAG instead of just giving Claude a big system prompt?

A fixed system prompt with all care guidelines for all species and ages would be long, wasteful, and harder to maintain. The RAG step means Claude only receives the guidelines relevant to the pets actually registered. Adding a new species (rabbit, bird) only requires updating `CARE_KNOWLEDGE_BASE` — no prompt engineering needed.

**Trade-off:** The knowledge base is hand-curated, not vector-searched. For a small, stable domain (pet care categories by species/age) this is simpler and more predictable than setting up embeddings. If the knowledge base grew to hundreds of entries, a vector store would become worthwhile.

### Why Claude Haiku and not a larger model?

The task is structured and the context is well-defined — retrieve guidelines, check a schedule, respond. Haiku handles this reliably at lower latency and cost. Opus or Sonnet would not meaningfully improve responses for this use case.

### Why in-memory storage instead of a database?

Keeping state in Python dataclasses keeps the project self-contained and easy to run locally without any infrastructure. The trade-off is that state resets when the app restarts. A SQLite or Postgres backend would be the next step for a production version.

### Why tool use instead of having Claude just describe what to do?

Without tools, the AI can only advise — the owner would have to manually add every suggested task. Tool use closes the loop: Claude reads the real schedule and writes back to it. This is what makes the workflow genuinely agentic rather than just conversational.

---

## Testing Summary

**22 tests across four categories:**

| Category | Tests | What's covered |
|---|---|---|
| Scheduler unit tests | 7 | Task lifecycle, conflict detection, recurring tasks, filtering, error handling |
| RAG retrieval tests | 6 | Correct guideline retrieval by species/age, unknown species gracefully returns empty, multiple pets |
| Tool handling tests | 4 | `get_schedule` with and without tasks, `add_task` success and error cases, unknown tool name |
| Reliability tests (mocked) | 5 | End-to-end chat returns non-empty string, history grows correctly, reset clears history, agentic tool-call loop runs to completion |

**What worked well:** Separating the tool handler (`_handle_tool`) from the API loop made unit testing possible without any mocking. The scheduler logic was also independently testable, which caught a `timedelta` import issue early.

**What was harder than expected:** Testing the agentic loop required simulating a `tool_use` response followed by a `end_turn` response from two different `side_effect` returns — getting the mock structure right for the Anthropic SDK's content block objects took iteration.

**What would be tested next with more time:** Multi-turn conversation coherence (does the advisor remember context across turns?), edge cases where the owner has no pets registered, and rate-limit handling.

---

## Reflection

Building PawPal+ taught me that the interesting engineering in AI systems is not the model call itself — it's everything around it: what context you retrieve, how you structure tools, what you log, and how you verify behavior without calling a live API in tests.

The RAG layer was the most clarifying decision. It forced me to think explicitly about what the model needs to know versus what it already knows, and it made the knowledge base a concrete, inspectable artifact rather than invisible prompt text. When something goes wrong, I can look at the retrieved context and trace exactly why the model responded the way it did.

The agentic tool loop was the most surprising to implement. The model alternates between "thinking" and "acting" across multiple API calls, and the loop has to be managed explicitly in code. That made the non-determinism concrete — the model might call one tool, two tools, or none, and the code has to handle all three cases. Writing a test that simulated a full tool-call cycle before the final response was the moment I understood what "agentic" actually means at the code level.

The biggest open question this project leaves me with: how do you evaluate whether an AI system is giving good advice, not just syntactically correct responses? The reliability tests confirm the system behaves consistently, but they do not verify that the advice is medically sound. That gap — between behavioral consistency and factual correctness — is where responsible AI development gets genuinely hard.

---

## Project Structure

```
applied-ai-system-project/
├── app.py                  # Streamlit UI (two-column: schedule + AI chat)
├── ai_advisor.py           # RAG retriever, PetCareAdvisor, tool handler
├── pawpal_system.py        # Domain model: Owner, Pet, Task, Scheduler
├── main.py                 # CLI demo script
├── requirements.txt        # anthropic, streamlit, pytest
├── pawpal.log              # Runtime log (generated on first run)
├── assets/
│   ├── architecture.md     # Mermaid source for system diagram
│   └── architecture.png    # Exported diagram image
└── tests/
    └── test_pawpal.py      # 22 tests (no API key required)
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `anthropic` | ≥ 0.40 | Claude Haiku API — AI advisor |
| `streamlit` | ≥ 1.30 | Web UI framework |
| `pytest` | ≥ 7.0 | Test runner |
