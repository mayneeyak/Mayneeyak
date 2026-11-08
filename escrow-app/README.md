# Pact Escrow

A two-party escrow app. One person creates a **temporary, encrypted escrow account**
that only they and one other person can open. The creator sets the **rules for how the
money is paid out**: for example when the buyer confirms they received the item, or when
a bet is won. The other person reviews the rules and joins. After that the rules are locked.

It runs on Node.js with **no dependencies** and ships with a **sandbox payment provider**,
so you can try every step without real money.

```bash
cd escrow-app
npm start          # http://localhost:3000
npm test           # rule engine + full API flow tests
```

## How it works

1. **Create.** Choose *a purchase* (you're the buyer or the seller) or *a bet*. Set the
   deposits (purchase price, or each side's stake), the outcomes, and how the pot is split
   for each one: a percentage split, or "refund each deposit". Also choose what happens if
   nobody confirms an outcome before the deadline (1 to 90 days).
2. **Invite.** You get a private, single-use invite link. The other person opens it, reads
   the terms and rules, and joins with **their own passphrase**. The rules are now locked.
3. **Fund.** Each side deposits what the rules require. The money is held.
4. **Confirm.** Either party confirms an outcome:
   - If **both confirm the same outcome**, it pays out.
   - If a confirmation is **the worst possible result for the person confirming it**, it pays
     out right away. So the buyer confirming "item received" pays the seller immediately, and
     a bettor conceding they lost pays the winner immediately. Nobody can grab money this way,
     only give it up.
   - Anything else waits for the other party. If they confirm something different, the
     escrow is **disputed** and stays locked until they agree or the deadline passes.
5. **Deadline.** If the deadline passes first, the creator's expiry rule applies. Before it
   is fully funded, either party can cancel and all deposits are refunded.
6. **Temporary.** Closed escrows are deleted for good after `RETENTION_DAYS` (default 30).

### Default rules

| Type | Outcome | Pays |
|---|---|---|
| Purchase | Item received | 100% to the seller |
| Purchase | Not received | refund to the buyer |
| Bet | Creator wins / Challenger wins | 100% to the winner |
| Bet | Draw | refund each stake |
| Both | Deadline passes | refund each deposit |

The creator can rename these, change any split (e.g. 70/30), and add up to 8 outcomes.

## The encryption

- Every escrow has a random 256-bit key. Everything in it (title, terms, names, payout
  details, deposits, confirmations, history) is encrypted with **AES-256-GCM** under that key.
- That key is stored only **wrapped** (encrypted) once per party, with a key derived from
  that party's passphrase using **scrypt**. Passphrases are never stored.
- The invite link carries a one-time code in the URL fragment (which browsers never send to
  the server). The key is also wrapped under that code until the other person joins, then
  that wrap is deleted, so the link stops working.
- The data file on disk holds only ciphertext plus the status and timestamps
  (`test/api.test.js` checks that no names, terms or payout details leak into it).
- Unlocking gives a 30-minute session. Five wrong passphrases lock the escrow for 15 minutes.
- There is no passphrase reset: if both parties forget theirs, the escrow can't be opened.

Note: the server decrypts an escrow in memory while a party is using it, because it has to
enforce the rules and send the payouts. This protects the stored data (backups, a leaked
database, anyone without a passphrase), but you still have to trust whoever runs the server.

## Files

```
server.js            HTTP server, JSON API, static files, security headers
lib/crypto.js        AES-256-GCM, scrypt key wrapping
lib/rules.js         Rule validation, payout maths, "who can settle alone" logic
lib/escrow.js        Create / join / unlock / deposit / confirm / cancel / expiry
lib/store.js         JSON file storage with atomic writes and per-escrow locking
lib/payments.js      Payment provider interface + sandbox provider
public/              The web app (plain HTML/CSS/JS, no build step)
test/                node:test tests
```

### Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `3000` | Port to listen on |
| `DATA_FILE` | `data/escrows.json` | Where encrypted escrows are stored |
| `PLATFORM_FEE_BPS` | `0` | Service fee on split payouts, in basis points (100 = 1%). Refunds are never charged. |
| `RETENTION_DAYS` | `30` | Days to keep a closed escrow before deleting it |

## Going live with real money

The sandbox only records simulated transfers. Before handling real money:

- **Use a licensed payment processor** that supports holding funds for a marketplace, such
  as Stripe Connect (separate charges and transfers) or Adyen for Platforms, and implement the
  three methods in `lib/payments.js` (`collect`, `payout`, `refund`). Holding and moving other
  people's money usually requires money-transmitter licences; using such a processor is how
  most apps stay compliant. Check the rules where you operate.
- **Bets:** escrowing wagers between people is gambling in many places and is restricted or
  illegal in some, and most payment processors forbid it. Get legal advice before enabling
  bets with real money, or turn the bet option off.
- Serve it over **HTTPS** only (behind a reverse proxy such as Caddy or nginx).
- Swap the JSON file for a real database if more than one server process will run.
- Payout details are free text in this version; with a processor you would replace them with
  the processor's verified connected accounts.
