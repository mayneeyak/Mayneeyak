// Pact Escrow front end. Plain JS, no build step. All text is inserted with
// textContent (never innerHTML) so user-entered names and terms can't inject code.

const app = document.getElementById('app');

// ---------- tiny DOM helper ----------
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs ?? {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked') el.checked = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : String(kid));
  return el;
}
const render = (...nodes) => { app.replaceChildren(...nodes); window.scrollTo(0, 0); };

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => t.classList.remove('show'), 2500);
}

const money = (cents, cur = 'USD') => new Intl.NumberFormat(undefined, { style: 'currency', currency: cur }).format(cents / 100);
const toCents = (s) => Math.round(parseFloat(String(s).replace(/[^0-9.]/g, '')) * 100) || 0;

// ---------- session storage (this tab only) ----------
const sess = {
  get: (id) => { try { return JSON.parse(sessionStorage.getItem(`pact:${id}`)); } catch { return null; } },
  set: (id, v) => { try { sessionStorage.setItem(`pact:${id}`, JSON.stringify({ ...sess.get(id), ...v })); } catch {} },
  clear: (id) => { try { sessionStorage.removeItem(`pact:${id}`); } catch {} },
};

async function api(path, { body, token, method } = {}) {
  const res = await fetch(`/api${path}`, {
    method: method ?? (body ? 'POST' : 'GET'),
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error(data.error ?? `Error ${res.status}`); e.status = res.status; throw e; }
  return data;
}

// Run an async action from a form, showing errors in `errEl` and disabling `btn`.
async function busy(btn, errEl, fn) {
  btn.disabled = true; errEl.textContent = '';
  try { await fn(); } catch (e) { errEl.textContent = e.message; } finally { btn.disabled = false; }
}

// ---------- router ----------
window.addEventListener('hashchange', route);
route();

function route() {
  const parts = location.hash.replace(/^#\/?/, '').split('/');
  if (parts[0] === 'new') return createPage();
  if (parts[0] === 'join' && parts[1] && parts[2]) return joinPage(parts[1], parts[2]);
  if (parts[0] === 'e' && parts[1]) return escrowPage(parts[1]);
  return homePage();
}

// ---------- home ----------
function homePage() {
  const idInput = h('input', { type: 'text', placeholder: 'Escrow ID or link', autocomplete: 'off' });
  const err = h('div', { class: 'error' });
  const open = () => {
    const v = idInput.value.trim();
    const m = v.match(/#\/(?:e|join)\/([\w-]+)/) ?? v.match(/^([\w-]{8,})$/);
    if (!m) { err.textContent = 'Paste the escrow ID or link you were given.'; return; }
    location.hash = v.includes('#/join/') ? v.slice(v.indexOf('#')) : `#/e/${m[1]}`;
  };
  render(
    h('section', { class: 'hero' },
      h('h1', {}, 'Hold money safely between two people'),
      h('p', { class: 'muted' }, 'Create a temporary, encrypted escrow account that only you and the other party can open. You set the rules for who gets paid when the purchase is received or the bet is won.'),
      h('div', { class: 'row' }, h('a', { class: 'btn', href: '#/new' }, 'Create an escrow'))),
    h('div', { class: 'card' },
      h('h2', {}, 'How it works'),
      h('ol', { class: 'steps' },
        h('li', {}, 'You create the escrow, pick a purchase or a bet, and set how the money is split for each outcome.'),
        h('li', {}, 'Send the private invite link. The other person reviews your rules and joins with their own passphrase. From then on the rules are locked.'),
        h('li', {}, 'Each side deposits what the rules require. The money is held until an outcome is confirmed.'),
        h('li', {}, 'When the buyer confirms the item arrived, or the loser concedes, or you both agree, the money is paid out by your rules. If the deadline passes first, your expiry rule applies.'),
      )),
    h('div', { class: 'card' },
      h('h2', {}, 'Open an existing escrow'),
      h('div', { class: 'copy' }, idInput, h('button', { onclick: open }, 'Open')),
      err),
  );
}

// ---------- create ----------
function createPage() {
  const s = {
    kind: 'purchase', creatorRole: 'buyer', title: '', description: '', price: '', stakeMe: '', stakeThem: '',
    hours: 168, outcomes: null, onExpiry: { type: 'refund' }, name: '', payout: '', pass: '', pass2: '',
  };
  s.outcomes = preset(s);

  function preset({ kind, creatorRole }) {
    if (kind === 'purchase') {
      const seller = creatorRole === 'seller' ? 'creator' : 'counterparty';
      return [
        { id: 'received', label: 'Item received: pay the seller', split: { type: 'percent', creator: seller === 'creator' ? 10000 : 0, counterparty: seller === 'creator' ? 0 : 10000 } },
        { id: 'not_received', label: 'Not received: refund the buyer', split: { type: 'refund' } },
      ];
    }
    return [
      { id: 'creator_wins', label: 'Creator wins', split: { type: 'percent', creator: 10000, counterparty: 0 } },
      { id: 'counterparty_wins', label: 'Challenger wins', split: { type: 'percent', creator: 0, counterparty: 10000 } },
      { id: 'draw', label: 'Draw: everyone gets their stake back', split: { type: 'refund' } },
    ];
  }

  const err = h('div', { class: 'error' });
  const form = h('div');

  function seg(options, current, onPick) {
    return h('div', { class: 'seg', role: 'group' }, options.map(([v, label]) =>
      h('button', { type: 'button', 'aria-pressed': String(current === v), onclick: () => onPick(v) }, label)));
  }

  function field(label, input, hint) {
    return h('div', {}, h('label', {}, label, hint ? h('span', { class: 'muted' }, ` ${hint}`) : null), input);
  }

  function bind(key, attrs = {}) {
    const el = h(attrs.tag ?? 'input', { type: 'text', ...attrs, tag: null, value: s[key], oninput: (e) => { s[key] = e.target.value; } });
    return el;
  }

  function splitEditor(split, onChange, them = 'Them') {
    const type = h('select', { onchange: (e) => { onChange(e.target.value === 'refund' ? { type: 'refund' } : { type: 'percent', creator: 5000, counterparty: 5000 }); draw(); } },
      h('option', { value: 'percent' }, 'Split the pot'),
      h('option', { value: 'refund' }, 'Refund each deposit'));
    type.value = split.type;
    if (split.type === 'refund') return h('div', { class: 'split' }, type, h('span', { class: 'who' }, 'Everyone gets back exactly what they put in'));
    const label = h('span', { class: 'who' });
    const show = (c) => { label.textContent = `You ${c / 100}% · ${them} ${(10000 - c) / 100}%`; };
    const range = h('input', { type: 'range', min: 0, max: 10000, step: 500, value: split.creator, 'aria-label': 'Your share',
      oninput: (e) => { const c = Number(e.target.value); onChange({ type: 'percent', creator: c, counterparty: 10000 - c }); show(c); } });
    show(split.creator);
    return h('div', { class: 'split' }, type, range, label);
  }

  function draw() {
    const isBuy = s.kind === 'purchase';
    const outcomes = s.outcomes.map((o, i) => h('div', { class: 'outcome' },
      h('div', { class: 'head' },
        h('input', { type: 'text', value: o.label, 'aria-label': 'Outcome name', oninput: (e) => { o.label = e.target.value; } }),
        s.outcomes.length > 2 ? h('button', { type: 'button', class: 'iconbtn', 'aria-label': 'Remove outcome', onclick: () => { s.outcomes.splice(i, 1); draw(); } }, 'Remove') : null),
      splitEditor(o.split, (sp) => { o.split = sp; })));

    form.replaceChildren(
      h('div', { class: 'card' },
        h('h2', {}, 'What is this escrow for?'),
        seg([['purchase', 'A purchase'], ['bet', 'A bet']], s.kind, (v) => { s.kind = v; s.outcomes = preset(s); draw(); }),
        isBuy ? h('div', {}, h('label', {}, 'I am the'), seg([['buyer', 'Buyer'], ['seller', 'Seller']], s.creatorRole, (v) => { s.creatorRole = v; s.outcomes = preset(s); draw(); })) : null,
        field('Title', bind('title', { maxlength: 120, placeholder: isBuy ? 'Used bike, blue, 54cm frame' : 'Lakers beat the Celtics on Friday' })),
        field('Terms', bind('description', { tag: 'textarea', maxlength: 2000, placeholder: isBuy ? 'Condition, delivery method, what counts as received…' : 'Exactly what decides the bet…' }), '(both of you will see this)'),
        isBuy
          ? field('Price', bind('price', { inputmode: 'decimal', placeholder: '250.00' }), '(USD, deposited by the buyer)')
          : h('div', { class: 'grid2' },
              field('My stake', bind('stakeMe', { inputmode: 'decimal', placeholder: '50.00' }), '(USD)'),
              field('Their stake', bind('stakeThem', { inputmode: 'decimal', placeholder: '50.00' }), '(USD)')),
      ),
      h('div', { class: 'card' },
        h('h2', {}, 'Payout rules'),
        h('p', { class: 'muted small' }, 'For each outcome, choose how the money is split. Once the other party joins, these rules are locked and can\'t be changed by anyone.'),
        outcomes,
        s.outcomes.length < 8 ? h('button', { type: 'button', class: 'secondary', onclick: () => {
          s.outcomes.push({ id: `custom_${Date.now().toString(36)}`, label: 'New outcome', split: { type: 'percent', creator: 5000, counterparty: 5000 } }); draw();
        } }, 'Add an outcome') : null,
        h('label', {}, 'If no outcome is confirmed before the deadline'),
        splitEditor(s.onExpiry, (sp) => { s.onExpiry = sp; }),
        field('Deadline', (() => {
          const sel = h('select', { onchange: (e) => { s.hours = Number(e.target.value); } },
            [[24, '1 day'], [72, '3 days'], [168, '1 week'], [336, '2 weeks'], [720, '30 days'], [2160, '90 days']].map(([v, l]) => h('option', { value: v }, l)));
          sel.value = String(s.hours); return sel;
        })(), '(the account is temporary and closes after this)'),
      ),
      h('div', { class: 'card' },
        h('h2', {}, 'You'),
        h('div', { class: 'grid2' },
          field('Your name', bind('name', { maxlength: 60, autocomplete: 'name' })),
          field('Where to pay you', bind('payout', { maxlength: 200, placeholder: 'Bank, PayPal or Venmo handle' }))),
        h('div', { class: 'grid2' },
          field('Passphrase', bind('pass', { type: 'password', autocomplete: 'new-password' }), '(10+ characters)'),
          field('Repeat passphrase', bind('pass2', { type: 'password', autocomplete: 'new-password' }))),
        h('p', { class: 'muted small' }, 'Your passphrase is the only way to open this escrow. It is never stored, and there is no reset, so keep it safe.'),
        h('div', { class: 'row' }, submit), err),
    );
  }

  const submit = h('button', { onclick: () => busy(submit, err, async () => {
    if (s.pass !== s.pass2) throw new Error('The passphrases don\'t match');
    const buyerIsMe = s.creatorRole === 'buyer';
    const deposits = s.kind === 'purchase'
      ? { creator: buyerIsMe ? toCents(s.price) : 0, counterparty: buyerIsMe ? 0 : toCents(s.price) }
      : { creator: toCents(s.stakeMe), counterparty: toCents(s.stakeThem) };
    const out = await api('/escrows', { body: {
      kind: s.kind, creatorRole: s.creatorRole, title: s.title, description: s.description, currency: 'USD',
      deposits, outcomes: s.outcomes, onExpiry: s.onExpiry, expiresInHours: s.hours,
      name: s.name, payout: s.payout, passphrase: s.pass,
    } });
    sess.set(out.id, { token: out.token, invite: out.inviteCode });
    location.hash = `#/e/${out.id}`;
  }) }, 'Create escrow');

  render(h('h1', {}, 'New escrow'), h('p', { class: 'muted' }, 'You make the rules. The other party agrees to them when they join.'), form);
  draw();
}

// ---------- shared: show terms ----------
function partyName(v, role) { return v.parties[role]?.name ?? (role === v.you ? 'You' : 'The other party'); }
function label(v, role) { return role === v.you ? `You (${partyName(v, role)})` : partyName(v, role); }

function termsCard(v) {
  return h('div', { class: 'card' },
    h('h2', {}, 'Rules set by the creator'),
    v.outcomes.map((o) => h('div', { class: `ocard ${v.reports?.[v.you] === o.id ? 'picked' : ''}` },
      h('strong', {}, o.label),
      payLines(v, o.payouts, o.split))),
    h('div', { class: 'ocard' }, h('strong', {}, 'If the deadline passes'), payLines(v, v.onExpiry.payouts, v.onExpiry.split)),
    v.feeBps ? h('p', { class: 'muted small' }, `A ${v.feeBps / 100}% service fee applies to split payouts (not refunds).`) : null);
}

function payLines(v, payouts, split) {
  return h('div', {},
    split.type === 'refund' ? h('div', { class: 'muted small' }, 'Each deposit is refunded') : null,
    ['creator', 'counterparty'].map((r) => h('div', { class: 'payline' }, h('span', {}, label(v, r)), h('strong', {}, money(payouts[r], v.currency)))));
}

// ---------- join ----------
async function joinPage(id, code) {
  render(h('p', { class: 'muted' }, 'Opening invite…'));
  let v;
  try { v = await api(`/escrows/${id}/preview`, { body: { inviteCode: code } }); }
  catch (e) {
    return render(h('h1', {}, 'Invite unavailable'), h('p', {}, e.message),
      h('a', { class: 'btn secondary', href: `#/e/${id}` }, 'Already joined? Unlock it'));
  }
  const f = { name: '', payout: '', pass: '', pass2: '', ok: false };
  const err = h('div', { class: 'error' });
  const inp = (k, attrs) => h('input', { type: 'text', ...attrs, oninput: (e) => { f[k] = e.target.value; } });
  const btn = h('button', { onclick: () => busy(btn, err, async () => {
    if (f.pass !== f.pass2) throw new Error('The passphrases don\'t match');
    const out = await api(`/escrows/${id}/join`, { body: { inviteCode: code, name: f.name, payout: f.payout, passphrase: f.pass, acceptTerms: f.ok } });
    sess.set(id, { token: out.token });
    history.replaceState(null, '', `#/e/${id}`); // drop the invite code from the address bar
    route();
  }) }, 'Accept rules and join');
  const theirSide = v.parties.counterparty?.side ?? (v.kind === 'purchase' ? (v.parties.creator.side === 'buyer' ? 'seller' : 'buyer') : 'bettor');

  render(
    h('h1', {}, v.title),
    h('p', { class: 'muted' }, `${v.parties.creator.name} invited you to a ${v.kind === 'purchase' ? 'purchase' : 'bet'} escrow as the ${theirSide}.`),
    v.description ? h('div', { class: 'card' }, h('h2', {}, 'Terms'), h('p', {}, v.description)) : null,
    h('div', { class: 'card' }, h('h2', {}, 'Deposits'),
      ['creator', 'counterparty'].map((r) => h('div', { class: 'payline' }, h('span', {}, r === 'creator' ? v.parties.creator.name : 'You'), h('strong', {}, money(v.deposits[r].required, v.currency)))),
      h('p', { class: 'muted small' }, `Closes ${new Date(v.expiresAt).toLocaleString()}.`)),
    termsCard(v),
    h('div', { class: 'card' },
      h('h2', {}, 'Join'),
      h('div', { class: 'grid2' },
        h('div', {}, h('label', {}, 'Your name'), inp('name', { maxlength: 60, autocomplete: 'name' })),
        h('div', {}, h('label', {}, 'Where to pay you'), inp('payout', { maxlength: 200, placeholder: 'Bank, PayPal or Venmo handle' }))),
      h('div', { class: 'grid2' },
        h('div', {}, h('label', {}, 'Choose a passphrase ', h('span', { class: 'muted' }, '(10+ characters)')), inp('pass', { type: 'password', autocomplete: 'new-password' })),
        h('div', {}, h('label', {}, 'Repeat passphrase'), inp('pass2', { type: 'password', autocomplete: 'new-password' }))),
      h('p', { class: 'muted small' }, 'Use your own passphrase, not the creator\'s. It is never stored and can\'t be reset.'),
      h('label', { class: 'check' }, h('input', { type: 'checkbox', onchange: (e) => { f.ok = e.target.checked; } }),
        h('span', {}, 'I accept these rules. I understand they are locked once I join and money will be paid out exactly as shown.')),
      h('div', { class: 'row' }, btn), err),
  );
}

// ---------- escrow dashboard ----------
async function escrowPage(id) {
  const saved = sess.get(id);
  if (!saved?.token) return unlockPage(id);
  render(h('p', { class: 'muted' }, 'Decrypting…'));
  try {
    dashboard(id, await api('/escrow', { token: saved.token }));
  } catch (e) {
    if (e.status === 401) { sess.set(id, { token: null }); return unlockPage(id); }
    render(h('h1', {}, 'Couldn\'t open escrow'), h('p', {}, e.message));
  }
}

function unlockPage(id) {
  const pass = h('input', { type: 'password', autocomplete: 'current-password', 'aria-label': 'Passphrase' });
  const err = h('div', { class: 'error' });
  const btn = h('button', { onclick: () => busy(btn, err, async () => {
    const out = await api(`/escrows/${id}/unlock`, { body: { passphrase: pass.value } });
    sess.set(id, { token: out.token });
    route();
  }) }, 'Unlock');
  pass.addEventListener('keydown', (e) => { if (e.key === 'Enter') btn.click(); });
  render(h('div', { class: 'card' },
    h('h1', {}, 'Unlock escrow'),
    h('p', { class: 'muted' }, 'This account is encrypted. Enter the passphrase you chose when you created or joined it.'),
    h('div', { class: 'copy' }, pass, btn), err));
  pass.focus();
}

const STATUS = {
  awaiting_counterparty: ['Waiting for the other party', 'warn'],
  awaiting_funding: ['Waiting for deposits', 'warn'],
  active: ['Funded and held', 'accent'],
  disputed: ['Disputed', 'bad'],
  settled: ['Settled', 'good'],
  expired: ['Expired', ''],
  cancelled: ['Cancelled', ''],
};

function dashboard(id, v) {
  const token = sess.get(id).token;
  const err = h('div', { class: 'error' });
  const act = (btn, path, body) => busy(btn, err, async () => { dashboard(id, await api(path, { token, body: body ?? {} })); toast('Done'); });
  const [statusText, tone] = STATUS[v.status];
  const open = !['settled', 'expired', 'cancelled'].includes(v.status);
  const other = v.you === 'creator' ? 'counterparty' : 'creator';
  const invite = sess.get(id)?.invite;

  const blocks = [];
  blocks.push(h('div', { class: 'row' }, h('span', { class: `pill ${tone}` }, statusText),
    h('span', { class: 'muted small' }, open ? `Closes ${new Date(v.expiresAt).toLocaleString()}` : v.purgeAt ? `Deleted for good after ${new Date(v.purgeAt).toLocaleDateString()}` : '')));
  blocks.push(h('h1', {}, v.title));
  if (v.description) blocks.push(h('p', { class: 'muted' }, v.description));

  if (v.status === 'awaiting_counterparty' && v.you === 'creator') {
    const link = invite ? `${location.origin}/#/join/${id}/${invite}` : null;
    const linkInput = link ? h('input', { type: 'text', readonly: true, value: link }) : null;
    blocks.push(h('div', { class: 'card' },
      h('h2', {}, 'Invite the other party'),
      link
        ? [h('p', { class: 'muted small' }, 'Send this private link only to the other person. It works once. Anyone with it can view the terms and join, so share it directly.'),
           h('div', { class: 'copy' }, linkInput, h('button', { onclick: async () => { try { await navigator.clipboard.writeText(link); toast('Link copied'); } catch { linkInput.select(); } } }, 'Copy'))]
        : h('p', { class: 'muted small' }, 'The invite link is only shown in the tab where you created the escrow. If you lost it, cancel this escrow and create a new one.'),
      h('p', { class: 'muted small' }, `Escrow ID: ${id}. Bookmark this page to come back later.`)));
  }

  // Money
  const dep = ['creator', 'counterparty'].map((r) => h('div', { class: 'party' },
    h('div', {}, h('strong', {}, label(v, r)), h('div', { class: 'muted small' }, v.parties[r]?.side ?? 'not joined yet')),
    h('div', {}, v.deposits[r].required === 0 ? h('span', { class: 'muted small' }, 'No deposit') :
      v.deposits[r].paid ? h('span', { class: 'pill good' }, `Paid ${money(v.deposits[r].required, v.currency)}`) :
      h('span', { class: 'pill warn' }, `Owes ${money(v.deposits[r].required, v.currency)}`))));
  const myDep = v.deposits[v.you];
  const depBtn = h('button', { onclick: () => act(depBtn, '/escrow/deposit') }, `Deposit ${money(myDep.required, v.currency)}`);
  blocks.push(h('div', { class: 'card' },
    h('h2', {}, 'Held in escrow'),
    h('div', { class: 'big' }, money(v.pot.held, v.currency)),
    h('p', { class: 'muted small' }, `of ${money(v.pot.whenFunded, v.currency)} when fully funded`),
    dep,
    v.status === 'awaiting_funding' && myDep.required && !myDep.paid
      ? h('div', {}, h('div', { class: 'row' }, depBtn), v.provider === 'sandbox' ? h('p', { class: 'muted small' }, 'Sandbox mode: this simulates the payment.') : null)
      : null));

  // Confirm outcome
  if (v.status === 'active' || v.status === 'disputed') {
    const mine = v.reports[v.you], theirs = v.reports[other];
    const name = (oid) => v.outcomes.find((o) => o.id === oid)?.label;
    blocks.push(h('div', { class: 'card' },
      h('h2', {}, v.kind === 'purchase' ? 'Confirm what happened' : 'Confirm the result'),
      v.status === 'disputed' ? h('div', { class: 'notice warn' }, `You chose "${name(mine)}" but ${partyName(v, other)} chose "${name(theirs)}". The money stays locked until you agree or the deadline passes.`) : null,
      !mine && theirs ? h('div', { class: 'notice' }, `${partyName(v, other)} confirmed "${name(theirs)}". Confirm the same to pay out.`) : null,
      v.outcomes.map((o) => {
        const b = h('button', { class: mine === o.id ? 'secondary' : '', disabled: mine === o.id, onclick: () => {
          if (confirm(`Confirm "${o.label}"?${o.settlesIfYouConfirm || theirs === o.id ? '\n\nThis pays out immediately and cannot be undone.' : ''}`)) act(b, '/escrow/report', { outcomeId: o.id });
        } }, mine === o.id ? 'Your answer' : 'Confirm');
        return h('div', { class: `ocard ${mine === o.id ? 'picked' : ''}` },
          h('div', { class: 'row', style: null }, h('strong', { class: '' }, o.label)),
          payLines(v, o.payouts, o.split),
          h('div', { class: 'row' }, b,
            h('span', { class: 'muted small' }, o.settlesIfYouConfirm ? 'Pays out right away, since it\'s the least favorable result for you' : theirs === o.id ? 'Matches the other party: pays out' : 'Needs the other party to agree')));
      })));
  }

  if (v.settlement) {
    const s = v.settlement;
    blocks.push(h('div', { class: 'card' },
      h('h2', {}, 'Payout'),
      h('p', {}, s.reason),
      s.transfers.length ? s.transfers.map((t) => h('div', { class: 'payline' }, h('span', {}, `${t.kind === 'refund' ? 'Refunded to' : 'Paid to'} ${label(v, t.role)}`), h('strong', {}, money(t.amount, v.currency)))) : h('p', { class: 'muted' }, 'No money was held.'),
      s.fee ? h('div', { class: 'payline muted' }, h('span', {}, 'Service fee'), h('span', {}, money(s.fee, v.currency))) : null));
  }

  blocks.push(termsCard(v));
  blocks.push(h('div', { class: 'card' }, h('h2', {}, 'History'), h('ul', { class: 'events' }, v.events.slice().reverse().map((e) =>
    h('li', {}, h('div', {}, e.text), h('div', { class: 'muted small' }, new Date(e.at).toLocaleString()))))));

  const lockBtn = h('button', { class: 'secondary', onclick: async () => { try { await api('/escrow/lock', { token, body: {} }); } catch {} sess.clear(id); route(); } }, 'Lock');
  const refresh = h('button', { class: 'secondary', onclick: () => escrowPage(id) }, 'Refresh');
  const cancelBtn = h('button', { class: 'danger', onclick: () => { if (confirm('Cancel this escrow? Any deposits are refunded.')) act(cancelBtn, '/escrow/cancel'); } }, 'Cancel escrow');
  blocks.push(h('div', { class: 'row' }, refresh, lockBtn,
    v.status === 'awaiting_counterparty' || v.status === 'awaiting_funding' ? cancelBtn : null), err);

  render(...blocks);
}
