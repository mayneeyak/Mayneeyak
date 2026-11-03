# Family Alerts

Texts your family automatically when you:

- 🏠 **get home:** "Made it home 🏠 (6:10 PM)"
- 🚗 **leave home:** "Just left home 🚗 (8:02 AM)"
- ⬆️ **pass downtown heading north:** "Passing downtown, heading north toward Shoreline 🚗 (5:37 PM)"

It runs entirely on your iPhone. The texts come from your own number, so your family
doesn't need to install anything. Your location never leaves your phone; only the
texts do.

## How it works

The iPhone's **Shortcuts** app can run an automation when you arrive at or leave a place.
You make four of them. Each one runs the **Family Alerts** script with an event name, and
the script decides whether to send a text:

| Automation | Place | Event name to type |
|---|---|---|
| **Arrive** | Home | `home-arrive` |
| **Leave** | Home | `home-leave` |
| **Leave** | Downtown | `downtown-leave` |
| **Arrive** | North checkpoint | `north-arrive` |

**How it knows you're heading north:** leaving the downtown zone and then reaching a
checkpoint north of downtown within 45 minutes means you're driving north. Going south
(checkpoint first, downtown after) never sends that text. It sends one text per trip.

**Where to put the zones** (for Seattle → Shoreline):
- **Downtown:** around the middle of downtown, big enough to cover downtown and the
  freeway through it, about **1 km**.
- **North checkpoint:** on your usual route north of downtown but before Shoreline,
  for example I-5 around **Northgate**, about **500–800 m**. Don't let it overlap the downtown
  zone or your home zone.
- **Home:** your address, about **150 m**.

Zones bigger than that are fine. Small zones can be missed at freeway speed.

## Setup

### 1. Add the script
1. Open **Scriptable**, tap **+**, and paste all of [`FamilyAlerts.js`](FamilyAlerts.js).
2. Tap the title at the top and name it **Family Alerts**. Tap **Done**.
3. Tap it to try it: **Preview** shows exactly what your family will get.

### 2. Make the four automations
Do this once for each row of the table above.

1. Open **Shortcuts** and go to the **Automation** tab. Tap **+** (New Automation).
2. Pick **Arrive** or **Leave**.
3. Tap **Location > Choose**, search for the place or drag the map, and set the zone size. Tap **Done**.
4. Choose **Run Immediately** and turn **off** "Notify When Run". Tap **Next**.
5. Tap **New Blank Automation**. Then add these actions:
   1. **Run Script** (from Scriptable). Choose **Family Alerts**. In **Parameter**, type the
      event name from the table, like `home-arrive`. Leave **Run In App** off.
   2. **If**. It picks up the Run Script result by itself. Set the condition to **has any value**.
   3. Inside the If: **Send Message**. For the message, tap the field and pick the
      **Run Script** result from the bar above the keyboard. For recipients, add your family.
6. Tap **Done**.

> The **downtown-leave** automation never texts by itself (it just remembers when you
> left downtown), but give it the same three actions anyway. That keeps all four identical
> and easy to copy.

### 3. Check it's allowed to use your location
**Settings > Privacy & Security > Location Services** must be on. If Shortcuts asks
for location access, allow it.

## Checking it worked

Open **Family Alerts** in Scriptable and choose **Recent activity**. It lists every time an
automation ran and what it decided ("Texted", "Same event again too soon, ignored", and so on).

## Changing things

At the top of the script, in `SETTINGS`:
- `destination`: the place named in the "heading north" text.
- `messages`: the exact wording of each text.
- `tripMinutes`: how long after leaving downtown the checkpoint still counts (45).
- `repeatMinutes`: ignores the same event repeated within this time (10). This stops
  double texts when you hover at the edge of a zone.
- `addTime`: set to `false` to leave the time off.

## Good to know

- iPhone location automations can be a minute or two late, and very small zones can be
  missed when you drive past fast. Bigger zones help.
- Low Power Mode, or turning off Location Services, can delay or stop them.
- If the "heading north" text comes too late or too early, move the checkpoint.
- For only home arrive/leave, Apple's **Find My** app can also do it without any setup:
  open a family member, tap **Notify** (their name), and choose when you arrive or leave.
  The downtown-heading-north alert is what Find My can't do.
