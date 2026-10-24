"""Writes app/default-program.js: Tarik's current A/B/C program as the app's built-in default (schema v5).

Run once from the repo root with the private v4 data file (never commit that file):
    python tools/default_program.py <path to calisthenics-data.json (v4)> [--out app/default-program.js]

Sources, field by field:
  v4 file   plans["3"] (the day order), weeks[0].days[] (day ids and names, exercise ids, names, set counts),
            reps -> target ("6" reps, "40s" a timed hold), weight -> load ("BW" = bodyweight with 0 added,
            "BW + 5 kg" / "+5 kg" = bodyweight with 5 added, "110 kg" = 110), repMin, repMax, loadStep,
            incrementUnit "yok" (a one-off row: the stretch, the walk, the wrist warm-up) -> kind check.
  PAIRS     below, from D:/TarikOS/600-Life/Health/Antrenman.md -> "Guncel program - v2" (the v4 file has
            no pairs): adjacent exercises done alternately in one session share a `pair`.
  durations a check row's countdown, from the minutes in its name ("Esneme 4 dk" -> 240 s).
  defaults  loadStep 2.5 (Blueprint -> settings) where the v4 row has none; time and check rows have no
            rep range (repMin and repMax null).
  NOTES     below: form and health cues kept out of the names, in the exercise's `note` (2026-10-24: the repo is
            public and the names show on every stranger's screen).
No logs come over: old logs stay out (Blueprint -> What v1 is); the v4 file has no notes of its own.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "abc"
PROGRAM_NAME = "A/B/C"
DEFAULT_LOAD_STEP = 2.5

# Antrenman.md -> "Guncel program - v2" (2026-10-24): "<->" pairs per day, by the exercise names in the v4 file.
PAIRS = {
    "A Ağır": [("Weighted Pull-up", "Weighted Dip"), ("Leg Press", "Side Lateral Raise"),
               ("Machine Row", "Shoulder Press"), ("Seated Leg Curl", "Standing Calf Raise")],
    "B Hacim": [("Pull-up", "Dips"), ("Pike Push-up (dambıl/paralet üstünde, bilek düz)", "Seated Leg Curl"),
                ("Leg Extension", "Side Lateral Raise"), ("Incline Dumbbell Curl", "Overhead Cable Triceps Extension")],
    "C Bacak": [("Chin-up", "Incline Barbell Bench Press"), ("Leg Press (ayak yüksek)", "Side Lateral Raise"),
                ("Glute Kickback (makine/kablo)", "Standing Calf Raise"), ("Reverse Pec Deck Fly", "Hip Abduction"),
                ("Incline Dumbbell Curl", "Overhead Cable Triceps Extension")],
}


# English names for the app (Tarık 2026-10-24: the whole app in English); the v4 file and PAIRS keep the Turkish ones.
ENGLISH = {
    "A Ağır": "A Heavy",
    "B Hacim": "B Volume",
    "C Bacak": "C Legs",
    "Bilek ısınması 1 dk (daire + dört ayakta ağrısız sallanma)": "Wrist warm-up 1 min",
    "Captain's Chair Knee Raise (diz bükük)": "Captain's Chair Knee Raise",
    "Esneme 4 dk: sinir kayması 10/bacak + hamstring havlu 1 dk/bacak (diz arkası yanmadan, ayak serbest)": "Stretch 4 min: hamstring",
    "Eğimli Yürüyüş 22 dk (5,0 km/h · %6, her hafta +%2 → %12)": "Incline Walk 22 min (5.0 km/h · 6%, +2% a week → 12%)",
    "Glute Kickback (makine/kablo)": "Glute Kickback (machine/cable)",
    "Leg Press (ayak yüksek)": "Leg Press (feet high)",
    "Pike Push-up (dambıl/paralet üstünde, bilek düz)": "Pike Push-up",
}

# The cues the Turkish names carried, by the same names, written to `note` instead of the English name.
NOTES = {
    "Bilek ısınması 1 dk (daire + dört ayakta ağrısız sallanma)": "Circles + pain-free rocking on all fours",
    "Captain's Chair Knee Raise (diz bükük)": "Knees bent",
    "Esneme 4 dk: sinir kayması 10/bacak + hamstring havlu 1 dk/bacak (diz arkası yanmadan, ayak serbest)":
        "Nerve glide 10/leg + towel hamstring 1 min/leg; no burn behind the knee, foot free",
    "Pike Push-up (dambıl/paralet üstünde, bilek düz)": "On dumbbells or parallettes, wrists straight",
}


def load_of(weight):
    """'BW' -> (0, True); 'BW + 5 kg' or '+5 kg' -> (5, True); '110 kg' -> (110, False)."""
    w = str(weight or "").strip().replace(",", ".")
    m = re.fullmatch(r"(?i)(BW)?\s*(\+)?\s*(\d+(?:\.\d+)?)?\s*(kg)?", w)
    if not w or not m or (m.group(3) is None and not m.group(1)):
        raise ValueError(f"weight {weight!r} is not BW, BW + n kg or n kg")
    added = float(m.group(3)) if m.group(3) else 0.0
    bodyweight = bool(m.group(1) or m.group(2))
    return (int(added) if added.is_integer() else added), bodyweight


def number(v):
    f = float(v)
    return int(f) if f.is_integer() else f


def exercise(src):
    name = src["name"]
    reps = str(src["reps"]).strip()
    load, bodyweight = load_of(src.get("weight"))
    one_off = src.get("incrementUnit") == "yok"
    if one_off:
        kind, target = "check", 1
    elif re.fullmatch(r"\d+\s*s", reps):
        kind, target = "time", int(reps.rstrip("s").strip())
    elif re.fullmatch(r"\d+", reps):
        kind, target = "reps", int(reps)
    else:
        raise ValueError(f"{name}: reps {reps!r} is neither a number nor a time")
    ex = {"id": src["id"], "name": name, "kind": kind, "sets": int(src["sets"]), "target": target}
    if kind == "reps":
        if "repMin" not in src or "repMax" not in src:
            raise ValueError(f"{name}: a reps row without repMin/repMax")
        ex["repMin"], ex["repMax"] = int(src["repMin"]), int(src["repMax"])
        if not ex["repMin"] <= target <= ex["repMax"]:
            raise ValueError(f"{name}: target {target} outside {ex['repMin']}-{ex['repMax']}")
    else:
        ex["repMin"] = ex["repMax"] = None
    ex["load"] = 0 if kind == "check" else load
    ex["loadStep"] = number(src["loadStep"]) if "loadStep" in src else (0 if kind == "check" else DEFAULT_LOAD_STEP)
    if bodyweight and kind != "check":
        ex["bodyweight"] = True
    if kind == "check":
        m = re.search(r"(\d+)\s*dk\b", name)
        if m:
            ex["duration"] = int(m.group(1)) * 60
    return ex


def build(v4):
    if v4.get("_version") != 4:
        raise ValueError(f"expected a v4 file, got _version {v4.get('_version')}")
    order = v4["plans"]["3"]
    by_id = {d["id"]: d for d in v4["weeks"][0]["days"]}
    days = []
    for day_id in order:
        src = by_id[day_id]
        exercises = [exercise(e) for e in src["exercises"]]
        names = [e["name"] for e in exercises]
        for n, (a, b) in enumerate(PAIRS.get(src["name"], []), 1):
            if a not in names or b not in names:
                raise ValueError(f"{src['name']}: pair {a} <-> {b} not in the day")
            ia, ib = names.index(a), names.index(b)
            if ib != ia + 1:
                raise ValueError(f"{src['name']}: pair {a} <-> {b} is not adjacent")
            exercises[ia]["pair"] = exercises[ib]["pair"] = f"p{n}"
        if src["name"] not in PAIRS:
            raise ValueError(f"no pairs listed for day {src['name']}")
        days.append({"id": day_id, "name": src["name"], "exercises": exercises})
    for d in days:
        d["name"] = ENGLISH.get(d["name"], d["name"])
        for e in d["exercises"]:
            if e["name"] in NOTES:
                e["note"] = NOTES[e["name"]]
            e["name"] = ENGLISH.get(e["name"], e["name"])
    return {"id": PROGRAM_ID, "name": PROGRAM_NAME, "days": days}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("v4", help="the private v4 calisthenics-data.json")
    ap.add_argument("--out", default=str(ROOT / "app" / "default-program.js"))
    args = ap.parse_args()
    v4 = json.loads(Path(args.v4).read_text(encoding="utf-8"))
    program = build(v4)
    body = json.dumps(program, ensure_ascii=False, indent=2)
    text = ("/* Tarik's A/B/C program, the built-in default (schema v5 program). Generated by tools/default_program.py\n"
            "   from the v4 data file (days, exercises, sets, targets, ranges, loads, steps) and the pairs in\n"
            "   Antrenman.md -> v2. Do not edit by hand: run the tool. Week 1 is built from it on first open. */\n"
            f"self.CALI_DEFAULT_PROGRAM = {body};\n")
    Path(args.out).write_bytes(text.encode("utf-8"))
    for d in program["days"]:
        kinds = {}
        for e in d["exercises"]:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        pairs = len({e["pair"] for e in d["exercises"] if "pair" in e})
        print(f"{d['name']}: {len(d['exercises'])} exercises {kinds}, {pairs} pairs")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError) as e:
        print(f"default_program.py: {e}", file=sys.stderr)
        sys.exit(1)
