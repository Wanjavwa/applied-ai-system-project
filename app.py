import logging
import os
from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler
from ai_advisor import PetCareAdvisor

# ---------------------------------------------------------------------------
# Logging — writes to pawpal.log so the UI stays clean
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("pawpal.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("AI-powered pet care scheduling assistant")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="")
if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(owner=st.session_state.owner)
if "advisor" not in st.session_state:
    st.session_state.advisor = None
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []  # list of {"role": ..., "content": ...}


def get_or_create_advisor() -> PetCareAdvisor:
    """Return the advisor, creating it (or recreating it) as needed."""
    if st.session_state.advisor is None:
        st.session_state.advisor = PetCareAdvisor(st.session_state.scheduler)
    return st.session_state.advisor


# ---------------------------------------------------------------------------
# Layout: left column = schedule management | right column = AI advisor
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1], gap="large")

# ============================================================
# LEFT — Schedule management
# ============================================================
with left:
    st.subheader("Owner & Pets")

    owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
    if st.button("Set owner"):
        st.session_state.owner.name = owner_name
        # Reset advisor so it picks up the new name
        st.session_state.advisor = None
        logger.info("Owner name set to '%s'", owner_name)

    st.markdown("**Add a pet**")
    col_a, col_b = st.columns(2)
    with col_a:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col_b:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=2.0, step=0.5)

    if st.button("Add pet"):
        if pet_name:
            existing = [p.name for p in st.session_state.owner.pets]
            if pet_name in existing:
                st.warning(f"{pet_name} is already registered.")
            else:
                new_pet = Pet(name=pet_name, species=species, age_years=age)
                st.session_state.owner.add_pet(new_pet)
                st.session_state.advisor = None  # refresh advisor for new pet
                logger.info("Pet added: %s (%s, %.1fyr)", pet_name, species, age)
                st.success(f"Added {pet_name}!")

    if st.session_state.owner.pets:
        st.table(
            [{"name": p.name, "species": p.species, "age": p.age_years}
             for p in st.session_state.owner.pets]
        )
    else:
        st.info("No pets yet — add one above.")

    st.divider()
    st.subheader("Tasks")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority_label = st.selectbox("Priority", ["high", "medium", "low"])

    priority_map = {"high": 1, "medium": 2, "low": 3}
    pet_options = [p.name for p in st.session_state.owner.pets]
    pet_for_task = st.selectbox("Pet", pet_options if pet_options else ["(add a pet first)"])
    category = st.selectbox("Category", ["Walk", "Feeding", "Grooming", "Health", "Play", "Other"])

    if st.button("Add task"):
        if pet_for_task and pet_for_task != "(add a pet first)" and task_title:
            try:
                st.session_state.scheduler.add_task(
                    title=task_title,
                    pet_name=pet_for_task,
                    category=category,
                    duration_minutes=int(duration),
                    priority=priority_map[priority_label],
                )
                st.success(f"Task '{task_title}' added for {pet_for_task}.")
            except ValueError as e:
                st.error(f"Could not add task: {e}")
                logger.warning("Task add failed: %s", e)
        else:
            st.warning("Please add a pet and fill in the task title first.")

    all_tasks = st.session_state.scheduler.get_all_owner_tasks()
    if all_tasks:
        st.table([
            {
                "id": t.id,
                "pet": t.pet_name,
                "title": t.title,
                "category": t.category,
                "duration": t.duration_minutes,
                "priority": t.priority,
                "scheduled": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "—",
                "done": t.completed,
            }
            for t in all_tasks
        ])
    else:
        st.info("No tasks yet.")

    st.divider()
    st.subheader("Generate Today's Schedule")
    if st.button("Build schedule"):
        today = date.today()
        conflicts = st.session_state.scheduler.detect_conflicts()
        for warning_msg in conflicts:
            st.warning(warning_msg)
        plan = st.session_state.scheduler.generate_daily_plan(today)
        if plan:
            st.success(f"Schedule for {today}:")
            st.table([
                {
                    "time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "unscheduled",
                    "pet": t.pet_name,
                    "task": t.title,
                    "priority": t.priority,
                    "done": t.completed,
                }
                for t in plan
            ])
        else:
            st.info("No tasks scheduled for today.")

# ============================================================
# RIGHT — PawPal AI Advisor
# ============================================================
with right:
    st.subheader("PawPal AI Advisor")
    st.caption(
        "Ask about your pets' care needs. The advisor checks your live schedule "
        "and can add tasks directly."
    )

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        st.warning(
            "Set the `OPENROUTER_API_KEY` environment variable to enable the AI advisor. "
            "Run: `$env:OPENROUTER_API_KEY='your-key'` in PowerShell, then restart."
        )
    elif not st.session_state.owner.pets:
        st.info("Add at least one pet on the left to start chatting.")
    else:
        # Render existing chat history
        for msg in st.session_state.chat_display:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("confidence", "N/A") != "N/A":
                    st.caption(f"Confidence: {msg['confidence']}")

        user_input = st.chat_input("Ask the advisor anything about your pets...")

        if user_input:
            # Show user message immediately
            st.session_state.chat_display.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            advisor = get_or_create_advisor()
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        reply = advisor.chat(user_input)
                        confidence = advisor.last_confidence
                    except Exception as exc:
                        reply = f"Sorry, something went wrong: {exc}"
                        confidence = "N/A"
                        logger.error("Advisor error: %s", exc)
                st.markdown(reply)
                if confidence != "N/A":
                    st.caption(f"Confidence: {confidence}")
            st.session_state.chat_display.append(
                {"role": "assistant", "content": reply, "confidence": confidence}
            )
            st.rerun()

        if st.session_state.chat_display:
            if st.button("Clear chat"):
                st.session_state.chat_display = []
                if st.session_state.advisor:
                    st.session_state.advisor.reset()
                st.rerun()
