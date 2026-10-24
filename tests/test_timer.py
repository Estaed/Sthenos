"""Checks for the independent timer (Task-02, app/timer.js): screen 4 and the top-bar pill.

Run from the repo root: python tests/acceptance.py (or this file alone). Reuses the gate's phone with Playwright's clock
paused: buttons are touched like the phone does, and time moves only when the test runs the clock (run_for fires every
tick on the way; fast_forward jumps like a phone that slept). The probe from tests/test_alert.py records the messages to
the service worker and the alert flashes. Nothing personal is stored.
"""
import datetime
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402
from test_alert import PROBE, posted, take  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402


def scenario(browser, url, errors):
    ctx, page = A.phone(browser, errors, "timer")
    ctx.add_init_script(PROBE)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate

    def tap(sel):
        A.touch_tap(page, sel)

    def text(key):
        return ev(f"() => {{ const el = document.querySelector('[data-timer=\"{key}\"]'); return el && el.textContent; }}")

    def cd():
        return ev("() => Cali.timers.get('countdown')")

    def main_label():
        return ev("() => document.querySelector('[data-act=\"cd-main\"]').textContent")

    def pressed():
        return ev("() => [...document.querySelectorAll('.timer-chip[aria-pressed=\"true\"]')].map(b => b.textContent)")

    def bar():
        return ev("() => { const el = document.querySelector('[data-timer=\"bar\"]'); return Math.round(parseFloat(el.style.width) * 10) / 10; }")

    def top():
        return ev("""() => { const d = document.querySelector('[data-screen="day"]'); if (!d) return null;
            const pill = document.querySelector('.timer-pill'), open = document.querySelector('.timer-open');
            return { pill: pill.hidden ? null : pill.textContent, label: pill.getAttribute('aria-label'), open: !open.hidden,
                     inBar: d.contains(pill) && d.contains(open),
                     edge: Math.round(open.parentElement.getBoundingClientRect().right - open.getBoundingClientRect().right) }; }""")

    # ── the top bar with nothing running; the button opens screen 4 ──
    got = top()
    A.check("with no timer running the day's top bar shows the timer button at the right end of its holder (before Start/Finish) and no pill",
            got and got["pill"] is None and got["open"] and got["inBar"] and got["edge"] <= 1, got)
    tap(".timer-open")
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    A.check("the timer button opens the timer screen (route 'timer') with the countdown at 1:00 ready to start",
            ev("() => Cali.current().name") == "timer" and text("left") == "1:00" and cd() is None and main_label() == "Start",
            (text("left"), main_label()))
    A.check("the timer screen fits 360 px without sideways scrolling", ev("() => document.documentElement.scrollWidth") <= 360,
            ev("() => document.documentElement.scrollWidth"))

    # ── countdown: preset, pause, +1 min, resume, the end ──
    take(page, "posted")
    tap('[data-preset="60"]')
    t = cd()
    sched = posted(page, {"op": "schedule", "tag": "timer"})
    A.check("a preset starts the countdown at once (1 min) and schedules its end: Cali.alert.schedule('timer', endAt, 'timer')",
            t and t["duration"] == 60000 and t["running"] and text("left") == "1:00" and pressed() == ["1 min"]
            and [(m["kind"], m["endAt"]) for m in sched] == [("timer", t["endAt"])], (t, sched))
    ctx.clock.run_for(10000)
    A.check("10 s later it shows 0:50 of 1:00, the bar at the share left", text("left") == "0:50" and text("status") == "of 1:00"
            and bar() == 83.3, (text("left"), text("status"), bar()))
    take(page, "posted")
    tap('[data-act="cd-main"]')
    cancel = posted(page, {"op": "cancel", "tag": "timer"})
    ctx.clock.run_for(60000)
    A.check("Pause holds it at 0:50 for a minute and cancels its alert", text("left") == "0:50" and text("status") == "Paused"
            and main_label() == "Resume" and len(cancel) == 1, (text("left"), text("status"), cancel))
    tap('[data-act="cd-add"]')
    A.check("+1 min on a paused countdown: 1:50", text("left") == "1:50" and cd()["duration"] == 120000, text("left"))
    take(page, "posted")
    tap('[data-act="cd-main"]')
    t = cd()
    sched = posted(page, {"op": "schedule", "tag": "timer"})
    ctx.clock.run_for(20000)
    A.check("Resume goes on from 1:50 and schedules the new end; 20 s later 1:30",
            text("left") == "1:30" and text("status") == "of 2:00" and [m["endAt"] for m in sched] == [t["endAt"]]
            and t["endAt"] == ev("() => Cali.now()") - 20000 + 110000, (text("left"), sched, t))
    take(page, "flashes")
    ctx.clock.run_for(89000)
    before = take(page, "flashes")
    ctx.clock.run_for(1500)
    A.check("at zero: 0:00, Done, Start again, and the alert plays once ('Countdown done')",
            before == [] and text("left") == "0:00" and text("status") == "Done" and main_label() == "Start"
            and take(page, "flashes") == [["timer", "Countdown done"]], (before, text("left"), text("status")))

    # ── the phone slept: the countdown and the stopwatch are right when it wakes ──
    tap('[data-act="cd-main"]')
    A.check("Start after the end runs the chosen length again (1 min, not the minute added)",
            cd()["duration"] == 60000 and cd()["running"] and text("left") == "1:00", cd())
    ctx.clock.fast_forward(5 * 60000)
    ctx.clock.run_for(200)
    A.check("after the page was hidden for 5 minutes the countdown shows 0:00 Done, and the stale end is not played late",
            text("left") == "0:00" and text("status") == "Done" and cd()["done"] and take(page, "flashes") == [],
            (text("left"), text("status")))
    take(page, "posted")
    tap('[data-act="cd-reset"]')
    A.check("Reset removes the countdown, shows the chosen 1:00 ready, and cancels its alert",
            cd() is None and text("left") == "1:00" and main_label() == "Start" and len(posted(page, {"op": "cancel", "tag": "timer"})) == 1,
            (cd(), text("left")))

    # ── stopwatch with laps ──
    tap('[data-act="sw-main"]')
    ctx.clock.run_for(5000)
    tap('[data-act="sw-lap"]')
    ctx.clock.run_for(2500)
    tap('[data-act="sw-lap"]')
    laps = ev("() => [...document.querySelectorAll('.timer-lap')].map(li => [...li.children].map(s => s.textContent))")
    A.check("stopwatch: 0:07.5 with two laps, newest first, each with its split and total",
            text("watch") == "0:07.5" and laps == [["Lap 2", "0:02.5", "0:07.5"], ["Lap 1", "0:05.0", "0:05.0"]], (text("watch"), laps))
    tap('[data-act="sw-main"]')
    ctx.clock.run_for(60000)
    tap('[data-act="sw-lap"]')
    A.check("Pause holds the stopwatch at 0:07.5; Lap does nothing while paused",
            text("watch") == "0:07.5" and ev("() => Cali.timers.get('stopwatch').laps.length") == 2
            and ev("() => document.querySelector('[data-act=\"sw-lap\"]').getAttribute('aria-disabled')") == "true", text("watch"))
    tap('[data-act="sw-main"]')
    ctx.clock.fast_forward(10 * 60000)
    ctx.clock.run_for(100)
    A.check("after 10 minutes hidden the stopwatch shows 10:07.6", text("watch") == "10:07.6", text("watch"))

    # ── both at once, shown as a pill on the workout ──
    tap('[data-preset="120"]')
    tap('[data-act="back"]')
    page.wait_for_selector('[data-screen="day"] [data-set]')
    got = top()
    ctx.clock.run_for(10000)
    later = top()
    A.check("back on the workout both run: the pill shows the countdown left (2:00, then 1:50) and replaces the timer button",
            got["pill"] == "2:00" and later["pill"] == "1:50" and not got["open"] and got["inBar"]
            and ev("() => Cali.timers.get('stopwatch').running") is True, (got, later))
    tap(".timer-pill")
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    A.check("the pill opens the timer screen", ev("() => Cali.current().name") == "timer" and text("left") == "1:50", text("left"))
    tap('[data-act="cd-reset"]')
    tap('[data-act="back"]')
    page.wait_for_selector('[data-screen="day"] [data-set]')
    got = top()
    A.check("with only the stopwatch running the pill shows its time", got["pill"] == "10:17" and "Stopwatch" in got["label"], got)
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    ctx.clock.run_for(1000)
    A.check("after a reload the stopwatch still runs and the pill shows it", top()["pill"] == "10:18", top())

    # ── Cali.go('timer', { countdown }) from a timed row ──
    ev("() => Cali.go('timer', { countdown: 240 })")
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    t = cd()
    A.check("Cali.go('timer', { countdown: 240 }) starts a 4:00 countdown, the 4 min preset marked",
            t and t["duration"] == 240000 and t["running"] and text("left") == "4:00" and pressed() == ["4 min"], (t, pressed()))
    ctx.clock.run_for(5000)
    take(page, "posted")
    page.reload()
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    sched = posted(page, {"op": "schedule", "tag": "timer"})
    A.check("a reload of that screen does not restart it, and schedules its running end again",
            cd()["startedAt"] == t["startedAt"] and text("left") == "3:55" and [m["endAt"] for m in sched] == [t["endAt"]],
            (cd()["startedAt"], t["startedAt"], text("left"), sched))
    tap('[data-act="cd-main"]')
    page.reload()
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    A.check("paused, a reload of the request that started it still does not restart it",
            cd()["startedAt"] == t["startedAt"] and not cd()["running"] and text("left") == "3:55" and text("status") == "Paused",
            (cd(), text("left")))
    tap('[data-act="cd-main"]')
    page.go_back()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    page.go_forward()
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    ev("() => Cali.go('timer', { countdown: 240 })")
    A.check("back and forward, or the same request while it runs, keep the running countdown",
            cd()["startedAt"] == t["startedAt"] and text("left") == "3:55", (cd()["startedAt"], text("left")))
    ev("() => Cali.go('timer', { countdown: 1320 })")
    A.check("a 22 min row: 22:00, Custom marked, the number set a size down to fit",
            cd()["duration"] == 1320000 and text("left") == "22:00" and pressed() == ["Custom"]
            and ev("() => document.querySelector('[data-timer=\"left\"]').dataset.len") == "5"
            and ev("() => document.documentElement.scrollWidth") <= 360, (text("left"), pressed()))

    # ── custom length ──
    tap('[data-act="custom"]')
    page.fill('.timer-custom input[name="min"]', "0")
    page.fill('.timer-custom input[name="sec"]', "0")
    tap('.timer-custom button[type="submit"]')
    A.check("Custom with 0:00 says what is wrong and starts nothing",
            ev("() => !document.querySelector('[data-timer=\"error\"]').hidden") and cd()["duration"] == 1320000, cd()["duration"])
    page.fill('.timer-custom input[name="min"]', "2")
    page.fill('.timer-custom input[name="sec"]', "30")
    ctx.clock.run_for(1000)   # retyping takes time; a second tap on the same spot within 350 ms is a double tap
    tap('.timer-custom button[type="submit"]')
    A.check("Custom 2 min 30 s starts a 2:30 countdown and closes the editor",
            cd()["duration"] == 150000 and text("left") == "2:30" and pressed() == ["Custom"]
            and ev("() => document.querySelector('.timer-custom') === null"), (cd()["duration"], text("left")))

    # ── done with both: the button is back (the day opened directly: back now leads to the earlier timer entries) ──
    tap('[data-act="cd-reset"]')
    tap('[data-act="sw-reset"]')
    ev("() => Cali.go('day')")
    page.wait_for_selector('[data-screen="day"] [data-set]')
    got = top()
    A.check("both reset: no pill, the timer button is back, no timer left in Cali.timers",
            got["pill"] is None and got["open"] and ev("() => Cali.timers.list().length") == 0, got)
    keys = ev("() => Object.keys(localStorage)")
    A.check("the timer stores only cali.* keys", all(k.startswith("cali.") for k in keys), keys)
    ctx.close()


def double_taps(browser, url, errors):
    """A quick double tap (a sweaty finger that bounces) is one tap: the second lands on a button the first redrew.
    On the counting buttons (+1 min, Lap), which the first tap does not change, each tap counts."""
    ctx, page = A.phone(browser, errors, "timer-double")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate

    def double(sel, gap=150):
        x, y = A.center(page, sel)
        page.touchscreen.tap(x, y)
        ctx.clock.run_for(gap)
        page.touchscreen.tap(x, y)

    def state(name):
        return ev(f"() => {{ const t = Cali.timers.get('{name}'); return t && [t.running, t.duration]; }}")

    def label(act):
        return ev(f"() => document.querySelector('[data-act=\"{act}\"]').textContent")

    A.touch_tap(page, ".timer-open")
    page.wait_for_selector('[data-screen="timer"] [data-timer="left"]')
    ctx.clock.run_for(1000)
    double('[data-act="cd-main"]')
    A.check("two taps 150 ms apart on the countdown's Start leave it running (not paused by the second)",
            state("countdown") == [True, 60000] and label("cd-main") == "Pause", (state("countdown"), label("cd-main")))
    double('[data-act="sw-main"]')
    A.check("two taps 150 ms apart on the stopwatch's Start leave it running",
            (state("stopwatch") or [None])[0] is True and label("sw-main") == "Pause", (state("stopwatch"), label("sw-main")))
    ctx.clock.run_for(1000)
    A.touch_tap(page, '[data-act="cd-main"]')
    A.check("a second tap a second later still counts: Pause", state("countdown") == [False, 60000], state("countdown"))
    ctx.clock.run_for(1000)
    A.touch_tap(page, '[data-act="cd-reset"]')
    ctx.clock.run_for(150)
    A.touch_tap(page, '[data-act="cd-main"]')
    A.check("quick taps on two different buttons both count: Reset, then Start 150 ms later",
            state("countdown") == [True, 60000], state("countdown"))
    ctx.clock.run_for(1000)
    A.touch_tap(page, '[data-act="custom"]')
    page.fill('.timer-custom input[name="min"]', "0")
    page.fill('.timer-custom input[name="sec"]', "45")
    ctx.clock.run_for(1000)
    double('.timer-custom button[type="submit"]')
    A.check("two quick taps on Custom's Start start 0:45 once; the second does not land on the +1 min drawn under it",
            state("countdown") == [True, 45000], state("countdown"))
    ctx.clock.run_for(1000)
    double('[data-act="cd-add"]')
    A.check("two taps 150 ms apart on +1 min add two minutes", state("countdown") == [True, 165000], state("countdown"))
    ctx.clock.run_for(1000)
    double('[data-act="sw-lap"]')
    laps = ev("() => Cali.timers.get('stopwatch').laps.length")
    A.check("two taps 150 ms apart on Lap record two laps", laps == 2, laps)
    ctx.close()


def long_stopwatch(browser, url, errors):
    """A stopwatch forgotten overnight or for days (no cap, survives a reload) still fits its card at 360 px."""
    ctx, page = A.phone(browser, errors, "timer-long")
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    A.touch_tap(page, ".timer-open")
    page.wait_for_selector('[data-screen="timer"] [data-timer="watch"]')
    A.touch_tap(page, '[data-act="sw-main"]')
    fit = """() => { const v = document.querySelector('[data-timer="watch"]'), card = v.closest('.timer-sw');
        const r = document.createRange(); r.selectNodeContents(v);
        const inner = card.getBoundingClientRect().right - parseFloat(getComputedStyle(card).paddingRight);
        const cells = [...document.querySelectorAll('.timer-lap > *')];
        return { text: v.textContent, over: Math.round(r.getBoundingClientRect().right - inner),
                 cells: cells.filter(c => c.scrollWidth > c.clientWidth).map(c => c.textContent), docW: document.documentElement.scrollWidth }; }"""
    seen = []
    for hours in (11, 100):   # the first lengths a digit longer than 1:12:00.0: 11:12:00.0 and 100:12:00.0
        left = hours * 3600000 + 12 * 60000 - page.evaluate("() => Cali.timers.get('stopwatch').elapsed")
        while left > 0:       # the clock jumps at most a day at a time
            ctx.clock.fast_forward(min(left, 86400000))
            left -= 86400000
        A.touch_tap(page, '[data-act="sw-lap"]')
        ctx.clock.run_for(100)
        seen.append(page.evaluate(fit))
    A.check("a stopwatch at 11:12 h and 100:12 h, with laps, fits its card and the page at 360 px (no sideways scroll)",
            [s["text"][:6] for s in seen] == ["11:12:", "100:12"]
            and all(s["over"] <= 0 and not s["cells"] and s["docW"] <= 360 for s in seen), seen)
    ctx.close()


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        A.guarded("the timer scenario", scenario, browser, url, errors)
        A.guarded("the double-tap scenario", double_taps, browser, url, errors)
        A.guarded("the long stopwatch scenario", long_stopwatch, browser, url, errors)
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors (timer)", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
