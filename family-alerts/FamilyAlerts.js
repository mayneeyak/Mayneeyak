// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: green; icon-glyph: route;

/*
 * Family Alerts
 * Texts your family when you get home, when you leave home, and when you pass
 * downtown heading north toward Shoreline.
 *
 * How it fits together:
 *   - The iPhone Shortcuts app watches your location (Arrive / Leave automations).
 *   - Each automation runs this script with an event name, like "home-arrive".
 *   - This script decides whether that's worth a text and hands the text back.
 *   - The automation sends that text to your family with Send Message.
 * Setup steps are in README.md next to this file.
 *
 * "Heading north" works with two zones: downtown, and a checkpoint north of it.
 * Leaving downtown and then reaching the north checkpoint soon after means you're
 * driving north. Going the other way never sends that text.
 */

const SETTINGS = {
  destination: "Shoreline",

  // After you leave downtown, reaching the north checkpoint within this many
  // minutes counts as "heading north". Allows for rush-hour traffic.
  tripMinutes: 45,

  // The same event again within this many minutes is ignored. This stops double
  // texts when your phone wobbles in and out at the edge of a zone.
  repeatMinutes: 10,

  // What your family sees. {destination} is replaced with the destination above.
  messages: {
    "home-arrive": "Made it home 🏠",
    "home-leave": "Just left home 🚗",
    "heading-north": "Passing downtown, heading north toward {destination} 🚗",
  },

  // Adds the time to the end of each text, like "Made it home 🏠 (5:24 PM)".
  addTime: true,
};

// The event names to type into each automation's Run Script action.
const EVENTS = {
  "home-arrive": "Arrived home",
  "home-leave": "Left home",
  "downtown-leave": "Left downtown",
  "north-arrive": "Reached the north checkpoint",
};

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
// message is the text to send, or null when nothing should be sent.
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
      return { message: messageFor(event, now), note: "Texted" };

    case "downtown-leave":
      state.downtownLeftAt = now.toISOString();
      return { message: null, note: "Left downtown (no text yet, waiting for the north checkpoint)" };

    case "north-arrive":
      if (minutesSince(state.downtownLeftAt) <= SETTINGS.tripMinutes) {
        state.downtownLeftAt = null; // one text per trip
        return { message: messageFor("heading-north", now), note: "Texted" };
      }
      return { message: null, note: "Didn't come from downtown just before, so no text" };
  }
  return { message: null, note: "" };
}

function record(event, now) {
  const state = loadState();
  const result = decide(event, now, state);
  state.log.unshift({ t: now.toISOString(), event, note: result.note });
  state.log = state.log.slice(0, 30);
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

async function menu() {
  const a = new Alert();
  a.title = "Family Alerts";
  a.message = "This runs on its own from your Shortcuts automations. Here you can preview texts or check what happened.";
  a.addAction("Preview: arrive home");
  a.addAction("Preview: leave home");
  a.addAction("Preview: trip north");
  a.addAction("Recent activity");
  a.addCancelAction("Close");
  const choice = await a.presentAlert();
  const now = new Date();

  if (choice === 0) await show("Your family would get", messageFor("home-arrive", now));
  if (choice === 1) await show("Your family would get", messageFor("home-leave", now));
  if (choice === 2) {
    // Runs a pretend trip on a scratch copy, so your real history isn't touched.
    const scratch = freshState();
    decide("downtown-leave", new Date(now - 12 * 60000), scratch);
    const r = decide("north-arrive", now, scratch);
    await show(
      "Your family would get",
      `${r.message}\n\nThis text goes out when you leave the downtown zone and then reach the north checkpoint within ${SETTINGS.tripMinutes} minutes.`
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
}

// ------------------------------------------------------------------------------ start

const input = args.shortcutParameter ?? (args.plainTexts && args.plainTexts[0]);

if (input !== undefined && input !== null && String(input).trim() !== "") {
  // Run by an automation: no pop-ups, just hand the text (if any) back to Shortcuts.
  const result = record(String(input).trim().toLowerCase(), new Date());
  if (result.message) Script.setShortcutOutput(result.message);
} else if (config.runsInApp) {
  await menu();
}

Script.complete();
