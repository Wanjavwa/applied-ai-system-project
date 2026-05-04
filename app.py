import streamlit as st
from datetime import date

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

from pawpal_system import Owner, Pet, Scheduler

st.divider()

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="")

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(owner=st.session_state.owner)

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"], index=0)

if st.button("Set owner"):
    st.session_state.owner.name = owner_name

st.markdown("### Pets")
if st.button("Add Pet"):
    if pet_name:
        new_pet = Pet(name=pet_name, species=species, age_years=0)
        st.session_state.owner.add_pet(new_pet)
        st.success(f"Added pet: {pet_name}")

if st.session_state.owner.pets:
    st.write("Current pets:")
    st.table([{"name": p.name, "species": p.species, "age_years": p.age_years} for p in st.session_state.owner.pets])
else:
    st.info("No pets yet. Add a pet to continue.")

st.markdown("### Tasks")
col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)

priority_map = {"low": 3, "medium": 2, "high": 1}

pet_for_task = st.selectbox("Pet for Task", [p.name for p in st.session_state.owner.pets] if st.session_state.owner.pets else [""])

if st.button("Add task"):
    if pet_for_task and task_title:
        st.session_state.scheduler.add_task(
            title=task_title,
            pet_name=pet_for_task,
            category="General",
            duration_minutes=int(duration),
            priority=priority_map[priority_label],
        )
        st.success(f"Task '{task_title}' added for {pet_for_task}")

if st.session_state.scheduler.get_all_owner_tasks():
    st.write("Current tasks:")
    st.table([
        {
            "id": t.id,
            "pet": t.pet_name,
            "title": t.title,
            "duration": t.duration_minutes,
            "priority": t.priority,
            "scheduled": t.scheduled_time.isoformat() if t.scheduled_time else "unscheduled",
            "completed": t.completed,
        }
        for t in st.session_state.scheduler.get_all_owner_tasks()
    ])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button executes your scheduling logic.")

if st.button("Generate schedule"):
    today = date.today()
    conflicts = st.session_state.scheduler.detect_conflicts()
    if conflicts:
        for warning_msg in conflicts:
            st.warning(warning_msg)
    plan = st.session_state.scheduler.sort_by_time(today)
    if plan:
        st.success(f"Today's schedule ({today}):")
        table_data = [
            {
                "time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "unscheduled",
                "pet": t.pet_name,
                "task": t.title,
                "priority": t.priority,
                "completed": t.completed,
            }
            for t in plan
        ]
        st.table(table_data)
    else:
        st.info("No tasks available for today. Add tasks to see a plan.")
