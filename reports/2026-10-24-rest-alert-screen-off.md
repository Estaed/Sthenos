# Rest alert with the screen off: what a PWA can do on Android (2026-10-24)

Serves: Blueprint v1, notes.md decision 11: does the rest timer rely on a notification at the end, or on keeping the screen awake?

**Verdict: partly.** A PWA cannot schedule an OS alarm: Notification Triggers ended, the page cannot vibrate while hidden, and the notification `vibrate` option has no effect on Android 8+. The best route with the screen off is a service-worker timer, held open with `event.waitUntil` (up to about 5 min), that fires `showNotification`. Whether that notification makes a sound or vibrates depends on the phone's notification-channel settings, and whether Android keeps the browser alive with the screen off is unproven. **Wake Lock plus an in-page beep and vibration is the reliable path, so make it the main path.**

## Mechanisms

| Mechanism | Chrome Android | Samsung Internet | Source (date) |
|---|---|---|---|
| Notification Triggers (`showTrigger`) | Not available: "development has ended"; behind a flag only | Same (Chromium) | [Chrome docs](https://developer.chrome.com/docs/web-platform/notification-triggers) (read 2026-10-24); [chromestatus API](https://chromestatus.com/feature/5133150283890688) (updated 2022-09-13) |
| SW `setTimeout` after the page leaves | Killed after 30 s idle; one event may run up to 5 min, so `waitUntil` holds it | Same engine | [Chromium constants](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/public/mojom/service_worker/service_worker.mojom) (read 2026-10-24); headless test below |
| `showNotification` + `requireInteraction` | Yes (Chrome 42 / 47) | Yes (mirrors Chrome) | [MDN](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/showNotification) (modified 2026-10-11) |
| Notification `vibrate` option | **No effect on Android 8+**; the channel decides sound and vibration | Mirrors Chrome | [MDN BCD](https://github.com/mdn/browser-compat-data/blob/main/api/ServiceWorkerRegistration.json) (commit 2026-10-22), [crbug 40630890](https://issues.chromium.org/issues/40630890) (opened 2019) |
| `navigator.vibrate()` from the page | Only when visible and after a tap; returns false when hidden | Mirrors Chrome | [W3C Vibration](https://w3c.github.io/vibration/) (read 2026-10-24); [MDN BCD Navigator](https://github.com/mdn/browser-compat-data/blob/main/api/Navigator.json) (read 2026-10-24) |
| Screen Wake Lock | Yes since Chrome 84 | Yes since 14.0 | [caniuse](https://caniuse.com/wake-lock) (usage data Sep 2026) |
| Wake Lock vs. power button and tab switch | Released when the page is hidden; the lock "MUST NOT be applicable after the screen is manually switched off". Re-acquire on `visibilitychange` | Same spec | [W3C spec](https://w3c.github.io/screen-wake-lock/) (read 2026-10-24); [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API) (modified 2026-09-11) |
| Page timers while hidden | Checked once per second for the first 5 min hidden; intensive throttling starts after 5 min. A 60-180 s rest fits inside that window, unless Android freezes the browser | Unknown | [Chrome blog](https://developer.chrome.com/blog/timer-throttling-in-chrome-88) (2021-01-18) |
| Web Audio with the screen off | Practice: Web Audio loops stopped on Android Chrome after the screen went dark; HTML `<audio>` kept playing | Unknown | [howler.js #1253](https://github.com/goldfire/howler.js/issues/1253) (2019-11 to 2022-01) |
| Silent `<audio>` + Media Session keep-alive | Plays on in the background. Media 5 s or longer gets "full" audio focus, which **pauses Spotify** | Unknown | [web.dev](https://web.dev/articles/media-session) (2024-06-10); [bathroom_timer README](https://github.com/daniel-jayu/bathroom_timer) (2026-09-18, 0 stars) |
| Periodic Background Sync | Installed apps only; frequency follows site engagement, roughly daily. Useless for 60-180 s | Mirrors | [Chrome docs](https://developer.chrome.com/docs/capabilities/periodic-background-sync) (2025-08-19) |
| Badging | Not on Android | Not on Android | [Chrome docs](https://developer.chrome.com/docs/capabilities/web-apis/badging-api) (read 2026-10-24); MDN BCD `chrome_android: false` |

Samsung Internet's own release notes stop at 23.0.1.1 (2023-11-30) ([Samsung](https://developer.samsung.com/internet/release-note.html), read 2026-10-24). A forum thread says v28 ran on Chromium 130 ([forum](https://forum.developer.samsung.com/t/why-have-browser-updates-to-upgrade-chromium-become-so-infrequent/42404), read 2026-10-24). Every API above is older than that, so the Samsung rows follow Chromium. Samsung adds its own battery manager on top.

**What real PWA timers do:** [vajkri/interval-timer](https://github.com/vajkri/interval-timer) (pushed 2026-10-23) uses Wake Lock and says "Web apps can't play sound while the phone is locked". [Ketan-K/interval-timer](https://github.com/Ketan-K/interval-timer) (2026-09-08) uses Wake Lock plus a Web Worker. [bathroom_timer](https://github.com/daniel-jayu/bathroom_timer) (2026-09-18) uses silent `<audio>`, Media Session and pre-scheduled Web Audio. These are practice reports from small repos, not proof.

**Headless test (desktop Chromium 1243 with no DevTools attached, 2026-10-24).** The test page leaves after posting a message to the service worker.
- A 45 s `setTimeout` without `waitUntil` never fired.
- A 90 s `setTimeout` without `waitUntil` never fired.
- A 75 s `setTimeout` with `waitUntil` fired 12 ms late.

This proves the 30 s idle kill and the `waitUntil` hold in the Chromium core. Android behaviour with the screen off is **not proven by this**.

## Recommended v1 design

1. **Main path:** the workout screen holds a Wake Lock and re-acquires it on `visibilitychange`. When the rest ends: a Web Audio beep, `navigator.vibrate`, and the visual change. The phone lies screen-up.
2. **Fallback for screen off or pocket:** when the rest starts, the page posts the end time to the service worker, which waits with `waitUntil` and then calls `showNotification` with `tag` and `renotify`. The page keeps its own `setTimeout` as a second trigger, using the same tag so only one notification appears. Ask for notification permission once, on the first rest.
3. **Not in v1:** Notification Triggers, push, periodic sync, badging. Also not the long `<audio>` keep-alive, because it pauses music; it can go under *After v1* if the test shows the fallback fails.

## Only Tarık's phone can settle

- Does the service-worker timer survive 60 s with the screen off, in Samsung Internet and in Chrome?
- Does the notification ring or vibrate with the channel defaults?
- Does Samsung's battery manager kill the browser?

**2-minute test:** host the test page from `C:\Users\TARIK\AppData\Local\Temp\claude\D--Projects-Calisthenics-App\5be50840-7a9a-4974-a907-dab39604bfb3\scratchpad\rest-alert-test\` (index.html, sw.js, manifest, icon) on GitHub Pages. Install it from Samsung Internet. Then:

1. Tap "Allow notifications", then "Start 60 s rest".
2. Press the power button and put the phone in a pocket.
3. At 60 s, note whether you hear a sound, feel a vibration, and see a notification.
4. Unlock and read the log, which shows the page and SW firing times and the wake-lock release.
5. Repeat with the Wake Lock box ticked and the screen left on.
6. Repeat once in Chrome.

## Where this belongs

Blueprint → Decisions (decision 11, rest alert), and the reason column for "Wake Lock + SW notification fallback". This report does not write into Blueprint or notes.md.

## Sources

- https://developer.chrome.com/docs/web-platform/notification-triggers (read 2026-10-24; "development ... has ended")
- https://chromestatus.com/feature/5133150283890688 (API updated 2022-09-13; "In developer trial (Behind a flag)")
- https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/public/mojom/service_worker/service_worker.mojom (read 2026-10-24; idle 30 s, 5 min per event)
- https://w3c.github.io/ServiceWorker/ (Editor's Draft 2026-09-17; lifetime tied to events)
- https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/showNotification (modified 2026-10-11)
- https://github.com/mdn/browser-compat-data/blob/main/api/ServiceWorkerRegistration.json (last commit 2026-10-22; vibrate no effect on Android O+)
- https://issues.chromium.org/issues/40630890 ("Notification vibrations not respected", opened 2019-06)
- https://developer.mozilla.org/en-US/docs/Web/API/Notification/vibrate (modified 2026-10-23; deprecated)
- https://w3c.github.io/vibration/ (read 2026-10-24; hidden → false; sticky activation)
- https://github.com/mdn/browser-compat-data/blob/main/api/Navigator.json (read 2026-10-24; vibrate needs gesture since Chrome 60; setAppBadge chrome_android false)
- https://caniuse.com/wake-lock (usage data Sep 2026; Samsung 14.0+)
- https://w3c.github.io/screen-wake-lock/ (read 2026-10-24)
- https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API (modified 2026-09-11)
- https://developer.chrome.com/blog/timer-throttling-in-chrome-88 (2021-01-18)
- https://github.com/goldfire/howler.js/issues/1253 (2019-11-20, last comment 2022-01-19)
- https://web.dev/articles/media-session (2024-06-10)
- https://developer.chrome.com/docs/capabilities/periodic-background-sync (2025-08-19)
- https://developer.chrome.com/docs/capabilities/web-apis/badging-api (read 2026-10-24)
- https://developer.samsung.com/internet/release-note.html (read 2026-10-24; last entry 2023-11-30)
- https://forum.developer.samsung.com/t/why-have-browser-updates-to-upgrade-chromium-become-so-infrequent/42404 (read 2026-10-24)
- https://github.com/vajkri/interval-timer (pushed 2026-10-23)
- https://github.com/Ketan-K/interval-timer (pushed 2026-09-08)
- https://github.com/daniel-jayu/bathroom_timer (pushed 2026-09-18)

**Route:** Chromium source and MDN compat data (raw JSON) answered most of this faster than the docs did. A headless run without DevTools showed the service-worker lifetime directly; Playwright's own run was contaminated because its attached DevTools keeps service workers alive.

When you rewrite this, keep each link and date beside its claim and paste the Sources block unchanged.
