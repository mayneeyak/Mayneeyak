import test from 'node:test';
import assert from 'node:assert/strict';
import { computePayouts, resolveReports, validateTerms, presetRules } from '../lib/rules.js';

const bet = presetRules('bet');
const buy = presetRules('purchase', 'buyer'); // creator is the buyer
const dBet = { creator: 5000, counterparty: 5000 };
const dBuy = { creator: 25000, counterparty: 0 };

test('percent splits and refunds', () => {
  assert.deepEqual(computePayouts({ type: 'percent', creator: 10000, counterparty: 0 }, dBet), { fee: 0, creator: 10000, counterparty: 0 });
  assert.deepEqual(computePayouts({ type: 'refund' }, { creator: 7, counterparty: 3 }, 500), { fee: 0, creator: 7, counterparty: 3 });
  // 3333 / 6667 of 101 cents: rounding leftover goes to the bigger share, and nothing is lost
  const r = computePayouts({ type: 'percent', creator: 3333, counterparty: 6667 }, { creator: 101, counterparty: 0 });
  assert.equal(r.creator + r.counterparty, 101);
  assert.ok(r.counterparty > r.creator);
});

test('platform fee comes out of percent splits', () => {
  assert.deepEqual(computePayouts({ type: 'percent', creator: 5000, counterparty: 5000 }, dBet, 250), { fee: 250, creator: 4875, counterparty: 4875 });
});

test('buyer confirming receipt settles alone; seller claiming it does not', () => {
  assert.equal(resolveReports(buy, { creator: 'received', counterparty: null }, dBuy).settle, 'received');
  assert.ok(resolveReports(buy, { creator: null, counterparty: 'received' }, dBuy).waiting);
  // seller conceding a refund settles alone
  assert.equal(resolveReports(buy, { creator: null, counterparty: 'not_received' }, dBuy).settle, 'not_received');
});

test('bets: conceding settles, claiming waits, disagreement disputes', () => {
  assert.equal(resolveReports(bet, { creator: 'counterparty_wins', counterparty: null }, dBet).settle, 'counterparty_wins');
  assert.ok(resolveReports(bet, { creator: 'creator_wins', counterparty: null }, dBet).waiting);
  assert.ok(resolveReports(bet, { creator: 'draw', counterparty: null }, dBet).waiting);
  assert.ok(resolveReports(bet, { creator: 'creator_wins', counterparty: 'counterparty_wins' }, dBet).disputed);
  assert.equal(resolveReports(bet, { creator: 'draw', counterparty: 'draw' }, dBet).settle, 'draw');
});

test('validation rejects bad rules', () => {
  const base = { kind: 'bet', title: 'x', deposits: dBet, outcomes: bet.outcomes, expiresInHours: 24 };
  assert.ok(validateTerms(base));
  assert.throws(() => validateTerms({ ...base, outcomes: [{ id: 'a', label: 'A', split: { type: 'percent', creator: 6000, counterparty: 6000 } }, bet.outcomes[0]] }), /100%/);
  assert.throws(() => validateTerms({ ...base, outcomes: [bet.outcomes[0]] }), /between 2 and 8/);
  assert.throws(() => validateTerms({ ...base, deposits: { creator: 0, counterparty: 0 } }), /deposit/);
  assert.throws(() => validateTerms({ ...base, kind: 'purchase', creatorRole: 'seller', deposits: { creator: 100, counterparty: 0 } }), /buyer must deposit/);
  assert.throws(() => validateTerms({ ...base, expiresInHours: 0 }), /between/);
  assert.throws(() => validateTerms({ ...base, deposits: { creator: 1.5, counterparty: 0 } }), /cents/);
});
