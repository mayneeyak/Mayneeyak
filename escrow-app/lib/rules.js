// Payout rules: what the creator decides, how it's validated, and how a
// settlement is computed. Pure functions, no I/O.
//
// Amounts are integer cents. Percent splits are basis points (10000 = 100%).
//
// A split is either
//   { type: 'refund' }                                   each party gets their own deposit back
//   { type: 'percent', creator: bps, counterparty: bps } the pot is divided (must total 10000)

export const PARTIES = ['creator', 'counterparty'];
export const MAX_CENTS = 100_000_000; // $1,000,000 per deposit
export const MIN_HOURS = 1;
export const MAX_HOURS = 24 * 90;

export function other(role) {
  return role === 'creator' ? 'counterparty' : 'creator';
}

/** Default rules for a new escrow, which the creator can then edit. */
export function presetRules(kind, creatorRole) {
  if (kind === 'purchase') {
    const seller = creatorRole === 'seller' ? 'creator' : 'counterparty';
    const buyer = other(seller);
    return {
      outcomes: [
        { id: 'received', label: 'Item received: pay the seller', split: pct({ [seller]: 10000, [buyer]: 0 }) },
        { id: 'not_received', label: 'Not received: refund the buyer', split: { type: 'refund' } },
      ],
      onExpiry: { type: 'refund' },
    };
  }
  return {
    outcomes: [
      { id: 'creator_wins', label: 'Creator wins', split: pct({ creator: 10000, counterparty: 0 }) },
      { id: 'counterparty_wins', label: 'Challenger wins', split: pct({ creator: 0, counterparty: 10000 }) },
      { id: 'draw', label: 'Draw: everyone gets their stake back', split: { type: 'refund' } },
    ],
    onExpiry: { type: 'refund' },
  };
}

function pct({ creator, counterparty }) {
  return { type: 'percent', creator, counterparty };
}

class RuleError extends Error {
  constructor(msg) { super(msg); this.status = 400; }
}

function cents(v, name) {
  if (!Number.isInteger(v) || v < 0 || v > MAX_CENTS) throw new RuleError(`${name} must be a whole number of cents between 0 and ${MAX_CENTS}`);
  return v;
}

function validSplit(s, where) {
  if (!s || typeof s !== 'object') throw new RuleError(`${where}: missing split`);
  if (s.type === 'refund') return { type: 'refund' };
  if (s.type !== 'percent') throw new RuleError(`${where}: split type must be "refund" or "percent"`);
  const c = s.creator, p = s.counterparty;
  for (const v of [c, p]) if (!Number.isInteger(v) || v < 0 || v > 10000) throw new RuleError(`${where}: shares must be 0-100%`);
  if (c + p !== 10000) throw new RuleError(`${where}: shares must add up to 100%`);
  return { type: 'percent', creator: c, counterparty: p };
}

/** Validate and normalise everything the creator submits. Throws RuleError. */
export function validateTerms(input) {
  const kind = input.kind;
  if (kind !== 'purchase' && kind !== 'bet') throw new RuleError('kind must be "purchase" or "bet"');
  const creatorRole = kind === 'purchase' ? input.creatorRole : null;
  if (kind === 'purchase' && creatorRole !== 'buyer' && creatorRole !== 'seller') throw new RuleError('creatorRole must be "buyer" or "seller"');

  const title = str(input.title, 'title', 1, 120);
  const description = str(input.description ?? '', 'description', 0, 2000);
  const currency = /^[A-Z]{3}$/.test(input.currency ?? 'USD') ? (input.currency ?? 'USD') : null;
  if (!currency) throw new RuleError('currency must be a 3-letter code such as USD');

  const deposits = {
    creator: cents(input.deposits?.creator, 'Creator deposit'),
    counterparty: cents(input.deposits?.counterparty, 'Counterparty deposit'),
  };
  if (kind === 'purchase') {
    const buyer = creatorRole === 'buyer' ? 'creator' : 'counterparty';
    if (deposits[buyer] === 0) throw new RuleError('The buyer must deposit the purchase price');
  }
  if (deposits.creator + deposits.counterparty === 0) throw new RuleError('At least one party must deposit money');

  if (!Array.isArray(input.outcomes) || input.outcomes.length < 2 || input.outcomes.length > 8) throw new RuleError('Define between 2 and 8 outcomes');
  const ids = new Set();
  const outcomes = input.outcomes.map((o, i) => {
    const id = String(o.id ?? '').trim();
    if (!/^[a-z0-9_]{1,32}$/.test(id)) throw new RuleError(`Outcome ${i + 1}: id must be lowercase letters, digits or _`);
    if (ids.has(id)) throw new RuleError(`Outcome ids must be unique (${id})`);
    ids.add(id);
    return { id, label: str(o.label, `Outcome ${i + 1} label`, 1, 120), split: validSplit(o.split, `Outcome "${id}"`) };
  });
  const onExpiry = validSplit(input.onExpiry ?? { type: 'refund' }, 'Expiry rule');

  const hours = Number(input.expiresInHours);
  if (!Number.isFinite(hours) || hours < MIN_HOURS || hours > MAX_HOURS) throw new RuleError(`The account must last between ${MIN_HOURS} hour and ${MAX_HOURS / 24} days`);

  return { kind, creatorRole, title, description, currency, rules: { deposits, outcomes, onExpiry }, expiresInHours: hours };
}

function str(v, name, min, max) {
  const s = typeof v === 'string' ? v.trim() : '';
  if (s.length < min || s.length > max) throw new RuleError(`${name} must be ${min}-${max} characters`);
  return s;
}

/**
 * Compute who gets what. `deposited` is { creator: cents, counterparty: cents }.
 * A platform fee (bps) applies to percent splits only; refunds are always whole.
 * Leftover cents from rounding go to the party with the larger share.
 */
export function computePayouts(split, deposited, feeBps = 0) {
  const pot = deposited.creator + deposited.counterparty;
  if (split.type === 'refund') return { fee: 0, creator: deposited.creator, counterparty: deposited.counterparty };
  const fee = Math.floor((pot * feeBps) / 10000);
  const net = pot - fee;
  const c = Math.floor((net * split.creator) / 10000);
  const p = Math.floor((net * split.counterparty) / 10000);
  const rest = net - c - p;
  return split.creator >= split.counterparty
    ? { fee, creator: c + rest, counterparty: p }
    : { fee, creator: c, counterparty: p + rest };
}

/**
 * Decide whether reports settle the escrow.
 *
 * - If both parties report the same outcome, it settles.
 * - A single report settles at once when it's the worst possible outcome for
 *   the person reporting it (e.g. the buyer confirming the item arrived, or a
 *   bettor conceding they lost). Nobody can cheat by giving money away.
 * - Anything else waits for the other party; if they report something
 *   different, the escrow is disputed until they agree or it expires.
 */
export function resolveReports(rules, reports, deposited) {
  const { creator, counterparty } = reports;
  if (creator && creator === counterparty) return { settle: creator, reason: 'Both parties confirmed' };
  for (const role of PARTIES) {
    const id = reports[role];
    if (!id || reports[other(role)]) continue;
    if (isWorstFor(rules, id, role, deposited)) return { settle: id, reason: `Confirmed by the ${role}, against their own interest` };
  }
  if (creator && counterparty) return { disputed: true };
  return { waiting: true };
}

export function isWorstFor(rules, outcomeId, role, deposited) {
  const amount = (o) => computePayouts(o.split, deposited)[role];
  const target = rules.outcomes.find((o) => o.id === outcomeId);
  const worst = Math.min(...rules.outcomes.map(amount));
  return !!target && amount(target) === worst;
}
