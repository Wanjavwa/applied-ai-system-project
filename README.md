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

## Reliability and Evaluation

The system uses four complementary approaches to verify that the AI works correctly, not just seems to.

### 1. Automated unit tests (pytest)

22 tests, 0 failures across all runs. No API key required — Claude calls are fully mocked.

| Category | Tests | What's verified |
|---|---|---|
| Scheduler unit tests | 7 | Task lifecycle, conflict detection, recurring tasks, filtering, error handling |
| RAG retrieval tests | 6 | Correct guideline retrieval by species/age, unknown species returns empty, multi-pet context |
| Tool handling tests | 4 | `get_schedule` with/without tasks, `add_task` success and error cases, unknown tool name |
| Reliability tests (mocked) | 5 | End-to-end chat returns text, history grows correctly, reset clears history, full tool-call loop simulated |

Run with: `python -m pytest tests/ -v`

### 2. Deterministic evaluation script

`eval_advisor.py` runs 15 structured checks across three categories without any API calls, producing a pass/fail report with reasons on failure.

```
Results: 15/15 checks passed -- all checks passed

  RAG retrieval:      6/6 passed
  Tool reliability:   5/5 passed
  Confidence parsing: 4/4 passed
```

Run with: `python eval_advisor.py`

### 3. Confidence scoring

Every AI response includes a self-assessed confidence rating that Claude appends based on how well the retrieved guidelines and schedule data support its answer. The format is:

```
Confidence: 4/5 — retrieved adult dog feeding guidelines directly support this recommendation.
```

This rating is stripped from the visible reply and displayed as a caption below each message in the UI. It is also logged to `pawpal.log`, making it possible to spot responses where the AI was uncertain (score ≤ 2) and investigate why.

### 4. Structured logging

All meaningful events write to `pawpal.log` with timestamps and severity levels:

```
2026-05-04 12:01:03 [INFO] ai_advisor: RAG retrieved 843 chars for 2 pet(s)
2026-05-04 12:01:05 [INFO] ai_advisor: Tool get_schedule returned 3 task(s)
2026-05-04 12:01:06 [INFO] ai_advisor: Advisor (confidence=5/5): Rex needs feeding twice...
2026-05-04 12:01:06 [WARNING] pawpal_system: 1 scheduling conflict(s) detected
```

### Testing summary

**22/22 unit tests passed. 15/15 eval checks passed.** The AI's self-reported confidence averaged 4–5/5 on questions with species-specific knowledge base entries, and dropped to N/A only when no pets were registered. The main gap identified: multi-turn coherence is not yet evaluated — the advisor maintains history but there are no tests that verify it uses earlier context correctly across three or more turns. That is the next evaluation milestone.

---

## Reflection and Ethics

### Limitations and biases in this system

**The knowledge base reflects a narrow slice of reality.** `CARE_KNOWLEDGE_BASE` covers only dogs and cats, using generalised guidelines written for average healthy animals. It has no entries for rabbits, birds, reptiles, or fish, and it cannot account for breed-specific needs (a Border Collie needs far more exercise than a Bulldog), medical conditions, or geographic context (heartworm prevention is critical in some regions, irrelevant in others). A user who trusts the AI's advice for a pet outside this narrow profile will receive silence or a generic fallback — not a warning that the system doesn't know.

**Age thresholds are fixed and arbitrary.** The system classifies a dog as "senior" at exactly 7 years. That cutoff was borrowed from a common veterinary rule of thumb, but it does not account for size (giant breeds age faster, small breeds slower). A 7-year-old Great Dane and a 7-year-old Chihuahua are in very different life stages, yet the system treats them identically.

**Confidence scores are self-assessed, not verified.** When Claude reports "Confidence: 5/5," that score reflects the model's internal sense of certainty given the retrieved context — not an independent measure of factual accuracy. A confidently wrong answer looks identical to a confidently correct one in the UI. High confidence should be read as "the retrieved guidelines clearly apply," not as "this advice is medically validated."

**The knowledge base was written by a person and reviewed by no one.** Every guideline in `CARE_KNOWLEDGE_BASE` was authored as part of this project. It has not been reviewed by a veterinarian. For a production system giving health or dietary advice, professional review and citation of sources would be mandatory.

---

### Could this system be misused?

**The realistic risk is over-reliance, not malice.** A pet care scheduler is not a high-stakes domain compared to medical or financial AI, but the risks are real:

- An owner might follow an AI-generated feeding schedule for a pet with a condition (diabetes, kidney disease, allergies) that requires a completely different approach. The system has no mechanism to ask about health history.
- The `add_task` tool writes to the schedule without any confirmation step beyond the conversational flow. If a user says "just set up everything Rex needs," the AI could add tasks the owner does not review carefully.
- A user who sees "Confidence: 5/5" may treat the response as authoritative and skip consulting a vet.

**Prevention measures built into this system:**
- The UI warns clearly when no API key is set rather than silently failing
- The `add_task` tool validates the pet name before writing, preventing phantom tasks
- Error states are logged and surfaced rather than swallowed silently
- The README and UI copy do not claim veterinary authority

**What a production version would need:** a disclaimer that advice is not a substitute for veterinary care, health-history input fields that the AI can retrieve via RAG before responding, and a hard guardrail that escalates any symptom-related question to "please contact your vet."

---

### What surprised me during reliability testing

The confidence scoring was more revealing than expected. The format "Confidence: X/5 — [reason]" was included in the system prompt as an instruction, but Claude interpreted "reason" very differently across turns. Sometimes it cited the specific guideline retrieved ("adult dog feeding guidelines support twice-daily feeding"); other times it cited the schedule data ("confirmed no existing feeding tasks"); occasionally it wrote vague phrases like "based on available information." This inconsistency is invisible to the automated tests because they mock the response — it only appeared during live testing. It showed that even a simple structured output instruction produces varied formats that a regex can handle but that a human reviewer would rightly question.

The second surprise was how well the agentic loop handled the edge case of an empty schedule. When asked "what should Rex be doing today?" with no tasks at all, Claude reliably called `get_schedule`, received "No tasks currently in the schedule," and responded with concrete suggestions drawn from the retrieved guidelines rather than confabulating a schedule that didn't exist. That grounding behaviour — using tool results to constrain generation — was more robust than I anticipated.

---

### AI collaboration during this project

**Helpful instance:** When designing the reliability tests for the agentic loop, I needed to simulate Claude making a tool call and then returning a final text response across two separate API calls. The approach of passing a list to `mock.side_effect` — so the first call returns a `tool_use` response and the second returns a text response — was suggested by Claude Code and worked immediately. Without that pattern, I would have written a more complex stateful mock class. The suggestion was precise, used the correct unittest.mock API, and matched the exact structure of the Anthropic SDK's response objects.

**Flawed instance:** The first version of `eval_advisor.py` used Unicode box-drawing characters (`─`, `✓`, `✗`) in its print statements. On Windows, the default console encoding (cp1252) cannot encode those characters, so the script crashed with a `UnicodeEncodeError` before running a single check. Claude Code generated the Unicode characters without any awareness of the target platform, and did not warn that this would fail on Windows terminals. The fix was straightforward (replace with ASCII `-`, `+`, `x`) but it was a real failure — the script was unusable until it was corrected. It illustrated a common AI blind spot: generating code that works on the developer's assumed platform (macOS/Linux UTF-8) while silently breaking on the user's actual platform.

---

### Key takeaway

The most important thing this project taught me about AI systems is the difference between *behavioural correctness* and *factual correctness*. Every test in this repo verifies that the system behaves consistently — the right tool is called, the right fields are returned, the history grows as expected. None of it verifies that the advice is actually good for Rex. That gap is not a flaw in the testing approach; it reflects a genuine hard problem in applied AI. Closing it requires domain expertise, sourced data, and human review — not more unit tests. Knowing where your automated tests stop being meaningful is as important as writing them.

---

## Project Structure

```
applied-ai-system-project/
├── app.py                  # Streamlit UI (two-column: schedule + AI chat)
├── ai_advisor.py           # RAG retriever, PetCareAdvisor, tool handler
├── pawpal_system.py        # Domain model: Owner, Pet, Task, Scheduler
├── main.py                 # CLI demo script
├── eval_advisor.py         # Deterministic eval script (15 checks, no API key needed)
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
