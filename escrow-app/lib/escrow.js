// The escrow service: creating, joining, unlocking, funding, reporting
// outcomes, settling and expiring escrow accounts.

import * as C from './crypto.js';
import { validateTerms, computePayouts, resolveReports, isWorstFor, other, PARTIES } from './rules.js';

const OPEN = new Set(['awaiting_counterparty', 'awaiting_funding', 'active', 'disputed']);
const SESSION_MS = 30 * 60 * 1000;
const MAX_FAILS = 5;
const LOCKOUT_MS = 15 * 60 * 1000;

export class HttpError extends Error {
  constructor(status, msg) { super(msg); this.status = status; }
}

function passphraseOk(p) {
  if (typeof p !== 'string' || p.length < 10 || p.length > 200) throw new HttpError(400, 'Passphrase must be 10-200 characters');
  return p;
}

function partyInfo(name, payout) {
  const n = typeof name === 'string' ? name.trim() : '';
  const d = typeof payout === 'string' ? payout.trim() : '';
  if (n.length < 1 || n.length > 60) throw new HttpError(400, 'Name must be 1-60 characters');
  if (d.length < 3 || d.length > 200) throw new HttpError(400, 'Payout details must be 3-200 characters');
  return { name: n, payout: d };
}

export class EscrowService {
  constructor({ store, provider, feeBps = 0, retentionDays = 30, now = () => Date.now() }) {
    Object.assign(this, { store, provider, feeBps, retentionMs: retentionDays * 86400000, now });
    this.sessions = new Map();
    this.fails = new Map();
  }

  // ---------- helpers ----------

  #load(id) {
    const rec = this.store.get(String(id));
    if (!rec) throw new HttpError(404, 'Escrow not found');
    return rec;
  }

  #save(rec, key, state) {
    rec.blob = C.encryptState(key, state, rec.id);
    this.store.put(rec);
  }

  #event(state, who, text) {
    state.events.push({ at: new Date(this.now()).toISOString(), who, text });
  }

  #newSession(id, role, key) {
    const token = C.randomToken();
    this.sessions.set(token, { id, role, key, expires: this.now() + SESSION_MS });
    return token;
  }

  #session(token) {
    const s = token && this.sessions.get(token);
    if (!s || s.expires < this.now()) {
      if (s) this.sessions.delete(token);
      throw new HttpError(401, 'Session expired. Unlock the escrow again.');
    }
    s.expires = this.now() + SESSION_MS;
    return s;
  }

  #throttle(key) {
    const f = this.fails.get(key);
    if (f && f.until > this.now()) throw new HttpError(429, 'Too many wrong attempts. Try again in 15 minutes.');
  }

  #failed(key) {
    const f = this.fails.get(key) ?? { n: 0, until: 0 };
    if (f.until && f.until <= this.now()) { f.n = 0; f.until = 0; }
    f.n += 1;
    if (f.n >= MAX_FAILS) f.until = this.now() + LOCKOUT_MS;
    this.fails.set(key, f);
  }

  /** Apply the expiry rule if the deadline passed. Mutates rec/state. */
  async #checkExpiry(rec, state) {
    if (!OPEN.has(rec.status) || this.now() < rec.expiresAt) return false;
    if (rec.status === 'active' || rec.status === 'disputed') {
      await this.#settle(rec, state, state.rules.onExpiry, null, 'The deadline passed, so the creator\'s expiry rule was applied', 'expired');
    } else {
      await this.#refundAll(rec, state, 'The deadline passed before the escrow was funded; deposits refunded', 'expired');
    }
    return true;
  }

  #deposited(state) {
    return { creator: state.deposits.creator?.amount ?? 0, counterparty: state.deposits.counterparty?.amount ?? 0 };
  }

  async #settle(rec, state, split, outcomeId, reason, status = 'settled') {
    const amounts = computePayouts(split, this.#deposited(state), this.feeBps);
    const transfers = [];
    for (const role of PARTIES) {
      const amount = amounts[role];
      if (!amount) continue;
      const base = { escrowId: rec.id, role, amount, currency: state.currency };
      const dep = state.deposits[role];
      // A refund of exactly your own deposit goes back to how you paid; anything else is a payout.
      const { ref } = split.type === 'refund' && dep
        ? await this.provider.refund({ ...base, depositRef: dep.ref })
        : await this.provider.payout({ ...base, destination: state.parties[role].payout });
      transfers.push({ role, amount, ref, kind: split.type === 'refund' ? 'refund' : 'payout' });
    }
    state.settlement = { outcomeId, reason, fee: amounts.fee, transfers, at: new Date(this.now()).toISOString() };
    rec.status = status;
    rec.closedAt = this.now();
    this.#event(state, 'system', `${reason}. ${transfers.map((t) => `${state.parties[t.role].name}: ${fmt(t.amount, state.currency)}`).join(', ') || 'Nothing to pay out'}.`);
  }

  async #refundAll(rec, state, reason, status) {
    await this.#settle(rec, state, { type: 'refund' }, null, reason, status);
  }

  // ---------- public operations ----------

  async create(input) {
    const terms = validateTerms(input);
    const passphrase = passphraseOk(input.passphrase);
    const me = partyInfo(input.name, input.payout);

    const id = C.randomToken(12);
    const inviteCode = C.randomToken(18);
    const key = C.newDataKey();
    const now = this.now();
    const rec = {
      id,
      createdAt: now,
      expiresAt: now + Math.round(terms.expiresInHours * 3600000),
      status: 'awaiting_counterparty',
      wraps: {
        creator: await C.wrapKey(key, passphrase, `${id}:creator`),
        counterparty: null,
        invite: await C.wrapKey(key, inviteCode, `${id}:invite`),
      },
    };
    const state = {
      kind: terms.kind,
      creatorRole: terms.creatorRole,
      title: terms.title,
      description: terms.description,
      currency: terms.currency,
      rules: terms.rules,
      parties: { creator: me, counterparty: null },
      deposits: { creator: null, counterparty: null },
      reports: { creator: null, counterparty: null },
      settlement: null,
      events: [],
    };
    this.#event(state, 'creator', `${me.name} created the escrow and set its rules`);
    this.#save(rec, key, state);
    return { id, inviteCode, token: this.#newSession(id, 'creator', key), role: 'creator' };
  }

  async #openWithInvite(rec, inviteCode, ip) {
    const tk = `${ip}:${rec.id}:invite`;
    this.#throttle(tk);
    const key = await C.unwrapKey(rec.wraps.invite, String(inviteCode ?? ''), `${rec.id}:invite`);
    if (!key) {
      this.#failed(tk);
      throw new HttpError(403, rec.wraps.invite ? 'This invite link is not valid' : 'This invite has already been used');
    }
    return key;
  }

  /** Let an invitee read the terms before agreeing to them. */
  async preview(id, inviteCode, ip = '') {
    const rec = this.#load(id);
    const key = await this.#openWithInvite(rec, inviteCode, ip);
    const state = C.decryptState(key, rec.blob, rec.id);
    return this.#view(rec, state, 'counterparty');
  }

  async join(id, input, ip = '') {
    return this.store.withLock(String(id), async () => {
      const rec = this.#load(id);
      const key = await this.#openWithInvite(rec, input.inviteCode, ip);
      const state = C.decryptState(key, rec.blob, rec.id);
      if (await this.#checkExpiry(rec, state)) { this.#save(rec, key, state); throw new HttpError(410, 'This escrow expired before you joined'); }
      if (rec.status !== 'awaiting_counterparty') throw new HttpError(409, 'This escrow is no longer accepting a counterparty');
      if (input.acceptTerms !== true) throw new HttpError(400, 'You must accept the creator\'s rules to join');
      const passphrase = passphraseOk(input.passphrase);
      if (await C.unwrapKey(rec.wraps.creator, passphrase, `${rec.id}:creator`)) throw new HttpError(400, 'Choose a different passphrase from the creator\'s');
      const me = partyInfo(input.name, input.payout);

      rec.wraps.counterparty = await C.wrapKey(key, passphrase, `${rec.id}:counterparty`);
      rec.wraps.invite = null; // the invite link stops working from now on
      rec.status = 'awaiting_funding';
      state.parties.counterparty = me;
      this.#event(state, 'counterparty', `${me.name} joined and accepted the rules. The rules are now locked.`);
      this.#maybeActivate(rec, state);
      this.#save(rec, key, state);
      return { token: this.#newSession(rec.id, 'counterparty', key), role: 'counterparty' };
    });
  }

  async unlock(id, passphrase, ip = '') {
    const rec = this.#load(id);
    const tk = `${ip}:${rec.id}`;
    this.#throttle(tk);
    for (const role of PARTIES) {
      const key = await C.unwrapKey(rec.wraps[role], String(passphrase ?? ''), `${rec.id}:${role}`);
      if (key) {
        this.fails.delete(tk);
        return { token: this.#newSession(rec.id, role, key), role };
      }
    }
    this.#failed(tk);
    throw new HttpError(403, 'Wrong passphrase');
  }

  lock(token) {
    this.sessions.delete(token);
  }

  /** Run an authenticated action with the escrow decrypted, then re-encrypt and save. */
  async #act(token, fn) {
    const s = this.#session(token);
    return this.store.withLock(s.id, async () => {
      const rec = this.#load(s.id);
      const state = C.decryptState(s.key, rec.blob, rec.id);
      const expired = await this.#checkExpiry(rec, state);
      const result = expired ? null : await fn(rec, state, s.role);
      this.#save(rec, s.key, state);
      return result ?? this.#view(rec, state, s.role);
    });
  }

  view(token) {
    return this.#act(token, () => null);
  }

  deposit(token) {
    return this.#act(token, async (rec, state, role) => {
      if (rec.status !== 'awaiting_funding') throw new HttpError(409, rec.status === 'awaiting_counterparty' ? 'Wait for the other party to join first' : 'Deposits are closed');
      const amount = state.rules.deposits[role];
      if (!amount) throw new HttpError(409, 'You have nothing to deposit');
      if (state.deposits[role]) throw new HttpError(409, 'You already deposited');
      const { ref } = await this.provider.collect({ escrowId: rec.id, role, amount, currency: state.currency });
      state.deposits[role] = { amount, ref, at: new Date(this.now()).toISOString() };
      this.#event(state, role, `${state.parties[role].name} deposited ${fmt(amount, state.currency)}`);
      this.#maybeActivate(rec, state);
    });
  }

  #maybeActivate(rec, state) {
    if (rec.status !== 'awaiting_funding') return;
    const funded = PARTIES.every((r) => !state.rules.deposits[r] || state.deposits[r]);
    if (!funded) return;
    rec.status = 'active';
    this.#event(state, 'system', `Fully funded. ${fmt(sum(this.#deposited(state)), state.currency)} is now held until an outcome is confirmed.`);
  }

  report(token, outcomeId) {
    return this.#act(token, async (rec, state, role) => {
      if (rec.status !== 'active' && rec.status !== 'disputed') throw new HttpError(409, 'Outcomes can only be confirmed once the escrow is funded');
      const outcome = state.rules.outcomes.find((o) => o.id === outcomeId);
      if (!outcome) throw new HttpError(400, 'Unknown outcome');
      state.reports[role] = outcome.id;
      this.#event(state, role, `${state.parties[role].name} confirmed: "${outcome.label}"`);
      const r = resolveReports(state.rules, state.reports, this.#deposited(state));
      if (r.settle) {
        const o = state.rules.outcomes.find((x) => x.id === r.settle);
        await this.#settle(rec, state, o.split, o.id, `${r.reason}: "${o.label}"`);
      } else if (r.disputed) {
        if (rec.status !== 'disputed') this.#event(state, 'system', 'The parties disagree. Funds stay locked until you agree or the deadline passes.');
        rec.status = 'disputed';
      } else {
        rec.status = 'active';
      }
    });
  }

  cancel(token) {
    return this.#act(token, async (rec, state, role) => {
      if (rec.status !== 'awaiting_counterparty' && rec.status !== 'awaiting_funding') {
        throw new HttpError(409, 'Once fully funded, an escrow can only end through its rules');
      }
      await this.#refundAll(rec, state, `${state.parties[role].name} cancelled before it was fully funded; deposits refunded`, 'cancelled');
    });
  }

  /** Delete closed escrows once the retention period is over. */
  purge() {
    let n = 0;
    for (const r of this.store.all()) {
      if (!OPEN.has(r.status) && r.closedAt && this.now() - r.closedAt > this.retentionMs) { this.store.delete(r.id); n++; }
    }
    for (const [t, s] of this.sessions) if (s.expires < this.now()) this.sessions.delete(t);
    return n;
  }

  #view(rec, state, role) {
    const deposited = this.#deposited(state);
    const required = state.rules.deposits;
    const potIfFunded = sum(required);
    const sides = state.kind === 'purchase'
      ? { creator: state.creatorRole, counterparty: state.creatorRole === 'buyer' ? 'seller' : 'buyer' }
      : { creator: 'bettor', counterparty: 'bettor' };
    const party = (r) => state.parties[r] && { name: state.parties[r].name, side: sides[r], ...(r === role ? { payout: state.parties[r].payout } : {}) };
    return {
      id: rec.id,
      you: role,
      status: rec.status,
      createdAt: rec.createdAt,
      expiresAt: rec.expiresAt,
      purgeAt: rec.closedAt ? rec.closedAt + this.retentionMs : null,
      kind: state.kind,
      title: state.title,
      description: state.description,
      currency: state.currency,
      feeBps: this.feeBps,
      provider: this.provider.name,
      parties: { creator: party('creator'), counterparty: party('counterparty') },
      deposits: Object.fromEntries(PARTIES.map((r) => [r, { required: required[r], paid: !!state.deposits[r] }])),
      outcomes: state.rules.outcomes.map((o) => ({
        ...o,
        payouts: computePayouts(o.split, required, this.feeBps),
        settlesIfYouConfirm: isWorstFor(state.rules, o.id, role, required),
      })),
      onExpiry: { split: state.rules.onExpiry, payouts: computePayouts(state.rules.onExpiry, required, this.feeBps) },
      pot: { held: sum(deposited), whenFunded: potIfFunded },
      reports: state.reports,
      settlement: state.settlement,
      events: state.events,
    };
  }
}

function sum(o) { return o.creator + o.counterparty; }
function fmt(cents, cur) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: cur }).format(cents / 100);
}
