"""Visual Streamlit dashboard for the Karnataka PUC timetable generator."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from timetable import COMBINATIONS, DAYS, PRACTICAL_SUBJECTS, SUBJECTS, create_excel_report, example_config, generate_schedule, validate


st.set_page_config(page_title="Karnataka PUC Timetable", page_icon="🗓️", layout="wide")


def subject_label(code: str) -> str:
    return f"{code} — {SUBJECTS[code]}"


def reset_editor(config: dict) -> None:
    st.session_state.config = config
    st.session_state.update({
        "college_name": config["college"]["name"], "college_code": config["college"]["code"],
        "college_place": config["college"]["place"], "college_taluk": config["college"]["taluk"],
        "college_district": config["college"]["district"], "college_udise": config["college"]["udise_code"],
        "college_principal": config["college"]["principal_name"], "college_year": config["college"]["academic_year"],
        "college_management": config["college"]["management"], "college_timings": config["college"]["college_timings"],
        "college_lunch": config["college"]["lunch_break"],
    })
    st.session_state.pop("rows", None)


if "config" not in st.session_state:
    reset_editor(example_config())

config = st.session_state.config
college = config["college"]

st.title("Karnataka PUC Timetable Generator")
st.caption("Complete the college, section, and lecturer forms. No JSON editing is required.")

with st.sidebar:
    st.header("Configuration")
    uploaded = st.file_uploader("Import saved configuration", type="json")
    if uploaded is not None and st.button("Load configuration", width="stretch"):
        try:
            reset_editor(json.load(uploaded))
            st.rerun()
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON file: {exc}")
    if st.button("Restore example college", width="stretch"):
        reset_editor(example_config())
        st.rerun()
    st.download_button(
        "Save configuration",
        json.dumps(config, indent=2),
        "college_configuration.json",
        "application/json",
        width="stretch",
    )

college_tab, section_tab, lecturer_tab, generate_tab = st.tabs(
    ["1. College details", "2. Sections", "3. Lecturers", "4. Generate & export"]
)

with college_tab:
    st.subheader("College details and daily timings")
    with st.form("college_form"):
        left, right = st.columns(2)
        with left:
            name = st.text_input("College name", key="college_name")
            code = st.text_input("College code", key="college_code")
            place = st.text_input("Place", key="college_place")
            taluk = st.text_input("Taluk", key="college_taluk")
            district = st.text_input("District", key="college_district")
        with right:
            udise = st.text_input("UDISE code", key="college_udise")
            principal = st.text_input("Principal name", key="college_principal")
            academic_year = st.text_input("Academic year", key="college_year")
            management = st.selectbox(
                "Management", ["GOVERNMENT", "AIDED", "UNAIDED", "KRIES", "MINORITY", "BIFURCATED"],
                key="college_management",
            )
            timings = st.text_input("College timings", key="college_timings")
            lunch = st.text_input("Lunch break", key="college_lunch")
        if st.form_submit_button("Save college details", type="primary"):
            config["college"] = {
                "name": name, "code": code, "place": place, "taluk": taluk, "district": district,
                "udise_code": udise, "principal_name": principal, "academic_year": academic_year,
                "management": management, "college_timings": timings, "lunch_break": lunch,
            }
            st.success("College details saved.")

with section_tab:
    st.subheader("Add a section")
    st.caption("Choose two languages and an approved four-subject combination. Set batches only for practical subjects.")
    with st.form("section_form", clear_on_submit=True):
        first, second, third = st.columns(3)
        with first:
            section_name = st.text_input("Section name", placeholder="e.g. 1st PUC Science B")
            year = st.selectbox("Year", ["1st PUC", "2nd PUC"])
            stream = st.selectbox("Stream", ["Arts", "Commerce", "Science"])
            strength = st.number_input("Student strength", min_value=1, value=40, step=1)
        with second:
            language_one = st.selectbox("First language", list(SUBJECTS), format_func=subject_label, index=0)
            language_two = st.selectbox("Second language", list(SUBJECTS), format_func=subject_label, index=1)
            combination = st.selectbox(
                "Optional-subject combination", COMBINATIONS[stream],
                format_func=lambda item: " + ".join(subject_label(code) for code in item.split()),
            )
        with third:
            st.markdown("**Practical batches**")
            practical_batches = {
                code: st.number_input(subject_label(code), min_value=0, value=0, step=1, key=f"batch_{code}")
                for code in sorted(PRACTICAL_SUBJECTS)
            }
        if st.form_submit_button("Add section", type="primary"):
            if not section_name.strip():
                st.error("Enter a section name.")
            elif language_one == language_two:
                st.error("Choose two different languages.")
            else:
                optionals = combination.split()
                batches = {code: int(count) for code, count in practical_batches.items() if code in optionals and count}
                config["sections"].append({
                    "name": section_name.strip(), "year": year, "stream": stream, "strength": int(strength),
                    "languages": [language_one, language_two], "optionals": optionals, "practical_batches": batches,
                })
                st.success(f"{section_name} added.")
                st.rerun()

    st.subheader("Current sections")
    if config["sections"]:
        section_rows = [{
            "Name": item["name"], "Year": item["year"], "Stream": item["stream"], "Strength": item["strength"],
            "Languages": ", ".join(subject_label(code) for code in item["languages"]),
            "Optionals": ", ".join(subject_label(code) for code in item["optionals"]),
            "Practical batches": ", ".join(f"{subject_label(code)}: {count}" for code, count in item["practical_batches"].items()) or "—",
        } for item in config["sections"]]
        st.dataframe(pd.DataFrame(section_rows), width="stretch", hide_index=True)
        remove_section = st.selectbox("Remove a section", range(len(config["sections"])), format_func=lambda i: config["sections"][i]["name"])
        if st.button("Remove selected section"):
            config["sections"].pop(remove_section)
            st.rerun()

with lecturer_tab:
    st.subheader("Add a lecturer")
    with st.form("lecturer_form", clear_on_submit=True):
        left, right = st.columns(2)
        with left:
            lecturer_name = st.text_input("Lecturer name")
            taught_subjects = st.multiselect("Subjects taught", list(SUBJECTS), format_func=subject_label)
            employment = st.selectbox("Nature of employment", ["PERMANENT", "DEPUTATION", "TEMPORARY", "GUEST"])
            workload = st.number_input("Weekly workload target (hours)", min_value=1, value=20, step=1)
        with right:
            available_days = st.multiselect("Available days", config["days"], default=config["days"])
            preferred_periods = st.multiselect("Preferred periods (optional)", range(1, 7), format_func=lambda p: f"Period {p}")
            st.caption("For deputation or guest lecturers, select only the days they work.")
        if st.form_submit_button("Add lecturer", type="primary"):
            if not lecturer_name.strip() or not taught_subjects:
                st.error("Enter the lecturer's name and at least one subject.")
            elif not available_days:
                st.error("Select at least one available day.")
            else:
                config["lecturers"].append({
                    "name": lecturer_name.strip(), "subjects": taught_subjects, "employment": employment,
                    "weekly_workload_target": int(workload), "available_days": available_days,
                    "preferred_periods": [period - 1 for period in preferred_periods],
                })
                st.success(f"{lecturer_name} added.")
                st.rerun()

    st.subheader("Current lecturers")
    if config["lecturers"]:
        lecturer_rows = [{
            "Name": item["name"], "Subjects": ", ".join(subject_label(code) for code in item["subjects"]),
            "Employment": item["employment"], "Target hours": item["weekly_workload_target"],
            "Available days": ", ".join(item.get("available_days", config["days"])),
        } for item in config["lecturers"]]
        st.dataframe(pd.DataFrame(lecturer_rows), width="stretch", hide_index=True)
        remove_lecturer = st.selectbox("Remove a lecturer", range(len(config["lecturers"])), format_func=lambda i: config["lecturers"][i]["name"])
        if st.button("Remove selected lecturer"):
            config["lecturers"].pop(remove_lecturer)
            st.rerun()

with generate_tab:
    st.subheader("Generate timetable")
    st.info(f"The timetable uses {len(config['sections'])} section(s) and {len(config['lecturers'])} lecturer(s).")
    if st.button("Generate timetable", type="primary", width="stretch"):
        try:
            validate(config)
            with st.spinner("Scheduling lessons and practical batches…"):
                st.session_state.rows = generate_schedule(config)
            st.success("Timetable generated.")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

    if "rows" in st.session_state:
        timetable = pd.DataFrame(st.session_state.rows)
        metrics = st.columns(3)
        metrics[0].metric("Sections", len(config["sections"]))
        metrics[1].metric("Scheduled hours", len(timetable))
        metrics[2].metric("Lecturers used", timetable["Lecturer"].nunique())
        st.dataframe(timetable, width="stretch", hide_index=True)
        csv_data = timetable.to_csv(index=False).encode("utf-8")
        xlsx_data = create_excel_report(config, st.session_state.rows)
        first, second = st.columns(2)
        first.download_button("Download timetable CSV", csv_data, "College_Timetable.csv", "text/csv", width="stretch")
        second.download_button(
            "Download complete Excel report", xlsx_data, "College_Timetable.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
        )
