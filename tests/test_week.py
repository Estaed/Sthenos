"""Weeks (Task-04): the week menu, Finish week with its confirmation, building the next week from nextProgram with
Cali.progress, Undo until the next log, and past weeks read-only.

Run from the repo root: python tests/test_week.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py with Playwright's clock paused. Checks routes (Cali.current(), the address) and stored state
(localStorage 'cali.v5'), plus this feature's own menu and confirmation; never the day screen's own markup (Task-01).
Sets are logged through Cali.log, the one writer; a day is marked done the way the workout's Done stores it (its
finishedAt), through Cali.change. Data: Tarik's built-in program (app/default-program.js) with invented logs.
"""
import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PROGRAM = A.default_program()
DAYS = PROGRAM["days"]
A_ID, B_ID, C_ID = (d["id"] for d in DAYS)


def ex_id(day, name):
    return next(e["id"] for e in day["exercises"] if e["name"].startswith(name))


# Blueprint -> Data: week { n, program, startedAt, finishedAt?, days: { <dayId>: { startedAt?, finishedAt?, exercises } } }
WEEK_KEYS = {"n", "program", "startedAt", "finishedAt", "days"}
DAY_KEYS = {"startedAt", "finishedAt", "exercises"}


def off_blueprint(doc):
    """Fields of the stored document (the one sync pushes) that the Blueprint's week and day shapes do not have."""
    out = [f"week {w['n']}: {k}" for w in doc["weeks"] for k in sorted(set(w) - WEEK_KEYS)]
    return out + [f"week {w['n']} {d}: {k}" for w in doc["weeks"] for d, day in w["days"].items() for k in sorted(set(day) - DAY_KEYS)]


PULL, DIP, LP, CURL, CALF, PLANK, STRETCH = (ex_id(DAYS[0], n) for n in (
    "Weighted Pull-up", "Weighted Dip", "Leg Press", "Seated Leg Curl", "Standing Calf Raise", "Plank", "Mobility"))
B_PULL = ex_id(DAYS[1], "Dips")

LOG = """([dayId, rows]) => { for (const [exId, sets] of Object.entries(rows)) sets.forEach((r, i) => Cali.log(dayId, exId, i, r)); }"""
DONE = """(dayId) => Cali.change(d => { const day = d.weeks[d.weeks.length - 1].days[dayId];
    day.startedAt = day.startedAt || Cali.iso(); day.finishedAt = Cali.iso(); }, { why: 'dayDone' })"""


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "week")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate

        def stored():
            return A.stored(page)

        def week_ex(doc, n, day, ex):
            return doc["weeks"][n - 1]["days"][day]["exercises"][ex]

        def menu_items():
            return ev("() => [...document.querySelectorAll('.week-menu .week-item')].map(b => b.dataset.week ? 'week ' + b.dataset.week : b.dataset.weekAct)")

        def open_menu():
            A.touch_tap(page, '[data-screen="day"] [data-slot="dayheader"] .week-btn')
            page.wait_for_selector(".week-menu")

        def close_menu():
            """Taps the scrim beside the menu (the gap on its right), as a thumb would."""
            r = page.locator(".week-menu").bounding_box()
            page.touchscreen.tap(min(r["x"] + r["width"] + 24, 350), r["y"] + 12)
            page.wait_for_function("() => document.querySelector('.week-menu') === null")

        ev("() => { window.__events = []; Cali.on('weekFinished', w => __events.push(w)); }")

        # ── week 1, Monday: day A done (Tarik's numbers, screen 6), day B started (Pull-up 8, 8, 8, every set at target)
        #    but not done, day C not started ──
        ev(LOG, [A_ID, {PULL: [6, 6, 6], DIP: [8, 8, 7], LP: [10, 10, 10], CALF: [15, 15, 15], PLANK: [40, 40], STRETCH: [1]}])
        ev(DONE, A_ID)
        ev(LOG, [B_ID, {B_PULL: [8, 8, 8]}])
        ctx.clock.run_for(1000)

        # ── the week menu ──
        A.check("the week menu sits in the day screen's dayheader slot and names the week",
                ev("() => document.querySelector('[data-screen=\"day\"] [data-slot=\"dayheader\"] .week-btn').textContent.trim()") == "Week 1")
        open_menu()
        A.check("the menu lists week 1 (this week) and Finish week, no Undo yet", menu_items() == ["week 1", "finish"], menu_items())
        before = ev("() => localStorage.getItem('cali.v5')")
        # a set cell the menu does not cover: under the finger is the scrim, under the scrim that cell
        cell = ev("""() => { for (const el of document.querySelectorAll('[data-screen="day"] [data-set]')) {
            const r = el.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
            if (y > 0 && y < innerHeight && document.elementFromPoint(x, y).classList.contains('week-scrim')) return [x, y]; } return null; }""")
        A.check("a set cell lies under the scrim, outside the menu", cell is not None)
        page.touchscreen.tap(cell[0], cell[1])
        A.check("a tap outside the open menu closes it and logs nothing (the scrim takes it)",
                ev("() => document.querySelector('.week-menu') === null") and ev("() => localStorage.getItem('cali.v5')") == before)
        ctx.clock.run_for(1000)

        # ── Finish week asks for confirmation ──
        open_menu()
        A.touch_tap(page, '.week-menu [data-week-act="finish"]')
        page.wait_for_selector('[data-screen="finish-week"] [data-week-act="confirm"]')
        A.check("Finish week opens the confirmation route 'finish-week' { week: 1 }",
                ev("() => Cali.current()") == {"name": "finish-week", "args": {"week": 1}}, ev("() => Cali.current()"))
        A.check("the confirmation stores nothing by itself", ev("() => localStorage.getItem('cali.v5')") == before)
        text = ev("() => document.querySelector('[data-screen=\"finish-week\"]').innerText")
        A.check("the confirmation shows what moves up (Pull-up BW to +2.5 kg, Calf 77.5 to 80 kg) and the days not done",
                all(t in text for t in ("Weighted Pull-up", "BW to", "+2.5 kg", "77.5 to", "80 kg", "Not done", "Not started")), text[:400])
        A.touch_tap(page, '[data-screen="finish-week"] .week-dock [data-week-act="close"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        A.check("Cancel goes back to the day and finishes nothing",
                ev("() => localStorage.getItem('cali.v5')") == before and ev("() => __events") == [])
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 1 })")
        page.go_back()
        page.wait_for_function("() => Cali.current().name === 'day'")
        A.check("the phone's back gesture leaves the confirmation and finishes nothing",
                ev("() => localStorage.getItem('cali.v5')") == before and ev("() => __events") == [])

        # ── Finish: week 2 from nextProgram with Cali.progress ──
        depth = ev("() => (history.state && history.state.depth) || 0")
        ev("() => Cali.go('finish-week', { week: 1 })")
        page.wait_for_selector('[data-screen="finish-week"] [data-week-act="confirm"]')
        ev("() => { window.__why = []; Cali.on('change', c => __why.push(c.why)); }")
        # two taps that land together (a sweaty double tap): one week is built
        ev("() => { const b = document.querySelector('[data-week-act=\"confirm\"]'); b.click(); b.click(); }")
        page.wait_for_function("() => Cali.current().name === 'day' && Cali.current().args.week === 2")
        doc = stored()
        now_iso = ev("() => Cali.iso()")
        A.check("Finish week emits weekFinished { week: 1, next: 2 } once, after one change why 'weekFinished'",
                ev("() => __events") == [{"week": 1, "next": 2}] and ev("() => __why") == ["weekFinished"], (ev("() => __events"), ev("() => __why")))
        A.check("week 1 is stored finished and week 2 built from nextProgram, now, every set empty",
                len(doc["weeks"]) == 2 and doc["weeks"][0].get("finishedAt") == now_iso and doc["weeks"][1]["n"] == 2
                and doc["weeks"][1]["program"] == doc["nextProgram"] == doc["activeProgram"] == "abc"
                and doc["weeks"][1]["startedAt"] == now_iso
                and all(s is None for d in doc["weeks"][1]["days"].values() for e in d["exercises"].values() for s in e["sets"]),
                [w.get("finishedAt") for w in doc["weeks"]])
        A.check("while Finish can be undone, the stored document (pushed at once) holds only the Blueprint's week and "
                "day fields", off_blueprint(doc) == [], off_blueprint(doc))
        got = {k: (week_ex(doc, 2, d, e)["load"], week_ex(doc, 2, d, e)["target"]) for k, d, e in (
            ("pull", A_ID, PULL), ("dip", A_ID, DIP), ("lp", A_ID, LP), ("curl", A_ID, CURL), ("calf", A_ID, CALF),
            ("plank", A_ID, PLANK), ("stretch", A_ID, STRETCH), ("b-pull", B_ID, B_PULL))}
        want = {"pull": (2.5, 4), "dip": (0, 8), "lp": (110, 11), "curl": (35, 12), "calf": (80, 12), "plank": (0, 45),
                "stretch": (0, 1), "b-pull": (0, 10)}
        A.check("week 2 takes each load and target from Cali.progress: Pull-up BW +2.5 x 4, Dip stays (short), Leg Press 11, "
                "Leg Curl stays (not logged), Calf 80 kg x 12, Plank 45 s, stretch copied, day B not done unchanged "
                "(Dips 8, 8, 8 stays x 10: a day not done never moves up)", got == want, got)
        A.check("day C (not started) carries over the program's values",
                all((e["load"], e["target"]) == (x["load"], x["target"]) for x in DAYS[2]["exercises"]
                    for e in [week_ex(doc, 2, C_ID, x["id"])]))
        rules = ("name", "kind", "repMin", "repMax", "loadStep", "bodyweight", "pair", "note", "duration")
        A.check("week 2 copies the program's rules for every exercise",
                all({k: e.get(k) for k in rules} == {k: x.get(k) for k in rules}
                    for d in DAYS for x in d["exercises"] for e in [week_ex(doc, 2, d["id"], x["id"])]))
        A.check("after Finish the day shows week 2 in place of the confirmation (back does not return to it)",
                ev("() => [location.hash, (history.state && history.state.depth) || 0]") == ["#/day?week=2", depth],
                ev("() => [location.hash, (history.state && history.state.depth) || 0]"))
        A.check("the week label says Week 2 and a snackbar offers Undo",
                ev("() => document.querySelector('.week-btn').textContent.trim()") == "Week 2"
                and ev("() => document.querySelector('.week-snack [data-week-undo]') !== null"))

        # ── Undo until the next log ──
        A.touch_tap(page, ".week-snack [data-week-undo]")
        page.wait_for_function("() => Cali.week().n === 1")
        doc = stored()
        A.check("Undo drops week 2 and reopens week 1 with its logs",
                len(doc["weeks"]) == 1 and "finishedAt" not in doc["weeks"][0] and doc["activeProgram"] == "abc"
                and [s["r"] for s in week_ex(doc, 1, A_ID, PULL)["sets"]] == [6, 6, 6]
                and ev("() => Cali.current().args.week") == 1, (len(doc["weeks"]), ev("() => Cali.current()")))
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 1 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.current().name === 'day' && Cali.week().n === 2")
        A.check("the Undo snackbar is up after Finish", ev("() => document.querySelector('.week-snack') !== null"))
        ctx.clock.run_for(8000)
        A.check("the Undo snackbar leaves after 8 s", ev("() => document.querySelector('.week-snack') === null"))
        ev("() => Cali.go('finish-week', { week: 1 })")
        A.check("a confirmation for a week that is no longer current offers no Finish",
                ev("() => document.querySelector('[data-screen=\"finish-week\"] [data-week-act=\"confirm\"]') === null"))
        ev("() => Cali.back()")
        page.wait_for_function("() => Cali.current().name === 'day'")
        open_menu()
        A.check("the menu still offers Undo finish week 1 before any log", menu_items() == ["week 2", "week 1", "finish", "undo"], menu_items())
        close_menu()

        def reload():
            """The phone killed the app and it was opened again."""
            page.reload()
            page.wait_for_selector('[data-screen="day"] [data-slot="dayheader"] .week-btn')
            ctx.clock.run_for(1000)

        reload()
        open_menu()
        A.check("after a reload, still before any log, the menu offers Undo finish week 1",
                menu_items() == ["week 2", "week 1", "finish", "undo"], menu_items())
        close_menu()
        A.check("the Undo window is kept in no field outside the Blueprint's week and day shapes",
                off_blueprint(stored()) == [], off_blueprint(stored()))
        ctx.clock.run_for(1000)
        ev(f"() => {{ Cali.log({json.dumps(A_ID)}, {json.dumps(LP)}, 0, 11); Cali.log({json.dumps(A_ID)}, {json.dumps(LP)}, 0, null); }}")
        open_menu()
        A.check("after the next log the menu offers no Undo, even with that set cleared again",
                menu_items() == ["week 2", "week 1", "finish"], menu_items())
        close_menu()
        reload()
        open_menu()
        A.check("after that log and a reload the menu still offers no Undo (week 2 has no logged set, Undo stays over)",
                menu_items() == ["week 2", "week 1", "finish"], menu_items())
        close_menu()
        ctx.clock.run_for(1000)
        ev(LOG, [A_ID, {LP: [11, 11, 11]}])
        open_menu()
        A.check("with a set logged in week 2 the menu offers no Undo", menu_items() == ["week 2", "week 1", "finish"], menu_items())
        close_menu()
        ctx.clock.run_for(1000)

        # ── a program edit afterwards changes no week ──
        weeks_before = json.dumps(stored()["weeks"])
        ev(f"""() => Cali.change(d => {{ const e = d.programs[0].days[0].exercises.find(x => x.id === {json.dumps(LP)});
            Object.assign(e, {{ name: 'Renamed Press', target: 99, load: 300, repMax: 30 }}); }}, {{ why: 'program' }})""")
        A.check("editing the program afterwards changes no past or current week", json.dumps(stored()["weeks"]) == weeks_before)
        got = ev(f"() => {{ const e = Cali.weekExercise(2, {json.dumps(A_ID)}, {json.dumps(LP)}); return [e.name, e.repMax, e.target, e.load]; }}")
        A.check("week 2 still reads its own copy (Leg Press 8-12, 11 at 110 kg)", got == ["Leg Press", 12, 11, 110], got)

        # ── nextProgram: week 3 from another program ──
        ev(f"""() => Cali.change(d => {{
            const p = structuredClone(d.programs[0]); p.id = 'abc-next'; p.name = 'A/B/C next';
            const day = p.days[0];
            day.exercises = day.exercises.filter(e => e.id !== {json.dumps(DIP)});
            const lp = day.exercises.find(e => e.id === {json.dumps(LP)}); Object.assign(lp, {{ name: 'Leg Press', repMax: 15, target: 10, load: 110 }});
            const pl = day.exercises.find(e => e.id === {json.dumps(PLANK)}); Object.assign(pl, {{ kind: 'reps', repMin: 10, repMax: 20, target: 10 }});
            day.exercises.push({{ id: 'hlr', name: 'Hanging Leg Raise', kind: 'reps', sets: 3, target: 8, repMin: 8, repMax: 12, load: 0, loadStep: 2.5, bodyweight: true }});
            d.programs.push(p); d.nextProgram = 'abc-next'; }}, {{ why: 'program' }})""")
        ev(LOG, [A_ID, {PLANK: [45, 45]}])
        ev(DONE, A_ID)
        week2 = json.dumps(stored()["weeks"][1])
        ev("() => Cali.go('finish-week', { week: 2 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        text = ev("() => document.querySelector('[data-screen=\"finish-week\"]').innerText")
        A.check("the confirmation names the program next week is built from", "A/B/C next" in text, text[-200:])
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 3 && Cali.current().name === 'day'")
        ctx.clock.run_for(1000)
        A.touch_tap(page, ".week-snack [data-week-undo]")
        page.wait_for_function("() => Cali.week().n === 2")
        doc = stored()
        A.check("Undo of a Finish that switched programs reopens week 2 with its own program active again "
                "('abc'), and the program chosen for next week stays chosen ('abc-next')",
                len(doc["weeks"]) == 2 and "finishedAt" not in doc["weeks"][1]
                and (doc["weeks"][1]["program"], doc["activeProgram"], doc["nextProgram"]) == ("abc", "abc", "abc-next"),
                (len(doc["weeks"]), doc["activeProgram"], doc["nextProgram"]))
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 2 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 3 && Cali.current().name === 'day'")
        doc = stored()
        w3 = doc["weeks"][2]["days"][A_ID]["exercises"]
        A.check("week 3 is built from nextProgram, which becomes active",
                doc["weeks"][2]["program"] == "abc-next" and doc["activeProgram"] == "abc-next" and doc["nextProgram"] == "abc-next")
        A.check("week 3: Leg Press keeps progressing (11 x3 at 110 -> 12) under nextProgram's range 8-15",
                (w3[LP]["load"], w3[LP]["target"], w3[LP]["repMax"]) == (110, 12, 15), w3.get(LP))
        A.check("week 3: an exercise dropped from nextProgram is gone, a new one starts from the program's values",
                DIP not in w3 and (w3["hlr"]["load"], w3["hlr"]["target"], w3["hlr"]["sets"]) == (0, 8, [None] * 3), list(w3)[:4])
        A.check("week 3: an exercise whose kind changed starts from the program's values (Plank as reps, 10)",
                (w3[PLANK]["kind"], w3[PLANK]["target"]) == ("reps", 10), w3.get(PLANK))
        A.check("finishing week 2 left week 2 as it was, apart from its finishedAt",
                json.loads(week2) == {k: v for k, v in doc["weeks"][1].items() if k != "finishedAt"} and "finishedAt" in doc["weeks"][1])
        ctx.clock.run_for(1000)

        # ── past weeks read-only through the menu ──
        open_menu()
        A.touch_tap(page, '.week-menu [data-week="1"]')
        page.wait_for_function("() => Cali.current().args.week === 1")
        A.check("the menu opens a past week read-only: Cali.go('day', { week, dayId, readOnly: true })",
                ev("() => Cali.current()") == {"name": "day", "args": {"week": 1, "dayId": A_ID, "readOnly": True}}, ev("() => Cali.current()"))
        A.check("on a past week the label says so (Week 1, Past)",
                ev("() => [document.querySelector('.week-btn').textContent.trim(), document.querySelector('.week-past').hidden]") == ["Week 1", False])
        depth = ev("() => history.state.depth")
        open_menu()
        A.touch_tap(page, '.week-menu [data-week="3"]')
        page.wait_for_function("() => Cali.current().args.week === 3")
        A.check("from a past week the menu returns to this week, editable, in place of the past one",
                ev("() => [Cali.current(), history.state.depth]") == [{"name": "day", "args": {"week": 3, "dayId": A_ID}}, depth],
                ev("() => [Cali.current(), history.state.depth]"))
        A.check("this week shows no Past pill", ev("() => document.querySelector('.week-past').hidden") is True)
        ctx.clock.run_for(1000)

        # ── a day not done carries its own week's values: week 3's Weighted Pull-up stands at BW +2.5 x 4 (week 1's
        #    load up, carried), above the program's BW x 6; day A is logged in full at target but not Done ──
        pull3 = (w3[PULL]["load"], w3[PULL]["target"])
        ev(LOG, [A_ID, {PULL: [4, 4, 4]}])
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 3 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 4 && Cali.current().name === 'day'")
        pull4 = week_ex(stored(), 4, A_ID, PULL)
        A.check("Finish week carries a day not done over unchanged: Pull-up BW +2.5 x 4 in week 3, every set at target, "
                "day not Done -> BW +2.5 x 4 in week 4 (not x 5, not back to the program's BW x 6)",
                pull3 == (2.5, 4) and (pull4["load"], pull4["target"]) == (2.5, 4), (pull3, pull4["load"], pull4["target"]))

        # ── three short weeks at one load, through Finish week: a fresh document with weeks 1-3 of invented logs on
        #    Tarik's program, day A done each week. Leg Press 110 kg short three weeks -> 100 kg; Weighted Pull-up
        #    BW +5 short three weeks -> -10 % is 4.5, which rounds back to +5 at step 2.5, so it stays ──
        ev("""([program, dayId, rows]) => {
            const base = structuredClone(Cali.doc());
            const t0 = Cali.now() - 21 * 864e5, at = ms => new Date(ms).toISOString();
            base.programs = [program]; base.activeProgram = base.nextProgram = program.id;
            base.weeks = [0, 1, 2].map(i => {
              const w = Cali.weekFrom(program, i + 1), s = t0 + i * 7 * 864e5;
              w.startedAt = at(s); if (i < 2) w.finishedAt = at(s + 6 * 864e5);
              for (const [exId, load, target, sets] of rows) {
                const e = w.days[dayId].exercises[exId]; e.load = load; e.target = target;
                e.sets = sets.map((r, k) => ({ r, at: at(s + 36e5 + k * 18e4) }));
              }
              w.days[dayId].startedAt = at(s + 35e5); w.days[dayId].finishedAt = at(s + 72e5);
              return w; });
            Cali.replace(base); }""", [PROGRAM, A_ID, [[LP, 110, 10, [10, 9, 9]], [PULL, 5, 6, [6, 5, 5]]]])
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 3 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        text = ev("() => document.querySelector('[data-screen=\"finish-week\"]').innerText")
        A.check("the confirmation shows the real cut (Leg Press 110 to 100 kg) under a line that claims no fixed "
                "percentage, and lists Weighted Pull-up (BW +5, rounds back) as the same next week",
                all(t in text for t in ("Leg Press", "110 to", "100 kg", "Load down after three short weeks at this load",
                                        "a set was short: Weighted Pull-up")) and "%" not in text and "BW +5 to" not in text, text[:700])
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 4 && Cali.current().name === 'day'")
        w4 = stored()["weeks"][3]["days"][A_ID]["exercises"]
        A.check("Finish week: Leg Press 110 -> 100 kg x 10; Weighted Pull-up stays BW +5 x 6",
                [(w4[LP]["load"], w4[LP]["target"]), (w4[PULL]["load"], w4[PULL]["target"])] == [(100, 10), (5, 6)],
                [(w4[LP]["load"], w4[LP]["target"]), (w4[PULL]["load"], w4[PULL]["target"])])

        # ── Undo reaches back while no set is logged (week 4 finished with none); the first log ends every window ──
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 4 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 5 && Cali.current().name === 'day'")
        ctx.clock.run_for(1000)
        A.touch_tap(page, ".week-snack [data-week-undo]")
        page.wait_for_function("() => Cali.week().n === 4")
        ctx.clock.run_for(1000)
        open_menu()
        A.check("with no set logged since week 3's Finish, undoing week 4's Finish leaves Undo finish week 3 on offer",
                menu_items() == ["week 4", "week 3", "week 2", "week 1", "finish", "undo"], menu_items())
        close_menu()
        ctx.clock.run_for(1000)
        ev("() => Cali.go('finish-week', { week: 4 })")
        page.wait_for_selector('[data-week-act="confirm"]')
        A.touch_tap(page, '[data-week-act="confirm"]')
        page.wait_for_function("() => Cali.week().n === 5 && Cali.current().name === 'day'")
        ctx.clock.run_for(1000)
        ev(f"() => {{ Cali.log({json.dumps(A_ID)}, {json.dumps(LP)}, 0, 10); Cali.log({json.dumps(A_ID)}, {json.dumps(LP)}, 0, null); }}")
        open_menu()
        A.check("the first log after Finish ends the Undo window, with that set cleared again: the menu offers no Undo",
                menu_items() == ["week 5", "week 4", "week 3", "week 2", "week 1", "finish"], menu_items())
        close_menu()
        A.check("after that log the stored document still holds only the Blueprint's week and day fields",
                off_blueprint(stored()) == [], off_blueprint(stored()))

        keys = ev("() => Object.keys(localStorage)")
        A.check("only cali.* keys were written", all(k.startswith("cali.") for k in keys), keys)
        ctx.close()
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
