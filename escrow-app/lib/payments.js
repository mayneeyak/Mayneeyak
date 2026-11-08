// Payment provider interface. The app ships with a sandbox provider that only
// records simulated transfers, so you can try the full flow without real money.
//
// To go live, implement the same three methods against a licensed payment
// processor that supports holding funds for marketplaces (for example Stripe
// Connect with separate charges and transfers, or Adyen for Platforms):
//   collect({ escrowId, role, amount, currency })            -> { ref }
//   payout({ escrowId, role, amount, currency, destination }) -> { ref }
//   refund({ escrowId, role, amount, currency, depositRef })  -> { ref }
// Moving other people's money usually requires the processor (or you) to hold
// money-transmission licences; using such a processor is what makes this legal.

import { randomToken } from './crypto.js';

export class SandboxProvider {
  constructor() { this.name = 'sandbox'; this.log = []; }
  #record(type, data) {
    const ref = `sbx_${type}_${randomToken(9)}`;
    this.log.push({ ref, type, ...data, at: new Date().toISOString() });
    return { ref };
  }
  async collect(d) { return this.#record('dep', d); }
  async payout(d) { return this.#record('pay', d); }
  async refund(d) { return this.#record('ref', d); }
}
