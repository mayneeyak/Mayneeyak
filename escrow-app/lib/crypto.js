// Encryption for escrow accounts.
//
// Each escrow has one random 256-bit data key. All of the escrow's contents
// (names, terms, payout details, deposits, reports, history) are encrypted with
// it using AES-256-GCM. The data key itself is never stored in the clear: it is
// "wrapped" (encrypted) once per party with a key derived from that party's
// passphrase via scrypt. A third wrap, under the one-time invite code, exists
// only until the counterparty joins and is then deleted.
//
// So the stored file holds only ciphertext; opening an escrow requires the
// passphrase of one of its two parties.

import crypto from 'node:crypto';

const SCRYPT = { N: 2 ** 15, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };

export function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString('base64url');
}

export function newDataKey() {
  return crypto.randomBytes(32);
}

function deriveKey(secret, salt) {
  return new Promise((resolve, reject) => {
    crypto.scrypt(secret.normalize('NFKC'), salt, 32, SCRYPT, (err, key) =>
      err ? reject(err) : resolve(key));
  });
}

function seal(key, plaintext, aad) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(Buffer.from(aad));
  const ct = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  return { iv: iv.toString('base64'), tag: cipher.getAuthTag().toString('base64'), ct: ct.toString('base64') };
}

function open(key, box, aad) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(box.iv, 'base64'));
  decipher.setAAD(Buffer.from(aad));
  decipher.setAuthTag(Buffer.from(box.tag, 'base64'));
  return Buffer.concat([decipher.update(Buffer.from(box.ct, 'base64')), decipher.final()]);
}

/** Wrap the data key under a secret (passphrase or invite code). */
export async function wrapKey(dataKey, secret, aad) {
  const salt = crypto.randomBytes(16);
  const kek = await deriveKey(secret, salt);
  return { salt: salt.toString('base64'), ...seal(kek, dataKey, `wrap:${aad}`) };
}

/** Returns the data key, or null if the secret is wrong. */
export async function unwrapKey(wrap, secret, aad) {
  if (!wrap) return null;
  const kek = await deriveKey(secret, Buffer.from(wrap.salt, 'base64'));
  try {
    return open(kek, wrap, `wrap:${aad}`);
  } catch {
    return null;
  }
}

export function encryptState(dataKey, state, aad) {
  return seal(dataKey, Buffer.from(JSON.stringify(state)), `state:${aad}`);
}

export function decryptState(dataKey, box, aad) {
  return JSON.parse(open(dataKey, box, `state:${aad}`).toString('utf8'));
}

export function sha256(s) {
  return crypto.createHash('sha256').update(s).digest('hex');
}

export function safeEqual(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}
