"""Checks for the seams in app/core.js that the wave-1 features build on (Task-00, Fixed).

Run from the repo root: python tests/test_core.py   (exit 0 = no FAIL). Reuses the gate's server and phone from
tests/acceptance.py, with Playwright's clock paused, so every time below is moved by the test (Cali.now()).
The data is the built-in program and tests/fixtures/v5-document.json; nothing personal is stored.
"""
import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

FIXTURE = json.loads((A.ROOT / "tests" / "fixtures" / "v5-document.json").read_text(encoding="utf-8"))


def throws(page, body):
    """True when the arrow body throws in the page."""
    return page.evaluate(f"() => {{ try {{ {body}; return false; }} catch (e) {{ return true; }} }}")


def main():
    srv, site, url = A.start_site()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = A.phone(browser, errors, "core")
        A.open_day(page, url)
        ctx.clock.pause_at(A.NOW + datetime.timedelta(seconds=30))
        ev = page.evaluate
        ids = ev("""() => { const d = Cali.program().days[0]; const by = n => d.exercises.find(e => e.name.startsWith(n)).id;
            return { day: d.id, pull: by('Weighted Pull-up'), dip: by('Weighted Dip'), plank: by('Plank'), walk: by('Eğimli'),
                     lp: by('Leg Press'), lat: by('Side Lateral Raise') }; }""")
        D = json.dumps(ids["day"])

        def ex(name):
            return json.dumps(ids[name])

        # ── the logging rule ──
        got = ev(f"() => Array.from({{ length: 10 }}, () => {{ const s = Cali.tap({D}, {ex('dip')}, 0); return s && s.r; }})")
        A.check("reps: tap = target, again one less down to 0, then empty", got == [8, 7, 6, 5, 4, 3, 2, 1, 0, None], got)
        got = ev(f"() => [Cali.hold({D}, {ex('dip')}, 0).r, Cali.hold({D}, {ex('dip')}, 0).r]")
        A.check("reps: hold on an empty set = target + 1, hold again + 1", got == [9, 10], got)
        got = ev(f"() => [Cali.tap({D}, {ex('plank')}, 0).r, Cali.tap({D}, {ex('plank')}, 0).r, Cali.hold({D}, {ex('plank')}, 0).r, Cali.hold({D}, {ex('plank')}, 0).r]")
        A.check("time: tap = target 40 s, again -5 s, hold +5 s", got == [40, 35, 40, 45], got)
        got = ev(f"() => [Cali.tap({D}, {ex('walk')}, 0), Cali.tap({D}, {ex('walk')}, 0), Cali.hold({D}, {ex('walk')}, 0), Cali.hold({D}, {ex('walk')}, 0)].map(s => s && s.r)")
        A.check("check: tap and hold toggle between 1 and empty", got == [1, None, 1, None], got)

        # ── Cali.log, its events and Undo ──
        got = ev(f"""() => {{ const seen = [];
            const a = Cali.on('change', c => seen.push(['change', c.why, c.detail, c.dirty, c.prev !== c.doc]));
            const b = Cali.on('log', l => seen.push(['log', l]));
            Cali.log({D}, {ex('pull')}, 1, 4); a(); b(); return seen; }}""")
        at = A.NOW + datetime.timedelta(seconds=30)
        want_at = at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        A.check("Cali.log emits change (why log, detail, dirty) then log { week, dayId, exId, i, value, prev }",
                got == [["change", "log", {"week": 1, "dayId": ids["day"], "exId": ids["pull"], "i": 1}, True, True],
                        ["log", {"week": 1, "dayId": ids["day"], "exId": ids["pull"], "i": 1, "value": {"r": 4, "at": want_at}, "prev": None}]],
                got)
        got = ev(f"""() => {{ let undo; const off = Cali.on('log', l => {{ undo = l; }});
            Cali.log({D}, {ex('pull')}, 1, 3); off(); Cali.log({D}, {ex('pull')}, 1, undo.prev);
            return Cali.week().days[{D}].exercises[{ex('pull')}].sets[1]; }}""")
        A.check("Undo puts the exact previous set back through Cali.log(…, prev)", got == {"r": 4, "at": want_at}, got)
        got = ev(f"() => {{ Cali.log({D}, {ex('pull')}, 2, {{ r: 5, pain: true }}); return Cali.tap({D}, {ex('pull')}, 2); }}")
        A.check("a tap keeps the set's pain flag", got and got.get("r") == 4 and got.get("pain") is True, got)
        bad = [b for b in (f"Cali.log({D}, 'nope', 0, 1)", f"Cali.log({D}, {ex('pull')}, 9, 1)", f"Cali.log({D}, {ex('pull')}, 0, -1)",
                           f"Cali.log({D}, {ex('pull')}, 0, 'x')", f"Cali.tap('nope', {ex('pull')}, 0)") if not throws(page, b)]
        A.check("Cali.log, Cali.tap refuse an unknown day, exercise, index or value", not bad, bad)

        # ── Cali.log is the only writer of a set ──
        before = ev("() => localStorage.getItem('cali.v5')")
        bad = [b for b in (
            f"Cali.change(d => {{ d.weeks[0].days[{D}].exercises[{ex('lp')}].sets[0] = {{ r: 1, at: Cali.iso() }}; }})",
            f"Cali.change(d => {{ d.weeks[0].days[{D}].exercises[{ex('pull')}].sets[1].r = 9; }})",
            f"Cali.change(d => {{ d.weeks[0].days[{D}].exercises[{ex('pull')}].sets[1] = null; }})",
            "Cali.change(d => { d.weeks = [Cali.weekFrom(d.programs[0], 1)]; })",
        ) if not throws(page, b)]
        A.check("Cali.change refuses to add, change or drop a logged set and saves nothing",
                not bad and ev("() => localStorage.getItem('cali.v5')") == before, bad)
        got = ev(f"() => Cali.change(d => {{ d.weeks[0].days[{D}].exercises[{ex('lp')}].load = 112.5; }}, {{ why: 'load' }}).weeks[0].days[{D}].exercises[{ex('lp')}].load")
        A.check("Cali.change saves anything else (the pencil's load)", got == 112.5, got)
        A.check("the document is frozen", throws(page, "Cali.doc().weeks.push({})")
                and throws(page, "(() => { 'use strict'; Cali.doc().settings.restPair = 1; })()"))
        A.check("a change that breaks the shape throws", throws(page, "Cali.change(d => { d.weeks[0].n = 7; })"))

        # ── the pair alternation ──
        got = ev(f"() => Cali.setOrder({D}).slice(0, 11).map(s => s.exId + ':' + s.i)")
        P, Q, L, T = ids["pull"], ids["dip"], ids["lp"], ids["lat"]
        want = [f"{P}:0", f"{Q}:0", f"{P}:1", f"{Q}:1", f"{P}:2", f"{Q}:2", f"{L}:0", f"{T}:0", f"{L}:1", f"{T}:1", f"{L}:2"]
        A.check("setOrder alternates a pair set by set (3 and 2 sets end on the longer one)", got == want, got)
        got = ev(f"() => Cali.nextSet({D})")
        A.check("nextSet is the first set in that order not logged", got == {"exId": ids["pull"], "i": 0}, got)

        # ── settings and theme ──
        got = ev("() => Cali.settings.all()")
        A.check("Cali.settings has every default", got == A.DEFAULTS, got)
        got = ev("() => { Cali.settings.set('restPair', 60); return [Cali.settings.get('restPair'), JSON.parse(localStorage.getItem('cali.v5')).settings.restPair]; }")
        A.check("Cali.settings.set saves through the document", got == [60, 60], got)
        bad = [b for b in ("Cali.settings.set('restPair', -1)", "Cali.settings.set('restPair', '60')", "Cali.settings.set('nope', 1)",
                           "Cali.settings.get('nope')", "Cali.settings.set('theme', 'blue')") if not throws(page, b)]
        A.check("Cali.settings refuses an unknown key or a wrong value", not bad, bad)
        got = ev("() => { Cali.settings.set('theme', 'light'); const a = document.documentElement.dataset.theme; Cali.settings.set('theme', 'dark'); return [a, document.documentElement.dataset.theme]; }")
        A.check("the theme setting is applied on <html data-theme>", got == ["light", "dark"], got)

        # ── timers from timestamps ──
        ev("() => { window.__timer = []; Cali.on('timer', t => __timer.push(t.action)); Cali.timers.start('rest', { duration: 90000, kind: 'rest', data: { set: 1 } }); }")
        ctx.clock.run_for(60000)
        r1 = ev("() => Cali.timers.get('rest').remaining")
        ev("() => Cali.timers.pause('rest')")
        ctx.clock.run_for(100000)
        r2 = ev("() => Cali.timers.get('rest').remaining")
        got = ev("() => { Cali.timers.resume('rest'); const t = Cali.timers.add('rest', 60000); return [t.remaining, t.endAt - Cali.now(), t.data, t.kind]; }")
        A.check("a countdown is computed from its start: 30 s left after 60 s, paused stays, +1 min",
                r1 == 30000 and r2 == 30000 and got == [90000, 90000, {"set": 1}, "rest"], (r1, r2, got))
        A.check("Cali.timers emits 'timer' for each call", ev("() => __timer") == ["start", "pause", "resume", "add"], ev("() => __timer"))
        ev("() => { Cali.timers.start('watch'); }")
        ctx.clock.run_for(5000)
        ev("() => Cali.timers.lap('watch')")
        ctx.clock.run_for(2000)
        page.reload()
        page.wait_for_selector('[data-screen="day"] [data-set]')
        got = ev("() => { const w = Cali.timers.get('watch'), r = Cali.timers.get('rest'); return [w.elapsed, w.laps, w.remaining, r.remaining, Cali.timers.list().length]; }")
        A.check("both timers run at once and survive a reload (stopwatch 7 s with a lap at 5 s, rest 90 - 7 s)",
                got == [7000, [5000], None, 83000, 2], got)
        ctx.clock.run_for(10 * 60000)
        got = ev("() => { const r = Cali.timers.get('rest'); return [r.remaining, r.done, Cali.timers.get('watch').elapsed]; }")
        A.check("after the phone slept 10 min the countdown is done and the stopwatch shows 10:07", got == [0, True, 607000], got)
        got = ev("() => { Cali.timers.stop('watch'); return [Cali.timers.get('watch'), Cali.timers.list().length]; }")
        A.check("Cali.timers.stop removes a timer", got == [None, 1], got)

        # ── routes ──
        got = ev("""() => { const seen = []; const off = Cali.on('route', r => seen.push(r.name)); Cali.go('nope', { a: 1 });
            off(); return [Cali.current(), location.hash, seen]; }""")
        A.check("Cali.go to an unknown route opens the day with no args", got[0] == {"name": "day", "args": {}} and got[1] == "#/day"
                and got[2] == ["day"], got)
        day_b = ev("() => Cali.program().days[1].id")
        got = ev(f"() => {{ Cali.go('day', {{ week: 1, dayId: {json.dumps(day_b)} }}); return [Cali.current(), location.hash, [...document.querySelectorAll('[data-set]')].every(el => el.dataset.set.startsWith({json.dumps(day_b)} + ':'))]; }}")
        A.check("Cali.go('day', { week, dayId }) shows that day and keeps its args in the address",
                got[0] == {"name": "day", "args": {"week": 1, "dayId": day_b}} and got[2], got)
        page.go_back()
        page.wait_for_function(f"() => Cali.current() && Cali.current().args.dayId !== {json.dumps(day_b)}")
        A.check("the phone's back gesture returns to the screen before", ev("() => Cali.current().name") == "day")
        got = ev("""() => { Cali.route('probe', { render(root, args) { root.innerHTML = '<p data-probe>' + JSON.stringify(args) + '</p>'; } });
            Cali.go('probe', { countdown: 30, tag: 'a:b?c', on: true }); return [Cali.current(), document.querySelector('[data-screen="probe"] [data-probe]') !== null]; }""")
        A.check("a feature's route gets its args back typed (number, text, boolean)",
                got == [{"name": "probe", "args": {"countdown": 30, "tag": "a:b?c", "on": True}}, True], got)
        ev("() => Cali.back()")
        page.wait_for_function("() => Cali.current().name === 'day'")
        got = ev("() => [Cali.dayArgs({}), Cali.dayArgs({ week: 7, dayId: 'nope' }), Cali.dayArgs({ readOnly: true })]")
        A.check("Cali.dayArgs fills week, dayId and readOnly", got == [{"week": 1, "dayId": ids["day"], "readOnly": False}] * 2
                + [{"week": 1, "dayId": ids["day"], "readOnly": True}], got)

        # ── slots ──
        got = ev(f"""() => {{ const a = document.createElement('button'), b = document.createElement('button'), w = document.createElement('span');
            a.id = 'slot-a'; b.id = 'slot-b'; w.id = 'slot-w';
            window.__rm = Cali.slot('topbar', a, 20); Cali.slot('topbar', b, 10); Cali.slot('dayheader', w);
            const order = () => [...document.querySelectorAll('[data-screen="day"] [data-slot="topbar"] > *')].map(x => x.id).filter(id => id.startsWith('slot-'));
            const first = order();
            Cali.tap({D}, {ex('lp')}, 0);
            const fb = document.querySelector('[data-slot="dayheader"] > [data-fallback]');
            return [first, order(), document.querySelector('[data-slot="dayheader"] #slot-w') !== null, fb ? getComputedStyle(fb).display : 'none']; }}""")
        A.check("Cali.slot puts nodes in the day screen's holders in order, and they stay after a re-render",
                got[0] == ["slot-b", "slot-a"] and got[1] == ["slot-b", "slot-a"] and got[2], got)
        A.check("a holder's fallback hides while a feature's node is in it", got[3] == "none", got[3])
        got = ev("() => { __rm(); return document.getElementById('slot-a'); }")
        A.check("the function Cali.slot returns takes the node out", got is None)
        A.check("Cali.slot refuses an unknown slot", throws(page, "Cali.slot('footer', document.createElement('i'))"))

        # ── dirty marks for sync ──
        got = ev("""() => { const n = Cali.changes(); const st = Cali.syncState();
            Cali.markClean(n - 1); const still = Cali.dirty(); Cali.markClean(n);
            return [st.dirty, typeof st.dirtySince, still, Cali.dirty(), Cali.syncState().dirtySince]; }""")
        A.check("a change marks cali.sync dirty with dirtySince; markClean(upTo) clears only when nothing changed since",
                got == [True, "string", True, False, None], got)
        got = ev("() => { let seen = null; const off = Cali.on('sync', s => { seen = s.state.lastError; }); Cali.setSyncState({ lastError: 'x' }); off(); return [seen, Cali.syncState().lastError]; }")
        A.check("Cali.setSyncState merges, saves and emits 'sync'", got == ["x", "x"], got)

        # ── read-only keys ──
        ev("() => localStorage.setItem('cali_sync_config', JSON.stringify({ token: 'TESTTOKEN' }))")
        got = ev("() => [JSON.parse(Cali.readOnly('cali_sync_config')).token, Cali.readOnly('pantry.v1')]")
        A.check("Cali.readOnly reads cali_sync_config and pantry.v1", got == ["TESTTOKEN", None], got)
        A.check("Cali.readOnly refuses any other key", throws(page, "Cali.readOnly('cali4_program_data')") and throws(page, "Cali.readOnly('cali.v5')"))

        # ── progress and alert stubs, provide ──
        got = ev(f"() => Cali.progress(Cali.weekExercise(1, {D}, {ex('lp')}), Cali.history({D}, {ex('lp')}, 1))")
        A.check("the progress stub answers no change", got == {"load": 112.5, "target": 10, "reason": "no change"}, got)
        got = ev("""async () => [Cali.alert('rest'), Cali.alert.schedule('rest', Cali.now() + 1000, 'rest'), Cali.alert.cancel('rest'),
            await Cali.alert.requestPermission()]""")
        A.check("the alert stubs do nothing and requestPermission answers without asking", got[:3] == [None, None, None]
                and got[3] in ("default", "denied", "granted"), got)
        bad = [b for b in ("Cali.alert('nope')", "Cali.alert.schedule('rest', NaN, 'rest')", "Cali.alert.schedule('rest', 1, '')",
                           "Cali.alert.cancel('')", "Cali.provide('alert', { alert() {} })", "Cali.provide('nope', () => 1)") if not throws(page, b)]
        A.check("Cali.alert and Cali.provide refuse a wrong kind, time, tag or implementation", not bad, bad)
        got = ev("""() => { const seen = [];
            Cali.provide('alert', { alert: k => seen.push(k), schedule: (k, at, tag) => seen.push(tag), cancel: t => seen.push('x' + t),
                                    requestPermission: async () => 'granted' });
            Cali.alert('test'); Cali.alert.schedule('headsup', 5, 'rest-h'); Cali.alert.cancel('rest-h'); return seen; }""")
        A.check("Cali.provide('alert', impl) puts the implementation behind Cali.alert", got == ["test", "rest-h", "xrest-h"], got)
        ev("() => Cali.provide('progress', () => ({ load: 1 }))")
        A.check("a progress result of the wrong shape throws", throws(page, f"Cali.progress(Cali.weekExercise(1, {D}, {ex('lp')}), [])"))

        # ── replace, weeks, history ──
        A.check("Cali.replace never adopts a document without _version 5",
                throws(page, "Cali.replace({ ...JSON.parse(localStorage.getItem('cali.v5')), _version: 4 })")
                and throws(page, "Cali.replace(null)"))
        got = ev(f"""(fx) => {{ let c = null; const off = Cali.on('change', x => {{ c = [x.why, x.dirty]; }});
            const d = Cali.replace(fx); off(); return [c, d.programs[0].id, Cali.week().n, JSON.parse(localStorage.getItem('cali.v5')).weeks.length]; }}""", FIXTURE)
        A.check("Cali.replace adopts a v5 document (why replace, not dirty)", got == [["replace", False], "fixture", 2, 2], got)
        got = ev("() => Cali.history('F', 'f1')")
        A.check("Cali.history gives the earlier weeks of an exercise, newest first, with dayDone",
                got == [{"week": 1, "load": 20, "target": 8, "dayDone": True,
                         "sets": FIXTURE["weeks"][0]["days"]["F"]["exercises"]["f1"]["sets"]}], got)
        got = ev("() => { const e = Cali.weekExercise(2, 'F', 'f2'); return [e.name, e.kind, e.target, e.load, e.bodyweight, e.pair, e.repMin, e.repMax, e.loadStep, e.week, e.dayId, e.sets.length, Object.isFrozen(e)]; }")
        A.check("Cali.weekExercise joins the program's rules with the week's values",
                got == ["Fixture Dip", "reps", 7, 0, True, "p1", 4, 8, 2.5, 2, "F", 2, True], got)
        got = ev("() => [Cali.setOrder('F').map(s => s.exId + ':' + s.i), Cali.dayArgs({}), Cali.dayExercises(2, 'F').map(e => e.id)]")
        A.check("setOrder, dayArgs and dayExercises on the fixture",
                got == [["f1:0", "f2:0", "f1:1", "f2:1", "f3:0", "f4:0"], {"week": 2, "dayId": "F", "readOnly": False}, ["f1", "f2", "f3", "f4"]], got)
        got = ev("""() => { Cali.change(d => { d.weeks.push(Cali.weekFrom(d.programs[0], 3)); }, { why: 'week' });
            const w3 = Cali.week(3).days.F.exercises; Cali.change(d => { d.programs[0].days[0].exercises[1].target = 99; }, { why: 'program' });
            return [w3.f2, Cali.week(1).days.F.exercises.f2.target, Cali.week(2).days.F.exercises.f2.target, Cali.week(3).days.F.exercises.f2.target,
                    Cali.dayArgs({ week: 2 }).readOnly]; }""")
        A.check("Cali.weekFrom copies the program's values; a program edit afterwards changes no week",
                got == [{"name": "Fixture Dip", "kind": "reps", "repMin": 4, "repMax": 8, "loadStep": 2.5, "bodyweight": True,
                         "pair": "p1", "load": 0, "target": 6, "sets": [None, None]}, 6, 7, 6, True], got)
        got = ev("""() => { Cali.change(d => { const e = d.programs[0].days[0].exercises[1];
                Object.assign(e, { name: 'Renamed', kind: 'time', repMin: null, repMax: null }); delete e.pair; }, { why: 'program' });
            const e = Cali.weekExercise(3, 'F', 'f2'); return [e.name, e.kind, e.repMin, e.repMax, e.pair, Cali.tap('F', 'f2', 0).r]; }""")
        A.check("a week keeps its copied rules (name, kind, range, pair) after the program's exercise is edited",
                got == ["Fixture Dip", "reps", 4, 8, "p1", 6], got)

        # ── misc ──
        got = ev("() => [Cali.loadLabel(0, true), Cali.loadLabel(5, true), Cali.loadLabel(110, false), Cali.loadLabel(47.5), Cali.esc('<a\"&>'), Cali.iso() === new Date(Cali.now()).toISOString()]")
        A.check("Cali.loadLabel, Cali.esc, Cali.iso", got == ["BW", "BW +5 kg", "110 kg", "47.5 kg", "&lt;a&quot;&amp;&gt;", True], got)
        keys = ev("() => Object.keys(localStorage)")
        A.check("the app wrote only cali.* keys (cali_sync_config is the test's own)", all(k.startswith("cali.") or k == "cali_sync_config" for k in keys), keys)
        ctx.close()

        # ── a stored document that cannot be used is never written over ──
        for name, raw in (("newer", '{"_version": 6, "weeks": []}'), ("unreadable", '{"_version": 5}')):
            seen = []
            pctx, pg = A.phone(browser, seen, f"problem-{name}")
            pctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ localStorage.setItem('cali.v5', {json.dumps(raw)}); sessionStorage.setItem('seeded', '1'); }}")
            A.open_day(pg, url)
            got = pg.evaluate("""() => { let threw = false; try { Cali.log(Cali.dayArgs({}).dayId, Cali.dayExercises(null, Cali.dayArgs({}).dayId)[0].id, 0, 1); } catch (e) { threw = true; }
                return [Cali.problem(), threw, localStorage.getItem('cali.v5'), document.querySelector('.banner[role="alert"]') !== null]; }""")
            A.check(f"a {name} stored document: Cali.problem() says why, writes throw, the stored text stays, a banner shows",
                    bool(got[0]) and got[1] and got[2] == raw and got[3], got)
            pctx.close()
        browser.close()
    srv.shutdown()
    A.check("no console errors or page errors", not errors, "\n".join(errors[:10]))
    print(f"\n{'ALL PASS' if not A.FAILS else str(len(A.FAILS)) + ' FAIL'}")
    sys.exit(1 if A.FAILS else 0)


if __name__ == "__main__":
    main()
