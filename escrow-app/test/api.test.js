import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createApp } from '../server.js';
import { SandboxProvider } from '../lib/payments.js';
import { presetRules } from '../lib/rules.js';

async function start(opts = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pact-'));
  const dataFile = path.join(dir, 'escrows.json');
  const provider = new SandboxProvider();
  const clock = { t: Date.now() };
  const { server } = createApp({ dataFile, provider, now: () => clock.t, ...opts });
  await new Promise((r) => server.listen(0, r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const call = async (p, { body, token, method } = {}) => {
    const res = await fetch(base + '/api' + p, {
      method: method ?? (body ? 'POST' : 'GET'),
      headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: res.status, data: await res.json() };
  };
  return { server, call, dataFile, provider, clock, close: () => new Promise((r) => server.close(r)) };
}

const purchase = {
  kind: 'purchase', creatorRole: 'buyer', title: 'Road bike', description: 'Blue, 54cm. Shipped tracked.',
  deposits: { creator: 25000, counterparty: 0 }, ...presetRules('purchase', 'buyer'), expiresInHours: 48,
  name: 'Alex', payout: 'paypal:alex@example.com', passphrase: 'correct horse battery',
};

test('purchase: create, join, fund, buyer confirms receipt, seller is paid', async (t) => {
  const app = await start();
  t.after(app.close);

  const c = await app.call('/escrows', { body: purchase });
  assert.equal(c.status, 200, JSON.stringify(c.data));
  const { id, inviteCode, token: buyer } = c.data;

  // Stored file contains no plaintext terms, names or payout details.
  const raw = fs.readFileSync(app.dataFile, 'utf8');
  for (const secret of ['Road bike', 'Alex', 'paypal', 'Blue', inviteCode]) assert.ok(!raw.includes(secret), `leaked ${secret}`);

  // Bad invite code is rejected; good one previews the terms without the creator's payout details.
  assert.equal((await app.call(`/escrows/${id}/preview`, { body: { inviteCode: 'nope' } })).status, 403);
  const pv = await app.call(`/escrows/${id}/preview`, { body: { inviteCode } });
  assert.equal(pv.data.title, 'Road bike');
  assert.equal(pv.data.parties.creator.payout, undefined);

  // Must accept terms, and can't reuse the creator's passphrase.
  const joinBody = { inviteCode, name: 'Sam', payout: 'venmo:@sam', passphrase: 'sams own passphrase', acceptTerms: true };
  assert.equal((await app.call(`/escrows/${id}/join`, { body: { ...joinBody, acceptTerms: false } })).status, 400);
  assert.equal((await app.call(`/escrows/${id}/join`, { body: { ...joinBody, passphrase: purchase.passphrase } })).status, 400);
  const j = await app.call(`/escrows/${id}/join`, { body: joinBody });
  assert.equal(j.status, 200, JSON.stringify(j.data));
  const seller = j.data.token;

  // Invite is single-use.
  assert.equal((await app.call(`/escrows/${id}/join`, { body: joinBody })).status, 403);

  // Seller has nothing to deposit; buyer funds it.
  assert.equal((await app.call('/escrow/deposit', { token: seller, body: {} })).status, 409);
  const d = await app.call('/escrow/deposit', { token: buyer, body: {} });
  assert.equal(d.data.status, 'active');
  assert.equal(d.data.pot.held, 25000);

  // Seller claiming "received" isn't enough on its own.
  const s1 = await app.call('/escrow/report', { token: seller, body: { outcomeId: 'received' } });
  assert.equal(s1.data.status, 'active');

  // Buyer confirms receipt: settles, seller is paid to their payout address.
  const s2 = await app.call('/escrow/report', { token: buyer, body: { outcomeId: 'received' } });
  assert.equal(s2.data.status, 'settled');
  assert.deepEqual(s2.data.settlement.transfers.map((x) => [x.role, x.amount, x.kind]), [['counterparty', 25000, 'payout']]);
  const pay = app.provider.log.find((x) => x.type === 'pay');
  assert.equal(pay.destination, 'venmo:@sam');

  // No more actions after settling.
  assert.equal((await app.call('/escrow/report', { token: buyer, body: { outcomeId: 'not_received' } })).status, 409);
});

test('unlock with each passphrase, wrong passphrase locks out', async (t) => {
  const app = await start();
  t.after(app.close);
  const { id, inviteCode } = (await app.call('/escrows', { body: purchase })).data;
  await app.call(`/escrows/${id}/join`, { body: { inviteCode, name: 'Sam', payout: 'venmo:@sam', passphrase: 'sams own passphrase', acceptTerms: true } });

  assert.equal((await app.call(`/escrows/${id}/unlock`, { body: { passphrase: purchase.passphrase } })).data.role, 'creator');
  assert.equal((await app.call(`/escrows/${id}/unlock`, { body: { passphrase: 'sams own passphrase' } })).data.role, 'counterparty');
  assert.equal((await app.call('/escrow', { token: 'forged' })).status, 401);

  for (let i = 0; i < 5; i++) assert.equal((await app.call(`/escrows/${id}/unlock`, { body: { passphrase: 'guess guess ' + i } })).status, 403);
  assert.equal((await app.call(`/escrows/${id}/unlock`, { body: { passphrase: purchase.passphrase } })).status, 429);
});

test('bet: disagreement disputes, then expiry applies the creator\'s rule', async (t) => {
  const app = await start({ feeBps: 0 });
  t.after(app.close);
  const rules = presetRules('bet');
  rules.onExpiry = { type: 'percent', creator: 5000, counterparty: 5000 };
  const c = (await app.call('/escrows', { body: {
    kind: 'bet', title: 'Rain on Saturday', deposits: { creator: 2000, counterparty: 3000 }, ...rules, expiresInHours: 24,
    name: 'Alex', payout: 'acct-1', passphrase: 'alex passphrase 1',
  } })).data;
  const j = (await app.call(`/escrows/${c.id}/join`, { body: { inviteCode: c.inviteCode, name: 'Sam', payout: 'acct-2', passphrase: 'sam passphrase 22', acceptTerms: true } })).data;
  await app.call('/escrow/deposit', { token: c.token, body: {} });
  assert.equal((await app.call('/escrow/deposit', { token: j.token, body: {} })).data.status, 'active');

  await app.call('/escrow/report', { token: c.token, body: { outcomeId: 'creator_wins' } });
  const disputed = (await app.call('/escrow/report', { token: j.token, body: { outcomeId: 'counterparty_wins' } })).data;
  assert.equal(disputed.status, 'disputed');

  app.clock.t += 25 * 3600 * 1000;
  assert.equal((await app.call('/escrow', { token: j.token })).status, 401); // idle session expired too
  const again = (await app.call(`/escrows/${c.id}/unlock`, { body: { passphrase: 'sam passphrase 22' } })).data;
  const v = (await app.call('/escrow', { token: again.token })).data;
  assert.equal(v.status, 'expired');
  assert.deepEqual(v.settlement.transfers.map((x) => x.amount), [2500, 2500]);
});

test('bet: loser conceding pays the winner immediately; cancel before funding refunds', async (t) => {
  const app = await start({ feeBps: 100 });
  t.after(app.close);
  const body = { kind: 'bet', title: 'Chess match', deposits: { creator: 1000, counterparty: 1000 }, ...presetRules('bet'), expiresInHours: 24, name: 'Alex', payout: 'acct-1', passphrase: 'alex passphrase 1' };

  const c = (await app.call('/escrows', { body })).data;
  const j = (await app.call(`/escrows/${c.id}/join`, { body: { inviteCode: c.inviteCode, name: 'Sam', payout: 'acct-2', passphrase: 'sam passphrase 22', acceptTerms: true } })).data;
  await app.call('/escrow/deposit', { token: c.token, body: {} });
  await app.call('/escrow/deposit', { token: j.token, body: {} });
  const v = (await app.call('/escrow/report', { token: j.token, body: { outcomeId: 'creator_wins' } })).data;
  assert.equal(v.status, 'settled');
  assert.equal(v.settlement.fee, 20);
  assert.deepEqual(v.settlement.transfers.map((x) => [x.role, x.amount]), [['creator', 1980]]);

  const c2 = (await app.call('/escrows', { body })).data;
  const j2 = (await app.call(`/escrows/${c2.id}/join`, { body: { inviteCode: c2.inviteCode, name: 'Sam', payout: 'acct-2', passphrase: 'sam passphrase 22', acceptTerms: true } })).data;
  await app.call('/escrow/deposit', { token: c2.token, body: {} });
  const x = (await app.call('/escrow/cancel', { token: j2.token, body: {} })).data;
  assert.equal(x.status, 'cancelled');
  assert.deepEqual(x.settlement.transfers.map((t) => [t.role, t.amount, t.kind]), [['creator', 1000, 'refund']]);
});
