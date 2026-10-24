"""Checks for the day's summary (Task-01, app/summary.js): Finish -> summary (duration, sets done, short sets, what moves
next week from Cali.progress, with the stub and with a real result) -> Resume or Done ('dayDone'); Finish ends the rest.

Run from the repo root: python tests/test_summary.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py with Playwright's clock paused (Cali.now() is moved by the test). The data is
tests/fixtures/v5-document.json (week 1 done, week 2 current); nothing personal is stored."""
import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

FIXTURE = json.loads((A.ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8"))

# A real progression result for the fixture day, standing in for Task-04's rules: Fixture Row loads up 2.5 kg, the
# dip gets one rep more, the hold 5 s more. It records what it was asked with.
REAL = """() => { window.__asked = [];
  Cali.provide('progress', (e, h) => { __asked.push([e.id, e.week, e.dayId, e.sets.length, h.map(x => x.week)]);
    if (e.id === 'f1') return { load: e.load + 2.5, target: 6, reason: 'top of the range' };
    if (e.id === 'f2') return { load: e.load, target: e.target + 1, reason: 'all at target' };
    if (e.id === 'f3') return { load: e.load, target: e.target + 5, reason: 'all at target' };
    return { load: e.load, target: e.target, reason: 'no change' }; }); }"""

SUMMARY = """() => { const q = s => document.querySelector('[data-screen="summary"] ' + s);
  const t = s => { if (!q(s)) return null; const w = document.createTreeWalker(q(s), NodeFilter.SHOW_TEXT), out = [];
    while (w.nextNode()) if (w.currentNode.textContent.trim()) out.push(w.currentNode.textContent.trim());
    return out.join(' '); };
  return { title: t('.summary-title'), eyebrow: t('.eyebrow'), duration: t('.metric'), times: t('.anchor .top span'),
           sets: t('[data-sum="sets"]'), short: t('[data-sum="short"]'), next: t('[data-sum="next"]'), shorts: t('[data-sum="shorts"]'),
           buttons: [...document.querySelectorAll('[data-screen="summary"] .summary-dock button')].map(b => b.textContent) }; }"""


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "summary")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate
        step = lambda ms=1000: ctx.clock.run_for(ms)
        ev("(fx) => Cali.replace(fx)", FIXTURE)
        ev("() => { window.__done = []; Cali.on('dayDone', d => __done.push(d)); }")
        ev("() => Cali.go('day', { week: 2, dayId: 'F' }, { replace: true })")
        page.wait_for_selector('[data-set="F:f1:0"]')

        # a session: Start, four of five sets (Fixture Dip set 2 tapped down to 5 of 7), Finish 38:12 after Start
        A.touch_tap(page, '[data-act="session"]')
        started = ev("() => Cali.iso()")
        for key in ("f1:0", "f2:0", "f2:1", "f3:0"):
            step(7 * 60000)
            A.touch_tap(page, f'[data-set="F:{key}"]')
        for _ in range(2):
            step(1000)
            A.touch_tap(page, '[data-set="F:f2:1"]')
        end = A.NOW + datetime.timedelta(seconds=30) + datetime.timedelta(minutes=38, seconds=12)
        step(int((end - datetime.datetime.fromtimestamp(ev("() => Cali.now()") / 1000, tz=A.DARWIN)).total_seconds() * 1000))
        A.touch_tap(page, '[data-act="session"]')
        page.wait_for_selector('[data-screen="summary"] .summary-title')
        day = ev("() => Cali.week().days.F")
        A.check("Finish stores startedAt and finishedAt (38:12 apart) and opens the summary",
                day["startedAt"] == started and day["finishedAt"] == ev("() => Cali.iso()")
                and ev("() => Cali.current()") == {"name": "summary", "args": {"week": 2, "dayId": "F"}}, (day, ev("() => Cali.current()")))
        s = ev(SUMMARY)
        A.check("the summary shows the day, its date and the duration from startedAt to finishedAt",
                s["title"] == "F Fixture done" and s["eyebrow"] == "Week 2, Monday 26 October" and s["duration"] == "38:12"
                and s["times"] == "07:00 to 07:38", s)
        A.check("sets done counts reps and time sets (4 of 5); short sets 1", s["sets"] == "4 of 5" and s["short"] == "1", s)
        A.check("the short set is listed with its share (Fixture Dip, set 2, 5/7)", s["shorts"] == "Fixture Dip Set 2 5 /7", s["shorts"])
        A.check("with the progress stub nothing moves: 'Same loads and targets next week.'",
                s["next"] == "Same loads and targets next week.", s["next"])
        A.check("Resume and Done at the bottom", s["buttons"] == ["Resume", "Done"], s["buttons"])

        # a real progression result, through Cali.provide('progress', fn)
        ev(REAL)
        ev("() => Cali.go('summary', { week: 2, dayId: 'F' }, { replace: true })")
        page.wait_for_selector('[data-screen="summary"] [data-sum="next"]')
        s = ev(SUMMARY)
        A.check("'moves up' comes from Cali.progress: Fixture Row 20 to 22.5 kg; one rep more: Fixture Dip, Fixture Hold +5 s",
                s["next"] == "Fixture Row 20 to 22.5 kg One rep more: Fixture Dip, Fixture Hold +5 s", s["next"])
        asked = ev("() => __asked")
        A.check("Cali.progress is asked with Cali.weekExercise (week 2, day F) and Cali.history (week 1) for each reps and time row",
                sorted(a[0] for a in asked) == ["f1", "f2", "f3"] and all(a[1] == 2 and a[2] == "F" and a[4] == [1] for a in asked), asked)

        # Resume: the day runs again
        A.touch_tap(page, '[data-act="resume"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        got = ev("() => [Cali.week().days.F.finishedAt || null, document.querySelector('[data-act=\"session\"]').textContent, __done.length]")
        A.check("Resume clears finishedAt and returns to the running day (Finish), no dayDone", got == [None, "Finish", 0], got)
        step(60000)
        A.touch_tap(page, '[data-set="F:f1:1"]')
        got = ev("() => document.querySelector('.workout-row[data-ex=\"f1\"] .tag')?.textContent")
        A.check("a row whose sets are all logged shows Cali.progress' load step ('+2.5 kg next')", got == "+2.5 kg next", got)
        step(1000)

        # Finish ends the running rest and its alerts (the workout is over); Done marks the day and emits dayDone
        ev("""() => { window.__cancels = []; Cali.provide('alert', { alert() {}, schedule() {}, cancel: tag => __cancels.push(tag),
            requestPermission: async () => 'granted' }); }""")
        rest_before = ev("() => { const t = Cali.timers.get('rest'); return t && [t.data.week, t.data.dayId, t.done]; }")
        A.touch_tap(page, '[data-act="session"]')
        page.wait_for_selector('[data-screen="summary"] .summary-dock')
        got = [rest_before, ev("() => Cali.timers.get('rest')"), ev("() => __cancels")]
        A.check("Finish ends the day's running rest and cancels its alerts",
                got == [[2, "F", False], None, ["rest", "rest-headsup"]], got)
        A.touch_tap(page, '[data-act="done"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        got = ev("() => [__done, !!Cali.week().days.F.finishedAt, Cali.week().days.F.finishedAt === Cali.iso(), !!Cali.timers.get('rest'), document.querySelector('[data-act=\"session\"]').textContent]")
        A.check("Done keeps finishedAt, emits dayDone { week, dayId } once and returns to the day, no rest running",
                got == [[{"week": 2, "dayId": "F"}], True, True, False, "Summary"], got)

        # Done on a summary opened for a day without finishedAt stores it first
        ev("() => Cali.change(d => { delete d.weeks[1].days.F.finishedAt; })")
        step(1000)
        ev("() => Cali.go('summary', { dayId: 'F' })")
        page.wait_for_selector('[data-screen="summary"] .summary-dock')
        s = ev(SUMMARY)
        A.check("a day not finished reads 'so far'", s["title"] == "F Fixture, so far", s["title"])
        A.touch_tap(page, '[data-act="done"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        got = ev("() => [__done.length, Cali.week().days.F.finishedAt === Cali.iso()]")
        A.check("Done stores finishedAt before it emits dayDone", got == [2, True], got)

        # the close button changes nothing; a past week's summary has no buttons
        before = ev("() => localStorage.getItem('cali.v5')")
        ev("() => Cali.go('summary', { week: 1, dayId: 'F' })")
        page.wait_for_selector('[data-screen="summary"] .summary-title')
        s = ev(SUMMARY)
        A.check("a past week's summary: its duration (40:00, 18:30 to 19:10 here) and no Resume or Done",
                s["title"] == "F Fixture done" and s["duration"] == "40:00" and s["times"] == "18:30 to 19:10" and s["buttons"] == [], s)
        A.touch_tap(page, '[data-act="close"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        A.check("close returns and stores nothing", ev("() => localStorage.getItem('cali.v5')") == before)
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
