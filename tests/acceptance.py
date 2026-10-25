"""Calisthenics acceptance gate. Run from the repo root:  python tests/acceptance.py

Serves THIS repo (the folder holding tests/) under /Sthenos/, the GitHub Pages path, on a free local port,
mocks the GitHub API, and drives Chromium as Tarik's phone: 360 x 740, touch, Australia/Darwin. Then runs every
tests/test_*.py as `python <file>` from the repo root; a file's exit code is its verdict. Prints PASS or FAIL per
check and exits 1 on any FAIL. Nothing is written to the repo (a test that needs files writes under .tmp/).

Time: every phone context installs Playwright's clock at NOW, so Cali.now() (Date.now) and setTimeout follow the
test, never the wall clock: a gesture or a timer moves only when a test runs the clock.

Hooks the gate relies on (keep them when a screen is redrawn): window.Cali (app/core.js); the 'day' route shows
the day's sets as elements with data-set="<dayId>:<exId>:<i>"; a tap is one touch on a set cell (touchStart and
touchEnd at one point with no clock movement), a hold keeps the touch down while the clock runs 800 ms; gestures
are 1 s of clock time apart.
"""
import base64
import datetime
import functools
import hashlib
import http.server
import json
import mimetypes
import os
import pathlib
import re
import socketserver
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "/Sthenos/"
DARWIN = datetime.timezone(datetime.timedelta(hours=9, minutes=30))
NOW = datetime.datetime(2026, 10, 26, 7, 0, tzinfo=DARWIN)        # Monday, the first gym day
PHONE = dict(viewport={"width": 360, "height": 740}, device_scale_factor=3, is_mobile=True, has_touch=True,
             timezone_id="Australia/Darwin", locale="en-AU")
TOKEN = "TESTTOKEN"
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


# ── a GitHub Pages stand-in: this repo under /Sthenos/, with overlays and a switch that cuts the network ──
class Site:
    def __init__(self):
        self.overlay = {}        # path -> bytes served instead of the file
        self.down = False        # True: every request is dropped unanswered, like a phone with no network
        self.paths = []          # every path asked for while up


class Handler(http.server.SimpleHTTPRequestHandler):
    site = None

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        site = self.site
        path = urllib.parse.urlsplit(self.path).path
        if site.down:
            self.close_connection = True
            return
        site.paths.append(path)
        if path == BASE.rstrip("/"):
            self.send_response(301)
            self.send_header("Location", BASE)
            self.end_headers()
            return
        if path in site.overlay:
            body = site.overlay[path]
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not path.startswith(BASE):
            self.send_error(404, "outside " + BASE)
            return
        self.path = "/" + self.path[len(BASE):]
        super().do_GET()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def start_site():
    site = Site()
    handler = type("SiteHandler", (Handler,), {"site": site})
    srv = Server(("127.0.0.1", 0), functools.partial(handler, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, site, f"http://127.0.0.1:{srv.server_address[1]}{BASE}"


# ── mock GitHub (Contents API of Estaed/Calisthenics-Data) ──
class MockGitHub:
    CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*",
            "access-control-allow-methods": "GET,PUT,OPTIONS"}
    REPO = "/repos/Estaed/Calisthenics-Data"
    FILE = REPO + "/contents/calisthenics-data.json"

    def __init__(self, text=None, sha=None):
        self.text, self.sha = text, sha
        self.puts = 0
        self.requests = []

    def handle(self, route):
        req = route.request
        self.requests.append(f"{req.method} {req.url}")
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=self.CORS)
        if req.headers.get("authorization") != f"Bearer {TOKEN}":
            return route.fulfill(status=401, headers=self.CORS, body='{"message":"Bad credentials"}')
        path = urllib.parse.urlsplit(req.url).path
        if path == self.REPO:
            return route.fulfill(status=200, headers=self.CORS, content_type="application/json", body="{}")
        if path != self.FILE:
            return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
        if req.method == "GET":
            if self.text is None:
                return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
            raw = base64.b64encode(self.text.encode("utf-8")).decode()
            body = {"sha": self.sha, "content": "\n".join(raw[i:i + 60] for i in range(0, len(raw), 60)),
                    "encoding": "base64", "size": len(self.text.encode("utf-8"))}
            return route.fulfill(status=200, headers=self.CORS, content_type="application/json", body=json.dumps(body))
        if req.method == "PUT":
            body = json.loads(req.post_data or "{}")
            if self.sha is not None and body.get("sha") != self.sha:
                return route.fulfill(status=409, headers=self.CORS, body='{"message":"sha mismatch"}')
            self.text = base64.b64decode(body["content"]).decode("utf-8")
            self.sha = hashlib.sha1(self.text.encode("utf-8")).hexdigest()
            self.puts += 1
            return route.fulfill(status=201, headers=self.CORS, content_type="application/json",
                                 body=json.dumps({"content": {"sha": self.sha}}))
        return route.fulfill(status=405, headers=self.CORS)


# ── browser helpers ───────────────────────────────────────────────
def watch(page, errors, tag):
    page.on("pageerror", lambda e: errors.append(f"[{tag}] pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] console: {m.text}"))
    page.on("dialog", lambda d: d.accept())


def phone(browser, errors, tag, gh=None, clock=True, **extra):
    """A phone context with the mocked GitHub API and, by default, Playwright's clock installed at NOW (running)."""
    ctx = browser.new_context(**PHONE, **extra)
    ctx.route("https://api.github.com/**", (gh or MockGitHub()).handle)
    if clock:
        ctx.clock.install(time=NOW)
    page = ctx.new_page()
    watch(page, errors, tag)
    return ctx, page


def open_day(page, url):
    page.goto(url)
    page.wait_for_selector('[data-screen="day"] [data-set]')


def stored(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('cali.v5'))")


def poll(page, js, timeout=15.0):
    """Evaluates js (an async function is awaited) until it is truthy; the wall clock bounds the wait only."""
    end = time.monotonic() + timeout
    while True:
        value = page.evaluate(js)
        if value or time.monotonic() > end:
            return value
        page.wait_for_timeout(100)


def wait_controlled(page):
    return poll(page, "async () => { await navigator.serviceWorker.ready; return navigator.serviceWorker.controller !== null; }")


def go_offline(ctx, site):
    ctx.set_offline(True)
    site.down = True


def go_online(ctx, site):
    ctx.set_offline(False)
    site.down = False


def center(page, selector):
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def touch_tap(page, selector):
    page.locator(selector).scroll_into_view_if_needed()
    x, y = center(page, selector)
    page.touchscreen.tap(x, y)


def touch_hold(page, ctx, selector, ms=800):
    page.locator(selector).scroll_into_view_if_needed()
    x, y = center(page, selector)
    cdp = ctx.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    ctx.clock.run_for(ms)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    cdp.detach()


def default_program():
    text = (ROOT / "app" / "default-program.js").read_text(encoding="utf-8")
    body = text.split("self.CALI_DEFAULT_PROGRAM = ", 1)[1].rstrip().rstrip(";")
    return json.loads(body)


DEFAULTS = {"restPair": 90, "restExercise": 120, "restAfterLog": True, "headsUp": 10, "alternatePairs": False,
            "vibrate": True, "buzz": "short", "sound": True, "tone": "beep", "volume": 2, "keepAwake": True,
            "loadStep": 2.5, "theme": "system"}


# ── checks ────────────────────────────────────────────────────────
def check_files():
    app = ROOT / "app"
    leaks = [p.name for p in sorted(app.glob("*")) if p.is_file() and p.name != "core.js"
             and "localStorage" in p.read_text(encoding="utf-8", errors="replace")]
    check("only app/core.js touches localStorage", not leaks, leaks)
    core = (app / "core.js").read_text(encoding="utf-8")
    writes = re.findall(r"localStorage\.(?:setItem|removeItem|clear)\(([^,)]*)", core)
    check("app/core.js writes only cali.v5, cali.sync and cali.timers",
          writes and set(writes) <= {"KEY", "SYNC_KEY", "TIMERS_KEY"}
          and "const KEY = 'cali.v5'" in core and "const SYNC_KEY = 'cali.sync'" in core and "const TIMERS_KEY = 'cali.timers'" in core,
          writes)
    check("app/core.js opens with a header comment", core.startswith("/*") and "*/" in core, core[:60])

    registry = (app / "registry.js").read_text(encoding="utf-8")
    listed = re.findall(r"^CALI_FEATURES\.push\('([^']+)'\);$", registry, re.M)
    code_lines = [ln for ln in re.sub(r"/\*.*?\*/", "", registry, flags=re.S).splitlines() if ln.strip()]
    missing = [f for f in listed if not (ROOT / f).is_file()]
    check("app/registry.js lists one existing script or stylesheet per line",
          listed and not missing and len(code_lines) == len(listed) + 1 and all(re.fullmatch(r"app/[\w-]+\.(js|css)", f) for f in listed),
          (listed, missing))
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    order = [index.find(s) for s in ('href="tokens.css"', 'href="app/base.css"', 'src="app/registry.js"',
                                      'src="app/default-program.js"', 'src="app/core.js"')]
    check("index.html loads tokens, base.css, the registry, the default program and core, in that order",
          all(i >= 0 for i in order) and order == sorted(order), order)
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    check("sw.js names a versioned cache, reads the registry and lists no feature by hand",
          re.search(r"const CACHE = 'cali-app-v[\d.]+';", sw) is not None and "importScripts('app/registry.js')" in sw
          and not any(f in sw for f in listed), listed)

    design = ROOT / "design"
    pairs = [(ROOT / "tokens.css", design / "tokens.css")] + [
        (ROOT / "fonts" / n, design / "fonts" / n)
        for n in ("archivo.css", "Archivo-latin.woff2", "Archivo-latin-ext.woff2", "Manrope.woff2")]
    differ = [str(a.relative_to(ROOT)) for a, b in pairs
              if not a.is_file() or hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest()]
    check("tokens.css and fonts/ are unchanged copies of Tarik Base v6 (design/)", not differ, differ)

    prog = default_program()
    days = prog["days"]
    kinds = {e["kind"] for d in days for e in d["exercises"]}
    paired = all(sum(1 for e in d["exercises"] if e.get("pair") == p) == 2
                 for d in days for p in {e["pair"] for e in d["exercises"] if "pair" in e})
    check("app/default-program.js: three days A/B/C with reps, time and check rows, pairs of two, no logs",
          [d["name"][0] for d in days] == ["A", "B", "C"] and kinds == {"reps", "time", "check"} and paired
          and "sets\": [" not in json.dumps(prog) and all(isinstance(e["sets"], int) for d in days for e in d["exercises"]),
          [d["name"] for d in days])

    legacy = (ROOT / "legacy" / "index.html").read_text(encoding="utf-8")
    check("legacy/index.html no longer unregisters workers or deletes caches",
          "getRegistrations" not in legacy and "caches.delete" not in legacy and "caches.keys" not in legacy)
    check("legacy/index.html registers its own worker inside legacy/",
          re.search(r"serviceWorker\.register\('sw\.js[^']*'", legacy) is not None and (ROOT / "legacy" / "sw.js").is_file())
    lsw = (ROOT / "legacy" / "sw.js").read_text(encoding="utf-8")
    check("legacy/sw.js deletes only its own older caches", "key.startsWith('cali-legacy-')" in lsw)


def png_size(data):
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def check_manifest(url):
    murl = urllib.parse.urljoin(url, "manifest.json")
    m = json.loads(urllib.request.urlopen(murl).read())

    def get(u):
        try:
            with urllib.request.urlopen(u) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    for key in ("start_url", "scope"):
        raw = m.get(key, "")
        u = urllib.parse.urljoin(murl, raw)
        status, _ = get(u)
        check(f"manifest {key} is relative and resolves under {BASE} with 200",
              raw and not raw.startswith("/") and "://" not in raw and urllib.parse.urlsplit(u).path.startswith(BASE)
              and status == 200, (raw, u, status))
    check("manifest is installable (standalone, name, English)", m.get("display") == "standalone" and m.get("name")
          and m.get("lang") == "en", m)
    for size in (192, 512):
        icons = [i for i in m.get("icons", []) if i.get("sizes") == f"{size}x{size}"]
        purposes = {p for i in icons for p in i.get("purpose", "any").split()}
        ok = bool(icons)
        for icon in icons:
            status, data = get(urllib.parse.urljoin(murl, icon["src"]))
            ok = ok and status == 200 and png_size(data) == (size, size)
        check(f"manifest {size} px icon resolves with 200, is {size}x{size}, any and maskable", ok and {"any", "maskable"} <= purposes, icons)


def check_phone(browser, url, site, errors):
    gh = MockGitHub()
    ctx, page = phone(browser, errors, "phone", gh=gh)
    open_day(page, url)
    ctx.clock.pause_at(NOW + datetime.timedelta(seconds=30))

    # first open builds week 1 from the active program
    doc = stored(page)
    prog = default_program()
    check("first open stores the v5 document under cali.v5",
          doc and doc.get("_version") == 5 and set(doc) == {"_version", "updatedAt", "programs", "activeProgram",
                                                            "nextProgram", "weeks", "body", "settings"}, doc and list(doc))
    check("the built-in program is Tarik's A/B/C (app/default-program.js) and is active and next",
          doc["programs"] == [prog] and doc["activeProgram"] == doc["nextProgram"] == prog["id"])
    w = doc["weeks"]
    built = len(w) == 1 and w[0]["n"] == 1 and w[0]["program"] == prog["id"] and "startedAt" in w[0] and all(
        w[0]["days"][d["id"]]["exercises"][e["id"]] == {**{k: v for k, v in e.items() if k not in ("id", "sets")},
                                                         "sets": [None] * e["sets"]}
        for d in prog["days"] for e in d["exercises"]) and len(w[0]["days"]) == len(prog["days"])
    check("first open builds week 1 from activeProgram: every exercise's rules, load and target copied, no logs", built, w and w[0].get("n"))
    check("every setting has its default, body is empty", doc["settings"] == DEFAULTS and doc["body"] == [], doc["settings"])
    keys = page.evaluate("() => Object.keys(localStorage)")
    check("localStorage holds only cali.* keys", keys and all(k.startswith("cali.") for k in keys), keys)

    day = prog["days"][0]
    want = {f"{day['id']}:{e['id']}:{i}" for e in day["exercises"] for i in range(e["sets"])}
    shown = set(page.evaluate("() => [...document.querySelectorAll('[data-screen=\"day\"] [data-set]')].map(el => el.dataset.set)"))
    check("the day opens on day A with a data-set cell for every set", shown == want, sorted(shown ^ want)[:6])

    pull = next(e for e in day["exercises"] if e["name"] == "Weighted Pull-up")
    sel = f'[data-set="{day["id"]}:{pull["id"]}:0"]'
    set0 = f"() => {{ const s = Cali.week().days['{day['id']}'].exercises['{pull['id']}'].sets[0]; return s && s.r; }}"
    stored0 = lambda: (stored(page)["weeks"][-1]["days"][day["id"]]["exercises"][pull["id"]]["sets"][0] or {}).get("r")

    touch_tap(page, sel)
    check("touch-tap Pull-up set 1 stores 6 (the target)", stored0() == 6, stored0())
    ctx.clock.run_for(1000)
    page.reload()
    page.wait_for_selector(f'[data-screen="day"] {sel}')
    check("after a reload set 1 is still 6", stored0() == 6 and page.evaluate(set0) == 6, (stored0(), page.evaluate(set0)))
    ctx.clock.run_for(1000)
    touch_tap(page, sel)
    check("tap again stores 5 (one less)", stored0() == 5, stored0())
    ctx.clock.run_for(1000)
    touch_hold(page, ctx, sel)
    check("hold stores 6 (one more)", stored0() == 6, stored0())
    ctx.clock.run_for(1000)
    at = (stored(page)["weeks"][-1]["days"][day["id"]]["exercises"][pull["id"]]["sets"][0] or {}).get("at")
    check("a set's time comes from Cali.now() (the test clock), not the wall clock",
          at and datetime.datetime.fromisoformat(at.replace("Z", "+00:00")) - NOW < datetime.timedelta(minutes=1), at)

    members = page.evaluate("""() => [...Object.keys(Cali).map(k => 'Cali.' + k),
        ...Object.keys(Cali.settings).map(k => 'Cali.settings.' + k), ...Object.keys(Cali.alert).map(k => 'Cali.alert.' + k),
        ...Object.keys(Cali.timers).map(k => '.' + k + '(')]""")
    header = (ROOT / "app" / "core.js").read_text(encoding="utf-8").split("*/", 1)[0]
    undocumented = [k for k in members if k not in header]
    check("the core.js header documents every Cali member", members and not undocumented, undocumented)
    check("no request reached GitHub (no sync in Task-00)", not gh.requests, gh.requests[:3])

    # offline after one online load
    ctx.clock.resume()
    check("the service worker controls the app after the first load", wait_controlled(page))
    go_offline(ctx, site)
    page.reload()
    page.wait_for_selector(f'[data-screen="day"] {sel}', timeout=10000)
    fonts = page.evaluate("""async () => { await document.fonts.ready;
        return document.fonts.check('16px Manrope') && document.fonts.check('700 40px Archivo'); }""")
    check("offline, a reload shows the day with the logged set and the fonts", page.evaluate(set0) == 6 and fonts, fonts)
    go_online(ctx, site)

    # a release: the worker deletes its own older caches and 'cali-v4' (the old app's at this scope), no other
    page.evaluate("""async () => { for (const n of ['pantry-v9', 'cali-legacy-v1', 'cali-app-v0', 'cali-v4', 'other'])
        await (await caches.open(n)).put('probe-' + n, new Response('x')); }""")
    sw = (ROOT / "sw.js").read_bytes()
    site.overlay[BASE + "sw.js"] = re.sub(rb"const CACHE = 'cali-app-v[\d.]+';", b"const CACHE = 'cali-app-v999';", sw)
    page.evaluate("async () => { const reg = await navigator.serviceWorker.getRegistration(); await reg.update(); }")
    keys = poll(page, """async () => { const k = await caches.keys();
        return k.includes('cali-app-v999') && !k.includes('cali-app-v0') && !k.includes('cali-v4') && k; }""")
    keys = keys or page.evaluate("() => caches.keys()")
    check("a new release keeps every other cache (Pantry's, legacy's, any other)",
          all(k in keys for k in ("pantry-v9", "cali-legacy-v1", "other")), keys)
    check("a new release deletes this app's older caches and the old app's cali-v4",
          "cali-app-v999" in keys and not any(k in keys for k in ("cali-app-v0", "cali-app-v1", "cali-v4")), keys)
    site.overlay.clear()
    ctx.close()


def check_legacy(browser, url, site, errors):
    legacy_errors = []
    # 1) the new app is installed; opening legacy/ leaves its worker and caches alone; the new app then loads offline
    ctx, page = phone(browser, legacy_errors, "legacy-then-app", clock=False)   # legacy's own console is not the app's
    open_day(page, url)
    check("the new app's worker controls it before legacy/ is opened", wait_controlled(page))
    page.goto(url + "legacy/")
    page.wait_for_selector("#dayTabs button")
    origin = url.split(BASE)[0]
    regs = poll(page, f"""async () => {{ const r = await navigator.serviceWorker.getRegistrations();
        const s = r.filter(x => x.active).map(x => x.scope);
        return s.includes('{origin}{BASE}legacy/') && s; }}""")
    regs = regs or page.evaluate("async () => (await navigator.serviceWorker.getRegistrations()).map(x => x.scope)")
    check("legacy/ registers its own worker with scope legacy/, and the app's worker stays",
          f"{origin}{BASE}legacy/" in regs and f"{origin}{BASE}" in regs, regs)
    cache = re.search(r"const CACHE = '(cali-app-v[\d.]+)';", (ROOT / "sw.js").read_text(encoding="utf-8")).group(1)
    keys = page.evaluate("() => caches.keys()")
    check("opening legacy/ deletes no cache of the new app", cache in keys, keys)
    app_urls = page.evaluate("async (c) => (await (await caches.open(c)).keys()).map(r => r.url)", cache)
    check("the app's worker caches nothing under legacy/", app_urls and not any("/legacy/" in u for u in app_urls),
          [u for u in app_urls if "/legacy/" in u][:3])
    go_offline(ctx, site)
    page.goto(url)
    page.wait_for_selector('[data-screen="day"] [data-set]', timeout=10000)
    check("after legacy/ was opened, the new app still loads offline", page.locator("[data-set]").count() > 0)
    go_online(ctx, site)
    ctx.close()

    # 2) legacy refuses a v5 document from the data repo: no adoption, no write
    fixture = (ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8")
    gh = MockGitHub(text=fixture, sha="v5sha")
    ctx, page = phone(browser, legacy_errors, "legacy-v5", gh=gh, clock=False, service_workers="block")
    page.goto(url + "legacy/")
    page.wait_for_selector("#dayTabs button")
    page.evaluate("""() => localStorage.setItem('cali_sync_config', JSON.stringify({ owner: 'Estaed',
        repo: 'Calisthenics-Data', branch: 'main', path: 'calisthenics-data.json', token: 'TESTTOKEN', deviceName: 'test' }))""")
    page.reload()
    page.wait_for_selector("#dayTabs button")
    err = poll(page, "() => (JSON.parse(localStorage.getItem('cali_sync_state') || '{}').lastError || '')")
    local = page.evaluate("() => ({ mem: programData._version, saved: JSON.parse(localStorage.getItem('cali4_program_data'))._version })")
    check("legacy refuses a v5 document (tests/fixtures/v5-document.json): it says a newer version holds the data",
          "daha yeni" in (err or ""), err)
    check("legacy neither adopts nor overwrites the v5 document", gh.puts == 0 and gh.text == fixture
          and local == {"mem": 4, "saved": 4}, (gh.puts, local))
    real = [e for e in legacy_errors if "pageerror" in e]
    check("legacy opens without page errors", not real, real[:3])
    ctx.close()


def run_file(path):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900, env=env)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return "timeout", ""


def check_suite():
    code, _ = run_file(ROOT / "tests" / "fixtures" / "exits_1.py")
    check("the runner turns a test file that exits 1 red (tests/fixtures/exits_1.py, not in the suite)", code == 1, code)
    files = sorted((ROOT / "tests").glob("test_*.py"))
    check("tests/test_*.py exist", bool(files))
    for f in files:
        code, out = run_file(f)
        if not check(f"tests/{f.name} exits 0", code == 0, f"exit {code}"):
            print("\n".join("    " + line for line in out.strip().splitlines()[-30:]))


def guarded(name, fn, *args):
    """A scenario that crashes is one FAIL with its error, and the other scenarios still run."""
    try:
        fn(*args)
    except Exception as e:      # noqa: BLE001 - the gate reports every crash as a failure
        check(f"{name} ran to the end", False, f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}")


def main():
    sys.dont_write_bytecode = True
    srv, site, url = start_site()
    errors = []
    try:
        guarded("file checks", check_files)
        guarded("manifest checks", check_manifest, url)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            guarded("phone scenario", check_phone, browser, url, site, errors)
            site.overlay.clear()
            site.down = False
            guarded("legacy scenario", check_legacy, browser, url, site, errors)
            browser.close()
        outside = sorted({p for p in site.paths if not p.startswith(BASE) and p != BASE.rstrip("/")})
        check(f"every request stays under {BASE} (relative paths only)", not outside, outside)
        check("no console errors or page errors in the app", not errors, "\n".join(errors[:10]))
    finally:
        srv.shutdown()
    guarded("tests/test_*.py suite", check_suite)
    print(f"\n{'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAIL'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
