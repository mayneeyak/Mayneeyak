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
        return { ok: false, msg: "The TV doesn't recognize this iPhone anymore. Tap Pair to pair again." };
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
// Built with Scriptable's native table (UITable), so it looks and works like the rest of iOS.

const T = "︎"; // shows ▲ ▶ etc. as plain symbols instead of emoji

function buttonCell(label, size, onTap) {
  const cell = UITableCell.button(label);
  cell.titleFont = Font.boldSystemFont(size);
  cell.centerAligned();
  cell.dismissOnTap = false;
  cell.onTap = onTap;
  return cell;
}

function blankCell() {
  return UITableCell.text("");
}

async function runRemote(cfg) {
  const table = new UITable();
  table.showSeparators = false;

  let status = "Ready";
  let statusIsError = false;
  let busy = Promise.resolve();

  // Presses are sent one at a time, in the order you tap them.
  function press(cmd) {
    busy = busy.then(async () => {
      let result;
      if (cmd === "settings") {
        const updated = await settings(cfg);
        if (updated) cfg = updated;
        result = updated ? { ok: true, msg: `Paired with the TV at ${cfg.ip}` } : null;
      } else if (cmd.startsWith("tapscan:")) {
        const dir = cmd.split(":")[1];
        result = await send(cfg, `scan:${dir}:down`);
        if (result.ok) {
          await pause(350);
          result = await send(cfg, `scan:${dir}:up`);
        }
      } else {
        result = await send(cfg, cmd);
      }
      if (!result) return;
      const nextStatus = result.msg || (result.ok ? "Ready" : "Something went wrong.");
      if (nextStatus !== status || statusIsError === result.ok) {
        status = nextStatus;
        statusIsError = !result.ok;
        build();
        table.reload();
      }
    }).catch(() => {});
  }

  function row(cells, height) {
    const r = new UITableRow();
    r.height = height;
    r.cellSpacing = 10;
    cells.forEach((c) => r.addCell(c));
    table.addRow(r);
  }

  function build() {
    table.removeAllRows();

    const title = UITableCell.text("Fire TV", `TV at ${cfg.ip}`);
    title.titleFont = Font.boldSystemFont(22);
    title.centerAligned();
    row([buttonCell("Wake", 17, () => press("wake")), title, buttonCell("Pair", 17, () => press("settings"))], 70);

    row([blankCell(), buttonCell("▲" + T, 34, () => press("key:dpad_up")), blankCell()], 72);
    row([
      buttonCell("◀" + T, 34, () => press("key:dpad_left")),
      buttonCell("OK", 30, () => press("key:select")),
      buttonCell("▶" + T, 34, () => press("key:dpad_right")),
    ], 80);
    row([blankCell(), buttonCell("▼" + T, 34, () => press("key:dpad_down")), blankCell()], 72);

    row([
      buttonCell("Back", 19, () => press("key:back")),
      buttonCell("Home", 19, () => press("key:home")),
      buttonCell("Menu", 19, () => press("key:menu")),
    ], 64);
    row([
      buttonCell("⏪" + T, 30, () => press("tapscan:back")),
      buttonCell("⏯" + T, 30, () => press("play")),
      buttonCell("⏩" + T, 30, () => press("tapscan:forward")),
    ], 64);

    for (let i = 0; i < APPS.length; i += 2) {
      const pair = APPS.slice(i, i + 2).map((a) => buttonCell(a.name, 18, () => press(`app:${a.id}`)));
      if (pair.length === 1) pair.push(blankCell());
      row(pair, 56);
    }

    const s = UITableCell.text(status);
    s.titleFont = Font.systemFont(15);
    s.titleColor = statusIsError ? Color.red() : Color.gray();
    s.centerAligned();
    row([s], 60);
  }

  build();
  await table.present(false);
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
