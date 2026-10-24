"""GitHub sync (app/sync.js, Task-03): the old app's sync ported, with the v5 push policy and the v4 archive.

Run from the repo root: python tests/test_sync.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py; GitHub is the mocked Contents API (Repo below, built on acceptance.MockGitHub: several paths, git
blob shas as GitHub gives them, and failures to inject). Never a real token: the token is acceptance.TOKEN.
States: no token (no request at all), a token copied from the old app's cali_sync_config with the old v4 file in the
repo, a token typed in Settings with no file yet, a v5 file already there, and a saved log that cannot be read.
"""
import base64
import datetime
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PATH = "calisthenics-data.json"
ARCHIVE = "archive/calisthenics-data-v4.json"
FIXTURE = (A.ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8")
OLD_CONFIG = json.dumps({"owner": "Estaed", "repo": "Calisthenics-Data", "branch": "main", "path": PATH,
                         "token": A.TOKEN, "deviceName": "test"})
# the old app's file: v4 shape, Turkish text, so a copy that is not byte for byte shows
V4 = json.dumps({"_version": 4, "updatedAt": "2026-09-20T08:00:00.000Z", "plans": [{"id": "p1", "name": "A Ağır"}],
                 "weeks": [{"weekNumber": 1, "completed": False, "days": [{"id": "A", "exercises": [
                     {"name": "Ağırlıklı Barfiks", "sets": 3, "reps": "6,6,5", "weight": "BW", "status": "done"}]}]}]},
                ensure_ascii=False, indent=1)


class Repo(A.MockGitHub):
    """Estaed/Calisthenics-Data with any number of files. fail[n] = status (the n-th PUT is refused) or 'drop' (the
    n-th PUT is written but its answer never arrives); before_put(name, body) runs before a PUT is judged."""

    def __init__(self, files=None):
        super().__init__()
        self.files = dict(files or {})
        self.fail = {}
        self.attempts = 0
        self.bodies = []          # every PUT body as text, for the token check
        self.put_names = []       # the file of every PUT, in order
        self.before_put = None

    @staticmethod
    def blob(text):
        data = text.encode("utf-8")
        return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

    def sha_of(self, name):
        return self.blob(self.files[name]) if name in self.files else None

    def handle(self, route):
        req = route.request
        self.requests.append(f"{req.method} {req.url}")
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=self.CORS)
        if req.headers.get("authorization") != f"Bearer {A.TOKEN}":
            return route.fulfill(status=401, headers=self.CORS, body='{"message":"Bad credentials"}')
        path = urllib.parse.urlsplit(req.url).path
        if path == self.REPO:
            return route.fulfill(status=200, headers=self.CORS, content_type="application/json", body="{}")
        prefix = self.REPO + "/contents/"
        if not path.startswith(prefix):
            return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
        name = urllib.parse.unquote(path[len(prefix):])
        if req.method == "GET":
            if name not in self.files:
                return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
            raw = base64.b64encode(self.files[name].encode("utf-8")).decode()
            body = {"sha": self.sha_of(name), "content": "\n".join(raw[i:i + 60] for i in range(0, len(raw), 60)),
                    "encoding": "base64", "size": len(self.files[name].encode("utf-8"))}
            return route.fulfill(status=200, headers=self.CORS, content_type="application/json", body=json.dumps(body))
        if req.method == "PUT":
            self.attempts += 1
            body = json.loads(req.post_data or "{}")
            self.bodies.append(req.post_data or "")
            self.put_names.append(name)
            if self.before_put:
                self.before_put(name, body)
            fail = self.fail.get(self.attempts)
            if isinstance(fail, int):
                return route.fulfill(status=fail, headers=self.CORS, body='{"message":"injected"}')
            if body.get("sha") != self.sha_of(name):
                return route.fulfill(status=409, headers=self.CORS, body='{"message":"sha mismatch"}')
            self.files[name] = base64.b64decode(body["content"]).decode("utf-8")
            self.puts += 1
            if fail == "drop":
                return route.abort()
            return route.fulfill(status=201, headers=self.CORS, content_type="application/json",
                                 body=json.dumps({"content": {"sha": self.sha_of(name), "path": name}}))
        return route.fulfill(status=405, headers=self.CORS)


def app_errors(errors):
    """Page errors and console errors, without Chromium's own line for an HTTP error answer the test asked for."""
    return [e for e in errors if "Failed to load resource" not in e]


def settle(page):
    """Waits until no sync pass runs (the wall clock bounds it; sync uses no timers)."""
    page.wait_for_timeout(200)
    A.poll(page, "() => !CaliSync.status().running")


def status(page):
    return page.evaluate("() => CaliSync.status()")


def local_doc(page):
    return page.evaluate("() => JSON.parse(JSON.stringify(Cali.doc()))")


def day_ids(page):
    return page.evaluate("""() => { const d = Cali.program().days; return { a: d[0].id, b: d[1].id,
        ea: d[0].exercises[0].id, eb: d[1].exercises[0].id }; }""")


def phone(browser, errors, tag, gh, old_config=False, clock=True):
    ctx, page = A.phone(browser, errors, tag, gh=gh, clock=clock)
    if old_config:
        ctx.add_init_script(f"localStorage.setItem('cali_sync_config', {json.dumps(OLD_CONFIG)})")
    page.on("console", lambda m: errors.append(f"[{tag}] {m.type}: {m.text}") if A.TOKEN in m.text else None)
    return ctx, page


def finish_day(page, day):
    """What the workout's Done does (Task-01): store the day's finishedAt, then emit dayDone."""
    page.evaluate(f"""() => {{ Cali.change(d => {{ const x = d.weeks[d.weeks.length - 1].days[{json.dumps(day)}];
        x.startedAt = x.startedAt || Cali.iso(); x.finishedAt = Cali.iso(); }}, {{ why: 'done' }});
        Cali.emit('dayDone', {{ week: Cali.week().n, dayId: {json.dumps(day)} }}); }}""")


def scenario_no_token(browser, url):
    errors = []
    gh = A.MockGitHub()
    ctx, page = phone(browser, errors, "no-token", gh)
    A.open_day(page, url)
    ids = day_ids(page)
    page.evaluate(f"() => Cali.tap({json.dumps(ids['a'])}, {json.dumps(ids['ea'])}, 0)")
    finish_day(page, ids["a"])
    page.evaluate("() => { Cali.change(d => { d.programs[0].days[0].exercises[0].target += 1; }, { why: 'program' }); Cali.emit('weekFinished', { week: 1, next: 2 }); }")
    page.evaluate("() => CaliSync.now({ manual: true })")
    settle(page)
    s = status(page)
    A.check("no token: logging, Done, a program edit and Sync now send no request; the app works on the phone",
            not gh.requests and s["configured"] is False and s["lastError"] is None
            and A.stored(page)["weeks"][0]["days"][ids["a"]]["finishedAt"], (gh.requests[:3], s))
    A.check("no token: the service worker controls the app", A.wait_controlled(page))
    ctx.set_offline(True)
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    A.check("no token: the app opens offline and says sync is off", status(page)["configured"] is False and not gh.requests)
    ctx.close()
    A.check("no token: no console or page errors", not app_errors(errors), errors[:5])


def scenario_v4(browser, url):
    errors = []
    gh = Repo({PATH: V4})
    gh.fail = {2: 500}                       # the archive copy is written, the replace is refused
    ctx, page = phone(browser, errors, "v4", gh, old_config=True)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    settle(page)
    s = page.evaluate("() => Cali.syncState()")
    A.check("first open copies the old app's token into cali.sync once (cali_sync_config is only read)",
            s.get("token") == A.TOKEN and page.evaluate("() => localStorage.getItem('cali_sync_config')") == OLD_CONFIG, s.get("token"))
    A.check("a v4 remote is copied byte for byte to archive/calisthenics-data-v4.json before anything else",
            gh.files.get(ARCHIVE) == V4 and gh.put_names == [ARCHIVE, PATH] and "sha" not in json.loads(gh.bodies[0]),
            (gh.put_names, gh.files.get(ARCHIVE) == V4))
    A.check("the failed replace leaves the v4 file intact and says why",
            gh.files.get(PATH) == V4 and "Could not write to GitHub (500)" in (status(page)["lastError"] or ""), status(page)["lastError"])
    doc = local_doc(page)
    A.check("the v4 document is never adopted (the phone keeps its own v5 document)",
            doc["_version"] == 5 and doc["programs"] == [A.default_program()], doc["programs"][0]["id"])

    gh.fail = {}
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    settle(page)
    remote = json.loads(gh.files[PATH])
    A.check("the next open retries: the v5 document replaces the v4 file, the archive stays as it was (no second copy)",
            remote == local_doc(page) and remote["_version"] == 5 and gh.files[ARCHIVE] == V4 and gh.attempts == 3,
            (gh.attempts, remote.get("_version")))
    s = status(page)
    A.check("after the replace the phone is in sync (clean, no error)", s["lastError"] is None and s["dirty"] is False and s["lastSyncedAt"], s)

    # the token is in no document, push, backup or log line
    leaks = [n for n, t in (("cali.v5", page.evaluate("() => localStorage.getItem('cali.v5')")),
                            ("a PUT", "".join(base64.b64decode(json.loads(b)["content"]).decode("utf-8") for b in gh.bodies)),
                            ("the remote", gh.files[PATH])) if A.TOKEN in t]
    A.check("the token never enters the document or a pushed file", not leaks, leaks)

    # disconnect in Settings; the old token is not copied again
    page.evaluate("() => Cali.go('settings')")
    page.wait_for_selector('[data-screen="settings"]')
    A.touch_tap(page, '[data-act="github"]')
    A.touch_tap(page, '[data-act="disconnect"]')
    A.touch_tap(page, '.settings-dialog [data-answer="yes"]')
    n = len(gh.requests)
    page.reload()
    page.wait_for_selector('[data-screen="settings"]')
    settle(page)
    A.check("Disconnect removes the token; a reload does not copy the old one again and sends nothing",
            not page.evaluate("() => Cali.syncState().token") and len(gh.requests) == n
            and page.evaluate("() => localStorage.getItem('cali_sync_config')") == OLD_CONFIG,
            (page.evaluate("() => Cali.syncState().token"), gh.requests[n:]))
    ctx.close()
    A.check("v4 scenario: no console or page errors, no log line with the token", not app_errors(errors), app_errors(errors)[:5])


def scenario_policy(browser, url):
    errors = []
    gh = Repo()
    ctx, page = phone(browser, errors, "policy", gh)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    ids = day_ids(page)
    A_, B_, EA, EB = (json.dumps(ids[k]) for k in ("a", "b", "ea", "eb"))

    # a token typed in Settings: no file yet, so the phone's document creates it
    page.evaluate("() => Cali.go('settings')")
    page.wait_for_selector('[data-screen="settings"]')
    A.touch_tap(page, '[data-act="github"]')
    page.fill("#settings-token", A.TOKEN)
    A.touch_tap(page, '[data-act="connect"]')
    settle(page)
    A.check("Connect with a token and no file there: the file is created from the phone's document",
            gh.puts == 1 and json.loads(gh.files[PATH]) == local_doc(page) and page.locator("[data-sync-pill]").inner_text() == "Synced",
            (gh.puts, page.locator("[data-sync-pill]").inner_text()))
    page.evaluate("() => Cali.back()")
    page.wait_for_selector('[data-screen="day"] [data-set]')

    # mid-day: logs, timers, the page hidden and shown, back online: nothing goes
    n = len(gh.requests)
    page.evaluate(f"() => {{ Cali.tap({A_}, {EA}, 0); Cali.tap({A_}, {EA}, 1); Cali.timers.start('rest', {{ duration: 90000 }}); }}")
    ctx.clock.run_for(10 * 60 * 1000)
    page.evaluate("""() => { for (const v of ['hidden', 'visible']) {
        Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => v });
        document.dispatchEvent(new Event('visibilitychange')); }
        window.dispatchEvent(new Event('online')); }""")
    settle(page)
    s = status(page)
    A.check("a set logged mid-day waits: timers, hiding and showing the app, coming online push nothing",
            gh.puts == 1 and len(gh.requests) == n and s["dirty"] and not s["due"], (gh.puts, gh.requests[n:], s))

    finish_day(page, ids["a"])
    settle(page)
    A.check("Done (dayDone) pushes the day at once", gh.puts == 2 and json.loads(gh.files[PATH]) == local_doc(page)
            and status(page)["dirty"] is False, gh.puts)

    page.evaluate(f"() => Cali.log({A_}, {EA}, 1, 4)")
    settle(page)
    A.check("an edit to a finished day pushes at once", gh.puts == 3
            and json.loads(gh.files[PATH])["weeks"][0]["days"][ids["a"]]["exercises"][ids["ea"]]["sets"][1]["r"] == 4, gh.puts)

    page.evaluate(f"() => Cali.tap({B_}, {EB}, 0)")
    settle(page)
    A.check("a log on a day not finished does not push", gh.puts == 3, gh.puts)

    page.evaluate("() => Cali.change(d => { d.programs[0].days[0].exercises[0].target += 1; }, { why: 'program' })")
    settle(page)
    A.check("an edit to a program pushes at once (with the waiting log)", gh.puts == 4 and status(page)["dirty"] is False, gh.puts)

    page.evaluate("() => Cali.change(d => { d.weeks[0].finishedAt = Cali.iso(); d.weeks.push(Cali.weekFrom(d.programs[0], 2)); }, { why: 'week' })")
    settle(page)
    before = gh.puts
    page.evaluate("() => Cali.emit('weekFinished', { week: 1, next: 2 })")
    settle(page)
    A.check("Finish week (weekFinished) pushes at once", before == 4 and gh.puts == 5
            and len(json.loads(gh.files[PATH])["weeks"]) == 2, (before, gh.puts))

    # older than 12 h: goes on the next open, not before
    page.evaluate(f"() => Cali.tap({A_}, {EA}, 0)")
    settle(page)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(hours=1))
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    settle(page)
    gets = sum(1 for r in gh.requests if r.startswith("GET") and r.split("?")[0].endswith(PATH))
    A.check("an open pulls; a change younger than 12 h stays on the phone", gh.puts == 5 and status(page)["dirty"], gh.puts)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(hours=12, minutes=30))
    n = len(gh.requests)
    page.evaluate("""() => { for (const v of ['hidden', 'visible']) {
        Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => v });
        document.dispatchEvent(new Event('visibilitychange')); }
        window.dispatchEvent(new Event('online')); }""")
    settle(page)
    A.check("a change older than 12 h waits for an open: the screen off and on or coming online mid-workout send nothing",
            status(page)["due"] and len(gh.requests) == n, gh.requests[n:])
    ctx.clock.pause_at(A.NOW + datetime.timedelta(hours=13))
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    settle(page)
    gets2 = sum(1 for r in gh.requests if r.startswith("GET") and r.split("?")[0].endswith(PATH))
    A.check("a change older than 12 h is pushed on the next open", gh.puts == 6 and gets2 == gets + 1
            and status(page)["dirty"] is False and json.loads(gh.files[PATH]) == local_doc(page), (gh.puts, gets, gets2))

    # a due push that failed (no signal) is retried when the phone is back online
    gh.fail = {gh.attempts + 1: 500}
    page.evaluate("() => Cali.change(d => { d.programs[0].days[0].exercises[0].target += 1; }, { why: 'program' })")
    settle(page)
    failed_once = gh.puts == 6 and status(page)["due"]
    page.evaluate("() => window.dispatchEvent(new Event('online'))")
    settle(page)
    A.check("a due push that failed is retried when the phone comes back online", failed_once and gh.puts == 7
            and status(page)["lastError"] is None, (failed_once, gh.puts))

    # the write landed but its answer was lost, then a set is logged before the next open: the remote is no longer the
    # phone's document, so only the sha the phone sent (pendingSha) tells it is its own; no conflict, the set goes too
    gh.fail = {gh.attempts + 1: "drop"}
    page.evaluate("() => Cali.change(d => { d.programs[0].days[0].exercises[0].target += 1; }, { why: 'program' })")
    settle(page)
    lost = gh.puts == 8 and status(page)["lastError"]
    page.evaluate(f"() => Cali.tap({B_}, {EB}, 0)")
    page.reload()
    page.wait_for_selector('[data-screen="day"] [data-set]')
    settle(page)
    s = status(page)
    A.check("a push whose answer was lost is recognised by its sha after a new log: no conflict, the new set goes too",
            bool(lost) and not s["conflict"] and s["lastError"] is None and s["dirty"] is False and gh.puts == 9
            and json.loads(gh.files[PATH]) == local_doc(page) and page.locator("dialog.sync-dialog").count() == 0, (lost, gh.puts, s))
    ctx.close()
    A.check("policy scenario: no console or page errors", not app_errors(errors), app_errors(errors)[:5])


def scenario_finished_edits(browser, url):
    """Edits that are not a log (the sheet pencil's load fix goes through Cali.change): on a finished day, or on any day
    of a finished week, they push at once; on a day still open they wait like a set."""
    errors = []
    gh = Repo()
    ctx, page = phone(browser, errors, "finished-edits", gh, old_config=True)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    settle(page)
    ids = day_ids(page)
    A_, B_, EA, EB = (json.dumps(ids[k]) for k in ("a", "b", "ea", "eb"))

    def load_fix(day, ex):
        page.evaluate(f"() => Cali.change(d => {{ d.weeks[0].days[{day}].exercises[{ex}].load += 2.5; }}, {{ why: 'load' }})")
        settle(page)

    page.evaluate(f"() => Cali.tap({A_}, {EA}, 0)")
    finish_day(page, ids["a"])
    settle(page)
    done = gh.puts
    load_fix(A_, EA)
    A.check("a load fix on a finished day (Cali.change, not a log) pushes at once", done == 2 and gh.puts == 3
            and json.loads(gh.files[PATH]) == local_doc(page) and status(page)["dirty"] is False, (done, gh.puts))
    load_fix(B_, EB)
    A.check("the same load fix on a day still open waits", gh.puts == 3 and status(page)["dirty"] and not status(page)["due"], gh.puts)
    page.evaluate("() => { Cali.change(d => { d.weeks[0].finishedAt = Cali.iso(); d.weeks.push(Cali.weekFrom(d.programs[0], 2)); }, { why: 'week' }); Cali.emit('weekFinished', { week: 1, next: 2 }); }")
    settle(page)
    week = gh.puts
    load_fix(B_, EB)                  # day B of week 1 was never done: only the finished week makes this urgent
    A.check("a load fix on a day of a finished week (the day itself not done) pushes at once", week == 4 and gh.puts == 5
            and json.loads(gh.files[PATH]) == local_doc(page) and status(page)["dirty"] is False, (week, gh.puts))
    ctx.close()
    A.check("finished-edits scenario: no console or page errors", not app_errors(errors), app_errors(errors)[:5])


def scenario_problem(browser, url):
    """The log saved on the phone cannot be read, so core holds its empty stand-in. An unpushed Done waits (dirty, due,
    the remote sha the phone last saw): sync must not push the stand-in over the real file on GitHub."""
    errors = []
    gh = Repo({PATH: FIXTURE})
    state = {"token": A.TOKEN, "legacyChecked": True, "lastSha": gh.sha_of(PATH), "dirty": True, "changes": 3,
             "dirtySince": "2026-10-26T08:00:00.000Z", "pushDue": True}
    ctx, page = phone(browser, errors, "problem", gh)
    ctx.add_init_script(f"localStorage.setItem('cali.v5', {json.dumps(json.dumps({'_version': 5}))});"
                        f" localStorage.setItem('cali.sync', {json.dumps(json.dumps(state))});")
    A.open_day(page, url)
    settle(page)
    page.evaluate("() => CaliSync.now({ manual: true })")
    settle(page)
    s = status(page)
    A.check("while the saved log cannot be read, neither the open nor Sync now pushes the empty stand-in; GitHub's file "
            "stays and sync says why", s["problem"] and gh.attempts == 0 and gh.files[PATH] == FIXTURE
            and (s["lastError"] or "").startswith("Sync is off:"), (gh.attempts, s["lastError"]))
    ctx.close()
    # core's own console error names the problem; nothing else may fail
    rest = [e for e in app_errors(errors) if "could not be read" not in e]
    A.check("problem scenario: no other console or page errors", not rest, rest[:5])


def scenario_in_flight(browser, url):
    """An edit to the finished day lands while its Done push is in flight: GitHub has answered, the phone has not yet
    marked the push clean. That edit must stay dirty and go in a second push."""
    errors = []
    gh = Repo()
    ctx, page = phone(browser, errors, "in-flight", gh, old_config=True)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    settle(page)
    ids = day_ids(page)
    A_, EA = json.dumps(ids["a"]), json.dumps(ids["ea"])
    page.evaluate(f"() => {{ Cali.tap({A_}, {EA}, 0); Cali.tap({A_}, {EA}, 1); }}")
    page.evaluate(f"""() => {{ const f = window.fetch; let once = true;
        window.fetch = async (u, o) => {{ const r = await f(u, o);
          if (once && o && o.method === 'PUT') {{ once = false; Cali.log({A_}, {EA}, 1, 3); }}
          return r; }}; }}""")
    finish_day(page, ids["a"])
    settle(page)
    remote = json.loads(gh.files[PATH])
    s = status(page)
    A.check("an edit made while a push is in flight stays dirty and goes in the next push, never marked clean unsent",
            gh.puts == 3 and remote["weeks"][0]["days"][ids["a"]]["exercises"][ids["ea"]]["sets"][1]["r"] == 3
            and remote == local_doc(page) and s["dirty"] is False, (gh.puts, s))
    ctx.close()
    A.check("in-flight scenario: no console or page errors", not app_errors(errors), app_errors(errors)[:5])


def scenario_conflict(browser, url):
    errors = []
    gh = Repo()
    ctx, page = phone(browser, errors, "conflict", gh, old_config=True)
    A.open_day(page, url)
    ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
    settle(page)
    ids = day_ids(page)
    A_, EA = json.dumps(ids["a"]), json.dumps(ids["ea"])

    def remote_edit(kg):
        """Another device writes: the same document with a body-weight line."""
        d = json.loads(gh.files[PATH])
        d["body"] = d["body"] + [{"date": "2026-10-25", "kg": kg}]
        d["updatedAt"] = "2026-10-25T10:00:00.000Z"
        gh.files[PATH] = json.dumps(d, indent=1)

    first = gh.puts == 1
    remote_edit(81.5)
    theirs = gh.files[PATH]
    page.evaluate(f"() => Cali.tap({A_}, {EA}, 0)")
    finish_day(page, ids["a"])
    settle(page)
    dialog = page.locator("dialog.sync-dialog[open]")
    text = dialog.inner_text() if dialog.count() else ""
    A.check("a remote sha that changed while the phone has changes opens the conflict choice, never an overwrite",
            first and dialog.count() == 1 and gh.files[PATH] == theirs and gh.puts == 1 and status(page)["conflict"],
            (first, dialog.count(), gh.puts))
    A.check("the conflict choice is in English: both sides, Use this phone's, Take GitHub's, Not now",
            all(w in text for w in ("Sync conflict", "This phone", "GitHub", "Updated", "Week 1", "1 set logged", "0 sets logged",
                                     "Use this phone's", "Take GitHub's", "Not now")), text)

    A.touch_tap(page, 'dialog.sync-dialog [data-choice="later"]')
    n = len(gh.requests)
    page.evaluate(f"() => Cali.log({A_}, {EA}, 0, 5)")
    settle(page)
    s = status(page)
    A.check("Not now closes it and pauses sync: a due push sends nothing, nothing is overwritten",
            page.locator("dialog.sync-dialog").count() == 0 and s["paused"] and len(gh.requests) == n and gh.files[PATH] == theirs, s)

    page.evaluate("() => CaliSync.now({ manual: true })")
    settle(page)
    A.touch_tap(page, 'dialog.sync-dialog [data-choice="remote"]')
    settle(page)
    doc = local_doc(page)
    A.check("Take GitHub's replaces the phone's document with the remote one, clean, no push",
            doc == json.loads(theirs) and status(page)["dirty"] is False and gh.puts == 1, (doc["body"], gh.puts))

    remote_edit(82.0)
    finish_day(page, ids["a"])        # GitHub's document had the day open; Done again makes a push due
    settle(page)
    A.check("a second conflict opens the choice again", page.locator("dialog.sync-dialog[open]").count() == 1,
            (status(page), page.evaluate("() => Cali.syncState().pushDue"), gh.requests[-3:]))
    A.touch_tap(page, 'dialog.sync-dialog [data-choice="local"]')
    settle(page)
    A.check("Use this phone's writes the phone's document over GitHub's (with GitHub's sha)",
            gh.puts == 2 and json.loads(gh.files[PATH]) == local_doc(page) and status(page)["dirty"] is False, gh.puts)

    # a PUT refused as stale (another device wrote between the read and the write) reads again and asks
    gh.before_put = lambda name, body: (remote_edit(83.0), setattr(gh, "before_put", None))
    page.evaluate(f"() => Cali.log({A_}, {EA}, 2, 6)")
    settle(page)
    A.check("a PUT refused for its sha (409) reads the remote again and opens the choice, nothing overwritten",
            page.locator("dialog.sync-dialog[open]").count() == 1 and json.loads(gh.files[PATH])["body"][-1]["kg"] == 83.0
            and gh.puts == 2, (gh.puts, page.locator("dialog.sync-dialog[open]").count()))
    page.keyboard.press("Escape")
    A.check("Escape (the back gesture) on the choice means Not now", page.locator("dialog.sync-dialog").count() == 0
            and status(page)["paused"])
    ctx.close()
    A.check("conflict scenario: no console or page errors", not app_errors(errors), app_errors(errors)[:5])


def scenario_remote(browser, url):
    """A phone that has logged nothing adopts a v5 file; a newer or broken file is never adopted or overwritten."""
    errors = []
    gh = Repo({PATH: FIXTURE})
    ctx, page = phone(browser, errors, "adopt", gh, old_config=True)
    A.open_day(page, url)
    settle(page)
    A.check("a new phone with the token adopts the v5 file on open (no push)",
            local_doc(page)["programs"][0]["id"] == "fixture" and gh.puts == 0 and status(page)["dirty"] is False, gh.puts)
    ctx.close()

    # a phone that logged before it was connected (new or reset phone, or Disconnect and Connect again) has no last sha
    gh = Repo({PATH: FIXTURE})
    ctx, page = phone(browser, errors, "logged-first", gh)
    A.open_day(page, url)
    ids = day_ids(page)
    page.evaluate(f"() => Cali.tap({json.dumps(ids['a'])}, {json.dumps(ids['ea'])}, 0)")
    page.evaluate(f"() => CaliSync.connect('{A.TOKEN}')")
    settle(page)
    doc = local_doc(page)
    A.check("a phone with logs and no last sync that connects gets the conflict choice, never GitHub's file in silence",
            page.locator("dialog.sync-dialog[open]").count() == 1 and status(page)["conflict"]
            and doc["weeks"][0]["days"][ids["a"]]["exercises"][ids["ea"]]["sets"][0] is not None
            and gh.files[PATH] == FIXTURE and gh.attempts == 0, (doc["programs"][0]["id"], gh.attempts))
    ctx.close()

    for name, text, want in (("newer", json.dumps({**json.loads(FIXTURE), "_version": 6}), "newer version"),
                             ("broken", "{ not json", "not valid JSON")):
        gh = Repo({PATH: text})
        ctx, page = phone(browser, errors, name, gh, old_config=True)
        A.open_day(page, url)
        settle(page)
        s = status(page)
        A.check(f"a {name} remote file is neither adopted nor overwritten, and sync says why",
                want in (s["lastError"] or "") and gh.attempts == 0 and gh.files[PATH] == text
                and local_doc(page)["programs"] == [A.default_program()], s["lastError"])
        ctx.close()

    gh = Repo({PATH: FIXTURE})
    ctx, page = phone(browser, errors, "bad-token", gh)
    ctx.add_init_script("localStorage.setItem('cali_sync_config', JSON.stringify({ token: 'WRONG' }))")
    A.open_day(page, url)
    settle(page)
    A.check("a token GitHub refuses (401): the old app's message, in English", status(page)["lastError"] == "The token is invalid or has expired.",
            status(page)["lastError"])
    ctx.close()
    A.check("remote scenarios: no console or page errors", not app_errors(errors), app_errors(errors)[:5])


def main():
    srv, site, url = A.start_site()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fn in (("no token", scenario_no_token), ("v4 archive", scenario_v4), ("push policy", scenario_policy),
                         ("finished edits", scenario_finished_edits), ("push in flight", scenario_in_flight),
                         ("conflict", scenario_conflict), ("remote file", scenario_remote), ("unreadable log", scenario_problem)):
            A.guarded(f"sync scenario: {name}", fn, browser, url)
        browser.close()
    srv.shutdown()
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
