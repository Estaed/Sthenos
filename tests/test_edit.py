"""Checks for Tarık's first phone round (2026-10-24): each exercise runs through its sets before the next, a set at 0
is not done (a day tapped back to 0 is reset), the exercise editor in the card, How to use and the alert choices in
Settings, the English program.

Run from the repo root: python tests/test_edit.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py with Playwright's clock paused. Data: the built-in program only."""
import datetime
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

# Cali.alert and navigator.vibrate as recorders
RECORD = """() => { window.__alerts = []; window.__buzz = [];
  Object.defineProperty(Navigator.prototype, 'vibrate', { configurable: true, value(p) { __buzz.push(p); return true; } });
  Cali.provide('alert', { alert: k => __alerts.push(['alert', k]), schedule: (k, at, tag) => __alerts.push(['schedule', k, tag]),
    cancel: tag => __alerts.push(['cancel', tag]), requestPermission: async () => 'granted' }); }"""


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "edit", reduced_motion="reduce")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate
        step = lambda ms=1000: ctx.clock.run_for(ms)
        ids = ev("""() => { const d = Cali.program().days[0]; const by = n => d.exercises.find(e => e.name.startsWith(n)).id;
            return { day: d.id, pull: by('Weighted Pull-up'), dip: by('Weighted Dip'), lp: by('Leg Press') }; }""")
        D = ids["day"]
        cell = lambda ex, i: f'[data-screen="day"] [data-set="{D}:{ids[ex]}:{i}"]'
        now_cell = lambda: ev("() => { const el = document.querySelector('[data-screen=\"day\"] .cell.now'); return el && el.dataset.cell; }")
        day = lambda: ev(f"() => Cali.week().days[{json.dumps(D)}]")

        # ── the whole program in English ──
        names = ev("() => Cali.program().days.flatMap(d => [d.name, ...d.exercises.map(e => e.name)])")
        turkish = [n for n in names if re.search("[ğüşıöçĞÜŞİÖÇ]", n)]
        A.check("the built-in program has no Turkish name (days A Heavy, B Volume, C Legs)",
                not turkish and names[0] == "A Heavy", turkish or names[:1])

        # ── one exercise at a time ──
        A.touch_tap(page, cell("pull", 0))
        rest = ev("() => { const t = Cali.timers.get('rest'); return t && [t.duration, t.data.rest]; }")
        A.check("after Pull-up 1 the set in hand is Pull-up 2, not Dip 1, and the rest is the 2:00 between sets",
                now_cell() == f"{ids['pull']}:1" and rest == [120000, "exercise"], [now_cell(), rest])
        got = ev(f"() => Cali.setOrder({json.dumps(D)}).slice(0, 6).map(s => s.exId + ':' + s.i)")
        P, Q = ids["pull"], ids["dip"]
        A.check("setOrder runs each exercise through its sets (P1 P2 P3 D1 D2 D3)",
                got == [f"{P}:0", f"{P}:1", f"{P}:2", f"{Q}:0", f"{Q}:1", f"{Q}:2"], got)
        ev("() => Cali.settings.set('alternatePairs', true)")
        got = ev(f"() => Cali.setOrder({json.dumps(D)}).slice(0, 4).map(s => s.exId + ':' + s.i)")
        A.check("with Alternate paired exercises on, the pair alternates again (P1 D1 P2 D2)",
                got == [f"{P}:0", f"{Q}:0", f"{P}:1", f"{Q}:1"], got)
        ev("() => Cali.settings.set('alternatePairs', false)")

        # ── a set tapped down to 0 is not done; a day with none done is reset ──
        for _ in range(6):   # 6 -> 5 ... -> 0
            step(300)
            A.touch_tap(page, cell("pull", 0))
        step(300)
        got = [ev(f"() => Cali.week().days[{json.dumps(D)}].exercises[{json.dumps(P)}].sets[0].r"), bool(day().get("startedAt")),
               ev("() => [document.querySelector('.workout-bug-name').textContent, document.querySelector('[data-big=\"set\"]').textContent]"),
               ev("() => Cali.timers.get('rest')")]
        A.check("Pull-up 1 tapped down to 0: the day goes back to not started, Pull-up 1 is in hand again, no rest",
                got == [0, False, ["Weighted Pull-up", "1/3"], None], got)
        A.check("the app bar offers Start again and the clock is hidden",
                ev("() => [document.querySelector('[data-act=\"session\"]').textContent, document.querySelector('.workout-clock').hidden]") == ["Start", True])
        step(300)
        A.touch_tap(page, cell("pull", 0))
        A.check("one more tap clears the 0", ev(f"() => Cali.week().days[{json.dumps(D)}].exercises[{json.dumps(P)}].sets[0]") is None)

        # ── the tap legend lives in Settings now ──
        A.check("no tap legend under the score bug", ev("() => !document.querySelector('.workout-legend')"))

        # ── the exercise editor in the card ──
        name_btn = f'[data-screen="day"] [data-edit="{ids["lp"]}"]'
        A.touch_tap(page, name_btn)
        box = f'[data-screen="day"] [data-ed="{ids["lp"]}"]'
        page.wait_for_selector(f"{box}:not([hidden])")
        A.check("a tap on Leg Press's name opens its editor in the card",
                ev(f"() => document.querySelector('{name_btn}').getAttribute('aria-expanded')") == "true"
                and ev(f"() => document.querySelector('{box}').closest('.workout-card') === document.querySelector('{name_btn}').closest('.workout-card')"))
        shown = lambda: ev(f"() => [...document.querySelectorAll('{box} [data-ed-v]')].map(e => e.textContent)")
        A.check("it shows load, target, sets and the rep range", shown() == ["110 kg", "10", "3", "8", "12"], shown())
        A.touch_tap(page, f'{box} [data-ed-k="load"][data-ed-d="1"]')
        A.touch_tap(page, f'{box} [data-ed-k="sets"][data-ed-d="1"]')
        A.touch_tap(page, f'{box} [data-ed-k="repMax"][data-ed-d="-1"]')
        got = ev(f"""() => {{ const w = Cali.weekExercise(null, {json.dumps(D)}, {json.dumps(ids['lp'])});
            const p = Cali.program().days[0].exercises.find(e => e.id === {json.dumps(ids['lp'])});
            return [w.load, w.sets.length, w.repMax, p.load, p.sets, p.repMax,
                    document.querySelectorAll('[data-screen="day"] [data-cell^="{ids['lp']}:"]').length]; }}""")
        A.check("load + one step (5 kg), one more set and the range top down: in the week, the program and the cells",
                got == [115, 4, 11, 115, 4, 11, 4], got)
        A.check("the editor stays open after the row is drawn again (a fourth cell)", ev(f"() => !document.querySelector('{box}').hidden"))
        A.touch_tap(page, f'{box} [data-ed-step="2.5"]')
        A.check("the load step is chosen in the card", ev(f"() => Cali.weekExercise(null, {json.dumps(D)}, {json.dumps(ids['lp'])}).loadStep") == 2.5)
        page.fill(f"{box} .workout-ed-name", "Leg Press 45°")
        page.press(f"{box} .workout-ed-name", "Enter")
        A.check("the name is saved on Enter and shown in the row",
                ev(f"() => [Cali.weekExercise(null, {json.dumps(D)}, {json.dumps(ids['lp'])}).name, document.querySelector('{name_btn} .workout-name').textContent]")
                == ["Leg Press 45°", "Leg Press 45°"])
        lp = lambda i: f'[data-screen="day"] [data-set="{D}:{ids["lp"]}:{i}"]'
        step(300)
        A.touch_tap(page, lp(2))
        A.touch_tap(page, f'{box} [data-ed-k="sets"][data-ed-d="-1"]')
        got = ev(f"() => Cali.weekExercise(null, {json.dumps(D)}, {json.dumps(ids['lp'])}).sets.map(s => s && s.r)")
        dis = ev(f"() => document.querySelector('{box} [data-ed-k=\"sets\"][data-ed-d=\"-1\"]').disabled")
        A.check("sets never drop below a logged set (set 3 logged: 4 -> 3, then the minus is off)", got == [None, None, 10] and dis, [got, dis])
        done = f'{box} [data-act="ed-done"]'
        page.locator(done).scroll_into_view_if_needed()
        x, y = A.center(page, done)
        hit = ev(f"() => document.elementFromPoint({x}, {y}).closest('[data-act]')?.dataset.act || document.elementFromPoint({x}, {y}).className")
        A.touch_tap(page, done)
        A.check("Done closes it", ev(f"() => document.querySelector('{box}').hidden"), hit)
        ev("() => Cali.go('day', { week: 1, readOnly: true }, { replace: true })")
        A.check("a read-only week has no editor", ev("() => !document.querySelector('[data-screen=\"day\"] [data-edit]')"))

        # ── Settings: How to use, vibration and sound ──
        ev(RECORD)
        page.mouse.click(5, 5)   # a user gesture, so the page may vibrate
        ev("() => Cali.go('settings')")
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        how = '[data-screen="settings"] [data-act="how"]'
        A.check("How to use is closed at first", ev("() => document.querySelector('#settings-how').hidden"))
        A.touch_tap(page, how)
        text = page.locator("#settings-how").inner_text()
        A.check("How to use opens the gestures (tap, again, hold) and the name editor",
                all(t in text for t in ("Tap a set", "Tap it again", "Hold it", "Tap an exercise's name")), text)
        A.touch_tap(page, '[data-screen="settings"] [data-key="buzz"][data-val="long"]')
        got = ev("() => [Cali.settings.get('vibrate'), Cali.settings.get('buzz'), __alerts]")
        A.check("Vibration Long is saved and plays the test alert", got[:2] == [True, "long"] and ["alert", "test"] in got[2], got)
        A.touch_tap(page, '[data-screen="settings"] [data-key="buzz"][data-val="off"]')
        A.check("Vibration Off turns vibrate off and keeps the pattern",
                ev("() => [Cali.settings.get('vibrate'), Cali.settings.get('buzz')]") == [False, "long"])
        A.touch_tap(page, '[data-screen="settings"] [data-key="tone"][data-val="bell"]')
        A.touch_tap(page, '[data-screen="settings"] [data-key="volume"][data-val="3"]')
        A.check("Sound Bell and Volume High are saved",
                ev("() => [Cali.settings.get('sound'), Cali.settings.get('tone'), Cali.settings.get('volume')]") == [True, "bell", 3])
        pressed = ev("""() => [...document.querySelectorAll('[data-screen="settings"] .settings-seg [aria-pressed="true"]')].map(b => b.dataset.key + '=' + b.dataset.val)""")
        A.check("each choice shows as pressed", {"buzz=off", "tone=bell", "volume=3"} <= set(pressed), pressed)
        wide = ev("() => document.scrollingElement.scrollWidth <= innerWidth")
        A.check("Settings fits 360 px without sideways scrolling", wide)

        # the real alert plays the chosen pattern
        ev("() => Cali.settings.set('vibrate', true)")
        page.reload()
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        ev("() => { window.__buzz = []; Object.defineProperty(Navigator.prototype, 'vibrate', { configurable: true, value(p) { __buzz.push(p); return true; } }); }")
        page.mouse.click(5, 5)
        ev("() => Cali.alert('rest')")
        A.check("a rest alert vibrates the long pattern", ev("() => __buzz") == [[1000, 250, 1000, 250, 1500]], ev("() => __buzz"))

        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
