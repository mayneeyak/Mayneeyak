# Fire TV Remote for iPhone

A remote for a Fire TV (Toshiba Fire TV Edition, Fire TV Stick, Fire TV Cube...)
that runs on your iPhone and talks to the TV over Wi-Fi. You don't need a Mac or a computer:
it runs inside **Scriptable**, a free iPhone app that runs JavaScript.

- **Power:** wakes up the TV's Wi-Fi remote service if it has gone to sleep. (It can't switch the TV off.)
- **D-pad + OK:** hold an arrow to keep scrolling.
- **Back, Home, Menu.**
- **Rewind, Play/Pause, Fast-forward:** hold rewind or fast-forward to keep scanning.
- **App buttons:** Netflix, YouTube, Disney+ and Hulu. You can add your own.
- **Gear:** pair again or switch to a different TV.

## Set it up (about 3 minutes)

1. **Install Scriptable** from the App Store. It's free.
2. **Find the TV's IP address.** On the TV go to **Settings > My Fire TV > About > Network**
   (on some TVs it's **Settings > Device & Software > About > Network**)
   and write down the **IP Address** (it looks like `192.168.1.50`).
   Your iPhone has to be on the same Wi-Fi network as the TV.
3. **Add the script.** Open Scriptable, tap **+**, paste all of [`FireTVRemote.js`](FireTVRemote.js),
   then tap the name at the top and call it `TV Remote`. Tap **Done**.
4. **Run it.** Tap the script.
   - If the iPhone asks to let Scriptable **find devices on your local network**, tap **Allow**.
     If you tapped Don't Allow by mistake, turn it on in
     **Settings > Privacy & Security > Local Network > Scriptable**.
   - Type the TV's IP address.
   - A 4-digit code appears on the TV. Type it on the iPhone.
5. That's it. Next time it opens straight to the remote. It remembers the pairing in the
   iPhone's Keychain.

**Put it on your Home Screen:** open the **Shortcuts** app, make a new shortcut with the
Scriptable action **Run Script**, choose `TV Remote`, then use **Add to Home Screen** from the
shortcut's share menu. You can also say "Hey Siri, TV Remote".

Close the remote by swiping it down.

## Adding app buttons

At the top of the script there's a list called `APPS`. Each line is a label and the app's
package name:

```js
{ name: "Netflix", id: "com.netflix.ninja" },
```

## What it can't do

- **Volume and turning the TV off.** The Fire TV's Wi-Fi remote service doesn't offer them
  (Amazon's own Fire TV app can't do them either). Use the TV's remote for those.
- **Typing and voice search.** Use Amazon's free Fire TV app for these.

## Troubleshooting

- **"Can't reach the TV":** make sure the TV is on, the IP address is right, and your iPhone
  is on the same Wi-Fi (not on cellular data). The IP address can change after a router restart:
  tap the gear and enter the new one. Giving the TV a fixed IP address in your router
  settings stops that from happening.
- **"The TV doesn't recognize this iPhone":** tap the gear and pair again.
- **Start over completely:** change `const RESET = false;` to `true`, run the script once,
  then change it back.

## How it works

Fire TVs run a small remote-control service on your home network. It's the same one Amazon's
Fire TV app uses. The script:

1. Wakes the service with `POST http://<tv>:8009/apps/FireTVRemote`.
2. Pairs once: `POST https://<tv>:8080/v1/FireTV/pin/display` shows a code on the TV, and
   `POST .../pin/verify` with `{"pin": "1234"}` returns a token.
3. Sends buttons with that token:
   - keys: `POST /v1/FireTV?action=dpad_up` (and the other D-pad keys, `select`, `home`, `back`, `menu`);
   - media: `/v1/media?action=play`, and `/v1/media?action=scan` with a keyDown/keyUp body;
   - apps: `/v1/FireTV/app/<package>`.

The TV's service uses a self-signed certificate, which Scriptable is told to accept
(`allowInsecureRequest`). It only ever talks to the IP address you typed.

Amazon doesn't publish this service. These details come from community projects that
worked it out ([FireTVRest](https://github.com/SLC-Josh/FireTVRest),
[hms-firetv](https://github.com/hms-homelab/hms-firetv)), so a Fire TV software update could change it.
The script was tested against a stand-in TV that follows those details, not a real Fire TV.
