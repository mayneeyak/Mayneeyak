// Tiny JSON-file store. Records hold only ciphertext plus the minimum metadata
// the server needs (status and timestamps). Writes are atomic (temp + rename).

import fs from 'node:fs';
import path from 'node:path';

export class Store {
  constructor(file) {
    this.file = file;
    this.records = new Map();
    this.locks = new Map();
    if (file && fs.existsSync(file)) {
      for (const r of JSON.parse(fs.readFileSync(file, 'utf8'))) this.records.set(r.id, r);
    }
  }

  get(id) { return this.records.get(id) ?? null; }
  all() { return [...this.records.values()]; }

  put(record) {
    this.records.set(record.id, record);
    this.flush();
  }

  delete(id) {
    this.records.delete(id);
    this.flush();
  }

  flush() {
    if (!this.file) return;
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    const tmp = `${this.file}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this.all()), { mode: 0o600 });
    fs.renameSync(tmp, this.file);
  }

  /** Run fn with exclusive access to one escrow, so concurrent requests can't interleave. */
  async withLock(id, fn) {
    const prev = this.locks.get(id) ?? Promise.resolve();
    let release;
    const next = new Promise((r) => (release = r));
    const chained = prev.then(() => next);
    this.locks.set(id, chained);
    await prev;
    try {
      return await fn();
    } finally {
      release();
      if (this.locks.get(id) === chained) this.locks.delete(id);
    }
  }
}
