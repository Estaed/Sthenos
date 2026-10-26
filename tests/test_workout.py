"""Checks for the workout day (Task-01, app/workout.js): touch logging, the cell states, Undo, the pair order, the rest
timer and its alerts, Start / Finish, Wake Lock, last week's values, a read-only past week and the timed rows.

Run from the repo root: python tests/test_workout.py   (exit 0 = no FAIL). Reuses the gate's server, phone and gestures
from tests/acceptance.py with Playwright's clock paused, so every time below is moved by the test (Cali.now()). The data
is the built-in program and tests/fixtures/v5-document.json; nothing personal is stored. Cali.alert and the Wake Lock
are replaced by recorders (the real ones are Task-02's and the phone's)."""
import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

FIXTURE = json.loads((A.ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8"))

# Wake Lock and page visibility under the test's hand: requests and releases are counted; hiding the page releases
# the lock, as the phone does.
WAKE = """(() => {
  const log = window.__wake = { requests: 0, releases: 0, held: 0 };
  class Sentinel extends EventTarget {
    constructor() { super(); this.released = false; log.held++; }
    release() { if (!this.released) { this.released = true; log.releases++; log.held--; this.dispatchEvent(new Event('release')); } return Promise.resolve(); }
  }
  const live = new Set();
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: {
    request(type) { log.requests++; const s = new Sentinel(); live.add(s); s.addEventListener('release', () => live.delete(s)); return Promise.resolve(s); } } });
  let shown = 'visible';
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => shown });
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => shown !== 'visible' });
  window.__show = on => { shown = on ? 'visible' : 'hidden'; if (!on) for (const s of [...live]) s.release();
    document.dispatchEvent(new Event('visibilitychange')); };
})();"""

# Cali.alert as a recorder: every call lands in window.__alerts as [what, kind or tag, endAt - Cali.now()]
ALERTS = """() => { window.__alerts = [];
  Cali.provide('alert', { alert: k => __alerts.push(['alert', k]),
    schedule: (k, at, tag) => __alerts.push(['schedule', k, tag, at - Cali.now()]),
    cancel: tag => __alerts.push(['cancel', tag]), requestPermission: async () => 'granted' }); }"""

# the score bug's rest column as shown: [class, label, 'of …', the big number, the bar's width]
BUG_REST = """() => { const r = document.querySelector('[data-screen="day"] .workout-score .rest');
  return [r.className, r.querySelector('[data-lab="rest"]').textContent, r.querySelector('[data-lab="of"]').textContent,
          r.querySelector('[data-big="rest"]').textContent, document.querySelector('[data-screen="day"] .workout-bug .bar i').style.width]; }"""


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "workout", reduced_motion="reduce")   # no transitions: styles read settled
        ctx.add_init_script(WAKE)
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate
        ev(ALERTS)
        ev("() => Cali.settings.set('alternatePairs', true)")   # this file checks the pair alternation
        ids = ev("""() => { const d = Cali.program().days[0]; const by = n => d.exercises.find(e => e.name.startsWith(n)).id;
            return { day: d.id, dayB: Cali.program().days[1].id, pull: by('Weighted Pull-up'), dip: by('Weighted Dip'),
                     lp: by('Leg Press'), lat: by('Side Lateral Raise'), curl: by('Seated Leg Curl'), plank: by('Plank'),
                     walk: by('Incline Walk'), stretch: by('Mobility') }; }""")
        D = ids["day"]
        cell = lambda ex, i: f'[data-screen="day"] [data-set="{D}:{ids[ex]}:{i}"]'
        got_set = lambda ex, i: ev(f"() => Cali.week().days[{json.dumps(D)}].exercises[{json.dumps(ids[ex])}].sets[{i}]")
        r = lambda ex, i: (got_set(ex, i) or {}).get("r")
        now_cell = lambda: ev("() => { const el = document.querySelector('[data-screen=\"day\"] .cell.now, [data-screen=\"day\"] .workout-tile.now'); return el && el.dataset.cell; }")
        step = lambda ms=1000: ctx.clock.run_for(ms)

        # ── first open, no earlier week: last week reads none, no trend line ──
        got = ev("""() => [...document.querySelectorAll('[data-screen="day"] .workout-row[data-ex]')].map(r =>
            [r.querySelector('.workout-last').textContent, r.querySelectorAll('.workout-spark circle').length])""")
        A.check("no earlier week: every row's last week reads – and has no trend line", got and all(g == ["–", 0] for g in got), got)
        got = ev("() => [document.querySelector('[data-act=\"session\"]').textContent, document.querySelector('.workout-clock').hidden, Cali.week().days[Object.keys(Cali.week().days)[0]].startedAt || null]")
        A.check("before Start: the app bar offers Start, no session clock, no startedAt", got == ["Start", True, None], got)

        # ── whole day A on the phone without scrolling ──
        got = ev("""() => { const cards = [...document.querySelectorAll('.workout-card')]; const sheet = document.querySelector('.workout-sheet').getBoundingClientRect();
            return [document.scrollingElement.scrollHeight, innerHeight, Math.round(cards[cards.length - 1].getBoundingClientRect().bottom), Math.round(sheet.top),
                    document.scrollingElement.scrollWidth <= innerWidth]; }""")
        A.check("at 360 x 740 the whole of day A shows without scrolling (last card ends above the docked sheet)",
                got[0] <= got[1] and got[2] <= got[3] and got[4], got)

        # ── touch logging ──
        A.touch_tap(page, cell("pull", 0))
        A.check("one tap logs the target (6)", r("pull", 0) == 6, got_set("pull", 0))
        step()
        A.touch_tap(page, cell("pull", 0))
        A.check("two taps log one short (5)", r("pull", 0) == 5, got_set("pull", 0))
        step()
        A.touch_hold(page, ctx, cell("pull", 0))
        A.check("a hold adds one (6)", r("pull", 0) == 6, got_set("pull", 0))
        step()
        A.touch_tap(page, cell("pull", 0))
        A.check("tap (5)", r("pull", 0) == 5, got_set("pull", 0))
        step(100)
        A.touch_tap(page, cell("pull", 0))
        A.check("a second touch 100 ms after the first is a bounce: ignored (still 5)", r("pull", 0) == 5, got_set("pull", 0))
        step(49)
        A.touch_tap(page, cell("pull", 0))
        A.check("still a bounce at 149 ms after the first touch (still 5)", r("pull", 0) == 5, got_set("pull", 0))
        step(1)
        A.touch_tap(page, cell("pull", 0))
        A.check("a touch 150 ms after the first counts (4)", r("pull", 0) == 4, got_set("pull", 0))
        step()
        A.touch_hold(page, ctx, cell("pull", 0))
        step()
        A.touch_hold(page, ctx, cell("pull", 0))
        A.check("holds go on adding (6)", r("pull", 0) == 6, got_set("pull", 0))
        step()

        # a real long press, on the wall clock, so the browser's own long-press gesture runs
        ev("""() => { window.__menus = []; window.addEventListener('contextmenu', e => __menus.push(e.defaultPrevented));
            window.__selects = 0; document.addEventListener('selectstart', e => { if (!e.defaultPrevented) __selects++; }); }""")
        before = r("dip", 0)
        ctx.clock.resume()
        page.locator(cell("dip", 0)).scroll_into_view_if_needed()
        x, y = A.center(page, cell("dip", 0))
        cdp = ctx.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        page.wait_for_timeout(1500)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        cdp.detach()
        page.wait_for_timeout(300)
        ctx.clock.pause_at(datetime.datetime.fromtimestamp(ev("() => Date.now()") / 1000 + 5, tz=A.DARWIN))
        synthetic = ev(f"() => document.querySelector('{cell('dip', 0)}').dispatchEvent(new MouseEvent('contextmenu', {{ bubbles: true, cancelable: true }}))")
        menus = ev("() => __menus")
        A.check("a held cell opens no context menu (every contextmenu on it is cancelled)", all(menus) and synthetic is False, (menus, synthetic))
        A.check("a held cell selects no text", ev("() => getSelection().toString()") == "" and ev("() => __selects") == 0,
                (ev("() => getSelection().toString()"), ev("() => __selects")))
        A.check("the long press is one hold: target + 1, no tap after it", before is None and r("dip", 0) == 9, (before, got_set("dip", 0)))
        ev(f"() => Cali.log({json.dumps(D)}, {json.dumps(ids['dip'])}, 0, null)")
        step()

        # ── cell states ──
        ev(f"() => {{ Cali.log({json.dumps(D)}, {json.dumps(ids['pull'])}, 0, 6); Cali.log({json.dumps(D)}, {json.dumps(ids['dip'])}, 0, 6); }}")
        got = ev(f"""() => ['{cell('pull', 0)}', '{cell('dip', 0)}', '{cell('pull', 1)}', '{cell('dip', 1)}'].map(s => {{ const el = document.querySelector(s);
            return [el.className.split(' ').filter(c => ['hit', 'short', 'now', 'todo'].includes(c)).join(), el.style.getPropertyValue('--p'), el.textContent]; }})""")
        A.check("done = orange tint (hit), short = the partial ring at reps/target (6 of 8 = 75 %), current = the ink ring",
                got == [["hit", "", "6"], ["short", "75%", "6/8"], ["now", "", "6"], ["todo", "", "8"]], got)
        styles = ev(f"""() => ['{cell('pull', 0)}', '{cell('dip', 0)}', '{cell('pull', 1)}'].map(s => {{ const c = getComputedStyle(document.querySelector(s));
            return [c.backgroundColor, c.backgroundImage.includes('conic-gradient'), c.boxShadow]; }})""")
        A.check("the states are drawn: tint fill, conic ring, inset ink ring", styles[0][0] not in ("rgba(0, 0, 0, 0)", "transparent")
                and styles[1][1] and "inset" in styles[2][2], styles)
        step()
        A.touch_tap(page, cell("dip", 0))
        A.check("a logged set stays editable by the same taps (6 -> 5)", r("dip", 0) == 5, got_set("dip", 0))
        badges = ev("""() => [...document.querySelectorAll('[data-screen="day"] [data-hint]')].map(c => [c.dataset.cell,
            getComputedStyle(c, '::after').content, c.classList.contains('workout-edit'), c.getAttribute('aria-label')])""")
        A.check("the short set just tapped down carries the '−1' badge and the edit edge (screen 8), on that cell only",
                badges == [[f"{ids['dip']}:0", '"−1"', True, "Weighted Dip, set 1: 5 of 8, short; tap again for 4"]], badges)
        step()

        # ── Undo ──
        prev = got_set("dip", 0)
        step()
        A.touch_tap(page, cell("dip", 0))
        snack = ev("() => { const s = document.querySelector('.workout-snack'); return [s.hidden, s.textContent]; }")
        A.check("after a log the Undo snackbar shows what was logged", snack[0] is False and "set 1" in snack[1] and "4 of 8" in snack[1], snack)
        gap = ev("""() => { const sh = document.querySelector('.workout-sheet');
            return Math.round(sh.getBoundingClientRect().top + sh.clientTop - document.querySelector('.workout-snack').getBoundingClientRect().bottom); }""")
        A.check("with no set he taps under it, Undo floats 8 px above the docked sheet (screen 8)", gap == 8, gap)
        step(7999)
        A.check("Undo stays for 8 s", ev("() => document.querySelector('.workout-snack').hidden") is False)
        A.touch_tap(page, ".workout-snack [data-act=\"undo\"]")
        A.check("Undo restores the exact previous set (value and time)", got_set("dip", 0) == prev, (got_set("dip", 0), prev))
        A.check("Undo hides the snackbar", ev("() => document.querySelector('.workout-snack').hidden") is True)
        step()
        A.touch_tap(page, cell("pull", 1))
        A.check("a tap that logs the target shows no badge (screen 7)", ev("() => document.querySelectorAll('[data-hint]').length") == 0)
        step(5000)
        A.touch_tap(page, cell("dip", 1))
        snack = ev("() => [document.querySelector('.workout-snack').hidden, document.querySelector('.workout-snack').textContent]")
        A.check("the next log replaces the snackbar with its own", snack[0] is False and "Dip" in snack[1] and "set 2" in snack[1], snack)
        step(8000)
        A.check("Undo leaves 8 s after the log", ev("() => document.querySelector('.workout-snack').hidden") is True)
        ev(f"() => Cali.log({json.dumps(D)}, {json.dumps(ids['dip'])}, 1, 7)")
        shown = ev("() => document.querySelectorAll('[data-hint]').length")
        step(8000)
        A.check("the badge leaves with the Undo snackbar, 8 s after the log",
                shown == 1 and ev("() => document.querySelectorAll('[data-hint]').length") == 0, shown)

        # ── pair order, rest timer, alerts ──
        ev("() => { __alerts.length = 0; }")
        seen = []
        for ex, i in (("lp", 0), ("lat", 0), ("lp", 1), ("lat", 1), ("lp", 2), ("lat", 2)):
            A.touch_tap(page, cell(ex, i))
            t = ev("() => { const t = Cali.timers.get('rest'); return t && [t.duration, t.remaining, t.data.rest]; }")
            seen.append([now_cell(), t])
            step(1000)
        want_now = [f"{ids['lat']}:0", f"{ids['lp']}:1", f"{ids['lat']}:1", f"{ids['lp']}:2", f"{ids['lat']}:2", f"{ids['curl']}:0"]
        A.check("the next set follows the pair (Leg Press 1, Raise 1, Leg Press 2, Raise 2, Leg Press 3, Raise 3, then Seated Leg Curl 1)",
                [s[0] for s in seen] == want_now, [s[0] for s in seen])
        A.check("rest starts from the settings: pair rest 90 s inside the pair, 120 s after the pair's last set",
                [s[1] for s in seen] == [[90000, 90000, "pair"]] * 5 + [[120000, 120000, "exercise"]], [s[1] for s in seen])
        alerts = ev("() => __alerts")
        first = alerts[:4]
        A.check("each new set cancels the rest before and schedules rest at its end plus a heads-up 10 s before",
                first == [["cancel", "rest"], ["cancel", "rest-headsup"], ["schedule", "rest", "rest", 90000], ["schedule", "headsup", "rest-headsup", 80000]]
                and alerts[-2:] == [["schedule", "rest", "rest", 120000], ["schedule", "headsup", "rest-headsup", 110000]]
                and len(alerts) == 24, alerts)
        step(29500)
        got = ev("() => [document.querySelector('[data-big=\"rest\"]').textContent, document.querySelector('[data-lab=\"rest\"]').textContent, document.querySelector('[data-lab=\"of\"]').textContent]")
        A.check("the score bug shows the rest from Cali.timers: 1:30 left of 2:00 after 30.5 s", got == ["1:30", "Rest", "of 2:00"], got)
        bar = ev("() => parseFloat(document.querySelector('.workout-bug .bar i').style.width)")
        A.check("the rest bar drains with the time left (screen 1: 1:12 of 1:30 fills 80 %): 89.5 s of 2:00 fills 74.6 % "
                "(within one 250 ms tick)", abs(bar - 74.6) <= 0.3, bar)
        page.reload()
        page.wait_for_selector(cell("curl", 0))
        ev(ALERTS)
        step(15000)
        got = ev("() => [document.querySelector('[data-big=\"rest\"]').textContent, Cali.timers.get('rest').remaining]")
        A.check("the rest is computed from its start timestamp: right after a reload (1:15 left)", got == ["1:15", 74500], got)
        A.touch_tap(page, cell("lp", 2))
        step()
        A.touch_tap(page, cell("lp", 2))
        got = [ev("() => __alerts"), ev("() => Cali.timers.get('rest').remaining")]
        A.check("an edit of a logged set (tap again) keeps the running rest and schedules nothing", got == [[], 73500], got)
        step()
        ev("() => Cali.settings.set('restPair', 60)")
        ev("() => Cali.settings.set('headsUp', 0)")
        A.touch_tap(page, cell("curl", 0))
        got = [ev("() => Cali.timers.get('rest').duration"), ev("() => __alerts")]
        A.check("rest lengths and the heads-up come from Cali.settings at the log (pair rest set to 60 s, heads-up off)",
                got == [60000, [["cancel", "rest"], ["cancel", "rest-headsup"], ["schedule", "rest", "rest", 60000]]], got)
        step()
        ev("() => { Cali.settings.set('restAfterLog', false); __alerts.length = 0; }")
        A.touch_tap(page, f'[data-set="{D}:{ev("() => Cali.program().days[0].exercises[5].id")}:0"]')
        got = [ev("() => Cali.timers.get('rest')"), ev("() => __alerts")]
        A.check("with 'start rest after a log' off a log starts no rest and cancels the running one",
                got == [None, [["cancel", "rest"], ["cancel", "rest-headsup"]]], got)
        ev("() => Cali.settings.set('restAfterLog', true)")
        step()

        # ── timed rows ──
        ev("() => Cali.route('timer', { render(root, args) { root.innerHTML = '<p data-probe>' + JSON.stringify(args) + '</p>'; } })")
        # every set of day A but the last Plank set logged; that one by touch makes the stretch tile the current set while
        # Undo shows: neither the tile nor the Plank set may sit under the snackbar, and the tile takes a tap at once
        last = ev(f"""() => {{ const D = {json.dumps(D)}, list = Cali.dayExercises(null, D), plank = list.find(e => e.id === {json.dumps(ids['plank'])});
            for (const ex of list) if (ex.kind !== 'check') ex.sets.forEach((s, i) => {{ if (!s && !(ex === plank && i === ex.sets.length - 1)) Cali.log(D, ex.id, i, ex.target); }});
            return plank.sets.length - 1; }}""")
        step()
        A.touch_tap(page, cell("plank", last))
        hit = """(sel) => { const b = document.querySelector(sel).getBoundingClientRect(); const el = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
            return el.closest('.workout-snack') ? 'snackbar' : el.closest('[data-set]') ? el.closest('[data-set]').dataset.cell : el.className; }"""
        got = [ev("() => document.querySelector('.workout-snack').hidden"), now_cell(),
               ev(hit, f'[data-screen="day"] [data-set="{D}:{ids["stretch"]}:0"]'), ev(hit, cell("plank", last))]
        A.check("Undo shown after the last Plank set rises clear of the stretch tile (now the current set) and of that Plank set",
                got == [False, f"{ids['stretch']}:0", f"{ids['stretch']}:0", f"{ids['plank']}:{last}"], got)
        step()
        A.touch_tap(page, f'[data-screen="day"] [data-set="{D}:{ids["stretch"]}:0"]')
        page.wait_for_selector('[data-screen="timer"] [data-probe]')
        got = [ev("() => Cali.current()"), r("stretch", 0)]
        A.check("a timed row (the 7 min mobility tile) is marked done and opens Cali.go('timer', { countdown: 420 })",
                got == [{"name": "timer", "args": {"countdown": 420}}, 420], got)
        ev("() => Cali.back()")
        page.wait_for_selector(cell("pull", 0))
        step()
        # a hold on a timed tile marks it done as well, and its countdown opens once the finger lifts
        x, y = A.center(page, f'[data-screen="day"] [data-set="{D}:{ids["walk"]}:0"]')
        cdp = ctx.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        step(800)
        held = [ev("() => Cali.current().name"), r("walk", 0)]
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        cdp.detach()
        A.poll(page, "() => Cali.current().name === 'timer'", timeout=3.0)
        got = [held, ev("() => Cali.current()")]
        A.check("a hold on a timed row (the 22 min walk) marks it done too and opens Cali.go('timer', { countdown: 1320 }) "
                "when the finger lifts", got == [["day", 1380], {"name": "timer", "args": {"countdown": 1320}}], got)
        ev("() => { if (Cali.current().name === 'timer') Cali.back(); }")
        page.wait_for_selector(cell("pull", 0))
        step()
        # the walk ran 21 min: a tap on the logged tile takes a minute off and shows it, with no second countdown
        walk_tile = f'[data-screen="day"] [data-set="{D}:{ids["walk"]}:0"]'
        A.touch_tap(page, walk_tile)
        step()
        A.touch_tap(page, walk_tile)
        step()
        got = [r("walk", 0), ev("() => Cali.current().name"), ev(f"() => document.querySelector('{walk_tile} .val').textContent")]
        A.check("a tap on a logged timed tile takes a minute off (23 → 21 min after two taps), shows it, opens no countdown",
                got == [1260, "day", "21 min"], got)

        # ── session: Start, the clock, Wake Lock, Finish ──
        dayB = ids["dayB"]
        ev(f"() => Cali.change(d => {{ d.weeks[0].days[{json.dumps(D)}].finishedAt = Cali.iso(); }})")
        page.wait_for_function("() => __wake.held === 0")
        ev(f"() => Cali.go('day', {{ dayId: {json.dumps(dayB)} }}, {{ replace: true }})")
        page.wait_for_selector(f'[data-set^="{dayB}:"]')
        wake0 = ev("() => __wake.requests")
        A.touch_tap(page, '[data-act="session"]')
        started = ev(f"() => Cali.week().days[{json.dumps(dayB)}].startedAt")
        A.check("Start stores the day's startedAt from Cali.now()", started == ev("() => Cali.iso()"), (started, ev("() => Cali.iso()")))
        step(65000)
        got = ev("() => [document.querySelector('.workout-clock').textContent, document.querySelector('[data-act=\"session\"]').textContent]")
        A.check("the session clock counts from startedAt (1:05) and Finish replaces Start", got == ["1:05", "Finish"], got)
        page.wait_for_function("() => __wake.held === 1")
        got = ev("() => [__wake.requests, __wake.held]")
        A.check("Start takes the Wake Lock; it is held while the workout runs", got == [wake0 + 1, 1], (wake0, got))
        ev("() => __show(false)")
        held_hidden = ev("() => __wake.held")
        ev("() => __show(true)")
        page.wait_for_function("() => __wake.held === 1")
        got = ev("() => [__wake.requests, __wake.held]")
        A.check("hidden, the phone drops the lock; visible again, it is taken again", held_hidden == 0 and got[1] == 1 and got[0] >= 2, (held_hidden, got))
        ev("() => Cali.settings.set('keepAwake', false)")
        page.wait_for_function("() => __wake.held === 0")
        ev("() => Cali.settings.set('keepAwake', true)")
        page.wait_for_function("() => __wake.held === 1")
        A.check("the keep-awake setting off releases the lock, on takes it again", True)
        step(60000)
        # a running rest shows only on its own day; another day shows the rest its next log will start
        ev("() => { __alerts.length = 0; }")
        pull_b = ev("() => Cali.program().days[1].exercises[1].id")
        A.touch_tap(page, f'[data-screen="day"] [data-set="{dayB}:{pull_b}:0"]')
        rest_b = ev("() => { const t = Cali.timers.get('rest'); return t && [t.data.dayId, t.duration]; }")
        dayC = ev("() => Cali.program().days[2].id")
        ev(f"() => Cali.go('day', {{ dayId: {json.dumps(dayC)} }}, {{ replace: true }})")
        page.wait_for_selector(f'[data-set^="{dayC}:"]')
        step(300)
        other = ev(BUG_REST)
        ev(f"() => Cali.go('day', {{ dayId: {json.dumps(dayB)} }}, {{ replace: true }})")
        page.wait_for_selector(f'[data-set^="{dayB}:"]')
        step(300)
        own = ev(BUG_REST)
        A.check("day B's pair rest (1:00) runs in B's bug only; day C, not started, shows the pair rest its first log will "
                "start (1:00, not running, empty bar)", rest_b == [dayB, 60000] and other == ["rest", "Pair rest", "", "1:00", "0%"]
                and own[:3] == ["rest on", "Pair rest", "of 1:00"], (rest_b, other, own))
        step()
        A.touch_tap(page, '[data-act="session"]')
        page.wait_for_function("() => Cali.current().name === 'summary'")
        day = ev(f"() => Cali.week().days[{json.dumps(dayB)}]")
        A.check("Finish stores finishedAt and opens the summary { week, dayId }",
                day.get("finishedAt") == ev("() => Cali.iso()") and ev("() => Cali.current()") == {"name": "summary", "args": {"week": 1, "dayId": dayB}},
                (day.get("finishedAt"), ev("() => Cali.current()")))
        got = [ev("() => Cali.timers.get('rest')"), ev("() => __alerts")[-2:]]
        A.check("Finish ends the day's running rest and cancels its alerts", got == [None, [["cancel", "rest"], ["cancel", "rest-headsup"]]], got)
        page.wait_for_function("() => __wake.held === 0")
        A.check("with no workout running the lock is released", ev("() => __wake.held") == 0)
        A.touch_tap(page, '[data-screen="summary"] [data-act="close"]')
        page.wait_for_function("() => Cali.current().name === 'day'")
        step(300)
        got = [ev("() => Cali.current().args.dayId"), ev(BUG_REST), ev("() => Cali.timers.get('rest')")]
        A.check("the summary's X back to the finished day B: no rest runs or shows (–)",
                got == [dayB, ["rest", "Rest", "", "–", "0%"], None], got)

        # a first log on a day never started starts it
        dayC = ev("() => Cali.program().days[2].id")
        ev(f"() => Cali.go('day', {{ dayId: {json.dumps(dayC)} }}, {{ replace: true }})")
        first = ev(f"() => Cali.program().days[2].exercises[0].id")
        page.wait_for_selector(f'[data-set="{dayC}:{first}:0"]')
        A.touch_tap(page, f'[data-set="{dayC}:{first}:0"]')
        got = ev(f"() => [Cali.week().days[{json.dumps(dayC)}].startedAt, Cali.iso(), Cali.timers.get('rest') && Cali.timers.get('rest').data.dayId]")
        A.check("the first log of a day not started starts it (startedAt) and its rest", got[0] == got[1] and got[2] == dayC, got)

        # a set tapped down to 0 is not done: its rest stops; a hold back up starts one; clearing the day's only set
        # takes the day back to not started (how a day is reset)
        c0 = f'[data-set="{dayC}:{first}:0"]'
        setC = lambda: ev(f"() => Cali.week().days[{json.dumps(dayC)}].exercises[{json.dumps(first)}].sets[0]")
        while setC()["r"] > 0:
            step(200)
            A.touch_tap(page, c0)
        got = [setC()["r"], ev("() => Cali.timers.get('rest')")]
        A.check("tapping the set its rest belongs to down to 0 stops that rest", got == [0, None], got)
        step(200)
        A.touch_hold(page, ctx, c0)
        got = [setC()["r"], ev("() => Cali.timers.get('rest') && Cali.timers.get('rest').data.dayId")]
        A.check("a hold back up from 0 (to 1) starts a new rest", got == [1, dayC], got)
        for _ in range(2):
            step(200)
            A.touch_tap(page, c0)
        got = ev(f"() => [Cali.week().days[{json.dumps(dayC)}].startedAt || null, Cali.timers.get('rest'), document.querySelector('[data-act=\"session\"]').textContent]")
        A.check("clearing the day's last logged set resets the day: no startedAt, no rest, Start again", got == [None, None, "Start"], got)

        # ── last week present; a past week read-only ──
        ev("(fx) => Cali.replace(fx)", FIXTURE)
        ev("() => Cali.go('day', { week: 2, dayId: 'F' }, { replace: true })")
        page.wait_for_selector('[data-set="F:f1:0"]')
        got = ev("""() => ['f1', 'f2', 'f3'].map(id => { const r = document.querySelector(`.workout-row[data-ex="${id}"]`);
            return [r.querySelector('.workout-last').textContent, r.querySelectorAll('.workout-spark circle').length > 0]; })""")
        A.check("last week present: 8 7, 6 6, 30s beside each row, with a trend line", got == [["8 7", True], ["6 6", True], ["30s", True]], got)
        before = ev("() => localStorage.getItem('cali.v5')")
        ev("() => Cali.go('day', { week: 1, dayId: 'F', readOnly: true })")
        page.wait_for_selector('[data-screen="day"] [data-cell="f1:1"]')
        got = ev("""() => [document.querySelectorAll('[data-screen="day"] [data-set]').length, !!document.querySelector('.workout-sheet'),
            ['f1:0', 'f1:1', 'f3:0'].map(c => [document.querySelector(`[data-cell="${c}"]`).textContent, document.querySelector(`[data-cell="${c}"]`).className.includes('short')]),
            document.querySelector('[data-act="session"]').textContent]""")
        A.check("Cali.go('day', { week: 1, readOnly: true }) shows the past week's sets (8, 7/8 short, 30s) with no tap targets",
                got == [0, False, [["8", False], ["7/8", True], ["30s", False]], "Summary"], got)
        page.touchscreen.tap(*A.center(page, '[data-cell="f1:1"]'))
        step()
        A.touch_hold(page, ctx, '[data-cell="f1:0"]')
        step()
        A.check("taps and holds on a read-only day change nothing", ev("() => localStorage.getItem('cali.v5')") == before)

        # ── what the score bug and the cells show fits them; the idle rest column shows only a rest that will run ──
        # A fresh phone walks days A, B and C of the built-in program set by set in doing order; before each log the bug
        # is read with the rest of the set before running and again with it stopped.
        ctx, page = A.phone(browser, errors, "workout-fit", reduced_motion="reduce")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate
        step = lambda ms=1000: ctx.clock.run_for(ms)
        overflow = """() => { const out = [], score = document.querySelector('[data-screen="day"] .workout-score');
            if (score.scrollWidth > score.clientWidth) out.push(['score', score.textContent, score.scrollWidth, score.clientWidth]);
            for (const big of score.querySelectorAll('.big')) if (big.scrollWidth > big.clientWidth)
              out.push([document.querySelector('.workout-bug-name').textContent.slice(0, 24), big.textContent, big.scrollWidth, big.clientWidth]);
            for (const c of document.querySelectorAll('[data-screen="day"] .workout-cells .cell:not(.void)'))
              if (c.firstElementChild.getBoundingClientRect().width > c.clientWidth + 0.5) out.push([c.getAttribute('aria-label'), c.textContent, c.clientWidth]);
            return out; }"""
        spill, rest_wrong = [], []
        for d in range(3):
            day_id = ev(f"() => Cali.program().days[{d}].id")
            ev(f"() => Cali.go('day', {{ dayId: {json.dumps(day_id)} }}, {{ replace: true }})")
            page.wait_for_selector(f'[data-set^="{day_id}:"]')
            ev(f"() => Cali.change(d => {{ d.weeks[0].days[{json.dumps(day_id)}].startedAt = Cali.iso(); }})")
            while True:
                step(300)
                spill += ev(overflow)
                ev("() => { if (Cali.timers.get('rest')) Cali.timers.stop('rest'); }")
                step(300)
                spill += ev(overflow)
                nxt = ev(f"""() => {{ const n = Cali.nextSet({json.dumps(day_id)}); if (!n) return null;
                    const ex = Cali.weekExercise(null, {json.dumps(day_id)}, n.exId); return [n.exId, n.i, ex.kind, ex.kind === 'check' ? 1 : ex.target, ex.name.slice(0, 24)]; }}""")
                rest = ev("() => [document.querySelector('[data-lab=\"rest\"]').textContent, document.querySelector('[data-big=\"rest\"]').textContent]")
                if (nxt is None or nxt[2] == "check") != (rest[1] == "–"):
                    rest_wrong.append([nxt and nxt[4], rest])
                if nxt is None:
                    break
                ev(f"() => Cali.log({json.dumps(day_id)}, {json.dumps(nxt[0])}, {nxt[1]}, {nxt[3]})")
        A.check("every set of days A, B and C in turn as the current set: no number in the score bug runs past its column",
                spill == [], spill)
        A.check("with no rest running the bug's rest reads – when none will follow the set in hand (a stretch or walk tile, "
                "every set logged), else the rest that will run", rest_wrong == [], rest_wrong)
        ev("() => Cali.go('day', { dayId: Cali.program().days[0].id }, { replace: true })")
        page.wait_for_selector('[data-screen="day"] .workout-cells .cell.hit')
        ev("""() => { const D = Cali.program().days[0].id; const list = Cali.dayExercises(null, D); const plank = list.find(e => e.kind === 'time');
            for (const ex of list) if (ex.kind !== 'check') ex.sets.forEach((s, i) =>
              Cali.log(D, ex.id, i, i === 0 ? ex.target - (ex.kind === 'time' ? 5 : 1) : ex.kind === 'time' ? 120 : ex.target + 1));
            Cali.change(d => { d.weeks[0].days[D].exercises[plank.id].target = 100; });
            Cali.log(D, plank.id, 0, 95); }""")
        step(300)
        spill = ev(overflow)
        got = ev("""() => [...document.querySelectorAll('[data-screen="day"] .workout-cells .cell.short')].map(c =>
            [c.textContent, c.classList.contains('workout-fit'), c.style.getPropertyValue('--p')])""")
        A.check("two-digit short sets (11/12, 35/40), a 120 s hold and a 95 of 100 s hold fit their cells; the ring still "
                "shows reps/target", spill == [] and ["11/12", True, "92%"] in got and ["95", True, "95%"] in got
                and ["9/10", False, "90%"] in got, (spill, got))
        ev("() => { Cali.settings.set('restAfterLog', false); Cali.settings.set('alternatePairs', true); }")
        ev("() => Cali.go('day', { dayId: Cali.program().days[1].id }, { replace: true })")
        page.wait_for_selector(f'[data-screen="day"] [data-set^="{ev("() => Cali.program().days[1].id")}:"]')
        ev("""() => { const D = Cali.program().days[1].id, list = Cali.dayExercises(null, D);
            for (const ex of list) ex.sets.forEach((s, i) => { if (s) Cali.log(D, ex.id, i, null); });
            Cali.log(D, list[0].id, 0, 1); }""")   # day B again with only its warm-up tile done: Dips set 1 in hand
        step(300)
        bug = "() => [document.querySelector('.workout-bug-name').textContent, document.querySelector('[data-lab=\"rest\"]').textContent, document.querySelector('[data-big=\"rest\"]').textContent]"
        got = [ev(bug)]
        ev("() => Cali.settings.set('restAfterLog', true)")
        step(300)
        got.append(ev(bug))
        A.check("with 'start rest after a log' off the bug promises no rest (–); on, the pair rest that will run (1:30)",
                got == [["Dips", "Rest", "–"], ["Dips", "Pair rest", "1:30"]], got)

        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
