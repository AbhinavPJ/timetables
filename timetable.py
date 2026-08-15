"""Karnataka PUC timetable generator.

Run without arguments to generate the bundled example, or pass a JSON file with
your college data.  Use ``--write-example college.json`` to start from a fully
documented, editable input file.
"""

from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from ortools.sat.python import cp_model


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PRACTICAL_SUBJECTS = {"33", "34", "36", "40", "41", "67"}
SUBJECTS = {
    "01": "Kannada", "02": "English", "03": "Hindi", "04": "Tamil", "05": "Telugu",
    "06": "Malayalam", "07": "Marathi", "08": "Urdu", "09": "Sanskrit", "11": "Arabic",
    "12": "French", "16": "Optional Kannada", "21": "History", "22": "Economics",
    "23": "Logic", "24": "Geography", "25": "Carnatic Music", "26": "Hindustani Music",
    "27": "Business Studies", "28": "Sociology", "29": "Political Science", "30": "Accountancy",
    "31": "Statistics", "32": "Psychology", "33": "Physics", "34": "Chemistry",
    "35": "Mathematics", "36": "Biology", "37": "Geology", "40": "Electronics",
    "41": "Computer Science", "52": "Education", "59": "Electronics & Hardware",
    "60": "Apparels and Made Up/Home Furnishing", "61": "IT", "62": "Retail",
    "63": "Automobile", "64": "Health Care", "65": "Beauty and Wellness",
    "67": "Home Science", "75": "Basic Maths",
}
COMBINATIONS = {
    "Arts": ["21 22 28 29", "21 22 24 29", "21 22 23 29", "16 21 22 29", "16 21 22 24",
             "16 21 22 28", "21 22 29 32", "16 21 22 52", "16 21 29 52", "16 21 24 52",
             "16 21 28 52", "21 22 28 32", "21 22 28 52", "21 28 29 52", "21 24 28 52",
             "21 22 23 28", "16 21 22 25", "16 21 22 26", "16 21 28 25", "16 21 28 32",
             "21 24 29 52", "22 28 29 52", "22 24 29 52", "22 28 29 32", "22 23 28 32",
             "21 22 24 28", "21 22 25 28", "21 22 26 28", "21 22 26 29", "21 22 25 29",
             "21 22 29 75", "21 22 28 75", "21 22 24 75", "22 29 32 67", "21 28 29 16",
             "22 28 32 67"],
    "Commerce": ["21 22 27 30", "22 24 27 30", "22 27 30 41", "22 27 30 31", "27 30 31 75",
                 "27 30 31 41", "22 27 29 30", "22 27 30 75", "22 27 28 30"],
    "Science": ["33 34 35 36", "33 34 35 41", "33 34 35 40", "31 33 34 35", "33 34 36 67", "33 34 35 37"],
}


def example_config() -> dict[str, Any]:
    """A valid 1st/2nd PUC example; duplicate/edit sections and lecturers as needed."""
    subjects = ["01", "02", "21", "22", "28", "29", "27", "30", "33", "34", "35", "36"]
    lecturers = []
    for code in subjects:
        lecturers.append({"name": f"{SUBJECTS[code]} Lecturer", "subjects": [code],
                          "employment": "PERMANENT", "weekly_workload_target": 20})
    # Six sections need more than one language teacher to retain the mandatory
    # gap after two consecutive classes.
    lecturers.extend([
        {"name": "Kannada Lecturer 2", "subjects": ["01"], "employment": "PERMANENT", "weekly_workload_target": 20},
        {"name": "English Lecturer 2", "subjects": ["02"], "employment": "PERMANENT", "weekly_workload_target": 20},
    ])
    return {
        "college": {"name": "Example Pre-University College", "code": "PUC-0001", "place": "Bengaluru",
                    "taluk": "Bengaluru North", "district": "Bengaluru Urban", "udise_code": "00000000000",
                    "principal_name": "Principal Name", "academic_year": "2026-27", "management": "GOVERNMENT",
                    "college_timings": "09:00 AM - 04:00 PM", "lunch_break": "12:00 PM - 01:00 PM"},
        "days": DAYS,
        "periods": ["09:00-10:00", "10:00-11:00", "11:00-12:00", "01:00-02:00", "02:00-03:00", "03:00-04:00"],
        "sections": [
            {"name": "1st PUC Arts A", "year": "1st PUC", "stream": "Arts", "strength": 60,
             "languages": ["01", "02"], "optionals": ["21", "22", "28", "29"], "practical_batches": {}},
            {"name": "1st PUC Commerce A", "year": "1st PUC", "stream": "Commerce", "strength": 60,
             "languages": ["01", "02"], "optionals": ["21", "22", "27", "30"], "practical_batches": {}},
            {"name": "1st PUC Science A", "year": "1st PUC", "stream": "Science", "strength": 48,
             "languages": ["01", "02"], "optionals": ["33", "34", "35", "36"],
             "practical_batches": {"33": 1, "34": 1, "36": 1}},
            {"name": "2nd PUC Arts A", "year": "2nd PUC", "stream": "Arts", "strength": 58,
             "languages": ["01", "02"], "optionals": ["21", "22", "28", "29"], "practical_batches": {}},
            {"name": "2nd PUC Commerce A", "year": "2nd PUC", "stream": "Commerce", "strength": 55,
             "languages": ["01", "02"], "optionals": ["21", "22", "27", "30"], "practical_batches": {}},
            {"name": "2nd PUC Science A", "year": "2nd PUC", "stream": "Science", "strength": 45,
             "languages": ["01", "02"], "optionals": ["33", "34", "35", "36"],
             "practical_batches": {"33": 1, "34": 1, "36": 1}},
        ],
        "lecturers": lecturers,
    }


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return example_config()
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate(config: dict[str, Any]) -> None:
    required = {"college", "sections", "lecturers", "days", "periods"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Configuration is missing: {', '.join(sorted(missing))}")
    if len(config["periods"]) != 6:
        raise ValueError("Exactly six one-hour teaching periods are required per day.")
    if not config["sections"] or not config["lecturers"]:
        raise ValueError("Add at least one section and one lecturer.")
    for section in config["sections"]:
        codes = section.get("languages", []) + section.get("optionals", [])
        if len(section.get("languages", [])) != 2 or len(section.get("optionals", [])) != 4:
            raise ValueError(f"{section.get('name', 'A section')} must have two languages and four optionals.")
        unknown = set(codes) - SUBJECTS.keys()
        if unknown:
            raise ValueError(f"Unknown subject codes in {section['name']}: {sorted(unknown)}")
        if section["stream"] in COMBINATIONS and " ".join(section["optionals"]) not in COMBINATIONS[section["stream"]]:
            raise ValueError(f"{section['name']} has an unapproved {section['stream']} optional combination.")


def build_events(config: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for si, section in enumerate(config["sections"]):
        for code in section["languages"] + section["optionals"]:
            theory_count = 4 if code in PRACTICAL_SUBJECTS else 5
            for occurrence in range(theory_count):
                events.append({"section": si, "subject": code, "kind": "Theory", "duration": 1,
                               "label": f"{code}-T{occurrence + 1}"})
        for code, batches in section.get("practical_batches", {}).items():
            if code not in PRACTICAL_SUBJECTS:
                raise ValueError(f"{section['name']}: {code} is not a practical subject.")
            for batch in range(int(batches)):
                events.append({"section": si, "subject": code, "kind": "Practical", "duration": 2,
                               "label": f"{code}-Lab batch {batch + 1}"})
    return events


def generate_schedule(config: dict[str, Any]) -> list[dict[str, Any]]:
    days, periods = config["days"], config["periods"]
    n_days, n_periods = len(days), len(periods)
    events = build_events(config)
    lecturers = config["lecturers"]
    qualified = {e: [li for li, lecturer in enumerate(lecturers) if events[e]["subject"] in lecturer["subjects"]]
                 for e in range(len(events))}
    unstaffed = [events[e]["subject"] for e, choices in qualified.items() if not choices]
    if unstaffed:
        raise ValueError(f"No lecturer is assigned to subject(s): {', '.join(sorted(set(unstaffed)))})")

    model = cp_model.CpModel()
    assignments: dict[tuple[int, int, int, int], cp_model.IntVar] = {}
    for e, event in enumerate(events):
        for li in qualified[e]:
            available_days = lecturers[li].get("available_days", days)
            for d, day in enumerate(days):
                if day not in available_days:
                    continue
                for p in range(n_periods - event["duration"] + 1):
                    assignments[e, li, d, p] = model.NewBoolVar(f"e{e}_l{li}_d{d}_p{p}")
        model.AddExactlyOne(assignments[key] for key in assignments if key[0] == e)

    # A section cannot have theory while it has a practical, or two lessons at once.
    for si in range(len(config["sections"])):
        for d in range(n_days):
            for p in range(n_periods):
                occupied = [var for (e, _li, dd, start), var in assignments.items()
                            if events[e]["section"] == si and dd == d and start <= p < start + events[e]["duration"]]
                model.AddAtMostOne(occupied)

    # A lecturer cannot be double-booked; two consecutive lessons require a subsequent gap.
    for li in range(len(lecturers)):
        for d in range(n_days):
            teaches = []
            for p in range(n_periods):
                occupied = [var for (e, lecturer, dd, start), var in assignments.items()
                            if lecturer == li and dd == d and start <= p < start + events[e]["duration"]]
                model.AddAtMostOne(occupied)
                teaches.append(occupied)
            for p in range(n_periods - 2):
                model.Add(sum(teaches[p]) + sum(teaches[p + 1]) + sum(teaches[p + 2]) <= 2)

    # Normal theory does not repeat for the same section in a day; guest/deputation may repeat but not consecutively.
    for e, event in enumerate(events):
        if event["kind"] != "Theory":
            continue
        for d in range(n_days):
            same = [var for (other, _li, dd, _p), var in assignments.items()
                    if other != e and dd == d and events[other]["section"] == event["section"]
                    and events[other]["subject"] == event["subject"] and events[other]["kind"] == "Theory"]
            own = [var for (other, _li, dd, _p), var in assignments.items() if other == e and dd == d]
            model.Add(sum(own) + sum(same) <= 1)

    # Preference data is retained in the configuration for reporting and future
    # refinements.  We deliberately avoid a global optimization objective here:
    # the first feasible schedule gives the dashboard a predictable response time.
    solver = cp_model.CpSolver()
    # A dashboard must respond promptly.  The first feasible solution already
    # satisfies every hard timetable rule; preferences are an optional tie-break.
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.stop_after_first_solution = True
    # OR-Tools is more reliable in Streamlit's threaded runtime with a single
    # search worker; parallel workers can leave the web request waiting.
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("No feasible timetable. Add lecturers, relax availability, or reduce practical batches.")

    rows = []
    for (e, li, d, p), var in assignments.items():
        if solver.Value(var):
            event, section = events[e], config["sections"][events[e]["section"]]
            for offset in range(event["duration"]):
                rows.append({"Year": section["year"], "Stream": section["stream"], "Section": section["name"],
                             "Day": days[d], "Period": p + offset + 1, "Time": periods[p + offset],
                             "Subject Code": event["subject"], "Subject": SUBJECTS[event["subject"]],
                             "Activity": event["kind"], "Batch": event["label"] if event["kind"] == "Practical" else "",
                             "Lecturer": lecturers[li]["name"]})
    return sorted(rows, key=lambda r: (r["Section"], days.index(r["Day"]), r["Period"]))


def write_pdf(path: Path, lines: list[str]) -> None:
    """Small dependency-free PDF writer for the required printable report."""
    pages = [lines[i:i + 52] for i in range(0, len(lines), 52)] or [[""]]
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", ""]
    page_ids, content_ids = [], []
    for _ in pages:
        page_ids.append(len(objects) + 1); objects.append("")
        content_ids.append(len(objects) + 1); objects.append("")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{x} 0 R' for x in page_ids)}] /Count {len(pages)} >>"
    for page, page_id, content_id in zip(pages, page_ids, content_ids):
        text = "BT /F1 9 Tf 40 800 Td 12 TL " + " ".join(
            f"({line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')}) Tj T*" for line in page
        ) + " ET"
        objects[page_id - 1] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {len(objects)+1} 0 R >> >> /Contents {content_id} 0 R >>"
        objects[content_id - 1] = f"<< /Length {len(text.encode())} >>\nstream\n{text}\nendstream"
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    result, offsets = "%PDF-1.4\n", [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result.encode())); result += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = len(result.encode())
    result += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets[1:])
    result += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.write_bytes(result.encode("latin-1", "replace"))


def create_excel_report(config: dict[str, Any], rows: list[dict[str, Any]]) -> bytes:
    """Return the complete, multi-sheet Excel report as download-ready bytes."""
    college, df = config["college"], pd.DataFrame(rows)
    dashboard = pd.DataFrame(list(college.items()), columns=["Field", "Value"])
    sections = pd.DataFrame(config["sections"])
    lecturers = pd.DataFrame(config["lecturers"])
    analysis = df.groupby(["Lecturer", "Activity"]).size().unstack(fill_value=0).reset_index()
    analysis["Total Scheduled Hours"] = analysis.drop(columns="Lecturer").sum(axis=1)
    lecturer_schedule = df.sort_values(["Lecturer", "Day", "Period"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dashboard.to_excel(writer, sheet_name="Dashboard", index=False)
        sections.to_excel(writer, sheet_name="Sections", index=False)
        lecturers.to_excel(writer, sheet_name="Lecturers", index=False)
        df.to_excel(writer, sheet_name="Comprehensive", index=False)
        lecturer_schedule.to_excel(writer, sheet_name="Lecturer Timetable", index=False)
        analysis.to_excel(writer, sheet_name="Workload Analysis", index=False)
        for section, group in df.groupby("Section"):
            grid = group.pivot(index="Day", columns="Period", values="Subject").reindex(config["days"])
            grid.to_excel(writer, sheet_name=section[:31])
    return output.getvalue()


def write_reports(config: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    excel_path = output_dir / "College_Timetable.xlsx"
    excel_path.write_bytes(create_excel_report(config, rows))
    college, df = config["college"], pd.DataFrame(rows)
    lines = [f"{college['name']} ({college['code']})", f"Academic year: {college['academic_year']}",
             "College-wise Comprehensive Timetable", ""]
    for section, group in df.groupby("Section", sort=False):
        lines.extend([section, "Day | Period | Subject | Activity | Lecturer"])
        lines.extend(f"{r.Day} | {r.Period} | {r.Subject} | {r.Activity} | {r.Lecturer}" for r in group.itertuples())
        lines.append("")
    lines.extend(["Principal Signature: ____________________", "DDPUE Approval: ____________________"])
    pdf_path = output_dir / "College_Timetable.pdf"
    write_pdf(pdf_path, lines)
    return excel_path, pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Karnataka PUC Excel and PDF timetables.")
    parser.add_argument("config", nargs="?", type=Path, help="Path to college JSON configuration")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--write-example", type=Path, metavar="FILE", help="Write an editable example JSON and exit")
    args = parser.parse_args()
    if args.write_example:
        args.write_example.write_text(json.dumps(example_config(), indent=2), encoding="utf-8")
        print(f"Example configuration written to {args.write_example}")
        return
    config = load_config(args.config)
    validate(config)
    rows = generate_schedule(config)
    excel, pdf = write_reports(config, rows, args.output_dir)
    print(f"Generated {excel} and {pdf}")


if __name__ == "__main__":
    main()
