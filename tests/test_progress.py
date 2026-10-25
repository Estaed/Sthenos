"""Cali.progress against Blueprint -> Rules -> Finish week, one group of cases per rule (Task-04).

Run from the repo root: python tests/test_progress.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py. Every case seeds a document whose program is Tarik's built-in A/B/C (app/default-program.js,
his real loads, ranges and steps) with weeks of logged sets made up for the case (Cali.replace), then asks
  Cali.progress(Cali.weekExercise(n, dayId, exId), Cali.history(dayId, exId, n))
for the last week, the call shape the summary and Finish week use. A case names the exercise by its name on day A;
each week is (load, target, sets, day done), sets as reps or seconds with None for a set not logged. The current
week's day counts as done unless the case says it is not (then weekExercise carries dayDone: false). The reason is
'target up', 'load up' or 'deload' when something moves, else 'no change' (the stub's word, read by the summary).
Nothing personal is stored: the logs are invented.

The rules (Blueprint -> Rules -> Finish week):
  every set at target -> target + 1; past repMax -> load + loadStep and target back to repMin; any short set -> no
  change; short at the same load three weeks running -> load -10 % rounded to loadStep (no change at 0 added load);
  a day not done carries over unchanged and does not count toward the stall; bodyweight lifts progress on the added
  load; a time row with every set at target -> target + 5 s, any short set -> no change; check rows copy.
Readings this file fixes where the sentence leaves room (each is a case below, named in the report):
  - "past repMax": the next target would pass repMax, or every set already reached repMax (screen 6: Standing Calf
    Raise 15, 15 at target 12 moves 77.5 to 80 kg).
  - a set not logged in a done day is a short set; an exercise with no set logged at all in a done day was not done
    (a busy machine, a skipped finisher): it carries over unchanged and is skipped when counting the stall, as a day
    not done is, since a deload answers sets that fell short, not an exercise left out.
  - the deload is the sentence as written: load x 0.9 rounded to the nearest loadStep, never below 0; when that
    rounds back to the same load nothing moves ('no change'): BW +2.5 to +12.5 at step 2.5 (2.25 rounds to 2.5, 4.5
    to 5) and 5 kg Side Lateral Raise at step 1 (4.5 rounds to 5). Whether a stalled small load should drop one
    whole step instead (BW +2.5 to BW is -100 %) is Tarik's call, not this file's.
  - a week whose day was not done is skipped when counting the three weeks: it neither counts nor breaks the run.
  - a time row has no deload (its rule is only +5 s or no change).
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
DAY_A = PROGRAM["days"][0]
D = DAY_A["id"]


def ex_id(name):
    return next(e["id"] for e in DAY_A["exercises"] if e["name"].startswith(name))


# Seeds weeks 1..N for one exercise of day A (every other exercise keeps the program's values, no logs), then answers
# Cali.progress for week N. A week is [load, target, sets, done]; done for week N is passed as dayDone (true: omitted).
SEED = """([dayId, exId, weeks, edit]) => {
  const base = structuredClone(Cali.doc());
  const prog = base.programs.find(p => p.id === base.activeProgram);
  const t0 = Date.parse('2026-08-03T00:00:00Z');
  const at = ms => new Date(ms).toISOString();
  base.weeks = weeks.map(([load, target, sets, done], i) => {
    const w = Cali.weekFrom(prog, i + 1);
    const start = t0 + i * 7 * 864e5;
    w.startedAt = at(start);
    if (i < weeks.length - 1) w.finishedAt = at(start + 6 * 864e5);
    const e = w.days[dayId].exercises[exId];
    e.load = load; e.target = target;
    e.sets = sets.map((r, k) => (r === null ? null : { r, at: at(start + 36e5 + k * 18e4) }));
    if (done) { w.days[dayId].startedAt = at(start + 35e5); w.days[dayId].finishedAt = at(start + 72e5); }
    return w;
  });
  Cali.replace(base);
  if (edit) Cali.change(d => { Object.assign(d.programs[0].days[0].exercises.find(x => x.id === exId), edit); }, { why: 'program' });
  const n = weeks.length, done = weeks[n - 1][3];
  const we = Cali.weekExercise(n, dayId, exId);
  return Cali.progress(done ? we : { ...we, dayDone: false }, Cali.history(dayId, exId, n));
}"""


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "progress")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))

        def case(rule, name, weeks, load, target, reason, edit=None):
            got = page.evaluate(SEED, [D, ex_id(name), weeks, edit])
            want = {"load": load, "target": target, "reason": reason}
            got_core = {k: got.get(k) for k in want} if isinstance(got, dict) else got
            A.check(f"{rule}: {name} {json.dumps(weeks)} -> load {load}, target {target} ({reason})", got_core == want, got)

        Y, N = True, False   # the day was done / not done that week

        # ── every set at target -> target + 1 ──
        R = "all sets at target -> target + 1"
        case(R, "Weighted Dip", [[0, 8, [8, 8, 8], Y]], 0, 9, "target up")
        case(R, "Leg Press", [[110, 10, [10, 11, 12], Y]], 110, 11, "target up")              # above target counts as at it
        case(R, "Seated Leg Curl", [[60, 10, [10, 10, 10], Y]], 60, 11, "target up")

        # ── past repMax -> load + loadStep, target back to repMin ──
        R = "past repMax -> load + loadStep, target repMin"
        case(R, "Leg Press", [[110, 12, [12, 12, 12], Y]], 115, 8, "load up")                # 13 would pass 12
        case(R, "Standing Calf Raise", [[77.5, 12, [15, 15], Y]], 80, 12, "load up")         # screen 6: 77.5 to 80 kg
        case(R, "Seated Leg Curl", [[35, 12, [15, 15, 14], Y]], 35, 13, "target up")         # one set below repMax: +1 only
        case(R + " (the week's copied range, not the program's)", "Leg Press", [[110, 10, [10, 10, 10], Y]], 110, 11,
             "target up", edit={"repMax": 10})

        # ── any short set -> no change ──
        R = "a short set -> no change"
        case(R, "Side Lateral Raise", [[5, 12, [12, 9], Y]], 5, 12, "no change")
        case(R + " (a set not logged in a done day is short)", "Seated Leg Curl", [[47.5, 10, [10, 10, None], Y]], 47.5, 10, "no change")
        case(R, "Weighted Pull-up", [[0, 6, [6, 6, 5], Y]], 0, 6, "no change")

        # ── three short weeks at one load -> -10 % rounded to loadStep; none at 0 added load ──
        R = "three short weeks at one load -> load -10 % rounded to loadStep"
        short_lp = [110, 10, [10, 9, 9], Y]
        case(R, "Leg Press", [short_lp] * 3, 100, 10, "deload")                               # 99 -> 100 (step 5)
        case(R, "Seated Leg Curl", [[60, 10, [10, 10, 8], Y]] * 3, 55, 10, "deload")                  # 54 -> 55 (step 2.5)
        case(R, "Seated Leg Curl", [[47.5, 10, [10, 10, 8], Y]] * 3, 42.5, 10, "deload")           # 42.75 -> 42.5
        case(R + " (4.5 rounds back to 5 at step 1: nothing moves)", "Side Lateral Raise", [[5, 12, [12, 10], Y]] * 3, 5, 12, "no change")
        case(R + ": only two short weeks", "Leg Press", [short_lp] * 2, 110, 10, "no change")
        case(R + ": the load changed inside the three", "Leg Press", [[105, 10, [10, 9, 9], Y], short_lp, short_lp], 110, 10, "no change")
        case(R + ": a week at target breaks the run", "Leg Press", [short_lp, [110, 10, [10, 10, 10], Y], [110, 11, [11, 10, 10], Y]],
             110, 11, "no change")
        case(R + ": four short weeks at the deloaded load start a new run", "Leg Press", [short_lp, short_lp, short_lp, [100, 10, [10, 9, 9], Y]],
             100, 10, "no change")
        case(R + ": none at 0 added load", "Weighted Dip", [[0, 8, [8, 7, 6], Y]] * 3, 0, 8, "no change")

        # ── a day not done -> unchanged, and it does not count toward the stall ──
        R = "a day not done -> unchanged"
        case(R, "Weighted Dip", [[0, 8, [8, 8, 8], N]], 0, 8, "no change")
        case(R, "Leg Press", [short_lp, short_lp, [110, 10, [9, 9, None], N]], 110, 10, "no change")
        R = "an exercise with no set logged in a done day -> unchanged"
        case(R, "Leg Press", [[110, 10, [None, None, None], Y]], 110, 10, "no change")
        case(R, "Plank", [[0, 40, [None, None], Y]], 0, 40, "no change")
        R = "an exercise with no set logged does not count toward the stall"
        none_lp = [110, 10, [None, None, None], Y]
        case(R, "Leg Press", [none_lp, none_lp, short_lp], 110, 10, "no change")
        case(R + " (nor breaks the run)", "Leg Press", [short_lp, none_lp, short_lp, short_lp], 100, 10, "deload")
        R = "a day not done does not count toward the stall"
        case(R, "Leg Press", [[110, 10, [9, 9, None], N], short_lp, short_lp], 110, 10, "no change")
        case(R + " (nor breaks the run)", "Leg Press", [short_lp, [110, 10, [None, None, None], N], short_lp, short_lp], 100, 10, "deload")

        # ── bodyweight lifts progress on the added load ──
        R = "bodyweight on the added load"
        case(R, "Weighted Pull-up", [[0, 6, [6, 6, 6], Y]], 2.5, 4, "load up")                # screen 6: BW to +2.5 kg
        case(R, "Weighted Pull-up", [[2.5, 6, [6, 6, 6], Y]], 5, 4, "load up")
        case(R, "Weighted Pull-up", [[20, 5, [5, 4, 4], Y]] * 3, 17.5, 5, "deload")           # BW +20 -> 18 -> 17.5
        case(R, "Weighted Pull-up", [[15, 5, [5, 4, 4], Y]] * 3, 12.5, 5, "deload")           # BW +15 -> 13.5 -> 12.5
        case(R + ": -10 % of BW +5 is 4.5, which rounds back to +5 at step 2.5", "Weighted Pull-up",
             [[5, 6, [6, 5, 5], Y]] * 3, 5, 6, "no change")
        case(R + ": -10 % of BW +2.5 is 2.25, which rounds back to +2.5 at step 2.5", "Weighted Dip",
             [[2.5, 8, [8, 7, 7], Y]] * 3, 2.5, 8, "no change")
        case(R, "Weighted Dip", [[2.5, 8, [8, 8, 8], Y]], 2.5, 9, "target up")

        # ── a time row: every set at target -> target + 5 s; any short set -> no change ──
        R = "time row"
        case(R + " all at target -> +5 s (Plank, screen 6)", "Plank", [[0, 40, [40, 40], Y]], 0, 45, "target up")
        case(R + " above target counts as at it", "Plank", [[0, 40, [45, 40], Y]], 0, 45, "target up")
        case(R + " short -> no change", "Plank", [[0, 40, [40, 35], Y]], 0, 40, "no change")
        case(R + " short three weeks -> still no change", "Plank", [[0, 40, [40, 35], Y]] * 3, 0, 40, "no change")
        case(R + " with added load short three weeks -> no deload (a 20 kg plate stays)", "Plank",
             [[20, 40, [40, 35], Y]] * 3, 20, 40, "no change")
        case(R + " not done -> unchanged", "Plank", [[0, 40, [40, 40], N]], 0, 40, "no change")

        # ── check rows copy ──
        R = "check rows copy"
        case(R, "Hamstring Stretch", [[0, 1, [1], Y]], 0, 1, "no change")
        case(R, "Hamstring Stretch", [[0, 1, [None], Y]], 0, 1, "no change")

        # the answer is plain data, never a frozen piece of the document
        got = page.evaluate(f"() => {{ const r = Cali.progress(Cali.weekExercise(null, {json.dumps(D)}, {json.dumps(ex_id('Leg Press'))}), []);"
                            " return [Object.isFrozen(r), Object.keys(r).sort()]; }")
        A.check("Cali.progress answers a plain { load, target, reason }", got == [False, ["load", "reason", "target"]], got)
        ctx.close()
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
