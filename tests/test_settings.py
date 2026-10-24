"""The Settings screen (app/settings.js, Task-03): rest times and alerts, workout options, theme, backup and restore.

Run from the repo root: python tests/test_settings.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py (360 x 740, touch). Every control is driven by touch taps, and every value is read back through
Cali.settings and the stored document, so the rest timer (Task-01) and the alerts (Task-02) get it from there.
No token here, so the mocked GitHub API must see no request at all. Data: the built-in program and
tests/fixtures/v5-document.json; nothing personal.
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


def setting(page, key):
    return page.evaluate(f"() => [Cali.settings.get('{key}'), JSON.parse(localStorage.getItem('cali.v5')).settings['{key}']]")


def tap(page, selector):
    A.touch_tap(page, selector)


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        gh = A.MockGitHub()
        ctx, page = A.phone(browser, errors, "settings", gh=gh, color_scheme="dark")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))

        # ── the way in and out ──
        gear = '[data-screen="day"] .settings-open'
        placed = """() => { const g = document.querySelectorAll('[data-screen="day"] .settings-open');
            return g.length === 1 && g[0].previousElementSibling === document.querySelector('[data-screen="day"] [data-slot="topbar"]'); }"""
        A.check("a Settings button sits in the day screen's top bar, right after the topbar holder",
                page.evaluate(placed) and page.locator(gear).get_attribute("aria-label") == "Settings")
        page.evaluate("() => { const ids = Cali.dayArgs({}); Cali.tap(ids.dayId, Cali.dayExercises(null, ids.dayId)[0].id, 0); }")
        A.check("it stays there, once, after the day screen is drawn again", page.evaluate(placed))
        tap(page, gear)
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        A.check("tapping it opens the settings route", page.evaluate("() => Cali.current().name") == "settings")
        page.go_back()
        page.wait_for_selector('[data-screen="day"] [data-set]')
        A.check("the phone's back gesture returns to the day", page.evaluate("() => Cali.current().name") == "day")
        tap(page, gear)
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        text = page.locator('[data-screen="settings"]').inner_text()
        want = ["Settings", "How to use", "Rest and alerts", "Test alert", "Pair rest", "1:30", "Rest between sets", "2:00",
                "Alternate paired exercises", "Start rest after a log", "Heads-up 10 s before the end", "Vibration", "Short",
                "Long", "Pulse", "Sound", "Beep", "Bell", "Chirp", "Volume", "Notifications", "Workout",
                "Keep screen awake", "Load step", "Theme", "System", "Light", "Dark", "Data", "GitHub sync",
                "Your own private repository", "Download backup", "Restore from backup"]
        A.check("screen 5 shows every setting with its default", all(w in text for w in want), [w for w in want if w not in text])

        # ── rest times: the next rest reads them through Cali.settings ──
        minus = '[data-key="restPair"][data-step="-15"]'
        tap(page, minus)
        ctx.clock.run_for(1000)
        tap(page, minus)
        A.check("Pair rest minus twice: 90 s -> 60 s, through Cali.settings and saved in the document",
                setting(page, "restPair") == [60, 60] and page.locator('[data-show="restPair"]').inner_text() == "1:00",
                setting(page, "restPair"))
        A.check("a rest started after the change reads 60 s (the rest timer's source)",
                page.evaluate("() => { const t = Cali.timers.start('probe', { duration: Cali.settings.get('restPair') * 1000 }); Cali.timers.stop('probe'); return t.remaining; }") == 60000)
        tap(page, '[data-key="restExercise"][data-step="15"]')
        A.check("Rest between sets plus: 2:00 -> 2:15", setting(page, "restExercise") == [135, 135]
                and page.locator('[data-show="restExercise"]').inner_text() == "2:15", setting(page, "restExercise"))
        for _ in range(3):
            ctx.clock.run_for(1000)
            tap(page, minus)
        A.check("rest stops at 0:15 (its minus is disabled there)", setting(page, "restPair") == [15, 15]
                and page.locator(minus).is_disabled(), setting(page, "restPair"))

        # ── toggles and choices ──
        for key, after in (("restAfterLog", False), ("headsUp", 0), ("keepAwake", False)):
            sel = f'[role="switch"][data-key="{key}"]'
            tap(page, sel)
            ok = setting(page, key) == [after, after] and page.locator(sel).get_attribute("aria-checked") == "false"
            ctx.clock.run_for(1000)
            tap(page, sel)
            back = 10 if key == "headsUp" else True
            A.check(f"{key}: the row's switch turns it off and on again", ok and setting(page, key) == [back, back]
                    and page.locator(sel).get_attribute("aria-checked") == "true", setting(page, key))
        tap(page, '[data-key="loadStep"][data-val="5"]')
        A.check("Load step 5 kg is saved and shown as chosen", setting(page, "loadStep") == [5, 5]
                and page.locator('[data-key="loadStep"][data-val="5"]').get_attribute("aria-pressed") == "true"
                and page.locator('[data-key="loadStep"][data-val="2.5"]').get_attribute("aria-pressed") == "false")
        tap(page, '[data-key="theme"][data-val="light"]')
        light = page.evaluate("() => document.documentElement.dataset.theme")
        tap(page, '[data-key="theme"][data-val="dark"]')
        dark = page.evaluate("() => document.documentElement.dataset.theme")
        tap(page, '[data-key="theme"][data-val="system"]')
        system = page.evaluate("() => [document.documentElement.dataset.theme, matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark']")
        A.check("Theme Light, Dark and System apply app-wide on <html data-theme>; System follows the phone (dark here)",
                (light, dark, system) == ("light", "dark", ["dark", "dark"]) and setting(page, "theme") == ["system", "system"], (light, dark, system))
        page.reload()
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        A.check("after a reload the screen shows the saved values", page.locator('[data-show="restPair"]').inner_text() == "0:15"
                and page.locator('[data-key="loadStep"][data-val="5"]').get_attribute("aria-pressed") == "true")

        # ── alerts: Test alert, Allow notifications, the line while not granted ──
        page.evaluate("""() => { window.__alerts = []; Cali.provide('alert', { alert: k => __alerts.push(k), schedule() {}, cancel() {},
            requestPermission: async () => { __alerts.push('ask'); return Notification.permission; } }); }""")
        tap(page, '[data-act="test"]')
        perm = page.evaluate("() => Notification.permission")
        help_ = page.locator("[data-perm-help]")
        shown = help_.is_visible() and "screen kept awake" in help_.inner_text() and "site settings" in help_.inner_text()
        tap(page, '[data-act="allow"]')
        page.wait_for_timeout(100)
        A.check("Test alert calls Cali.alert('test'); Allow calls Cali.alert.requestPermission()",
                page.evaluate("() => __alerts") == ["test", "ask"], page.evaluate("() => __alerts"))
        A.check("while notifications are not granted, one line says the alert needs the screen kept awake and how to allow them",
                perm != "granted" and shown, (perm, help_.inner_text()))
        # headless Chromium answers 'denied' whatever is granted, so the test sets the value the page reads, then comes
        # back to the app as Tarik does from the browser's site settings
        ctx.add_init_script("Object.defineProperty(Notification, 'permission', { configurable: true, get: () => sessionStorage.getItem('perm') || 'denied' })")
        page.reload()
        page.wait_for_selector('[data-screen="settings"] .settings-body')
        page.evaluate("() => { sessionStorage.setItem('perm', 'granted'); document.dispatchEvent(new Event('visibilitychange')); }")
        A.check("once granted the line is gone and the row says Allowed",
                page.evaluate("() => Notification.permission") == "granted" and not help_.is_visible()
                and page.locator("[data-perm] .pill").inner_text() == "Allowed", page.evaluate("() => Notification.permission"))

        # ── GitHub row without a token ──
        tap(page, '[data-act="github"]')
        A.check("without a token the GitHub row says Off and offers a token field, nothing is sent",
                page.locator("[data-sync-pill]").inner_text() == "Off" and page.locator("#settings-token").is_visible()
                and not gh.requests, (page.locator("[data-sync-pill]").inner_text(), gh.requests[:2]))

        # ── backup ──
        page.evaluate(f"() => Cali.setSyncState({{ token: '{A.TOKEN}' }})")      # the token stays out of a backup
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")   # Data is the last section
        with page.expect_download() as info:
            tap(page, '[data-act="download"]')
        dl = info.value
        body = Path(dl.path()).read_text(encoding="utf-8")
        A.check("Download backup saves the whole v5 document as JSON, named by the date",
                json.loads(body) == A.stored(page) and json.loads(body)["_version"] == 5
                and dl.suggested_filename == "calisthenics-backup-2026-10-26.json", dl.suggested_filename)
        A.check("the token is not in the backup", A.TOKEN not in body)

        # Download, then Restore is the order the restore dialog asks for: the 4 s snack must not hide or eat that tap
        snack = page.evaluate("""() => { const s = document.querySelector('.settings-snack'), r = document.querySelector('[data-act="restore"]');
            const b = s.getBoundingClientRect();
            return { text: s.innerText, lines: Math.round(s.firstChild.getBoundingClientRect().height / 21),
                     clear: r.getBoundingClientRect().bottom <= b.top,
                     through: !document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2).closest('.settings-snack') }; }""")
        choosers = []
        page.on("filechooser", lambda fc: choosers.append(fc))
        page.touchscreen.tap(*A.center(page, '[data-act="restore"]'))
        page.wait_for_timeout(300)
        A.check("after Download the one-line snack leaves Restore in sight, a tap on it opens the file picker, and a tap "
                "on the snack passes to the row under it", snack["lines"] == 1 and snack["clear"] and snack["through"]
                and len(choosers) == 1, (snack, len(choosers)))
        page.evaluate("() => Cali.setSyncState({ token: '' })")

        # ── restore ──
        before = page.evaluate("() => localStorage.getItem('cali.v5')")
        inp = '[data-screen="settings"] [data-restore]'
        refusals = []
        for name, data in (("old.json", json.dumps({"_version": 4, "weeks": [{}]})), ("notes.txt", "not json"),
                           ("other.json", json.dumps({"weeks": []}))):
            page.evaluate("() => document.querySelectorAll('.settings-snack').forEach(e => e.remove())")
            page.set_input_files(inp, files=[{"name": name, "mimeType": "application/json", "buffer": data.encode()}])
            page.wait_for_selector(".settings-snack")
            refusals.append(page.locator(".settings-snack").inner_text())
        A.check("restore refuses a v4 backup, a file that is not JSON and one without _version 5, saying why",
                page.evaluate("() => localStorage.getItem('cali.v5')") == before and page.locator("dialog").count() == 0
                and "old app" in refusals[0] and "not JSON" in refusals[1] and "_version 5" in refusals[2], refusals)
        page.set_input_files(inp, files=[{"name": "b.json", "mimeType": "application/json", "buffer": FIXTURE.encode()}])
        page.wait_for_selector("dialog.settings-dialog[open]")
        ask = page.locator("dialog.settings-dialog").inner_text()
        tap(page, 'dialog.settings-dialog [data-answer="no"]')
        A.check("restore asks first; Cancel changes nothing", "Restore this backup?" in ask and "week 2" in ask
                and page.evaluate("() => localStorage.getItem('cali.v5')") == before, ask)
        clean = page.evaluate("() => { Cali.markClean(); return Cali.dirty(); }")    # as after a sync: nothing unpushed
        page.set_input_files(inp, files=[{"name": "b.json", "mimeType": "application/json", "buffer": FIXTURE.encode()}])
        page.wait_for_selector("dialog.settings-dialog[open]")
        tap(page, 'dialog.settings-dialog [data-answer="yes"]')
        page.wait_for_timeout(100)
        got = page.evaluate("() => [Cali.doc().programs[0].id, Cali.week().n, Cali.dirty(), JSON.parse(localStorage.getItem('cali.v5')).programs[0].id]")
        A.check("Restore replaces the log with the v5 backup (saved; a phone that was in sync is marked for sync again)",
                clean is False and got == ["fixture", 2, True, "fixture"], (clean, got))
        A.check("the restored settings show on the screen", page.locator('[data-show="restPair"]').inner_text() == "1:30"
                and page.locator('[data-key="theme"][data-val="system"]').get_attribute("aria-pressed") == "true")

        A.check("no token: the settings screen sent no request to GitHub", not gh.requests, gh.requests[:3])
        keys = page.evaluate("() => Object.keys(localStorage)")
        A.check("Settings wrote only cali.* keys", all(k.startswith("cali.") for k in keys), keys)
        ctx.close()

        # ── a saved log that cannot be read: the document in memory is core's empty stand-in, never a backup ──
        raw = '{"_version": 5}'
        pctx, pg = A.phone(browser, [], "settings-problem")      # core's own console error for the problem is expected
        pctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ localStorage.setItem('cali.v5', {json.dumps(raw)}); sessionStorage.setItem('seeded', '1'); }}")
        A.open_day(pg, url)
        pg.evaluate("() => Cali.go('settings')")
        pg.wait_for_selector('[data-screen="settings"] .settings-body')
        downloads = []
        pg.on("download", lambda d: downloads.append(d))
        tap(pg, '[data-act="download"]')
        pg.wait_for_selector(".settings-snack")
        pg.wait_for_timeout(300)
        note = pg.locator(".settings-snack").inner_text()
        A.check("while the saved log cannot be read, Download saves no blank stand-in and says why; the stored text stays",
                not downloads and note.startswith("No backup made.") and "could not be read" in note
                and pg.evaluate("() => localStorage.getItem('cali.v5')") == raw, (len(downloads), note))
        pctx.close()
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
