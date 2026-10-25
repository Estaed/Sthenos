"""Muscle map (app/muscles.js, Task-06): the week's fractional sets per muscle on a front and back body, by day.

Run from the repo root: python tests/test_muscles.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py (360 x 740, touch, Playwright's clock) and its console-error collection. Every expected number
below is counted by hand from the fixture, never by the app's own code. Data: fixtures written here; nothing personal.

Fixture "fx" (week 2 current, week 1 past), fractional count: sets x 1 for a muscle the exercise is for, x 0.5 for a
helper; done = logged sets above 0.
  Push (dP): Bench Press 3 sets {chest 1, triceps .5, deltoids .5}, logged 8, 0, empty   -> done 1
             Overhead Press 2 sets, no muscles: the name guesses {deltoids 1, triceps .5}, logged 6, 6 -> done 2
             Mystery Move 2 sets, no muscles, no guess: "Not counted"
             Stretch, a check row carrying {chest 1}: ignored
             Plank 2 sets (time) with {}: counts nothing, not listed
  Legs (dL): Squat 4 sets {quadriceps 1, gluteal .5}, logged 5, 5, 5, empty -> done 3
             Seated Leg Curl 1 set, guessed {hamstring 1}, not logged
             Mystery Move 1 set (the same name: listed once on Week)
             Push-up 2 sets, guessed {chest 1, triceps .5, deltoids .5}, logged 10, empty -> done 1
  Week 1 (past): Push only, Bench Press copied as {triceps 1}, 2 sets, both logged.
"""
import copy
import datetime
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

KEYS = ["chest", "deltoids", "biceps", "triceps", "forearm", "abs", "obliques", "upper-back", "trapezius", "lower-back",
        "gluteal", "quadriceps", "hamstring", "adductors", "calves", "tibialis"]
AT = "2026-10-25T21:{:02d}:00.000Z"


def ex(id_, name, kind="reps", sets=3, muscles=None):
    e = {"id": id_, "name": name, "kind": kind, "sets": sets, "target": 8 if kind == "reps" else 30 if kind == "time" else 1,
         "repMin": 6 if kind == "reps" else None, "repMax": 10 if kind == "reps" else None, "load": 0,
         "loadStep": 0 if kind == "check" else 2.5}
    if muscles is not None:
        e["muscles"] = muscles
    return e


def week_of(program, n, logged, started, finished=None, days=None, override=None):
    """Week n copied from program (as Cali.weekFrom does); logged: {exId: [r or None]}; override: {exId: {field: v}}."""
    out = {}
    for d in program["days"]:
        if days is not None and d["id"] not in days:
            continue
        exs = {}
        for e in d["exercises"]:
            if days is not None and e["id"] not in days[d["id"]]:
                continue
            c = {k: copy.deepcopy(v) for k, v in e.items() if k not in ("id", "sets")}
            c.update((override or {}).get(e["id"], {}))
            reps = logged.get(e["id"], [None] * e["sets"])
            c["sets"] = [None if r is None else {"r": r, "at": AT.format(i)} for i, r in enumerate(reps)]
            exs[e["id"]] = c
        out[d["id"]] = {"exercises": exs}
    w = {"n": n, "program": program["id"], "startedAt": started, "days": out}
    if finished:
        w["finishedAt"] = finished
    return w


FX = {"id": "fx", "name": "Fixture split", "days": [
    {"id": "dP", "name": "Push", "exercises": [
        ex("bp", "Bench Press", muscles={"chest": 1, "triceps": 0.5, "deltoids": 0.5}),
        ex("ohp", "Overhead Press", sets=2),
        ex("mys", "Mystery Move", sets=2),
        ex("str", "Stretch", kind="check", sets=1, muscles={"chest": 1}),
        ex("plk", "Plank", kind="time", sets=2, muscles={})]},
    {"id": "dL", "name": "Legs", "exercises": [
        ex("sq", "Squat", sets=4, muscles={"quadriceps": 1, "gluteal": 0.5}),
        ex("lc", "Seated Leg Curl", sets=1),
        ex("mys2", "Mystery Move", sets=1),
        ex("pu", "Push-up", sets=2)]}]}
LOGGED = {"bp": [8, 0, None], "ohp": [6, 6], "sq": [5, 5, 5, None], "pu": [10, None], "plk": [30, None], "str": [1]}
WEEK1 = week_of(FX, 1, {"bp": [8, 8]}, "2026-10-18T20:00:00.000Z", "2026-10-25T19:00:00.000Z",
                days={"dP": ["bp"]}, override={"bp": {"muscles": {"triceps": 1}}})
WEEK1["days"]["dP"]["exercises"]["bp"]["sets"] = [{"r": 8, "at": "2026-10-19T09:00:00.000Z"}, {"r": 8, "at": "2026-10-19T09:05:00.000Z"}]


def fx_doc():
    return {"_version": 5, "updatedAt": "2026-10-25T21:20:00.000Z", "programs": [copy.deepcopy(FX)], "activeProgram": "fx",
            "nextProgram": "fx", "weeks": [copy.deepcopy(WEEK1), week_of(FX, 2, LOGGED, "2026-10-25T20:00:00.000Z")],
            "body": [], "settings": {}}


# by hand: { muscle: (done, planned) }, muscles not listed are (0, 0)
PUSH = {"chest": (1, 3), "triceps": (1.5, 2.5), "deltoids": (2.5, 3.5)}
LEGS = {"quadriceps": (3, 4), "gluteal": (1.5, 2), "hamstring": (0, 1), "chest": (1, 2), "triceps": (0.5, 1), "deltoids": (0.5, 1)}
WEEK = {"chest": (2, 5), "triceps": (2, 3.5), "deltoids": (3, 4.5), "quadriceps": (3, 4), "gluteal": (1.5, 2), "hamstring": (0, 1)}
NOT_WORKED = "Biceps, Forearms, Abs, Obliques, Upper back, Traps, Lower back, Adductors, Calves, Shins"

ROWS = """() => Object.fromEntries([...document.querySelectorAll('[data-screen="muscles"] .mm-row')].map(r =>
    [r.dataset.m, r.querySelector('.num').textContent.split('/').map(Number)]))"""
ORDER = """() => [...document.querySelectorAll('[data-screen="muscles"] .mm-row')].map(r => r.dataset.m)"""
BOX = "() => document.querySelector('[data-screen=\"muscles\"] .mm-pick').innerText.replace(/\\s+/g, ' ').trim()"
FIX = """() => [...document.querySelectorAll('[data-screen="muscles"] .mm-fix:not([hidden]) [data-act="fix"]')].map(b => b.innerText.split('\\n')[0])"""
TARGETS = """() => [...document.querySelectorAll('#app [data-screen] button')].filter(el => el.getClientRects().length
    && getComputedStyle(el).visibility !== 'hidden').map(el => {
      const r = el.getBoundingClientRect(), a = getComputedStyle(el, '::after');
      let w = r.width, h = r.height;
      if (a.content && a.content !== 'none' && a.position === 'absolute') {
        h += -(parseFloat(a.top) || 0) - (parseFloat(a.bottom) || 0); w += -(parseFloat(a.left) || 0) - (parseFloat(a.right) || 0); }
      return [el.dataset.m || el.dataset.sel || el.dataset.act || el.className, Math.round(w), Math.round(h)]; })
    .filter(([, w, h]) => w < 44 || h < 44)"""
WIDE = "() => document.scrollingElement.scrollWidth <= innerWidth"


def full(expected):
    return {k: list(expected.get(k, (0, 0))) for k in KEYS}


def load(page, url, doc):
    page.goto(url)
    page.wait_for_selector('[data-screen="day"]')
    page.evaluate("(t) => localStorage.setItem('cali.v5', t)", json.dumps(doc))
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')


def open_map(page):
    A.poll(page, """() => { const b = document.querySelector('[data-screen="day"] .mm-open');
        return b && getComputedStyle(b).visibility === 'visible' && b.getBoundingClientRect().width >= 43.5; }""", timeout=5)
    A.touch_tap(page, '[data-screen="day"] .mm-open')
    page.wait_for_selector('[data-screen="muscles"] .mm-row')


def chip(page, name):
    i = page.evaluate("""(n) => [...document.querySelectorAll('[data-screen="muscles"] .mm-days button')]
        .findIndex(x => x.textContent.trim() === n)""", name)
    A.touch_tap(page, f'[data-screen="muscles"] .mm-days button:nth-child({i + 1})')


# ── colour, measured on the fills the screen paints ──
PAINTED = """() => { const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const g = cv.getContext('2d', { willReadFrequently: true });
  const rgb = c => { g.clearRect(0, 0, 1, 1); g.fillStyle = '#000'; g.fillStyle = c; g.fillRect(0, 0, 1, 1); return [...g.getImageData(0, 0, 1, 1).data].slice(0, 3); };
  const out = {};
  for (const m of document.querySelectorAll('[data-screen="muscles"] .mm-m')) for (const p of m.querySelectorAll('path')) {
    const c = rgb(getComputedStyle(p).fill); (out[m.dataset.m] = out[m.dataset.m] || []).push(c.join(',')); }
  const probe = document.createElement('i'); probe.style.color = 'var(--mm-zero)'; document.body.append(probe);
  const grey = rgb(getComputedStyle(probe).color); probe.remove();
  return { fills: Object.fromEntries(Object.entries(out).map(([k, v]) => [k, [...new Set(v)]])), grey }; }"""


def oklab(rgb):
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in rgb]
    r, g, b = lin
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


# one muscle per total: sets x part (sets <= 20); tibialis gets nothing
COLOUR_TOTALS = [("deltoids", 1, 0.5), ("biceps", 1, 1), ("triceps", 3, 0.5), ("forearm", 2, 1), ("calves", 5, 0.5),
                 ("abs", 3, 1), ("obliques", 4, 1), ("upper-back", 5, 1), ("trapezius", 6, 1), ("lower-back", 7, 1),
                 ("gluteal", 8, 1), ("quadriceps", 9, 1), ("chest", 10, 1), ("hamstring", 12, 1), ("adductors", 15, 1)]


def colour_doc():
    prog = {"id": "col", "name": "Colour", "days": [{"id": "dC", "name": "C", "exercises": [
        ex(f"c{i}", f"Colour {m}", sets=s, muscles={m: part}) for i, (m, s, part) in enumerate(COLOUR_TOTALS)]}]}
    return {"_version": 5, "updatedAt": "2026-10-25T21:20:00.000Z", "programs": [prog], "activeProgram": "col",
            "nextProgram": "col", "weeks": [week_of(prog, 1, {}, "2026-10-25T20:00:00.000Z")], "body": [], "settings": {}}


def scenario_colour(browser, url, errors):
    ctx, page = A.phone(browser, errors, "muscles-colour", reduced_motion="reduce")
    load(page, url, colour_doc())
    open_map(page)
    for theme in ("light", "dark"):
        page.evaluate("(t) => Cali.settings.set('theme', t)", theme)
        page.wait_for_function("(t) => document.documentElement.dataset.theme === t", arg=theme)
        got = page.evaluate(PAINTED)
        fills, grey = got["fills"], got["grey"]
        one = all(len(v) == 1 for v in fills.values())
        col = {k: tuple(int(x) for x in v[0].split(",")) for k, v in fills.items()}
        g = oklab(grey)
        steps = []
        for m, s, part in sorted(COLOUR_TOTALS, key=lambda t: t[1] * t[2]):
            L, a, b = oklab(col[m])
            steps.append((s * part, math.degrees(math.atan2(b, a)) % 360, math.dist((L, a, b), g)))
        down = all(y[1] <= x[1] + 0.75 for x, y in zip(steps, steps[1:]))
        away = all(y[2] >= x[2] - 0.003 for x, y in zip(steps, steps[1:]))
        first, at10 = steps[0], next(x for x in steps if x[0] == 10)
        flat = all(abs(x[1] - at10[1]) < 0.5 and abs(x[2] - at10[2]) < 0.002 for x in steps if x[0] >= 10)
        A.check(f"{theme}: a muscle's painted colour runs one way with its sets: the hue moves from orange toward red "
                "and the distance from the body grey grows, 10 sets and up full red",
                one and down and away and flat and 35 <= first[1] <= 75 and 15 <= at10[1] <= 33
                and at10[1] < first[1] - 15 and at10[2] > first[2] + 0.1,
                [(n, round(h, 1), round(d, 3)) for n, h, d in steps])
        A.check(f"{theme}: 0 sets paints the body grey", col["tibialis"] == tuple(grey), (col["tibialis"], grey))
        A.check(f"{theme}: the screen loads at 360 px with no sideways scroll and every control a 44 px target",
                page.evaluate(WIDE) and not page.evaluate(TARGETS), page.evaluate(TARGETS)[:5])
    ctx.close()


def scenario_map(browser, url, errors):
    ctx, page = A.phone(browser, errors, "muscles", color_scheme="dark", reduced_motion="reduce")
    load(page, url, fx_doc())
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate

    # ── the way in: beside the hourglass; the week the day screen shows; Back returns there ──
    bar = ev("""() => { const m = document.querySelector('[data-screen="day"] [data-slot="topbar"] .mm-open');
        const t = document.querySelector('[data-screen="day"] [data-slot="topbar"] .timer-open');
        const a = m.getBoundingClientRect(), b = t.getBoundingClientRect();
        return [m.nextElementSibling === t, Math.round(b.left - a.right), Math.round(a.width), Math.round(a.height),
                getComputedStyle(m).visibility, m.getAttribute('aria-label')]; }""")
    A.check("the muscle button sits in the day screen's top bar right beside the hourglass (before it), a 44 px target",
            bar[0] and 0 <= bar[1] <= 4 and bar[2] >= 44 and bar[3] >= 44 and bar[4] == "visible" and bar[5] == "Muscles", bar)
    ev("(d) => Cali.change(x => { x.weeks[1].days[d].startedAt = Cali.iso(Cali.now() - 300e3); }, { dirty: false })", "dP")
    clocked = A.poll(page, """() => { const b = document.querySelector('[data-screen="day"] .mm-open');
        const settled = getComputedStyle(b).visibility === 'hidden' || b.getBoundingClientRect().width >= 43.5;
        const items = [...document.querySelectorAll('[data-screen="day"] .workout-bar .week-btn, [data-screen="day"] .workout-clock, '
          + '[data-screen="day"] [data-slot="topbar"] > *, [data-screen="day"] .settings-open, [data-screen="day"] .workout-session')]
          .filter(el => !el.hidden && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
          .map(el => el.getBoundingClientRect()).sort((p, q) => p.left - q.left);
        const clock = document.querySelector('[data-screen="day"] .workout-clock');
        return settled && !clock.hidden && [items.every((r, i) => !i || r.left >= items[i - 1].right - 0.5), items.length]; }""", timeout=5)
    A.check("with the session clock running the bar's buttons never overlap: the muscle button keeps 44 px or steps aside",
            bool(clocked) and clocked[0], clocked)
    ev("(d) => Cali.change(x => { delete x.weeks[1].days[d].startedAt; }, { dirty: false })", "dP")
    A.touch_tap(page, '[data-screen="day"] [data-day="dL"]')
    page.wait_for_function("() => Cali.current().args.dayId === 'dL'")
    day_args = ev("() => Cali.current().args")
    open_map(page)
    pill = ev("() => document.querySelector('[data-screen=\"muscles\"] .mm-pill').textContent")
    chips = ev("() => [...document.querySelectorAll('[data-screen=\"muscles\"] .mm-days button')].map(b => [b.textContent.trim(), b.getAttribute('aria-pressed')])")
    A.check("it opens the muscle map of the week the day screen shows (week 2), chips Week then the days by name, Week chosen",
            ev("() => Cali.current()") == {"name": "muscles", "args": {"week": 2}} and pill == "Week 2"
            and chips == [["Week", "true"], ["Push", "false"], ["Legs", "false"]], (pill, chips))

    # ── the fractional totals per muscle, Week and each day ──
    A.check("Week: each muscle's done/planned fractional sets (1 a main muscle, 0.5 a helper; a set at 0 or empty is not done)",
            ev(ROWS) == full(WEEK), ev(ROWS))
    order = ev(ORDER)
    A.check("one row per muscle, most sets first, the muscles not worked at the end",
            len(order) == 16 and set(order) == set(KEYS) and order[:6] == ["chest", "deltoids", "quadriceps", "triceps", "gluteal", "hamstring"]
            and set(order[6:]) == set(KEYS) - set(WEEK), order)
    box = ev(BOX)
    A.check("Week: the box names the least worked main muscle with its exercise, and every muscle not worked",
            box == f"Least worked Hamstrings · 1 set a week Seated Leg Curl 1 (Legs) Not worked: {NOT_WORKED}", box)
    A.check("the check row (Stretch, carrying chest) is not counted, and Plank with {} counts nothing and is not listed",
            ev(ROWS)["chest"] == [2, 5] and ev(ROWS)["abs"] == [0, 0] and ev(FIX) == ["Not counted: Mystery Move"], ev(FIX))
    floors = ev("() => document.querySelectorAll('[data-screen=\"muscles\"] .mm-row .floor').length")
    A.check("on Week every bar has the 4-set tick", floors == 16, floors)
    chip(page, "Push")
    push, push_fix, push_floor = ev(ROWS), ev(FIX), ev("() => document.querySelectorAll('[data-screen=\"muscles\"] .mm-row .floor').length")
    A.check("Push: the day's own totals, its uncounted row, and no 4-set tick", push == full(PUSH) and push_fix == ["Not counted: Mystery Move"]
            and push_floor == 0, (push, push_fix, push_floor))
    box = ev(BOX)
    A.check("Push: the least worked main muscle on the day (triceps, worked only as a helper)",
            box.startswith("Least worked Triceps · 2.5 sets on Push Only as a helper Not worked: Biceps,"), box)
    chip(page, "Legs")
    A.check("Legs: the day's own totals", ev(ROWS) == full(LEGS), ev(ROWS))
    counted = ev("() => { const c = CaliMuscles.count(2); return [c.total.plan, c.byDay.dP.plan, c.byDay.dL.done]; }")
    A.check("CaliMuscles.count(2) gives the same numbers", counted == [{k: v[1] for k, v in WEEK.items()},
            {k: v[1] for k, v in PUSH.items()}, {k: v[0] for k, v in LEGS.items()}], counted)

    # ── a tap on a row, then on the body ──
    chip(page, "Week")
    A.touch_tap(page, '[data-screen="muscles"] .mm-row[data-m="triceps"]')
    box = ev(BOX)
    on = ev("() => [...document.querySelectorAll('[data-screen=\"muscles\"] .mm-m[data-on]')].map(g => g.dataset.m)")
    A.check("a tap on a row puts that muscle in the box with the exercises that give its sets, helpers counted half",
            box == "Selected muscle Triceps · 3.5 sets a week Helper, counts half: Bench Press 3 (Push), Overhead Press 2 (Push), Push-up 2 (Legs)"
            and ev("() => document.querySelector('.mm-row[data-m=\"triceps\"]').getAttribute('aria-pressed')") == "true"
            and set(on) == {"triceps"}, (box, on))
    A.touch_tap(page, '[data-screen="muscles"] .mm-row[data-m="triceps"]')
    A.check("a second tap on it gives the box back to the least worked", ev(BOX).startswith("Least worked Hamstrings"), ev(BOX))
    spot = ev("""() => { const g = document.querySelector('[data-screen="muscles"] .mm-m[data-m="chest"]');
        for (const p of g.querySelectorAll('path')) { const b = p.getBBox(), pt = new DOMPoint(b.x + b.width / 2, b.y + b.height / 2);
          if (!p.isPointInFill(pt)) continue; p.scrollIntoView({ block: 'center' }); const s = pt.matrixTransform(p.getScreenCTM());
          const hit = document.elementFromPoint(s.x, s.y); if (hit && g.contains(hit)) return [s.x, s.y]; }
        return null; }""")
    if spot:
        page.touchscreen.tap(*spot)
    box = ev(BOX)
    A.check("a tap on the chest on the body selects it and lists its exercises",
            spot is not None and box == "Selected muscle Chest · 5 sets a week Bench Press 3 (Push), Push-up 2 (Legs)", (spot, box))
    A.touch_tap(page, '[data-screen="muscles"] .mm-close')
    A.check("the box's close button gives it back to the least worked", ev(BOX).startswith("Least worked Hamstrings"), ev(BOX))
    A.check("the muscle map at 360 px: no sideways scroll, every control a 44 px target",
            ev(WIDE) and not ev(TARGETS), ev(TARGETS)[:5])

    # ── "Not counted" opens the exercise's editor at its Muscles field ──
    A.touch_tap(page, '[data-screen="muscles"] [data-act="fix"]')
    page.wait_for_selector('[data-screen="program"] .program-muscles')
    where = ev("""() => [Cali.current(), !!document.querySelector('#program-ed-mys .program-muscles'),
        document.querySelector('#program-ed-mys [data-v="mline"]').textContent]""")
    A.check("\"Not counted: Mystery Move\" opens its program editor with that exercise open at its Muscles field, saying why",
            where[0] == {"name": "program", "args": {"id": "fx", "dayId": "dP", "exId": "mys"}} and where[1]
            and where[2].startswith("No muscle yet"), where)
    A.touch_tap(page, '[data-screen="program"] [data-act="back"]')
    page.wait_for_selector('[data-screen="muscles"] .mm-row')
    A.touch_tap(page, '[data-screen="muscles"] [data-act="back"]')
    page.wait_for_selector('[data-screen="day"] [data-set]')
    A.check("Back returns to the day screen it came from (week 2, Legs)", ev("() => Cali.current()") == {"name": "day", "args": day_args},
            ev("() => Cali.current()"))

    # ── a past week opened from its read-only day screen shows its own copy, after the program changed ──
    ev("() => Cali.change(d => { d.programs[0].days[0].exercises[0].muscles = { biceps: 1 }; })")
    A.touch_tap(page, '[data-screen="day"] [data-slot="dayheader"] .week-btn')
    A.touch_tap(page, '.week-menu [data-week="1"]')
    page.wait_for_function("() => Cali.current().name === 'day' && Cali.current().args.week === 1 && Cali.current().args.readOnly === true")
    open_map(page)
    A.check("week 1 (past, read-only day screen): the map counts week 1's copy (Bench Press {triceps 1}, 2 sets), not the changed program",
            ev("() => Cali.current().args") == {"week": 1} and ev(ROWS) == full({"triceps": (2, 2)})
            and ev("() => document.querySelector('.mm-pill').textContent") == "Week 1", ev(ROWS))
    A.touch_tap(page, '[data-screen="muscles"] [data-act="back"]')
    page.wait_for_function("() => Cali.current().name === 'day' && Cali.current().args.week === 1")

    # ── a pulled week with bad muscles: ignored, never thrown ──
    doc = fx_doc()
    w2 = doc["weeks"][1]["days"]
    w2["dP"]["exercises"]["bp"]["muscles"] = {"chest": 2, "foo": 1, "triceps": 0.5}
    w2["dP"]["exercises"]["ohp"]["muscles"] = "chest"
    w2["dL"]["exercises"]["sq"]["muscles"] = [1, 2]
    took = ev("(d) => { try { Cali.replace(d); return 'ok'; } catch (e) { return e.message; } }", doc)
    ev("() => Cali.go('muscles', { week: 2 })")
    page.wait_for_selector('[data-screen="muscles"] .mm-row')
    got = ev(ROWS)
    bad = {"chest": (1, 2), "triceps": (2, 3.5), "deltoids": (2.5, 3), "quadriceps": (3, 4), "gluteal": (1.5, 2),
           "adductors": (1.5, 2), "hamstring": (0, 1)}
    A.check("a pulled week's bad muscles are ignored, never thrown: unknown keys and values other than 1 or 0.5 dropped, "
            "a value that is not an object falls back to the name's guess", took == "ok" and got == full(bad), (took, got))

    # ── core's check: Cali.change refuses what the Blueprint's schema does not allow ──
    tries = ev("""() => [{ chest: 2 }, { biceps: 1, foo: 1 }, 'chest', [1], { chest: 0.25 }, { chest: 0.5, triceps: 1 }, {}].map(m => {
        try { Cali.change(d => { d.programs[0].days[0].exercises[0].muscles = m; }); return 'saved'; } catch (e) { return e.message; } })""")
    A.check("Cali.change refuses a muscle value other than 1 or 0.5, a key not in Cali.muscles and a value that is not an "
            "object; it saves { chest: 0.5, triceps: 1 } and {}",
            all(re.search(r"muscle", t) for t in tries[:5]) and tries[5:] == ["saved", "saved"], tries)
    A.check("Cali.muscles lists the body paths' sixteen slugs and cannot be changed",
            ev("() => [Cali.muscles, Object.isFrozen(Cali.muscles)]") == [KEYS, True])
    ctx.close()


def scenario_table(browser, url, errors):
    ctx, page = A.phone(browser, errors, "muscles-table", reduced_motion="reduce")
    A.open_day(page, url)
    ev = page.evaluate
    prog = A.default_program()
    rows = [(e["name"], e["kind"], e.get("muscles")) for d in prog["days"] for e in d["exercises"]]
    guessed = ev("(r) => r.map(([n, k]) => CaliMuscles.guess(n, k))", [[n, k] for n, k, _ in rows])
    differ = [(n, m, g) for (n, k, m), g in zip(rows, guessed) if m != g]
    A.check("the built-in program: every reps and time exercise carries muscles equal to the name table's guess; "
            "check rows carry none and guess none", not differ and all((m is None) == (k == "check") for _, k, m in rows), differ)
    names = {"Lat Pulldown": "upper-back", "Squat": "quadriceps", "Hack Squat": "quadriceps", "Deadlift": "hamstring",
             "Romanian Deadlift": "hamstring", "Push-up": "chest", "Bench Press": "chest", "Hip Thrust": "gluteal",
             "Overhead Press": "deltoids", "Upright Row": "deltoids", "Close-grip Bench Press": "triceps", "Bench Dip": "triceps",
             "Hammer Curl": "biceps", "Face Pull": "deltoids", "Lunge": "quadriceps", "Hanging Leg Raise": "abs", "Shrug": "trapezius"}
    got = ev("(n) => Object.fromEntries(n.map(x => [x, CaliMuscles.guess(x, 'reps')]))", list(names))
    wrong = {n: g for n, g in got.items() if not g or g.get(names[n]) != 1 or [k for k, v in g.items() if v == 1] != [names[n]]}
    A.check("the name table guesses each named exercise's main muscle (and only that one as main)", not wrong, wrong)
    A.check("Upright Row guesses shoulders, not upper back", "upper-back" not in (got["Upright Row"] or {}), got["Upright Row"])

    totals = "() => { const c = CaliMuscles.count(1); return [c.total.plan, c.total.done, Object.fromEntries(Object.entries(c.byDay).map(([k, v]) => [k, v.plan]))]; }"
    day = prog["days"][0]
    for e in day["exercises"][:2]:
        A.touch_tap(page, f'[data-screen="day"] [data-set="{day["id"]}:{e["id"]}:0"]')
        ctx.clock.run_for(1000)
    with_muscles = ev(totals)
    bare = A.stored(page)
    for p in bare["programs"]:
        for d in p["days"]:
            for e in d["exercises"]:
                e.pop("muscles", None)
    for w in bare["weeks"]:
        for d in w["days"].values():
            for e in d["exercises"].values():
                e.pop("muscles", None)
    page.evaluate("(t) => localStorage.setItem('cali.v5', t)", json.dumps(bare))
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    stripped = "muscles" not in localStorage_text(page)
    A.check("a document stored without any muscles (built before the field) gives the same totals as the built-in one",
            stripped and ev(totals) == with_muscles and with_muscles[0].get("deltoids") == 14
            and with_muscles[1].get("upper-back") == 1 and with_muscles[1].get("triceps") == 0.5, (with_muscles, ev(totals)))
    ctx.close()


def localStorage_text(page):
    return page.evaluate("() => localStorage.getItem('cali.v5')")


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fn in (("map", scenario_map), ("colour", scenario_colour), ("table", scenario_table)):
            A.guarded(f"muscles scenario {name}", fn, browser, url, errors)
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
