"""Programs (app/program.js, Task-05): Settings -> Programs, the program editor, import, use now or from next week.

Run from the repo root: python tests/test_program.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py (360 x 740, touch, Playwright's clock paused). Every step goes through the visible controls:
a touch tap on a control scrolled to the middle of the screen, as a thumb would, after checking that the tap lands on
it (not on the docked bar or another row), and typing into the field that tap focused; never Cali.change. The stored
document is read back after each step. Prints the tap count of the path "duplicate the built-in program, add day D,
add one exercise and name it, use the program". Data: the built-in program and programs written here; nothing
personal.
"""
import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

FIXTURE = (A.ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8")
TAPS = [0]
MISSED = []      # taps that would have landed on something else


def tap(page, sel, nth=0):
    got = page.evaluate("""([s, n]) => { const el = document.querySelectorAll(s)[n]; if (!el) return null;
        el.scrollIntoView({ block: 'center' }); const r = el.getBoundingClientRect();
        const x = r.x + r.width / 2, y = r.y + r.height / 2, hit = document.elementFromPoint(x, y);
        return [x, y, Boolean(hit && (hit === el || el.contains(hit)))]; }""", [sel, nth])
    if got is None:
        raise AssertionError(f"nothing to tap at {sel}")
    x, y, lands = got
    if not lands:
        MISSED.append(sel)
    page.touchscreen.tap(x, y)
    TAPS[0] += 1


def type_into(page, sel, text):
    tap(page, sel)
    page.keyboard.press("Control+A")
    if text:
        page.keyboard.type(text)
    else:
        page.keyboard.press("Delete")
    page.keyboard.press("Enter")


def raw(page):
    return page.evaluate("() => localStorage.getItem('cali.v5')")


def program(doc, pid):
    return next((p for p in doc["programs"] if p["id"] == pid), None)


def day_of(doc, pid, day_id):
    return next(d for d in program(doc, pid)["days"] if d["id"] == day_id)


def ex_of(doc, pid, day_id, ex_id):
    return next((e for e in day_of(doc, pid, day_id)["exercises"] if e["id"] == ex_id), None)


def ids_of(doc):
    out = set()
    for p in doc["programs"]:
        out.add(p["id"])
        for d in p["days"]:
            out.add(d["id"])
            out.update(e["id"] for e in d["exercises"])
    return out


def msg(page):
    loc = page.locator('[data-screen] [data-msg]:not([hidden])')
    return loc.inner_text() if loc.count() else ""


DAY = lambda day_id, inner="": f'.program-day[data-day="{day_id}"] {inner}'.strip()
EX = lambda ex_id, inner="": f'.program-exbox[data-ex="{ex_id}"] {inner}'.strip()
ROW = lambda ex_id: f'.program-exbox[data-ex="{ex_id}"] > [data-act="ex"]'
HEAD = lambda day_id: f'.program-day[data-day="{day_id}"] > [data-act="day"]'


def go_programs(page):
    """From the day screen: the gear, then the Programs row."""
    tap(page, '[data-screen="day"] .settings-open')
    page.wait_for_selector('[data-screen="settings"] .settings-body')
    tap(page, '[data-screen="settings"] [data-act="programs"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')


def open_program(page, pid):
    tap(page, f'[data-screen="programs"] [data-act="open"][data-id="{pid}"]')
    page.wait_for_selector(f'[data-screen="program"] [data-f="pname"]')


def back_to_day(page):
    for screen in ("program", "programs", "settings"):
        if page.evaluate("() => Cali.current().name") == screen:
            tap(page, f'[data-screen="{screen}"] [data-act="back"]')
            page.wait_for_function(f"() => Cali.current().name !== '{screen}'")
    page.wait_for_selector('[data-screen="day"] [data-set]')


def answer(page, yes):
    page.wait_for_selector("dialog.program-dialog[open]")
    text = page.locator("dialog.program-dialog").inner_text()
    tap(page, f'dialog.program-dialog [data-answer="{"yes" if yes else "no"}"]')
    page.wait_for_function("() => !document.querySelector('dialog.program-dialog')")
    return text


TARGETS = """() => [...document.querySelectorAll('#app [data-screen] button, #app [data-screen] input:not([type="file"]), #app [data-screen] textarea')]
    .filter(el => el.getClientRects().length).map(el => {
      const r = el.getBoundingClientRect(), a = getComputedStyle(el, '::after');
      let w = r.width, h = r.height;
      if (a.content && a.content !== 'none' && a.position === 'absolute') {
        h += -(parseFloat(a.top) || 0) - (parseFloat(a.bottom) || 0); w += -(parseFloat(a.left) || 0) - (parseFloat(a.right) || 0); }
      return [el.dataset.act || el.dataset.f || el.dataset.v || el.className, Math.round(w), Math.round(h)]; })
    .filter(([, w, h]) => w < 44 || h < 44)"""
CUT = """() => [...document.querySelectorAll('#app [data-screen] .settings-t, #app [data-screen] .settings-t > *')]
    .filter(el => el.getClientRects().length && el.scrollWidth > el.clientWidth + 1).map(el => el.textContent)"""
WIDE = "() => document.scrollingElement.scrollWidth <= innerWidth"


def layout(page, where):
    small, cut, wide = page.evaluate(TARGETS), page.evaluate(CUT), page.evaluate(WIDE)
    A.check(f"{where} at 360 px: no sideways scroll, every control a 44 px target, no name cut",
            wide and not small and not cut, (wide, small[:5], cut[:5]))


# ── the path Tarık walks, then every editor control ───────────────────
def scenario_main(browser, url, errors):
    ctx, page = A.phone(browser, errors, "program", color_scheme="dark", reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate
    first = A.stored(page)
    builtin = first["programs"][0]
    week0 = first["weeks"][0]
    old_ids = ids_of(first)

    # ── duplicate the built-in program, add day D, add one exercise and name it, use the program ──
    TAPS[0] = 0
    tap(page, '[data-screen="day"] .settings-open')
    page.wait_for_selector('[data-screen="settings"] .settings-body')
    row = page.locator('[data-screen="settings"] [data-act="programs"]').inner_text()
    tap(page, '[data-screen="settings"] [data-act="programs"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    listed = page.locator('[data-screen="programs"]').inner_text()
    A.check("Settings has a Programs row naming this week's program; it opens the list: A/B/C runs this and next week",
            "This week: A/B/C" in row and ev("() => Cali.current().name") == "programs"
            and "A/B/C" in listed and "This and next week" in listed, (row, listed))
    open_program(page, builtin["id"])
    state = page.locator('[data-v="state"]').inner_text()
    tap(page, '[data-act="dup"]')
    page.wait_for_function(f"() => Cali.current().name === 'program' && Cali.current().args.id !== {json.dumps(builtin['id'])}")
    cid = ev("() => Cali.current().args.id")
    dup_msg = msg(page)
    tap(page, '[data-act="addday"]')
    day_d = program(A.stored(page), cid)["days"][-1]
    tap(page, DAY(day_d["id"], '[data-act="addex"]'))
    page.keyboard.type("Hip Thrust")
    tap(page, '[data-act="use"]')
    taps = TAPS[0]
    print(f"TAP COUNT duplicate -> use: {taps} taps from the day screen (gear, Programs, A/B/C, Duplicate, Add day, "
          "Add exercise, Use this program) plus typing the name", flush=True)
    A.check("the path from the day screen to the 4-day copy in use takes 7 taps and the name typed", taps == 7, taps)

    d = A.stored(page)
    copy = program(d, cid)
    D = day_d["id"]
    X = copy["days"][-1]["exercises"][0]["id"]
    A.check("the editor says the built-in program runs week 1 and edits show at once", "Week 1 runs it" in state, state)
    A.check("Duplicate adds \"A/B/C copy\" under a new id, keeps every day and exercise id and field, and opens the copy",
            len(d["programs"]) == 2 and cid != builtin["id"] and ":" not in cid and cid not in old_ids
            and copy["name"] == "A/B/C copy" and copy["days"][:3] == builtin["days"] and program(d, builtin["id"]) == builtin
            and "This is the copy" in dup_msg, (cid, copy["name"], dup_msg))
    new_ex = copy["days"][-1]["exercises"]
    A.check("Add day adds day D (the next letter) with an id unused in every program, never with ':'",
            [x["name"] for x in copy["days"]] == ["A", "B", "C", "D"] and D not in old_ids and ":" not in D, [x["name"] for x in copy["days"]])
    A.check("a new exercise is usable with only its name typed: reps, 3 sets, 8-12, target 8, load 0, the settings' load step, "
            "and the muscles its name guesses",
            new_ex == [{"id": X, "name": "Hip Thrust", "kind": "reps", "sets": 3, "target": 8, "repMin": 8, "repMax": 12, "load": 0,
                        "loadStep": 2.5, "muscles": {"gluteal": 1, "hamstring": 0.5}}] and X not in old_ids and ":" not in X and X != D, new_ex)
    w = d["weeks"]
    A.check("Use on a week with no set: week 1 is rebuilt from the copy (n and startedAt kept), activeProgram and nextProgram follow",
            len(w) == 1 and w[0]["n"] == 1 and w[0]["startedAt"] == week0["startedAt"] and w[0]["program"] == cid
            and d["activeProgram"] == d["nextProgram"] == cid and w[0]["days"][D]["exercises"][X]["sets"] == [None] * 3
            and {k: w[0]["days"][k] for k in week0["days"]} == week0["days"], (w[0]["program"], d["activeProgram"], d["nextProgram"]))
    A.check("the screen says week 1 now runs the copy, and Use is gone while it runs this week and next",
            "Week 1 now runs A/B/C copy" in msg(page) and page.locator('[data-act="use"]').is_hidden(), msg(page))
    back_to_day(page)
    tabs = ev("() => [...document.querySelectorAll('[data-screen=\"day\"] .workout-days button')].map(b => b.textContent.trim())")
    tap(page, f'[data-screen="day"] [data-day="{D}"]')
    page.wait_for_selector(f'[data-screen="day"] [data-set="{D}:{X}:0"]')
    A.check("the day screen shows days A B C D at once, and day D holds Hip Thrust", tabs == ["A", "B", "C", "D"], tabs)

    # ── rename the program and the days ──
    go_programs(page)
    open_program(page, cid)
    type_into(page, '[data-f="pname"]', "4-day split")
    A_ = copy["days"][0]["id"]
    tap(page, HEAD(A_))
    type_into(page, DAY(A_, '[data-f="dname"]'), "A Heavy")
    tap(page, DAY(A_, '[data-act="dayclose"]'))
    tap(page, HEAD(D))
    type_into(page, DAY(D, '[data-f="dname"]'), "D Pump")
    tap(page, DAY(D, '[data-act="dayclose"]'))
    d = A.stored(page)
    A.check("rename: the program and days A and D take the typed names (in the program and on the screen)",
            program(d, cid)["name"] == "4-day split" and [x["name"] for x in program(d, cid)["days"]] == ["A Heavy", "B", "C", "D Pump"]
            and page.locator(HEAD(D)).inner_text().startswith("D Pump"), [x["name"] for x in program(d, cid)["days"]])
    before = raw(page)
    tap(page, HEAD(D))
    type_into(page, DAY(D, '[data-f="dname"]'), "")
    A.check("an empty name is not saved: one line says so and the document is unchanged",
            raw(page) == before and "a name is needed" in msg(page)
            and page.locator(DAY(D, '[data-f="dname"]')).input_value() == "D Pump", msg(page))
    tap(page, DAY(D, '[data-act="dayclose"]'))

    # ── more exercises in day D ──
    names = {"Y": "Cable Pull-through", "Z": "Back Extension", "W": "Calf Raise"}
    E = {"X": X}
    for key, name in names.items():
        tap(page, DAY(D, '[data-act="addex"]'))
        page.keyboard.type(name)
        page.keyboard.press("Enter")
        E[key] = day_of(A.stored(page), cid, D)["exercises"][-1]["id"]
    order = lambda: [e["id"] for e in day_of(A.stored(page), cid, D)["exercises"]]
    pairs = lambda: {k: (ex_of(A.stored(page), cid, D, v) or {}).get("pair") for k, v in E.items()}
    A.check("Add exercise adds each named one at the end of its day, each with a fresh id",
            order() == [E["X"], E["Y"], E["Z"], E["W"]] and len(set(E.values()) | old_ids) == len(old_ids) + 4, order())

    # ── pairs ──
    tap(page, ROW(E["X"]))
    tap(page, EX(E["X"], '[data-act="pair"]'))
    p1 = pairs()
    tap(page, ROW(E["Z"]))
    tap(page, EX(E["Z"], '[data-act="pair"]'))
    p2 = pairs()
    A.check("pairing X with the next gives X and Y one pair value; pairing Z with W gives them another, unused elsewhere in the day",
            p1["X"] and p1["X"] == p1["Y"] and p1["Z"] is None and p2["Z"] and p2["Z"] == p2["W"] and p2["Z"] != p2["X"]
            and "paired with next" in page.locator(ROW(E["X"])).inner_text(), (p1, p2))
    tap(page, ROW(E["X"]))
    tap(page, EX(E["X"], '[data-act="pair"]'))
    p3 = pairs()
    A.check("unpairing X clears the pair on both X and Y; Z and W stay paired",
            p3["X"] is None and p3["Y"] is None and p3["Z"] == p3["W"] == p2["Z"], p3)
    tap(page, EX(E["X"], '[data-act="pair"]'))
    tap(page, ROW(E["Y"]))
    tap(page, EX(E["Y"], '[data-act="exdown"]'))
    p4, o4 = pairs(), order()
    A.check("moving Y away (down past the Z-W pair, which it jumps whole) clears the pair on both X and Y",
            o4 == [E["X"], E["Z"], E["W"], E["Y"]] and p4["X"] is None and p4["Y"] is None and p4["Z"] == p4["W"] and p4["Z"], (o4, p4))
    tap(page, EX(E["Y"], '[data-act="exup"]'))
    A.check("moving Y up jumps the Z-W pair whole again", order() == [E["X"], E["Y"], E["Z"], E["W"]] and pairs()["Z"] == pairs()["W"], order())
    tap(page, ROW(E["X"]))
    tap(page, EX(E["X"], '[data-act="exdown"]'))
    o5 = order()
    tap(page, EX(E["X"], '[data-act="exup"]'))
    A.check("reorder: X down swaps it with Y, X up puts it back", o5 == [E["Y"], E["X"], E["Z"], E["W"]]
            and order() == [E["X"], E["Y"], E["Z"], E["W"]], (o5, order()))

    # ── remove an exercise, reorder and remove a day (each removal asks first) ──
    tap(page, ROW(E["W"]))
    tap(page, EX(E["W"], '[data-act="exrm"]'))
    asked = answer(page, False)
    kept = order()
    tap(page, EX(E["W"], '[data-act="exrm"]'))
    answer(page, True)
    A.check("Remove asks first (Cancel keeps it); Remove takes W out, and Z, left alone in its pair, loses it",
            "Remove Calf Raise?" in asked and kept == [E["X"], E["Y"], E["Z"], E["W"]] and order() == [E["X"], E["Y"], E["Z"]]
            and pairs()["Z"] is None, (asked, order(), pairs()))
    days = lambda: [x["id"] for x in program(A.stored(page), cid)["days"]]
    B_, C_ = copy["days"][1]["id"], copy["days"][2]["id"]
    tap(page, HEAD(D))
    tap(page, DAY(D, '[data-act="dayup"]'))
    up = days()
    tap(page, DAY(D, '[data-act="daydown"]'))
    A.check("reorder a day: D up goes before C, down comes back", up == [A_, B_, D, C_] and days() == [A_, B_, C_, D], (up, days()))
    tap(page, DAY(D, '[data-act="dayclose"]'))
    tap(page, '[data-act="addday"]')
    E_ = days()[-1]
    added = day_of(A.stored(page), cid, E_)["name"]
    tap(page, HEAD(E_))
    tap(page, DAY(E_, '[data-act="dayrm"]'))
    asked = answer(page, False)
    kept = days()
    tap(page, DAY(E_, '[data-act="dayrm"]'))
    answer(page, True)
    A.check("Add day after days A Heavy, B, C, D Pump is named E; Remove day asks first, then takes it out",
            added == "E" and "Remove day E?" in asked and kept[-1] == E_ and days() == [A_, B_, C_, D], (added, asked, days()))

    # ── every field of an exercise; kind rewrites what depends on it ──
    x = lambda: ex_of(A.stored(page), cid, D, E["X"])
    wx = lambda: A.stored(page)["weeks"][-1]["days"][D]["exercises"][E["X"]]
    tap(page, ROW(E["X"]))
    tap(page, EX(E["X"], '[data-act="kind"][data-v="time"]'))
    t1 = x()
    tap(page, EX(E["X"], '[data-act="step"][data-k="target"][data-d="1"]'))
    A.check("kind Time: no rep range, a 30 s target, the pair goes on; its target steps by 5 s",
            t1["kind"] == "time" and t1["repMin"] is None and t1["repMax"] is None and t1["target"] == 30 and t1.get("pair") == pairs()["Y"]
            and x()["target"] == 35, t1)
    tap(page, EX(E["X"], '[data-act="kind"][data-v="check"]'))
    c1 = x()
    A.check("kind Check: target 1, one set, no rep range, and the pair is cleared on both",
            c1["kind"] == "check" and c1["target"] == 1 and c1["sets"] == 1 and c1["repMin"] is None and "pair" not in c1
            and pairs()["Y"] is None, c1)
    type_into(page, EX(E["X"], '[data-f="dur"]'), "7")
    seven = x().get("duration")
    type_into(page, EX(E["X"], '[data-f="dur"]'), "1,5")
    A.check("a check row's countdown is typed in minutes: 7 -> 420 s, 1,5 -> 90 s, and the week (no set stored) has it at once",
            seven == 420 and x()["duration"] == 90 and wx()["duration"] == 90, (seven, x().get("duration")))
    before = raw(page)
    type_into(page, EX(E["X"], '[data-f="dur"]'), "0")
    A.check("a countdown of 0 is refused by core: one plain line says why, the document is unchanged, the field shows 1.5 again",
            raw(page) == before and "Not saved" in msg(page) and "countdown" in msg(page)
            and page.locator(EX(E["X"], '[data-f="dur"]')).input_value() == "1.5", msg(page))
    tap(page, EX(E["X"], '[data-act="kind"][data-v="reps"]'))
    r1 = x()
    A.check("back to Reps: 8-12, target 8, 3 sets again, and no countdown",
            r1["kind"] == "reps" and (r1["repMin"], r1["repMax"], r1["target"], r1["sets"]) == (8, 12, 8, 3) and "duration" not in r1, r1)
    for k, dd in (("sets", 1), ("target", 1), ("repMin", 1), ("repMax", -1)):
        tap(page, EX(E["X"], f'[data-act="step"][data-k="{k}"][data-d="{dd}"]'))
    r2 = x()
    A.check("steppers: sets 3 -> 4, target 8 -> 9, range 8-12 -> 9-11; the week (no set) is rebuilt with 4 sets",
            (r2["sets"], r2["target"], r2["repMin"], r2["repMax"]) == (4, 9, 9, 11) and wx()["sets"] == [None] * 4, r2)
    type_into(page, EX(E["X"], '[data-f="load"]'), "42.5")
    before = raw(page)
    type_into(page, EX(E["X"], '[data-f="load"]'), "abc")
    refused = (raw(page) == before, msg(page), page.locator(EX(E["X"], '[data-f="load"]')).input_value())
    type_into(page, EX(E["X"], '[data-f="load"]'), "-5")
    A.check("load is typed in kg (42.5); \"abc\" and -5 are refused by core with one line each, the document unchanged",
            x()["load"] == 42.5 and refused[0] and "Not saved" in refused[1] and "load" in refused[1] and refused[2] == "42.5"
            and raw(page) == before and "load" in msg(page), (x()["load"], refused, msg(page)))
    tap(page, EX(E["X"], '[data-act="lstep"][data-v="5"]'))
    tap(page, EX(E["X"], '[data-act="bw"]'))
    bw = (x().get("bodyweight"), page.locator(EX(E["X"], '[data-l="load"]')).inner_text())
    tap(page, EX(E["X"], '[data-act="bw"]'))
    A.check("load step 5 is chosen; Bodyweight on makes the load the added load, off removes it",
            x()["loadStep"] == 5 and bw == (True, "Added load, kg") and "bodyweight" not in x(), (x(), bw))
    type_into(page, EX(E["X"], '[data-f="note"]'), "Squeeze at the top")
    type_into(page, EX(E["X"], '[data-f="ename"]'), "Barbell Hip Thrust")
    A.check("the note and the name are saved", x()["note"] == "Squeeze at the top" and x()["name"] == "Barbell Hip Thrust"
            and page.locator(ROW(E["X"])).inner_text().startswith("Barbell Hip Thrust"), x())
    tap(page, EX(E["X"], '[data-act="pair"]'))
    A.check("every field is in the program as the Blueprint's schema has it (the muscles guessed once, from the first name)", x() == {
        "id": E["X"], "name": "Barbell Hip Thrust", "kind": "reps", "sets": 4, "target": 9, "repMin": 9, "repMax": 11, "load": 42.5,
        "loadStep": 5, "note": "Squeeze at the top", "pair": pairs()["Y"], "muscles": {"gluteal": 1, "hamstring": 0.5}} and pairs()["Y"], x())
    layout(page, "the program editor with an exercise open")

    # ── a week with a set keeps its copy; the edit shows from the next week ──
    back_to_day(page)
    pull = builtin["days"][0]["exercises"][0]["id"]
    tap(page, f'[data-screen="day"] [data-day="{A_}"]')
    page.wait_for_selector(f'[data-screen="day"] [data-set="{A_}:{pull}:0"]')
    A.touch_tap(page, f'[data-screen="day"] [data-set="{A_}:{pull}:0"]')
    ctx.clock.run_for(1000)
    go_programs(page)
    open_program(page, cid)
    weeks = A.stored(page)["weeks"]
    state = page.locator('[data-v="state"]').inner_text()
    tap(page, ROW(E["X"]))
    tap(page, EX(E["X"], '[data-act="step"][data-k="sets"][data-d="1"]'))
    carry = page.locator(EX(E["X"], '[data-v="carry"]'))
    A.check("with a set logged in week 1, an edit changes the program only; the week keeps its copy and the editor says so",
            x()["sets"] == 5 and A.stored(page)["weeks"] == weeks and "has sets logged" in state and "week 2" in state
            and carry.is_visible() and "Week 2 carries load and target on from week 1" in carry.inner_text(), (state, x()["sets"]))
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    open_program(page, builtin["id"])
    tap(page, '[data-act="use"]')
    d = A.stored(page)
    used = msg(page)
    A.check("Use on a week with a set: nothing in the week changes and only nextProgram moves; the screen says from week 2",
            d["weeks"] == weeks and d["nextProgram"] == builtin["id"] and d["activeProgram"] == cid
            and "starts with week 2" in used and page.locator('[data-act="use"]').is_hidden(), (d["nextProgram"], d["activeProgram"], used))

    # ── delete: refused for a program in use, asked first for a never-used one ──
    before = raw(page)
    tap(page, '[data-act="del"]')
    next_refused = msg(page)
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    listed = page.locator('[data-screen="programs"]').inner_text()
    open_program(page, cid)
    tap(page, '[data-act="del"]')
    A.check("Delete is refused with the reason for nextProgram and for the program week 1 runs; nothing changes",
            raw(page) == before and "Not deleted" in next_refused and "week 2 is set to run it" in next_refused
            and "Not deleted" in msg(page) and "week 1 runs it" in msg(page) and page.locator("dialog").count() == 0, (next_refused, msg(page)))
    A.check("the list shows which program runs this week and which next", "This week" in listed and "Next week" in listed, listed)
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    tap(page, '[data-screen="programs"] [data-act="new"]')
    page.wait_for_function("() => Cali.current().name === 'program'")
    page.keyboard.type("Spare")    # the new program's name field opens focused and selected
    page.keyboard.press("Enter")
    sid = ev("() => Cali.current().args.id")
    spare = program(A.stored(page), sid)
    A.check("New program: one day A with no exercise, a fresh id, its name typed at once",
            spare and spare["name"] == "Spare" and len(spare["days"]) == 1 and spare["days"][0]["name"] == "A"
            and spare["days"][0]["exercises"] == [] and ":" not in sid and sid not in old_ids, spare)
    before = raw(page)
    tap(page, '[data-act="use"]')
    use_refused = msg(page)
    tap(page, HEAD(spare["days"][0]["id"]))
    tap(page, DAY(spare["days"][0]["id"], '[data-act="dayrm"]'))
    A.check("Use is refused for a program with a day that has no exercise, and its last day cannot be removed",
            raw(page) == before and "Not used" in use_refused and "day A has no exercise" in use_refused
            and "at least one day" in msg(page) and page.locator("dialog").count() == 0, (use_refused, msg(page)))
    tap(page, '[data-act="del"]')
    asked = answer(page, False)
    kept = program(A.stored(page), sid) is not None
    tap(page, '[data-act="del"]')
    answer(page, True)
    page.wait_for_selector('[data-screen="programs"] .program-list')
    A.check("Delete asks first (Cancel keeps it); a never-used program then goes, and the list says so",
            "Delete Spare?" in asked and kept and program(A.stored(page), sid) is None and "Deleted Spare" in msg(page), (asked, msg(page)))
    layout(page, "the program list")
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


# ── a set at 0 is stored; Finish week builds from nextProgram; a program a week ran stays ──
def scenario_zero(browser, url, errors):
    ctx, page = A.phone(browser, errors, "program-zero", color_scheme="light", reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate
    go_programs(page)
    tap(page, '[data-screen="programs"] [data-act="new"]')
    page.wait_for_function("() => Cali.current().name === 'program'")
    page.keyboard.type("Solo")
    page.keyboard.press("Enter")
    sid = ev("() => Cali.current().args.id")
    day = program(A.stored(page), sid)["days"][0]["id"]
    tap(page, DAY(day, '[data-act="addex"]'))
    page.keyboard.type("Dead Hang")
    page.keyboard.press("Enter")
    ex = program(A.stored(page), sid)["days"][0]["exercises"][0]["id"]
    for _ in range(7):
        tap(page, EX(ex, '[data-act="step"][data-k="target"][data-d="-1"]'))
    tap(page, '[data-act="use"]')
    d = A.stored(page)
    A.check("a program built from blank is used at once on the empty week 1",
            d["weeks"][0]["program"] == sid and d["activeProgram"] == d["nextProgram"] == sid
            and d["weeks"][0]["days"][day]["exercises"][ex]["target"] == 1, d["weeks"][0]["program"])
    back_to_day(page)
    cell = f'[data-screen="day"] [data-set="{day}:{ex}:0"]'
    A.touch_tap(page, cell)
    ctx.clock.run_for(1000)
    A.touch_tap(page, cell)
    ctx.clock.run_for(1000)
    weeks = A.stored(page)["weeks"]
    A.check("the set is tapped down to 0 (stored)", weeks[0]["days"][day]["exercises"][ex]["sets"][0]["r"] == 0, weeks[0]["days"][day])
    go_programs(page)
    open_program(page, "abc")
    tap(page, '[data-act="use"]')
    d = A.stored(page)
    A.check("Use on a week whose only set is at 0: the week stays, only nextProgram moves",
            d["weeks"] == weeks and d["nextProgram"] == "abc" and d["activeProgram"] == sid and "starts with week 2" in msg(page), msg(page))
    back_to_day(page)
    tap(page, '[data-screen="day"] [data-slot="dayheader"] .week-btn')
    tap(page, '.week-menu [data-week-act="finish"]')
    page.wait_for_selector('[data-screen="finish-week"] [data-week-act="confirm"]')
    tap(page, '[data-screen="finish-week"] [data-week-act="confirm"]')
    page.wait_for_function("() => Cali.current().name === 'day' && Cali.week().n === 2")
    d = A.stored(page)
    abc = program(d, "abc")
    A.check("Finish week then builds week 2 from it (every day of A/B/C), and it runs this week",
            len(d["weeks"]) == 2 and d["weeks"][1]["program"] == "abc" and d["activeProgram"] == "abc"
            and list(d["weeks"][1]["days"]) == [x["id"] for x in abc["days"]], (d["weeks"][1]["program"], d["activeProgram"]))
    go_programs(page)
    open_program(page, sid)
    before = raw(page)
    tap(page, '[data-act="del"]')
    A.check("a program a stored week ran cannot be deleted (core needs every week's program); the line says why",
            raw(page) == before and "week 1 ran it" in msg(page), msg(page))
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


# ── a copy used on a week Finish week built keeps that week's progression ──
def scenario_progression(browser, url, errors):
    ctx, page = A.phone(browser, errors, "program-progress", reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate
    prog = A.stored(page)["programs"][0]
    day = prog["days"][0]
    pull = day["exercises"][0]
    for i in range(pull["sets"]):
        A.touch_tap(page, f'[data-screen="day"] [data-set="{day["id"]}:{pull["id"]}:{i}"]')
        ctx.clock.run_for(1000)
    tap(page, '[data-screen="day"] [data-act="session"]')
    page.wait_for_selector('[data-screen="summary"] [data-act="done"]')
    tap(page, '[data-screen="summary"] [data-act="done"]')
    page.wait_for_selector('[data-screen="day"] [data-set]')
    tap(page, '[data-screen="day"] [data-slot="dayheader"] .week-btn')
    tap(page, '.week-menu [data-week-act="finish"]')
    page.wait_for_selector('[data-screen="finish-week"] [data-week-act="confirm"]')
    tap(page, '[data-screen="finish-week"] [data-week-act="confirm"]')
    page.wait_for_function("() => Cali.current().name === 'day' && Cali.week().n === 2")
    w2 = A.stored(page)["weeks"][1]
    moved = w2["days"][day["id"]]["exercises"][pull["id"]]
    A.check("week 2 moved Weighted Pull-up on from the program's values (the setup of this check)",
            (moved["load"], moved["target"]) != (pull["load"], pull["target"]), moved)
    go_programs(page)
    open_program(page, "abc")
    tap(page, '[data-act="dup"]')
    page.wait_for_function("() => Cali.current().args.id !== 'abc'")
    cid = ev("() => Cali.current().args.id")
    tap(page, '[data-act="use"]')
    w = A.stored(page)["weeks"][1]
    got = w["days"][day["id"]]["exercises"][pull["id"]]
    A.check("Use of the copy on empty week 2 rebuilds it from the copy and keeps week 2's load and target (progression kept)",
            w["program"] == cid and w["n"] == 2 and w["startedAt"] == w2["startedAt"]
            and (got["load"], got["target"]) == (moved["load"], moved["target"]) and w["days"] == w2["days"], got)
    tap(page, ROW(pull["id"]))
    type_into(page, EX(pull["id"], '[data-f="load"]'), "10")
    got = A.stored(page)["weeks"][1]["days"][day["id"]]["exercises"][pull["id"]]
    A.check("a load typed in the program the empty week runs reaches the week; the target the week moved on stays",
            got["load"] == 10 and got["target"] == moved["target"], got)
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


# ── import a program file ─────────────────────────────────────────────
def scenario_import(browser, url, errors):
    ctx, page = A.phone(browser, errors, "program-import", reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    go_programs(page)
    good = {"id": "abc", "name": "Upper Lower", "days": [
        {"id": "up", "name": "Upper", "exercises": [
            {"id": "bench", "name": "Bench Press", "kind": "reps", "sets": 3, "target": 8, "repMin": 6, "repMax": 10, "load": 60, "loadStep": 2.5},
            {"id": "row", "name": "Cable Row", "kind": "reps", "sets": 3, "target": 10, "repMin": 8, "repMax": 12, "load": 45, "loadStep": 2.5}]},
        {"id": "low", "name": "Lower", "exercises": [
            {"id": "plank", "name": "Plank", "kind": "time", "sets": 2, "target": 40, "repMin": None, "repMax": None, "load": 0, "loadStep": 2.5, "bodyweight": True},
            {"id": "walk", "name": "Walk", "kind": "check", "sets": 1, "target": 1, "repMin": None, "repMax": None, "load": 0, "loadStep": 0, "duration": 600}]}]}

    def choose(name, text):
        with page.expect_file_chooser() as info:
            tap(page, '[data-screen="programs"] [data-act="import"]')
        info.value.set_files(files=[{"name": name, "mimeType": "application/json", "buffer": text.encode("utf-8")}])

    choose("upper-lower.json", json.dumps(good))
    page.wait_for_function("() => Cali.current().name === 'program'")
    d = A.stored(page)
    got = d["programs"][-1]
    A.check("Import adds one program under a fresh id when its id is taken, day and exercise ids kept, and opens it",
            len(d["programs"]) == 2 and got["id"] != "abc" and ":" not in got["id"] and {**got, "id": "abc"} == good
            and program(d, "abc")["name"] == "A/B/C" and "Imported Upper Lower" in msg(page), (got["id"], msg(page)))
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')

    def bad(**change):
        p = json.loads(json.dumps(good))
        p["id"] = "fresh"
        for path, value in change.items():
            *keys, last = path.split("__")
            node = p
            for k in keys:
                node = node[int(k)] if k.isdigit() else node[k]
            node[int(last) if last.isdigit() else last] = value
        return json.dumps(p)

    twice_day = json.loads(bad())
    twice_day["days"][1]["id"] = "up"
    twice_ex = json.loads(bad())
    twice_ex["days"][0]["exercises"][1]["id"] = "bench"
    cases = [
        ("not JSON", "notes.txt", "{ not json", "not JSON"),
        ("an unknown kind", "k.json", bad(days__0__exercises__0__kind="sets"), "kind “sets”"),
        ("sets outside 1-20", "s.json", bad(days__0__exercises__1__sets=25), "25 sets; it must be 1 to 20"),
        ("a rep range with min above max", "r.json", bad(days__0__exercises__0__repMin=12, days__0__exercises__0__repMax=8), "low end is above its high end"),
        ("an id with ':'", "c.json", bad(days__0__exercises__0__id="bench:1"), "contains “:”"),
        ("a day id twice", "d.json", json.dumps(twice_day), "day id “up” is used twice"),
        ("an exercise id twice in a day", "e.json", json.dumps(twice_ex), "exercise id “bench” is used twice on day Upper"),
        ("a muscle counted other than 1 or 0.5", "m.json", bad(days__0__exercises__0__muscles={"chest": 2}), "it must be 1 (main) or 0.5 (helper)"),
        ("a muscle not in Cali.muscles", "n.json", bad(days__0__exercises__0__muscles={"pecs": 1}), "names the muscle “pecs”"),
        ("a whole document", "backup.json", FIXTURE, "whole backup"),
    ]
    before = raw(page)
    lines = []
    for what, name, text, want in cases:
        choose(name, text)
        page.wait_for_function("(w) => { const m = document.querySelector('[data-screen=\"programs\"] [data-msg]'); return m && !m.hidden && m.textContent.includes(w); }",
                               arg=want, timeout=5000)
        lines.append(msg(page))
        A.check(f"Import refuses {what} with one plain line and leaves the document unchanged",
                raw(page) == before and msg(page).startswith("Not imported") and want in msg(page)
                and page.evaluate("() => Cali.current().name") == "programs", msg(page))
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


# ── a program change pushes at once; the token stays out ──────────────
def scenario_sync(browser, url, errors):
    gh = A.MockGitHub()
    ctx, page = A.phone(browser, errors, "program-sync", gh=gh, reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    settle = lambda: (page.wait_for_timeout(200), A.poll(page, "() => !CaliSync.status().running"))
    tap(page, '[data-screen="day"] .settings-open')
    page.wait_for_selector('[data-screen="settings"] .settings-body')
    tap(page, '[data-act="github"]')
    page.fill("#settings-repo", "Estaed/Calisthenics-Data")
    page.fill("#settings-token", A.TOKEN)
    tap(page, '[data-act="connect"]')
    settle()
    first = gh.puts
    tap(page, '[data-screen="settings"] [data-act="programs"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    open_program(page, "abc")
    type_into(page, '[data-f="pname"]', "My A/B/C")
    settle()
    remote = json.loads(gh.text)
    A.check("a program change pushes at once (no Done needed), with the new name, and the token is not in it",
            first == 1 and gh.puts == 2 and remote["programs"][0]["name"] == "My A/B/C" and A.TOKEN not in gh.text, (first, gh.puts))
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


# ── the Muscles field: chips cycling off -> main -> helper -> off, the guess written once, the week that carries it ──
def scenario_muscles(browser, url, errors):
    ctx, page = A.phone(browser, errors, "program-muscles", color_scheme="light", reduced_motion="reduce")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    builtin = A.stored(page)["programs"][0]
    day = builtin["days"][0]["id"]
    lp = next(e["id"] for e in builtin["days"][0]["exercises"] if e["name"] == "Leg Press")
    chip = lambda ex, m: EX(ex, f'[data-act="muscle"][data-m="{m}"]')
    states = lambda ex: page.evaluate("""(s) => Object.fromEntries([...document.querySelectorAll(s)].filter(b => b.getAttribute('aria-pressed') !== 'false')
        .map(b => [b.dataset.m, b.getAttribute('aria-pressed')]))""", EX(ex, '[data-act="muscle"]'))
    line = lambda ex, v: page.evaluate("""(s) => { const el = document.querySelector(s); return el && !el.hidden ? el.textContent : ''; }""",
                                       EX(ex, f'[data-v="{v}"]'))
    pm = lambda ex, pid="abc": (ex_of(A.stored(page), pid, day, ex) or {}).get("muscles", "absent")
    wm = lambda ex, n=0: A.stored(page)["weeks"][n]["days"][day]["exercises"][ex].get("muscles", "absent")

    go_programs(page)
    open_program(page, "abc")
    tap(page, ROW(lp))
    shown = (states(lp), line(lp, "mline"), line(lp, "mweek"))
    A.check("the Muscles field shows a chip per muscle: Leg Press main on quads (pressed), helper on glutes and adductors (mixed)",
            shown == ({"quadriceps": "true", "gluteal": "mixed", "adductors": "mixed"}, "", "")
            and page.locator(EX(lp, '[data-act="muscle"]')).count() == 16, shown)
    tap(page, chip(lp, "hamstring"))
    one = pm(lp)
    tap(page, chip(lp, "hamstring"))
    half = pm(lp)
    tap(page, chip(lp, "hamstring"))
    A.check("a tap cycles a muscle off -> main (1) -> helper (0.5) -> off, saved in the program; week 1 (no set) carries it at once",
            one == {"quadriceps": 1, "gluteal": 0.5, "hamstring": 1, "adductors": 0.5}
            and half == {"quadriceps": 1, "gluteal": 0.5, "hamstring": 0.5, "adductors": 0.5}
            and pm(lp) == {"quadriceps": 1, "gluteal": 0.5, "adductors": 0.5} and wm(lp) == pm(lp), (one, half, pm(lp)))
    for m, n in (("quadriceps", 2), ("gluteal", 1), ("adductors", 1)):   # main -> helper -> off; helper -> off
        for _ in range(n):
            tap(page, chip(lp, m))
    off = (pm(lp), wm(lp), states(lp), line(lp, "mline"))
    tap(page, chip(lp, "quadriceps"))
    A.check("all off stores {} (counts nothing, and the field says so); a tap then starts from {}, not from the guess",
            off == ({}, {}, {}, "Counts nothing on the muscle map.") and pm(lp) == {"quadriceps": 1}, (off, pm(lp)))
    type_into(page, EX(lp, '[data-f="ename"]'), "Leg Press Machine")
    A.check("renaming an exercise that carries a pick keeps the pick (no guess over it)",
            pm(lp) == {"quadriceps": 1} and ex_of(A.stored(page), "abc", day, lp)["name"] == "Leg Press Machine", pm(lp))
    layout(page, "the program editor with the Muscles field open")

    # the guess: written the first time a name is saved, never over a pick, never again on a rename
    tap(page, DAY(day, '[data-act="addex"]'))
    page.keyboard.type("Lat Pulldown")
    page.keyboard.press("Enter")
    lat = day_of(A.stored(page), "abc", day)["exercises"][-1]["id"]
    first = pm(lat)
    type_into(page, EX(lat, '[data-f="ename"]'), "Squat")
    A.check("naming a new exercise writes its name's guess (Lat Pulldown: upper back, biceps as helper); renaming it does not guess again",
            first == {"upper-back": 1, "biceps": 0.5} and pm(lat) == first and states(lat) == {"upper-back": "true", "biceps": "mixed"}
            and line(lat, "mline") == "", (first, pm(lat)))
    tap(page, DAY(day, '[data-act="addex"]'))
    page.keyboard.type("Mystery Move")
    page.keyboard.press("Enter")
    mys = day_of(A.stored(page), "abc", day)["exercises"][-1]["id"]
    unknown = (pm(mys), line(mys, "mline"))
    type_into(page, EX(mys, '[data-f="ename"]'), "Hip Thrust")
    A.check("a name the table does not know writes nothing and the field says the map does not count it; the first name it knows writes its guess",
            unknown[0] == "absent" and unknown[1].startswith("No muscle yet, so the muscle map does not count it.")
            and pm(mys) == {"gluteal": 1, "hamstring": 0.5}, (unknown, pm(mys)))
    tap(page, EX(mys, '[data-act="exclose"]'))
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')

    # an exercise without muscles (a program file from before the field): the chips show the guess, a tap starts from it
    plain = {"id": "old", "name": "Old file", "days": [{"id": "od", "name": "A", "exercises": [
        {"id": "orow", "name": "Seated Row", "kind": "reps", "sets": 3, "target": 8, "repMin": 8, "repMax": 12, "load": 40, "loadStep": 2.5}]}]}
    with page.expect_file_chooser() as info:
        tap(page, '[data-screen="programs"] [data-act="import"]')
    info.value.set_files(files=[{"name": "old.json", "mimeType": "application/json", "buffer": json.dumps(plain).encode("utf-8")}])
    page.wait_for_function("() => Cali.current().name === 'program' && Cali.current().args.id === 'old'")
    tap(page, ROW("orow"))
    seen = (states("orow"), line("orow", "mline"))
    stored_before = (ex_of(A.stored(page), "old", "od", "orow") or {}).get("muscles", "absent")
    tap(page, chip("orow", "biceps"))
    A.check("an exercise without muscles shows its name's guess, says so, and stores nothing until a tap, which starts from the guess",
            seen == ({"upper-back": "true", "trapezius": "mixed", "biceps": "mixed", "deltoids": "mixed"},
                     "Guessed from the name. A tap makes a muscle main, a second tap a helper (½, counts half), a third off.")
            and stored_before == "absent" and (ex_of(A.stored(page), "old", "od", "orow") or {}).get("muscles")
            == {"upper-back": 1, "trapezius": 0.5, "deltoids": 0.5}, (seen, stored_before))
    tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="programs"] .program-list')
    tap(page, '[data-screen="programs"] [data-act="back"]')
    page.wait_for_selector('[data-screen="settings"] .settings-body')
    tap(page, '[data-screen="settings"] [data-act="back"]')
    page.wait_for_selector('[data-screen="day"] [data-set]')

    # a week with a set keeps its copy; the field says so; the week Finish builds carries the edit
    pull = builtin["days"][0]["exercises"][0]["id"]
    A.touch_tap(page, f'[data-screen="day"] [data-set="{day}:{pull}:0"]')
    ctx.clock.run_for(1000)
    week1 = wm(lp)
    go_programs(page)
    open_program(page, "abc")
    tap(page, ROW(lp))
    said = line(lp, "mweek")
    tap(page, chip(lp, "calves"))
    A.check("with a set logged, a Muscles edit changes the program only; week 1 keeps its muscles and the field says so in one line",
            said == "Week 1 keeps the muscles it was built with; a change shows from week 2."
            and pm(lp) == {"quadriceps": 1, "calves": 1} and wm(lp) == week1 == {"quadriceps": 1}, (said, pm(lp), wm(lp)))
    back_to_day(page)
    tap(page, '[data-screen="day"] [data-slot="dayheader"] .week-btn')
    tap(page, '.week-menu [data-week-act="finish"]')
    page.wait_for_selector('[data-screen="finish-week"] [data-week-act="confirm"]')
    tap(page, '[data-screen="finish-week"] [data-week-act="confirm"]')
    page.wait_for_function("() => Cali.current().name === 'day' && Cali.week().n === 2")
    A.check("Finish week builds week 2 carrying the edited muscles; week 1 keeps its own",
            wm(lp, 1) == {"quadriceps": 1, "calves": 1} and wm(lp, 0) == {"quadriceps": 1}, (wm(lp, 1), wm(lp, 0)))
    A.check("every tap landed on the control it aimed at", not MISSED, MISSED[:5])
    ctx.close()


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fn in (("main", scenario_main), ("zero", scenario_zero), ("progression", scenario_progression),
                         ("import", scenario_import), ("sync", scenario_sync), ("muscles", scenario_muscles)):
            A.guarded(f"program scenario {name}", fn, browser, url, errors)
        browser.close()
    srv.shutdown()
    real = [e for e in errors if "Failed to load resource" not in e]   # Chromium's line for the mocked 404 the sync expects
    A.check("no console errors or page errors", not real, "\n".join(real[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
