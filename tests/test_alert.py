"""Checks for the alerts (Task-02, app/alert.js and sw-alert.js).

Run from the repo root: python tests/acceptance.py (or this file alone). Part 1 reuses the gate's phone with Playwright's
clock paused, so every end is reached by moving Cali.now(); a probe records beeps (oscillator starts), vibrations,
messages to the service worker and the flashes, and stands in for the notification permission prompt and for user
activation (set only by a real touch, since Playwright's evaluate counts as a gesture). Part 2 registers
the real service worker in Chromium's full headless browser (the headless shell cannot grant notifications) on the real
clock, grants notifications, and reads what the worker shows. Nothing personal is stored.
"""
import datetime
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PROBE = """(() => {
  const p = window.__probe = { beeps: [], buzz: [], posted: [], flashes: [], ctx: null };
  const AC = window.AudioContext;
  if (AC) window.AudioContext = class extends AC { constructor(...a) { super(...a); p.ctx = this; } };
  const start = OscillatorNode.prototype.start;
  OscillatorNode.prototype.start = function (...a) { p.beeps.push(this.frequency.value); return start.apply(this, a); };
  Object.defineProperty(Navigator.prototype, 'vibrate', { configurable: true, value(pattern) { p.buzz.push(pattern); return true; } });
  const post = ServiceWorker.prototype.postMessage;
  ServiceWorker.prototype.postMessage = function (m, ...rest) { p.posted.push(JSON.parse(JSON.stringify(m))); return post.call(this, m, ...rest); };
  new MutationObserver(list => { for (const r of list) for (const n of r.addedNodes) {
    if (n.classList && n.classList.contains('alert-flash')) p.flashes.push([n.dataset.kind, n.textContent]); } })
    .observe(document, { childList: true, subtree: true });
})();"""

# Part 1 only: the permission prompt, answered 'granted' by the probe and counted; and user activation as a phone sees
# it, from real touches only (Playwright's evaluate counts as a gesture, so the browser's own flag is already set).
FAKE_BROWSER = """(() => {
  const p = window.__probe;
  p.perm = 'default'; p.asks = 0; p.active = false;
  Object.defineProperty(Notification, 'permission', { configurable: true, get: () => p.perm });
  Notification.requestPermission = () => { p.asks += 1; return new Promise(r => queueMicrotask(() => { p.perm = 'granted'; r('granted'); })); };
  Object.defineProperty(Navigator.prototype, 'userActivation', { configurable: true, get: () => ({ hasBeenActive: p.active }) });
  addEventListener('touchend', () => { p.active = true; }, true);
})();"""

REST_TONES, REST_BUZZ = 3, [300, 120, 300, 120, 500]


def take(page, key):
    """The probe's record under key, emptied."""
    return page.evaluate(f"() => __probe.{key}.splice(0)")


def posted(page, want, timeout=10.0):
    """Waits until the page has posted a message to the worker matching want (a dict of fields); returns them all."""
    js = f"() => __probe.posted.filter(m => Object.entries({json.dumps(want)}).every(([k, v]) => m[k] === v))"
    end = time.monotonic() + timeout
    while True:
        got = page.evaluate(js)
        if got or time.monotonic() > end:
            return got
        page.wait_for_timeout(50)


def part_page(browser, url):
    errors = []
    ctx, page = A.phone(browser, errors, "alert")
    ctx.add_init_script(PROBE)
    ctx.add_init_script(FAKE_BROWSER)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ev = page.evaluate

    # ── never asks on load; before any tap nothing can sound ──
    ctx.clock.run_for(5000)
    A.check("nothing asks for notification permission on load", ev("() => __probe.asks") == 0, ev("() => __probe.asks"))
    ev("() => Cali.alert('rest')")
    got = [take(page, "beeps"), take(page, "buzz"), take(page, "flashes"), ev("() => __probe.ctx === null")]
    A.check("before the first tap Cali.alert('rest') flashes 'Rest over' but makes no audio context, beep or vibration",
            got == [[], [], [["rest", "Rest over"]], True], got)

    # ── the first tap unlocks the sound; every kind beeps, vibrates and flashes ──
    A.touch_tap(page, ".appbar .week")
    state = A.poll(page, "() => __probe.ctx && __probe.ctx.state === 'running' && __probe.ctx.state")
    A.check("the first tap makes the audio context and it runs", state == "running", state)
    want = {"rest": (3, REST_BUZZ, "Rest over"), "headsup": (1, [150], "Rest ends in 10 s"),
            "timer": (4, [500, 150, 500, 150, 500], "Countdown done"), "test": (3, REST_BUZZ, "Test alert")}
    seen = {}
    for kind in want:
        ev(f"() => Cali.alert('{kind}')")
        seen[kind] = (len(take(page, "beeps")), (take(page, "buzz") or [None])[0], take(page, "flashes"))
    A.check("Cali.alert beeps, vibrates and flashes its words for rest, headsup, timer and test",
            all(seen[k] == (n, b, [[k, t]]) for k, (n, b, t) in want.items()), seen)
    ev("() => Cali.settings.set('sound', false)")
    ev("() => Cali.alert('rest')")
    quiet = [take(page, "beeps"), take(page, "buzz"), len(take(page, "flashes"))]
    ev("() => { Cali.settings.set('sound', true); Cali.settings.set('vibrate', false); }")
    ev("() => Cali.alert('rest')")
    still = [len(take(page, "beeps")), take(page, "buzz"), len(take(page, "flashes"))]
    ev("() => Cali.settings.set('vibrate', true)")
    A.check("settings.sound off: no beep; settings.vibrate off: no vibration; the flash shows either way",
            quiet == [[], [REST_BUZZ], 1] and still == [REST_TONES, [], 1], (quiet, still))

    # ── schedule: the page posts { endAt, tag, kind } to the worker and plays the end itself ──
    take(page, "posted")
    end = ev("() => { const end = Cali.now() + 90000; Cali.alert.schedule('rest', end, 'rest'); return end; }")
    msg = posted(page, {"op": "schedule", "tag": "rest"})
    A.check("schedule posts { endAt, tag, kind } to the service worker",
            msg == [{"type": "cali-alert", "op": "schedule", "kind": "rest", "endAt": end, "tag": "rest", "title": "Rest over"}], msg)
    ctx.clock.run_for(89000)
    early = take(page, "flashes")
    ctx.clock.run_for(1500)
    A.check("the page plays the alert at the end, not before (beep, vibration, 'Rest over')",
            early == [] and take(page, "flashes") == [["rest", "Rest over"]] and len(take(page, "beeps")) == REST_TONES
            and take(page, "buzz") == [REST_BUZZ], early)
    ctx.clock.run_for(60000)
    A.check("an end plays once", take(page, "flashes") == [])

    # ── cancel, replace, two kinds under one tag ──
    take(page, "posted")
    ev("() => Cali.alert.schedule('timer', Cali.now() + 30000, 'timer')")
    ctx.clock.run_for(10000)
    ev("() => Cali.alert.cancel('timer')")
    msg = posted(page, {"op": "cancel"})
    ctx.clock.run_for(60000)
    A.check("cancel(tag) before the end: the worker is told ({ op: 'cancel', tag }) and nothing plays",
            msg == [{"type": "cali-alert", "op": "cancel", "tag": "timer"}] and take(page, "flashes") == [], msg)
    ev("() => { Cali.alert.schedule('rest', Cali.now() + 20000, 'rest'); Cali.alert.schedule('rest', Cali.now() + 40000, 'rest'); }")
    ctx.clock.run_for(30000)
    first = take(page, "flashes")
    ctx.clock.run_for(15000)
    A.check("a later schedule under the same tag and kind replaces the earlier one",
            first == [] and take(page, "flashes") == [["rest", "Rest over"]], first)
    ev("() => { Cali.alert.schedule('headsup', Cali.now() + 5000, 'rest'); Cali.alert.schedule('rest', Cali.now() + 15000, 'rest'); }")
    ctx.clock.run_for(6000)
    a = take(page, "flashes")
    ctx.clock.run_for(10000)
    b = take(page, "flashes")
    ev("() => { Cali.alert.schedule('headsup', Cali.now() + 5000, 'rest'); Cali.alert.schedule('rest', Cali.now() + 15000, 'rest'); Cali.alert.cancel('rest'); }")
    ctx.clock.run_for(20000)
    A.check("headsup and rest under one tag both play; cancel(tag) drops both",
            a == [["headsup", "Rest ends in 10 s"]] and b == [["rest", "Rest over"]] and take(page, "flashes") == [], (a, b))

    # ── the phone slept through the end: the page does not play it minutes late ──
    ev("() => Cali.alert.schedule('rest', Cali.now() + 90000, 'rest')")
    ctx.clock.fast_forward(5 * 60000)
    ctx.clock.run_for(100)
    A.check("an end the page wakes up to more than 60 s late is not played in the page", take(page, "flashes") == [])

    # ── permission: asks once, never again once answered ──
    got = ev("""async () => { const a = Cali.alert.requestPermission(), b = Cali.alert.requestPermission();
        const r = [await a, await b, __probe.asks]; r.push(await Cali.alert.requestPermission(), __probe.asks); return r; }""")
    A.check("requestPermission asks once for two calls at once, and not again once granted", got == ["granted", "granted", 1, "granted", 1], got)

    # ── hidden but awake: no in-page alert, pending ends posted again, the notification asked of the worker ──
    take(page, "posted")
    end = ev("() => { const end = Cali.now() + 30000; Cali.alert.schedule('rest', end, 'rest'); return end; }")
    posted(page, {"op": "schedule", "endAt": end})
    take(page, "posted")
    ev("""() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
        document.dispatchEvent(new Event('visibilitychange')); }""")
    again = posted(page, {"op": "schedule", "endAt": end})
    ctx.clock.run_for(31000)
    show = posted(page, {"op": "show", "endAt": end})
    flashes = take(page, "flashes")
    ev("() => { delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange')); }")
    A.check("hidden: pending ends go to the worker again; at the end the page asks the worker to show the notification, no flash",
            len(again) == 1 and show == [{"type": "cali-alert", "op": "show", "kind": "rest", "endAt": end, "tag": "rest", "title": "Rest over"}]
            and flashes == [] and ev("() => document.visibilityState") == "visible", (again, show, flashes))

    # ── the worker's own trigger reached a page that lost its timer (a reload) ──
    fired = """(m) => navigator.serviceWorker.dispatchEvent(new MessageEvent('message', { data: { type: 'cali-alert', op: 'fired', ...m } }))"""
    now = ev("() => Cali.now()")
    page.evaluate(fired, {"kind": "rest", "tag": "rest", "endAt": now - 500})
    a = take(page, "flashes")
    page.evaluate(fired, {"kind": "rest", "tag": "rest", "endAt": now - 500})
    page.evaluate(fired, {"kind": "timer", "tag": "timer", "endAt": now + 3600000})
    A.check("a 'fired' from the worker plays in a page that lost its timer, once, and only when the page's clock agrees",
            a == [["rest", "Rest over"]] and take(page, "flashes") == [], a)

    keys = ev("() => Object.keys(localStorage)")
    A.check("the alerts store nothing (only cali.* keys)", all(k.startswith("cali.") for k in keys), keys)
    A.check("no console errors or page errors (alerts on the phone)", not errors, "\n".join(errors[:10]))
    ctx.close()


def part_worker(p, url):
    """The real service worker, the real clock, notifications granted."""
    try:
        browser = p.chromium.launch(channel="chromium")
    except Exception as e:  # noqa: BLE001 - reported as a failure, never skipped
        A.check("Chromium's full headless browser starts (needed to grant notifications)", False, str(e).splitlines()[0])
        return
    errors = []
    origin = url.split(A.BASE)[0]
    ctx, page = A.phone(browser, errors, "alert-sw", clock=False)
    ctx.grant_permissions(["notifications"], origin=origin)
    ctx.add_init_script(PROBE)
    A.open_day(page, url)
    A.check("the real service worker (sw.js with sw-alert.js) controls the app", A.wait_controlled(page))
    A.check("notifications are granted in this context", page.evaluate("() => Notification.permission") == "granted")
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    sw.evaluate("""() => { self.__shows = []; const show = self.registration.showNotification.bind(self.registration);
        self.registration.showNotification = (title, o) => { self.__shows.push([o.tag, title, o.data && o.data.by, o.requireInteraction, o.renotify]); return show(title, o); }; }""")
    shown = """async (tag) => (await (await navigator.serviceWorker.ready).getNotifications({ tag }))
        .map(n => [n.tag, n.title, n.requireInteraction, n.data && n.data.by])"""

    # the page leaves at once: only the worker can show it
    page.evaluate("() => Cali.alert.schedule('test', Date.now() + 2000, 'probe-sw')")
    posted(page, {"op": "schedule", "tag": "probe-sw"})
    page.evaluate("() => Cali.alert.schedule('test', Date.now() + 2000, 'probe-cancel')")
    posted(page, {"op": "schedule", "tag": "probe-cancel"})
    page.wait_for_timeout(500)
    page.evaluate("() => Cali.alert.cancel('probe-cancel')")
    posted(page, {"op": "cancel", "tag": "probe-cancel"})
    page.close()
    time.sleep(3.5)
    page = ctx.new_page()
    A.watch(page, errors, "alert-sw-2")
    A.open_day(page, url)
    got = A.poll(page, f"async () => {{ const l = await ({shown})('probe-sw'); return l.length && l; }}", timeout=5)
    A.check("a 2 s alert scheduled by a page that then left: the worker shows a requireInteraction notification with its tag",
            got == [["probe-sw", "Test alert", True, "worker"]], got)
    got = [page.evaluate(shown, "probe-cancel"), [s for s in sw.evaluate("() => self.__shows") if s[0] == "probe-cancel"]]
    A.check("cancel before the end: the worker shows none", got == [[], []], got)
    page.evaluate("() => Cali.alert.cancel('probe-sw')")
    got = A.poll(page, f"async () => (await ({shown})('probe-sw')).length === 0", timeout=5)
    A.check("cancel(tag) closes a notification already shown under it", got is True, page.evaluate(shown, "probe-sw"))

    # the page is awake at the end too: both triggers fire, one notification is shown once
    page.evaluate("() => Cali.alert.schedule('rest', Date.now() + 1500, 'probe-both')")
    page.wait_for_timeout(3500)
    shows = [s for s in sw.evaluate("() => self.__shows") if s[0] == "probe-both"]
    got = [page.evaluate(shown, "probe-both"), shows, page.evaluate("() => __probe.flashes.map(f => f[0])")]
    A.check("page and worker both reach the end: one notification, shown once (renotify, requireInteraction), and the page flashed",
            len(got[0]) == 1 and len(shows) == 1 and shows[0][3:] == [True, True] and got[2] == ["rest"], got)

    # the worker lost its wait (a restart): the page, awake at the end, still gets its tag shown
    page.evaluate("""async () => { Cali.alert.schedule('timer', Date.now() + 1500, 'probe-page');
        await new Promise(r => setTimeout(r, 300));
        (await navigator.serviceWorker.ready).active.postMessage({ type: 'cali-alert', op: 'cancel', tag: 'probe-page' }); }""")
    got = A.poll(page, f"async () => {{ const l = await ({shown})('probe-page'); return l.length && l; }}", timeout=6)
    A.check("the worker lost its wait: the page, awake at the end, has the same tag shown (by the page's trigger)",
            got == [["probe-page", "Countdown done", True, "page"]], got)
    page.evaluate("() => { Cali.alert.cancel('probe-both'); Cali.alert.cancel('probe-page'); }")

    A.check("no console errors or page errors (real service worker)", not errors, "\n".join(errors[:10]))
    ctx.close()
    browser.close()


def main():
    srv, site, url = A.start_site()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        A.guarded("alerts on the phone", part_page, browser, url)
        browser.close()
        A.guarded("alerts through the real service worker", part_worker, p, url)
    srv.shutdown()
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
