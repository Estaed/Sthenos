"""Acceptance test for sync + 3/4/5-day plans.

Run: python tests/acceptance.py
Serves the app over a local HTTP server, mocks the GitHub Contents API in-memory,
and drives two isolated browser contexts ("phone" and "pc").
"""
import base64
import functools
import hashlib
import http.server
import json
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = "TESTTOKEN"
REPO_PATH = "/repos/Estaed/Calisthenics-Data"
API_PATH = REPO_PATH + "/contents/calisthenics-data.json"
FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))
    if not cond:
        FAILS.append(name)


# ── local static server ────────────────────────────────────────────
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/index.html"


# ── mock GitHub ────────────────────────────────────────────────────
class MockGitHub:
    def __init__(self, repo_visible=True):
        self.text = None
        self.sha = None
        self.puts = 0
        self.repo_visible = repo_visible

    CORS = {
        "access-control-allow-origin": "*",
        "access-control-allow-headers": "*",
        "access-control-allow-methods": "GET,PUT,OPTIONS",
    }

    def handle(self, route):
        req = route.request
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=self.CORS)
        if req.headers.get("authorization") != f"Bearer {TOKEN}":
            return route.fulfill(status=401, headers=self.CORS, body='{"message":"Bad credentials"}')
        if req.url.split("?")[0].endswith(REPO_PATH):
            # GitHub answers 404 for a private repo the token cannot see
            return route.fulfill(status=200 if self.repo_visible else 404, headers=self.CORS,
                                 content_type="application/json", body="{}")
        if API_PATH not in req.url or not self.repo_visible:
            return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
        if req.method == "GET":
            if self.text is None:
                return route.fulfill(status=404, headers=self.CORS, body='{"message":"Not Found"}')
            raw = base64.b64encode(self.text.encode("utf-8")).decode()
            wrapped = "\n".join(raw[i:i + 60] for i in range(0, len(raw), 60))
            body = {"sha": self.sha, "content": wrapped, "encoding": "base64",
                    "size": len(self.text.encode("utf-8"))}
            return route.fulfill(status=200, headers=self.CORS, content_type="application/json",
                                 body=json.dumps(body))
        if req.method == "PUT":
            body = json.loads(req.post_data or "{}")
            if self.sha is not None and body.get("sha") != self.sha:
                return route.fulfill(status=409, headers=self.CORS, body='{"message":"sha mismatch"}')
            if self.sha is None and body.get("sha"):
                return route.fulfill(status=422, headers=self.CORS, body='{"message":"no file"}')
            self.text = base64.b64decode(body["content"]).decode("utf-8")
            self.sha = hashlib.sha1(self.text.encode("utf-8")).hexdigest()
            self.puts += 1
            return route.fulfill(status=201, headers=self.CORS, content_type="application/json",
                                 body=json.dumps({"content": {"sha": self.sha}}))
        return route.fulfill(status=405, headers=self.CORS)


# ── v2 seed (shape of the live phone data) ─────────────────────────
def ex(name, weight="", reps="8", unit="kg", amount=2.5, status="none", green=0):
    return {"id": name[:4] + "_x", "name": name, "sets": 2, "reps": reps, "weight": weight,
            "status": status, "incrementAmount": amount, "incrementUnit": unit,
            "requiredWeeks": 1, "consecutiveGreen": green}


def v2_seed():
    def days(status):
        return [
            {"name": "Push", "exercises": [ex("Weighted Dip", "+10 kg", status=status),
                                           ex("Wall Handstand Hold", reps="30s", unit="s", amount=2, status=status)]},
            {"name": "Pull", "exercises": [ex("Weighted Pull-up", "+5 kg", status=status)]},
            {"name": "Leg", "exercises": [ex("Leg Press Orta Ayak", "100 kg", amount=5, status=status)]},
            {"name": "Upper", "exercises": [ex("Machine Row", "40 kg", status=status, green=0)]},
            {"name": "Lower", "exercises": [ex("Leg Press Yüksek Ayak ğşı", "90 kg", amount=5, status=status)]},
        ]
    return {"_version": 2, "programName": "Calisthenic Program",
            "weeks": [{"weekNumber": 1, "completed": True, "days": days("done")},
                      {"weekNumber": 2, "completed": False, "days": days("none")}]}


def new_page(browser, url, gh, errors, tag):
    ctx = browser.new_context(service_workers="block")
    ctx.route("https://api.github.com/**", gh.handle)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"[{tag}] pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
            and errors.append(f"[{tag}] console: {m.text}"))
    page.on("dialog", lambda d: d.accept())
    page.goto(url)
    return page


def configure_sync(page):
    page.evaluate("""() => localStorage.setItem('cali_sync_config', JSON.stringify({
        owner: 'Estaed', repo: 'Calisthenics-Data', branch: 'main',
        path: 'calisthenics-data.json', token: 'TESTTOKEN', deviceName: 'test'}))""")
    page.reload()
    page.evaluate("() => syncNow({manual: true})")
    page.wait_for_timeout(300)


ACTIVE_NAMES = "() => getActiveDays(getCurrentWeek()).map(d => d.name)"
SYNC_STATE = "() => JSON.parse(localStorage.getItem('cali_sync_state') || '{}')"


def main():
    srv, url = start_server()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # T1 fresh install
        gh0 = MockGitHub()
        page = new_page(browser, url, gh0, errors, "fresh")
        d = page.evaluate("() => programData")
        lib = [x["name"] for x in d["weeks"][-1]["days"]]
        check("T1 version 4", d.get("_version") == 4, d.get("_version"))
        check("T1 library has 9 days", lib == ["Push", "Pull", "Leg", "Upper", "Lower", "Lower Quad", "Lower Posterior", "Ev A", "Ev B"], lib)
        check("T1 plan sizes", [len(d["plans"][k]) for k in ("3", "4", "5", "ev")] == [3, 4, 5, 2], d.get("plans"))
        check("T1 no mobility data", "mobility" not in d, list(d))
        check("T1 week plan 5 and 5 tabs", d["weeks"][0]["plan"] == 5 and page.locator("#dayTabs button").count() == 5,
              page.locator("#dayTabs button").count())

        # T2 plan switching
        page.evaluate("() => selectPlan(4)")
        check("T2 4-day tabs", page.evaluate(ACTIVE_NAMES) == ["Push", "Lower Quad", "Pull", "Lower Posterior"], page.evaluate(ACTIVE_NAMES))
        tabs = [t.strip() for t in page.locator("#dayTabs button").all_inner_texts()]
        check("T2 DOM tabs follow plan", tabs == ["Push", "Lower Quad", "Pull", "Lower Posterior"], tabs)
        page.evaluate("() => selectPlan(3)")
        check("T2 3-day tabs", page.evaluate(ACTIVE_NAMES) == ["Push", "Pull", "Leg"], page.evaluate(ACTIVE_NAMES))
        check("T1/T2 no sync without config", gh0.puts == 0, gh0.puts)

        # T12 plan editor: add Upper, move it above Leg, drop Leg, save
        page.evaluate("""() => {
            const ids = Object.fromEntries(getCurrentWeek().days.map(d => [d.name, d.id]));
            openPlanEditor();
            togglePlanDay(ids.Upper, true);
            movePlanDay(ids.Upper, -1);
            togglePlanDay(ids.Leg, false);
            savePlanEditor();
        }""")
        check("T12 plan editor updates active days", page.evaluate(ACTIVE_NAMES) == ["Push", "Pull", "Upper"], page.evaluate(ACTIVE_NAMES))
        plan3 = page.evaluate("() => programData.plans['3'].map(id => getCurrentWeek().days.find(d => d.id === id).name)")
        check("T12 plan editor updates plan", plan3 == ["Push", "Pull", "Upper"], plan3)

        # T13 JSON backup upload replaces data and migrates it
        page.set_input_files("#backupInput", files=[{"name": "b.json", "mimeType": "application/json",
                                                     "buffer": json.dumps(v2_seed()).encode("utf-8")}])
        page.wait_for_timeout(500)
        d = page.evaluate("() => programData")
        check("T13 backup upload migrated", len(d["weeks"]) == 2 and d["_version"] == 4, (len(d["weeks"]), d.get("_version")))
        page.context.close()

        # T3 v2 migration (phone)
        gh = MockGitHub()
        phone = new_page(browser, url, gh, errors, "phone")
        seed = json.dumps(v2_seed())
        phone.evaluate("s => localStorage.setItem('cali4_program_data', s)", seed)
        phone.reload()
        d = phone.evaluate("() => programData")
        backup = phone.evaluate("() => localStorage.getItem('cali4_program_data_backup_v2')")
        check("T3 backup of raw v2 kept", backup is not None and json.loads(backup) == json.loads(seed), (backup or "")[:80])
        w1, w2 = d["weeks"]
        check("T3 day ids stable across weeks", [x["id"] for x in w1["days"]] == [x["id"] for x in w2["days"][:5]])
        check("T3 last week gets Lower Quad/Posterior", [x["name"] for x in w2["days"]][5:] == ["Lower Quad", "Lower Posterior", "Ev A", "Ev B"],
              [x["name"] for x in w2["days"]])
        check("T3 active days = original 5", phone.evaluate(ACTIVE_NAMES) == ["Push", "Pull", "Leg", "Upper", "Lower"], phone.evaluate(ACTIVE_NAMES))
        byid = {x["id"]: x["name"] for x in w2["days"]}
        check("T3 plan 4 order", [byid[i] for i in d["plans"]["4"]] == ["Push", "Lower Quad", "Pull", "Lower Posterior"], d["plans"]["4"])
        check("T3 plan 3", [byid[i] for i in d["plans"]["3"]] == ["Push", "Pull", "Leg"], d["plans"]["3"])
        check("T3 v4 adds ev plan", [byid[i] for i in d["plans"]["ev"]] == ["Ev A", "Ev B"], d.get("plans"))
        check("T3 weights intact", w2["days"][0]["exercises"][0]["weight"] == "+10 kg")

        # T4 phone pushes to empty cloud
        configure_sync(phone)
        check("T4 phone created cloud file", gh.text is not None and gh.puts >= 1, gh.puts)
        st = phone.evaluate(SYNC_STATE)
        check("T4 phone clean after push", st.get("dirty") is False and st.get("lastSha") == gh.sha, st)

        # T5 render alone does not dirty / push
        puts = gh.puts
        phone.evaluate("() => { render(); render(); render(); }")
        phone.wait_for_timeout(5000)
        check("T5 render does not mark dirty", phone.evaluate(SYNC_STATE).get("dirty") is False and gh.puts == puts,
              (phone.evaluate(SYNC_STATE), gh.puts, puts))

        # T6 pc (pristine) adopts cloud, Turkish round-trip
        pc = new_page(browser, url, gh, errors, "pc")
        configure_sync(pc)
        d_pc = pc.evaluate("() => programData")
        check("T6 pc adopted cloud weeks", len(d_pc["weeks"]) == 2, len(d_pc["weeks"]))
        check("T6 pc jumps to current week after first adopt", pc.evaluate("() => currentWeekIdx") == 1,
              pc.evaluate("() => currentWeekIdx"))
        check("T6 turkish name round-trip", d_pc["weeks"][1]["days"][4]["exercises"][0]["name"] == "Leg Press Yüksek Ayak ğşı",
              d_pc["weeks"][1]["days"][4]["exercises"][0]["name"])

        # T7 pc edit -> debounced push -> phone pulls
        pc.evaluate("() => { switchDay(0); updateField(0, 'weight', '+12.5 kg'); }")
        pc.wait_for_timeout(6000)
        check("T7 pc pushed edit", '+12.5 kg' in (gh.text or ""), gh.puts)
        phone.evaluate("() => syncNow({manual: true})")
        w = phone.evaluate("() => programData.weeks[1].days[0].exercises[0].weight")
        check("T7 phone adopted pc edit", w == "+12.5 kg", w)

        # T8 completeWeek on 3-day plan: inactive days carried unchanged
        phone.evaluate("() => { currentWeekIdx = 1; selectPlan(3); }")
        phone.evaluate("""() => {
            const act = getActiveDays(getCurrentWeek());
            act.forEach((day, j) => { switchDay(j); day.exercises.forEach((_, i) => setStatus(i, 'done')); });
            completeWeek();
        }""")
        d = phone.evaluate("() => programData")
        nw = d["weeks"][-1]
        byname = {x["name"]: x for x in nw["days"]}
        check("T8 new week created with plan 3", len(d["weeks"]) == 3 and nw["plan"] == 3, (len(d["weeks"]), nw.get("plan")))
        check("T8 active day progressed", byname["Push"]["exercises"][0]["weight"] == "+15.0 kg", byname["Push"]["exercises"][0]["weight"])
        check("T8 inactive day unchanged", byname["Upper"]["exercises"][0]["weight"] == "40 kg"
              and byname["Upper"]["exercises"][0]["status"] == "none", byname["Upper"]["exercises"][0])
        check("T8 day ids preserved", [x["id"] for x in nw["days"]] == [x["id"] for x in d["weeks"][1]["days"]])
        check("T8 history shows active days only",
              phone.evaluate("() => { renderHistory(); return document.getElementById('historyBody').innerText; }").count("Machine Row") == 1)
        phone.wait_for_timeout(6000)

        # T9 conflict: both devices change offline-ish, pc sees conflict and takes cloud
        pc.evaluate("() => { programData.programName = 'pc-local-change'; saveData(); }")
        phone.evaluate("() => syncNow({manual: true})")
        pc.evaluate("() => syncNow({manual: true})")
        pc.wait_for_timeout(300)
        btn = pc.get_by_role("button", name="Buluttakini al")
        check("T9 conflict modal shown", btn.count() > 0 and btn.first.is_visible(), btn.count())
        if btn.count():
            btn.first.click()
            pc.wait_for_timeout(300)
        d_pc = pc.evaluate("() => programData")
        check("T9 pc took cloud", len(d_pc["weeks"]) == 3 and d_pc["programName"] != "pc-local-change",
              (len(d_pc["weeks"]), d_pc["programName"]))

        # T10 newer-version cloud is refused
        good_text, good_sha = gh.text, gh.sha
        newer = json.loads(gh.text)
        newer["_version"] = 99
        gh.text = json.dumps(newer)
        gh.sha = "newer"
        puts = gh.puts
        phone.evaluate("() => syncNow({manual: true})")
        check("T10 newer cloud not overwritten", gh.puts == puts and phone.evaluate("() => programData._version") == 4)
        gh.text, gh.sha = good_text, good_sha

        # T11 sw.js only handles same-origin GET
        sw = (ROOT / "sw.js").read_text(encoding="utf-8")
        check("T11 sw guards method/origin", "'GET'" in sw or '"GET"' in sw, "no GET guard")
        check("T11 sw cache bumped", "cali-v4" in sw)

        # T14 real phone flow: token typed into the modal, one button saves + syncs, result stays visible
        gh14 = MockGitHub()
        ui = new_page(browser, url, gh14, errors, "ui")
        ui.evaluate("s => localStorage.setItem('cali4_program_data', s)", json.dumps(v2_seed()))
        ui.reload()
        ui.evaluate("() => openSyncModal()")
        ui.fill("#syncToken", TOKEN)
        ui.fill("#syncDeviceName", "phone")
        ui.get_by_role("button", name="Kaydet ve senkronla").click()
        ui.wait_for_timeout(1500)
        status = ui.locator("#syncStatus").inner_text()
        check("T14 save button pushes to cloud", gh14.puts >= 1, gh14.puts)
        check("T14 modal stays open with success", ui.locator("#syncModal.open").count() == 1 and "Senkronize" in status, status)
        check("T14 no separate 'Şimdi senkronla' button", ui.get_by_role("button", name="Şimdi senkronla").count() == 0)
        ui.context.close()

        # T15 failures are shown inside the open modal, nothing is written
        cases = [
            ("repo not visible", MockGitHub(repo_visible=False), TOKEN, "Repo bulunamadı"),
            ("bad token", MockGitHub(), "WRONG", "Token geçersiz"),
            ("empty token", MockGitHub(), "", "Token boş"),
        ]
        for name, gh_bad, token, expect in cases:
            pg = new_page(browser, url, gh_bad, errors, f"t15-{name}")
            pg.evaluate("() => openSyncModal()")
            pg.fill("#syncToken", token)
            pg.get_by_role("button", name="Kaydet ve senkronla").click()
            pg.wait_for_timeout(1500)
            status = pg.locator("#syncStatus").inner_text()
            check(f"T15 {name}: message visible", pg.locator("#syncModal.open").count() == 1 and expect in status, status)
            check(f"T15 {name}: nothing written", gh_bad.puts == 0, gh_bad.puts)
            pg.context.close()


        # T16 automatic double progression
        dp = new_page(browser, url, MockGitHub(), errors, "dp")
        dp.evaluate("""() => {
            const w = getCurrentWeek();
            const day = getActiveDays(w)[0];
            const base = day.exercises[0];
            const mk = (id, name, reps, weight, lo, hi) => Object.assign({}, base, {
                id, name, reps, weight, status: 'none', incrementAmount: 1, incrementUnit: 'reps',
                requiredWeeks: 1, consecutiveGreen: 0, repMin: lo, repMax: hi, loadStep: 2.5 });
            day.exercises = [mk('dp1', 'DP top', '10', '+10 kg', 6, 10), mk('dp2', 'DP mid', '7', 'BW', 6, 10),
                             mk('dp3', 'DP bw top', '8', 'BW', 4, 8), mk('dp4', 'DP abs top', '12', '50 kg', 8, 12)];
            saveData();
            getActiveDays(w).forEach((d, j) => { switchDay(j); d.exercises.forEach((_, i) => setStatus(i, 'done')); });
            completeWeek();
        }""")
        byn = {e["name"]: e for e in dp.evaluate("() => getActiveDays(getCurrentWeek())[0].exercises")}
        check("T16 top of range: +load, reps to min", byn["DP top"]["reps"] == "6" and byn["DP top"]["weight"] == "+12.5 kg", byn.get("DP top"))
        check("T16 inside range: +1 rep only", byn["DP mid"]["reps"] == "8" and byn["DP mid"]["weight"] == "BW", byn.get("DP mid"))
        check("T16 bodyweight top becomes +2.5 kg", byn["DP bw top"]["reps"] == "4" and byn["DP bw top"]["weight"] == "+2.5 kg", byn.get("DP bw top"))
        check("T16 absolute load top", byn["DP abs top"]["reps"] == "8" and byn["DP abs top"]["weight"] == "52.5 kg", byn.get("DP abs top"))
        check("T16 range fields carried", byn["DP top"].get("repMax") == 10 and byn["DP top"].get("loadStep") == 2.5, byn.get("DP top"))

        # T19 last-week reference
        dp.evaluate("() => switchDay(0)")
        body = dp.locator("#exb").inner_text()
        check("T19 last-week reference shown", "geçen: +10 kg × 10" in body, body[:300])
        check("T19 range label shown", "6–10" in body, body[:300])

        # T18 Ev plan
        dp.evaluate("() => selectPlan('ev')")
        check("T18 ev plan tabs", dp.evaluate(ACTIVE_NAMES) == ["Ev A", "Ev B"], dp.evaluate(ACTIVE_NAMES))
        check("T18 Ev button present", dp.get_by_role("button", name="Ev", exact=True).count() >= 1)
        dp.evaluate("""() => {
            getActiveDays(getCurrentWeek()).forEach((d, j) => { switchDay(j); d.exercises.forEach((_, i) => setStatus(i, 'done')); });
            completeWeek();
        }""")
        check("T18 ev plan carried to next week", dp.evaluate("() => getCurrentWeek().plan") == "ev", dp.evaluate("() => getCurrentWeek().plan"))
        dp.context.close()

        # T20 real v3 program (2026-09-15 reset) upgrades to v4 without touching the program
        fx = (ROOT / "tests" / "fixtures" / "v3-program.json").read_text(encoding="utf-8")
        src = json.loads(fx)
        v3 = new_page(browser, url, MockGitHub(), errors, "v3")
        v3.evaluate("s => localStorage.setItem('cali4_program_data', s)", fx)
        v3.reload()
        d = v3.evaluate("() => programData")
        names = [x["name"] for x in d["weeks"][0]["days"]]
        check("T20 keeps days, appends Ev A/B", names == [x["name"] for x in src["weeks"][0]["days"]] + ["Ev A", "Ev B"], names)
        bk = v3.evaluate("() => localStorage.getItem('cali4_program_data_backup_v3')")
        check("T20 backup_v3 is the raw v3 data", bk is not None and json.loads(bk) == src)
        check("T20 active days and 3/4/5 plans unchanged", d["weeks"][0]["activeDayIds"] == src["weeks"][0]["activeDayIds"]
              and all(d["plans"][k] == src["plans"][k] for k in ("3", "4", "5")))
        check("T20 exercises unchanged", d["weeks"][0]["days"][:5] == src["weeks"][0]["days"])
        check("T20 no mobility data", "mobility" not in d, list(d))
        v3.context.close()

        browser.close()
    srv.shutdown()
    check("no page/console errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAIL'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
