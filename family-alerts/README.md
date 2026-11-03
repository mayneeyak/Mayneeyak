# Family Alerts

Sends push alerts to your family's phones when you:

- 🏠 **get home:** "Made it home 🏠 (6:10 PM)"
- 🚗 **leave home:** "Just left home 🚗 (8:02 AM)"
- ⬆️ **pass downtown heading north:** "Passing downtown, heading north toward Shoreline 🚗 (5:37 PM)"

Your family gets them in **ntfy**, a free notifications app for iPhone and Android.
Alerts pop up with a sound, show on the lock screen with your name on top, and stay
in a history in the app. Nobody needs an account.

Everything on your side runs on your iPhone with **Scriptable** and the **Shortcuts** app.
Your location never leaves your phone; only the alert text is sent.

## How it works

The Shortcuts app can run an automation when you arrive at or leave a place. You make
four of them. Each one runs the **Family Alerts** script with an event name, and the script
decides whether to send an alert:

| Automation | Place | Event name to type |
|---|---|---|
| **Arrive** | Home | `home-arrive` |
| **Leave** | Home | `home-leave` |
| **Leave** | Downtown | `downtown-leave` |
| **Arrive** | North checkpoint | `north-arrive` |

**How it knows you're heading north:** leaving the downtown zone and then reaching a
checkpoint north of downtown within 45 minutes means you're driving north. Going south
(checkpoint first, downtown after) never sends that alert. You get one alert per trip.

**Where to put the zones** (for Seattle → Shoreline):
- **Downtown:** around the middle of downtown, big enough to cover downtown and the
  freeway through it, about **1 km**.
- **North checkpoint:** on your usual route north of downtown but before Shoreline,
  for example I-5 around **Northgate**, about **500–800 m**. Don't let it overlap the downtown
  zone or your home zone.
- **Home:** your address, about **150 m**.

## Setup

### 1. Add the script (your iPhone)
1. Open **Scriptable**, tap **+**, and paste all of [`FamilyAlerts.js`](FamilyAlerts.js).
2. Tap the title at the top and name it **Family Alerts**. Tap **Done**.
3. Tap the script to run it. It asks your name, then opens the share sheet with
   an **invite** for your family. Send it to them in Messages.

### 2. Your family subscribes (their phones)
The invite tells them what to do:
1. Install the free **ntfy** app from the App Store or Google Play.
2. Open it, tap **+**, and type the topic from the invite (it looks like `family-k3x9...`).
   Leave the server as the default (ntfy.sh).
3. Allow notifications.

Then on your iPhone, open Family Alerts and tap **Send a test alert**. Everyone should
get it within a few seconds.

### 3. Make the four automations (your iPhone)
Do this once for each row of the table above.

1. Open **Shortcuts** and go to the **Automation** tab. Tap **+** (New Automation).
2. Pick **Arrive** or **Leave**.
3. Tap **Location > Choose**, search for the place or drag the map, and set the zone size. Tap **Done**.
4. Choose **Run Immediately** and turn **off** "Notify When Run". Tap **Next**.
5. Tap **New Blank Automation** and add one action: **Run Script** (from Scriptable).
   Choose **Family Alerts**, and in **Parameter** type the event name from the table,
   like `home-arrive`. Leave **Run In App** off.
6. Tap **Done**.

**Location access:** **Settings > Privacy & Security > Location Services** must be on.
If Shortcuts asks for location access, allow it.

## Checking it worked

Open **Family Alerts** in Scriptable and choose **Recent activity**. It lists every time an
automation ran and what happened, for example "Alert sent to family", "Same event again
too soon, ignored", or "Couldn't send the alert (no internet?)".

## Changing things

At the top of the script, in `SETTINGS`:
- `destination`: the place named in the "heading north" alert.
- `messages`: the exact wording of each alert.
- `tripMinutes`: how long after leaving downtown the checkpoint still counts (45).
- `repeatMinutes`: ignores the same event repeated within this time (10). This stops
  double alerts when you hover at the edge of a zone.
- `addTime`: set to `false` to leave the time off.

**Change your name:** open the script and choose **Change my name**.

## Privacy

- Your alerts go to a private channel with a long random name, made on your phone
  and kept in its Keychain. Only people who have that name get the alerts, so share
  it only with family.
- The alerts pass through ntfy.sh, a free public notification service. They contain only
  the alert text, never your location.
- If the channel name gets shared by mistake, open Family Alerts and choose
  **Start a new private channel**, then send your family the new invite.

## Good to know

- iPhone location automations can be a minute or two late, and very small zones can be
  missed at freeway speed. Bigger zones help.
- Low Power Mode, or turning off Location Services, can delay or stop them.
- If the "heading north" alert comes too late or too early, move the checkpoint.
