// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: green; icon-glyph: route;

/*
 * Family Alerts
 * Sends push alerts to your family's phones when you get home, when you leave home,
 * and when you pass downtown heading north toward Shoreline.
 *
 * Your family gets the alerts in the free "ntfy" app (iPhone or Android). This script
 * makes a private channel for you; open it in Scriptable and tap "Invite family" to
 * send them the steps.
 *
 * How it fits together:
 *   - The iPhone Shortcuts app watches your location (Arrive / Leave automations).
 *   - Each automation runs this script with an event name, like "home-arrive".
 *   - This script decides whether that's worth an alert and pushes it to your channel.
 * Setup steps are in README.md next to this file.
 *
 * "Heading north" works with two zones: downtown, and a checkpoint north of it.
 * Leaving downtown and then reaching the north checkpoint soon after means you're
 * driving north. Going the other way never sends that alert.
 */

const SETTINGS = {
  destination: "Shoreline",

  // After you leave downtown, reaching the north checkpoint within this many
  // minutes counts as "heading north". Allows for rush-hour traffic.
  tripMinutes: 45,

  // The same event again within this many minutes is ignored. This stops double
  // alerts when your phone wobbles in and out at the edge of a zone.
  repeatMinutes: 10,

  // What your family sees. {destination} is replaced with the destination above.
  messages: {
    "home-arrive": "Made it home 🏠",
    "home-leave": "Just left home 🚗",
    "heading-north": "Passing downtown, heading north toward {destination} 🚗",
  },

  // Adds the time to the end of each alert, like "Made it home 🏠 (5:24 PM)".
  addTime: true,

  // The free public ntfy server. Change only if you run your own.
  server: "https://ntfy.sh",
};

// The event names to type into each automation's Run Script action.
const EVENTS = {
  "home-arrive": "Arrived home",
  "home-leave": "Left home",
  "downtown-leave": "Left downtown",
  "north-arrive": "Reached the north checkpoint",
};

// ---------------------------------------------------------------- your name and channel

const KEY_NAME = "family-alerts.name";
const KEY_CHANNEL = "family-alerts.channel";

function myName() {
  return Keychain.contains(KEY_NAME) ? Keychain.get(KEY_NAME) : "";
}

// Your private channel. Made once, then kept in the iPhone's Keychain. It's long and
// random so nobody can guess it; anyone who has it can see your alerts.
function channel() {
  if (Keychain.contains(KEY_CHANNEL)) return Keychain.get(KEY_CHANNEL);
  const chars = "abcdefghijkmnpqrstuvwxyz23456789";
  let id = "family-";
  for (let i = 0; i < 20; i++) id += chars[Math.floor(Math.random() * chars.length)];
  Keychain.set(KEY_CHANNEL, id);
  return id;
}

function pause(ms) {
  return new Promise((resolve) => Timer.schedule(ms, false, resolve));
}

// Pushes an alert to everyone subscribed to your channel. Returns true if it went out.
async function push(message) {
  const req = new Request(SETTINGS.server);
  req.method = "POST";
  req.timeoutInterval = 10;
  req.headers = { "Content-Type": "application/json" };
  req.body = JSON.stringify({
    topic: channel(),
    title: myName() || "Family Alerts",
    message,
    priority: 4, // high: makes a sound and shows on the lock screen
  });
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      await req.loadString();
      const status = req.response && req.response.statusCode;
      if (status >= 200 && status < 300) return true;
    } catch (e) {
      // no signal for a moment: wait and try once more
    }
    if (attempt === 0) await pause(3000);
  }
  return false;
}

// ------------------------------------------------------------------------- saved state

const files = FileManager.local();
const STATE_PATH = files.joinPath(files.documentsDirectory(), "family-alerts-state.json");

function freshState() {
  return { last: {}, downtownLeftAt: null, log: [] };
}

function loadState() {
  try {
    if (files.fileExists(STATE_PATH)) {
      const s = JSON.parse(files.readString(STATE_PATH));
      return { ...freshState(), ...s, last: s.last || {}, log: s.log || [] };
    }
  } catch (e) {
    // a damaged state file just starts over
  }
  return freshState();
}

function saveState(state) {
  files.writeString(STATE_PATH, JSON.stringify(state));
}

// ------------------------------------------------------------------------------ logic

function timeText(date) {
  const f = new DateFormatter();
  f.useNoDateStyle();
  f.useShortTimeStyle();
  return f.string(date);
}

function messageFor(kind, now) {
  let text = SETTINGS.messages[kind].replace("{destination}", SETTINGS.destination);
  if (SETTINGS.addTime) text += ` (${timeText(now)})`;
  return text;
}

// Decides what an event means. Returns { message, note } and updates state.
// message is the alert to send, or null when nothing should be sent.
function decide(event, now, state) {
  const minutesSince = (iso) => (iso ? (now - new Date(iso)) / 60000 : Infinity);

  if (!EVENTS[event]) {
    return { message: null, note: `Unknown event "${event}". Use one of: ${Object.keys(EVENTS).join(", ")}` };
  }
  if (minutesSince(state.last[event]) < SETTINGS.repeatMinutes) {
    return { message: null, note: "Same event again too soon, ignored" };
  }
  state.last[event] = now.toISOString();

  switch (event) {
    case "home-arrive":
    case "home-leave":
      return { message: messageFor(event, now), note: "" };

    case "downtown-leave":
      state.downtownLeftAt = now.toISOString();
      return { message: null, note: "Left downtown (no alert yet, waiting for the north checkpoint)" };

    case "north-arrive":
      if (minutesSince(state.downtownLeftAt) <= SETTINGS.tripMinutes) {
        state.downtownLeftAt = null; // one alert per trip
        return { message: messageFor("heading-north", now), note: "" };
      }
      return { message: null, note: "Didn't come from downtown just before, so no alert" };
  }
  return { message: null, note: "" };
}

function logEntry(state, now, event, note) {
  state.log.unshift({ t: now.toISOString(), event, note });
  state.log = state.log.slice(0, 30);
}

async function handleEvent(event, now) {
  const state = loadState();
  const result = decide(event, now, state);
  saveState(state); // save the decision before the network call, in case iOS stops us early
  let note = result.note;
  if (result.message) {
    note = (await push(result.message)) ? "Alert sent to family" : "Couldn't send the alert (no internet?)";
  }
  logEntry(state, now, event, note);
  saveState(state);
  return result;
}

// ----------------------------------------------------------------- when you open it yourself

async function show(title, message) {
  const a = new Alert();
  a.title = title;
  a.message = message;
  a.addAction("OK");
  await a.presentAlert();
}

async function askName() {
  const a = new Alert();
  a.title = "What's your name?";
  a.message = "Your family sees this at the top of every alert.";
  a.addTextField("Your name", myName());
  a.addAction("Save");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return;
  const name = a.textFieldValue(0).trim();
  if (name) Keychain.set(KEY_NAME, name);
}

function inviteText() {
  const who = myName() || "me";
  return (
    `Get alerts when ${who} gets home, leaves home, or is heading north toward ${SETTINGS.destination}:\n\n` +
    `1. Install the free app "ntfy" from the App Store (or Google Play).\n` +
    `2. Open it, tap +, and subscribe to this topic:\n${channel()}\n` +
    `3. Allow notifications when it asks.\n\n` +
    `No phone app? You can also follow along at ${SETTINGS.server}/${channel()}`
  );
}

async function invite() {
  await ShareSheet.present([inviteText()]);
}

async function menu() {
  if (!myName()) {
    await show(
      "Welcome to Family Alerts",
      "Two quick things: tell it your name, then invite your family so they get the alerts on their phones."
    );
    await askName();
    await invite();
  }

  const a = new Alert();
  a.title = "Family Alerts";
  a.message =
    `Alerts go to your private channel:\n${channel()}\n\n` +
    "This runs on its own from your Shortcuts automations.";
  a.addAction("Invite family");
  a.addAction("Send a test alert");
  a.addAction("Preview: trip north");
  a.addAction("Recent activity");
  a.addAction("Change my name");
  a.addDestructiveAction("Start a new private channel");
  a.addCancelAction("Close");
  const choice = await a.presentAlert();
  const now = new Date();

  if (choice === 0) await invite();
  if (choice === 1) {
    const ok = await push(`Test alert. If you can see this, you're all set 👍 (${timeText(now)})`);
    await show(
      ok ? "Test alert sent" : "Couldn't send",
      ok
        ? "Everyone subscribed to your channel should get it within a few seconds."
        : "Check that your iPhone is online, then try again."
    );
  }
  if (choice === 2) {
    // Runs a pretend trip on a scratch copy, so your real history isn't touched.
    const scratch = freshState();
    decide("downtown-leave", new Date(now - 12 * 60000), scratch);
    const r = decide("north-arrive", now, scratch);
    await show(
      "Your family would get",
      `${myName() || "Family Alerts"}\n${r.message}\n\nThis goes out when you leave the downtown zone and then reach the north checkpoint within ${SETTINGS.tripMinutes} minutes.`
    );
  }
  if (choice === 3) {
    const log = loadState().log;
    const lines = log.length
      ? log.slice(0, 15).map((e) => {
          const d = new Date(e.t);
          const day = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
          return `${day} ${timeText(d)}: ${EVENTS[e.event] || e.event}\n   ${e.note}`;
        })
      : ["Nothing yet. Once your automations run, each one shows up here."];
    await show("Recent activity", lines.join("\n"));
  }
  if (choice === 4) await askName();
  if (choice === 5) await newChannel();
}

// Makes a fresh channel name, for example if the old one was shared by mistake.
// Family must subscribe to the new one; the old one stops getting alerts.
async function newChannel() {
  const a = new Alert();
  a.title = "Start a new private channel?";
  a.message = "Your family will stop getting alerts until they subscribe to the new channel in ntfy. You'll get a new invite to send them.";
  a.addDestructiveAction("Start new channel");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return;
  Keychain.remove(KEY_CHANNEL);
  channel();
  await invite();
}

// ------------------------------------------------------------------------------ start

const input = args.shortcutParameter ?? (args.plainTexts && args.plainTexts[0]);

if (input !== undefined && input !== null && String(input).trim() !== "") {
  // Run by an automation: no pop-ups, just decide and send.
  const result = await handleEvent(String(input).trim().toLowerCase(), new Date());
  if (result.message) Script.setShortcutOutput(result.message);
} else if (config.runsInApp) {
  await menu();
}

Script.complete();
