// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-gray; icon-glyph: tv;

/*
 * Fire TV Remote
 * A Wi-Fi remote for a Fire TV (Toshiba Fire TV Edition, Fire TV Stick, Cube...)
 * that runs on an iPhone in the free Scriptable app. No computer needed.
 * Setup steps are in README.md next to this file.
 *
 * It talks to the remote-control service built into the TV, the same one Amazon's
 * Fire TV phone app uses. Amazon doesn't document that service. The details below
 * come from people who worked it out themselves, so a Fire TV update could change it.
 */

// Set this to true and run the script once to forget your TV and pair again.
// Then set it back to false.
const RESET = false;

// App shortcut buttons. Add your own: name is the label, id is the app's package name.
const APPS = [
  { name: "Netflix", id: "com.netflix.ninja" },
  { name: "YouTube", id: "com.amazon.firetv.youtube" },
  { name: "Disney+", id: "com.disney.disneyplus" },
  { name: "Hulu", id: "com.hulu.plus" },
];

// ------------------------------------------------------------------ talking to the TV

const API_KEY = "0987654321"; // the fixed key every Fire TV remote app sends
const STORE_IP = "firetv-remote.ip";
const STORE_TOKEN = "firetv-remote.token";

const KEYS = ["dpad_up", "dpad_down", "dpad_left", "dpad_right", "select", "home", "back", "menu"];

function stored(key) {
  return Keychain.contains(key) ? Keychain.get(key) : null;
}

function pause(ms) {
  return new Promise((resolve) => Timer.schedule(ms, false, resolve));
}

async function http(method, url, options = {}) {
  const req = new Request(url);
  req.method = method;
  req.timeoutInterval = options.timeout || 5;
  req.allowInsecureRequest = true; // the TV uses a self-signed certificate
  const headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "okhttp/4.10.0",
  };
  if (options.token) headers["X-Client-Token"] = options.token;
  req.headers = headers;
  if (options.body !== undefined) req.body = JSON.stringify(options.body);
  const text = await req.loadString();
  const status = req.response && req.response.statusCode ? req.response.statusCode : 0;
  return { status, text };
}

const ok = (status) => status >= 200 && status < 300;

// The control service on port 8080 sleeps with the TV. A plain POST to port 8009 wakes it.
async function wake(ip) {
  try {
    const res = await http("POST", `http://${ip}:8009/apps/FireTVRemote`, { timeout: 3 });
    return res.status > 0;
  } catch (e) {
    return false;
  }
}

// Turns a button's command string into a request.
function route(cmd) {
  const [kind, a, b] = String(cmd).split(":");
  if (kind === "key" && KEYS.includes(a)) return { path: `/v1/FireTV?action=${a}` };
  if (kind === "play") return { path: "/v1/media?action=play" };
  if (kind === "scan" && (a === "forward" || a === "back")) {
    return {
      path: "/v1/media?action=scan",
      body: { direction: a, keyAction: { keyActionType: b === "up" ? "keyUp" : "keyDown" } },
    };
  }
  if (kind === "app" && /^[\w.]+$/.test(a || "")) return { path: `/v1/FireTV/app/${a}` };
  return null;
}

const UNREACHABLE =
  "Can't reach the TV. Make sure it's on and your iPhone is on the same Wi-Fi.";

async function send(cfg, cmd) {
  if (cmd === "wake") {
    return (await wake(cfg.ip)) ? { ok: true, msg: "Waking the TV..." } : { ok: false, msg: UNREACHABLE };
  }
  const r = route(cmd);
  if (!r) return { ok: false, msg: "That button isn't set up." };
  const url = `https://${cfg.ip}:8080${r.path}`;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await http("POST", url, { token: cfg.token, body: r.body, timeout: attempt ? 6 : 3 });
      if (ok(res.status)) return { ok: true };
      if (res.status === 401 || res.status === 403) {
        return { ok: false, msg: "The TV doesn't recognize this iPhone anymore. Tap the gear to pair again." };
      }
      return { ok: false, msg: `The TV said no (error ${res.status}).` };
    } catch (e) {
      // Usually the TV's remote service is asleep: wake it and try once more.
      if (attempt === 0) {
        await wake(cfg.ip);
        await pause(1200);
        continue;
      }
    }
  }
  return { ok: false, msg: UNREACHABLE };
}

// ------------------------------------------------------------------------- pairing

async function tell(title, message) {
  const a = new Alert();
  a.title = title;
  a.message = message;
  a.addAction("OK");
  await a.presentAlert();
}

async function askIp(current) {
  const a = new Alert();
  a.title = "Connect to your Fire TV";
  a.message =
    "On the TV, go to Settings > My Fire TV (or Device & Software) > About > Network and type the IP Address shown there.\n\n" +
    "Your iPhone has to be on the same Wi-Fi as the TV.";
  a.addTextField("e.g. 192.168.1.50", current || "");
  a.addAction("Next");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return null;
  const ip = a.textFieldValue(0).trim();
  if (!/^[A-Za-z0-9.\-]+$/.test(ip)) {
    await tell("That doesn't look right", "Type just the numbers and dots, like 192.168.1.50");
    return askIp(ip);
  }
  return ip;
}

async function askPin() {
  const a = new Alert();
  a.title = "Enter the code";
  a.message = "Type the 4-digit code that just appeared on your TV.";
  const field = a.addTextField("1234", "");
  field.setNumberPadKeyboard();
  a.addAction("Pair");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return null;
  return a.textFieldValue(0).trim();
}

async function pair(currentIp) {
  const ip = await askIp(currentIp);
  if (!ip) return null;

  await wake(ip);
  await pause(1500);
  let shown = null;
  try {
    shown = await http("POST", `https://${ip}:8080/v1/FireTV/pin/display`, {
      body: { friendlyName: "iPhone Remote" },
      timeout: 8,
    });
  } catch (e) {
    shown = null;
  }
  if (!shown || !ok(shown.status)) {
    await tell(
      "Couldn't reach the TV",
      "Check that:\n• the TV is on\n• the IP address is right\n• your iPhone is on the same Wi-Fi\n" +
        "• Scriptable is allowed in iPhone Settings > Privacy & Security > Local Network"
    );
    return pair(ip);
  }

  for (let tries = 0; tries < 3; tries++) {
    const pin = await askPin();
    if (pin === null) return null;
    try {
      const res = await http("POST", `https://${ip}:8080/v1/FireTV/pin/verify`, { body: { pin }, timeout: 8 });
      const token = ok(res.status) ? JSON.parse(res.text).description : null;
      if (token) {
        Keychain.set(STORE_IP, ip);
        Keychain.set(STORE_TOKEN, token);
        return { ip, token };
      }
    } catch (e) {
      // fall through to "try again"
    }
    await tell("That code didn't work", "Check the code on the TV and try again.");
  }
  return null;
}

async function settings(cfg) {
  const a = new Alert();
  a.title = "Remote settings";
  a.message = `Connected to the TV at ${cfg.ip}`;
  a.addAction("Pair again / change TV");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return null;
  return pair(cfg.ip);
}

// --------------------------------------------------------------------------- the remote

const ICONS = {
  up: '<path d="M6 15l6-6 6 6"/>',
  down: '<path d="M6 9l6 6 6-6"/>',
  left: '<path d="M15 6l-6 6 6 6"/>',
  right: '<path d="M9 6l6 6-6 6"/>',
  back: '<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  home: '<path d="M3.5 11L12 3.5 20.5 11"/><path d="M6 9.5V20h12V9.5"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  play: '<path d="M4 5v14l9-7z" fill="currentColor"/><path d="M16 5v14M20 5v14"/>',
  rew: '<path d="M11 6l-8 6 8 6zM21 6l-8 6 8 6z" fill="currentColor"/>',
  ff: '<path d="M3 6l8 6-8 6zM13 6l8 6-8 6z" fill="currentColor"/>',
  power: '<path d="M12 3v8"/><path d="M6.4 6.6a8 8 0 1 0 11.2 0"/>',
  gear:
    '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
};

function icon(name) {
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function page(cfg) {
  const apps = APPS.map(
    (a) => `<button class="app" data-cmd="app:${escapeHtml(a.id)}">${escapeHtml(a.name)}</button>`
  ).join("");
  return `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<style>
  :root { --bg:#0e1014; --key:#22262e; --key-hi:#2e333d; --ring:#1a1d23; --text:#eef1f6; --dim:#8b93a3;
          --accent:#4d8dff; --good:#3ecf74; --bad:#ff6b5e; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; -webkit-user-select:none; user-select:none; }
  html, body { margin:0; background:var(--bg); color:var(--text); height:100%;
    font:16px -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; }
  body { display:flex; flex-direction:column; align-items:center; gap:22px; touch-action:manipulation;
    padding:calc(env(safe-area-inset-top) + 18px) 16px calc(env(safe-area-inset-bottom) + 18px); overflow:hidden; }
  button { font:inherit; color:inherit; border:0; background:var(--key); cursor:pointer;
    display:grid; place-items:center; transition:transform .06s, background .06s; }
  button.pressed { background:var(--key-hi); transform:scale(.94); }
  svg { width:26px; height:26px; fill:none; stroke:currentColor; stroke-width:2.2; stroke-linecap:round; stroke-linejoin:round; }
  header { width:100%; max-width:340px; display:flex; align-items:center; justify-content:space-between; }
  .round { width:48px; height:48px; border-radius:50%; }
  #power { color:var(--bad); }
  .title { text-align:center; }
  .title b { display:block; font-size:17px; letter-spacing:.2px; }
  .title span { font-size:13px; color:var(--dim); display:inline-flex; align-items:center; gap:6px; }
  #dot { width:8px; height:8px; border-radius:50%; background:var(--dim); transition:background .2s; }
  #dot.good { background:var(--good); } #dot.bad { background:var(--bad); }
  .pad { position:relative; width:min(78vw, 290px); aspect-ratio:1; border-radius:50%; background:var(--ring);
    box-shadow:inset 0 0 0 1px #ffffff0d; }
  .pad .arrow { position:absolute; background:transparent; width:34%; height:34%; border-radius:50%; color:var(--dim); }
  .pad .arrow.pressed { color:var(--text); background:#ffffff10; }
  .pad .up { top:0; left:33%; } .pad .down { bottom:0; left:33%; }
  .pad .left { left:0; top:33%; } .pad .right { right:0; top:33%; }
  .pad .ok { position:absolute; inset:31%; border-radius:50%; background:var(--key); font-weight:600; font-size:18px;
    box-shadow:0 0 0 1px #ffffff12, 0 6px 18px #0007; }
  .pad .ok.pressed { background:var(--accent); }
  .row { display:flex; gap:26px; }
  .row button { width:64px; height:64px; border-radius:50%; }
  .apps { width:100%; max-width:340px; display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .app { height:46px; border-radius:14px; font-size:15px; font-weight:600; }
  #status { min-height:20px; font-size:14px; color:var(--dim); text-align:center; max-width:320px; }
  #status.bad { color:var(--bad); }
</style>
</head><body>
<header>
  <button id="power" class="round" data-cmd="wake" aria-label="Wake TV">${icon("power")}</button>
  <div class="title"><b>Fire TV</b><span><i id="dot"></i><span id="ip">${escapeHtml(cfg.ip)}</span></span></div>
  <button class="round" data-cmd="settings" aria-label="Settings">${icon("gear")}</button>
</header>

<div class="pad">
  <button class="arrow up" data-cmd="key:dpad_up" data-repeat aria-label="Up">${icon("up")}</button>
  <button class="arrow left" data-cmd="key:dpad_left" data-repeat aria-label="Left">${icon("left")}</button>
  <button class="arrow right" data-cmd="key:dpad_right" data-repeat aria-label="Right">${icon("right")}</button>
  <button class="arrow down" data-cmd="key:dpad_down" data-repeat aria-label="Down">${icon("down")}</button>
  <button class="ok" data-cmd="key:select" aria-label="Select">OK</button>
</div>

<div class="row">
  <button data-cmd="key:back" aria-label="Back">${icon("back")}</button>
  <button data-cmd="key:home" aria-label="Home">${icon("home")}</button>
  <button data-cmd="key:menu" aria-label="Menu">${icon("menu")}</button>
</div>

<div class="row">
  <button data-hold="scan:back" aria-label="Rewind">${icon("rew")}</button>
  <button data-cmd="play" aria-label="Play or pause">${icon("play")}</button>
  <button data-hold="scan:forward" aria-label="Fast forward">${icon("ff")}</button>
</div>

<div class="apps">${apps}</div>
<div id="status">Ready</div>

<script>
  // Button presses go into a queue. The Scriptable side keeps asking for the next one
  // (waitForCommand), sends it to the TV, and reports back through showResult.
  var queue = [], waiting = null, idle = null;

  function waitForCommand(done) {
    waiting = done;
    clearTimeout(idle);
    // Answer "nothing yet" now and then so the Scriptable side never waits forever.
    idle = setTimeout(function () { if (waiting === done) { waiting = null; done(null); } }, 15000);
    pump();
  }
  function pump() {
    if (waiting && queue.length) {
      var done = waiting; waiting = null; clearTimeout(idle);
      done(queue.shift());
    }
  }
  function send(cmd, droppable) {
    if (droppable && queue.length > 2) return; // don't pile up held-arrow repeats
    queue.push(cmd);
    pump();
  }

  var statusEl = document.getElementById("status"), dot = document.getElementById("dot"), flash = null;
  function showResult(r) {
    if (!r || r.quiet) return;
    if (r.ip) document.getElementById("ip").textContent = r.ip;
    dot.className = r.ok ? "good" : "bad";
    clearTimeout(flash);
    if (r.ok) flash = setTimeout(function () { dot.className = ""; }, 900);
    if (r.msg || !r.ok) { statusEl.textContent = r.msg || "Something went wrong."; statusEl.className = r.ok ? "" : "bad"; }
    else if (statusEl.className === "bad") { statusEl.textContent = "Ready"; statusEl.className = ""; }
  }

  // Press handling: tap to send, hold arrows to repeat, hold rewind/fast-forward to scan.
  document.querySelectorAll("button").forEach(function (b) {
    var repeat = null, holding = false;
    function down(e) {
      e.preventDefault();
      b.classList.add("pressed");
      if (b.dataset.hold) { holding = true; send(b.dataset.hold + ":down"); return; }
      send(b.dataset.cmd);
      if (b.hasAttribute("data-repeat")) {
        repeat = setTimeout(function tick() { send(b.dataset.cmd, true); repeat = setTimeout(tick, 140); }, 420);
      }
    }
    function up() {
      b.classList.remove("pressed");
      clearTimeout(repeat); repeat = null;
      if (holding) { holding = false; send(b.dataset.hold + ":up"); }
    }
    b.addEventListener("pointerdown", down);
    b.addEventListener("pointerup", up);
    b.addEventListener("pointercancel", up);
    b.addEventListener("pointerleave", up);
    b.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  });
</script>
</body></html>`;
}

async function runRemote(cfg) {
  const view = new WebView();
  await view.loadHTML(page(cfg));
  let open = true;
  const closed = view.present(false).then(() => {
    open = false;
    return null;
  });

  while (open) {
    let cmd = null;
    try {
      cmd = await Promise.race([view.evaluateJavaScript("waitForCommand(completion)", true), closed]);
    } catch (e) {
      break;
    }
    if (!open) break;
    if (!cmd) continue;

    let result;
    if (cmd === "settings") {
      const updated = await settings(cfg);
      if (updated) cfg = updated;
      result = updated ? { ok: true, msg: `Paired with the TV at ${cfg.ip}`, ip: cfg.ip } : { ok: true, quiet: true };
    } else {
      result = await send(cfg, cmd);
    }
    try {
      await view.evaluateJavaScript(`showResult(${JSON.stringify(result)})`, false);
    } catch (e) {
      // the remote was closed while the TV was answering
    }
  }
}

// ------------------------------------------------------------------------------ start

async function main() {
  if (RESET) {
    if (Keychain.contains(STORE_IP)) Keychain.remove(STORE_IP);
    if (Keychain.contains(STORE_TOKEN)) Keychain.remove(STORE_TOKEN);
  }
  let cfg = stored(STORE_IP) && stored(STORE_TOKEN) ? { ip: stored(STORE_IP), token: stored(STORE_TOKEN) } : null;
  if (!cfg) {
    cfg = await pair(stored(STORE_IP));
    if (!cfg) return;
  }
  await runRemote(cfg);
}

await main();
Script.complete();
