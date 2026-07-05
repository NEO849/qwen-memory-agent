// Regress-Guard UI — vanilla ES module, no build step.
// Deck = 3D Rolodex arc: persistent node pool + one rAF lerp loop (idle = 0 CPU).
// Design law: one field -> one channel. lifecycle=card body · confidence=meter · severity=spine.
const $ = (s) => document.querySelector(s);
const api = (p, o) => fetch(p, o).then(r => r.ok ? r.json() : Promise.reject(r));

const state = {
  lessons: [], byId: new Map(), etag: -1, filter: 'all', knownIds: new Set(),
  lastRendered: -2, lastFilter: null, agentStatus: 'idle',
  activeF: 0, targetF: 0, dragging: false, flipLock: false, raf: null, booted: false, inspecting: false,
};
const pool = new Map();                       // lesson id -> card node (built once)
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

// arc geometry constants
const THETA = 30, LIFT = 92, DEPTH = 178, ROLL = 0.30, CAP = 3.4, D2R = Math.PI / 180;
const CARD_H = 168;
let deckH = 400;   // measured from .deck-wrap; keeps the fan vertically centered
function measureDeck() { const dw = document.querySelector('.deck-wrap'); if (dw) deckH = dw.clientHeight || deckH; }

// ---------- Beta PDF sparkline (built once per card, never on scroll) ----------
function betaSparkline(alpha, beta, w = 140, h = 64) {
  const a = Math.max(alpha, 0.001), b = Math.max(beta, 0.001);
  const N = 48, xs = [], ys = []; let ymax = 1e-9;
  for (let i = 0; i <= N; i++) {
    const x = (i + 0.5) / (N + 1);
    const v = Math.exp((a - 1) * Math.log(x) + (b - 1) * Math.log(1 - x));
    xs.push(x); ys.push(v); if (v > ymax) ymax = v;
  }
  const pts = xs.map((x, i) => `${(x * w).toFixed(1)},${(h - (ys[i] / ymax) * (h - 6) - 3).toFixed(1)}`);
  const mean = a / (a + b), col = hueFor(mean);
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <polyline points="${pts.join(' ')}" fill="none" stroke="${col}" stroke-width="2"/>
    <line x1="${(mean*w).toFixed(1)}" y1="2" x2="${(mean*w).toFixed(1)}" y2="${h}" stroke="${col}" stroke-dasharray="2 3" stroke-width="1" opacity=".55"/>
    <text x="${(mean*w).toFixed(1)}" y="${h-1}" fill="${col}" font-size="9" font-family="monospace" text-anchor="middle">${mean.toFixed(2)}</text>
  </svg>`;
}
function hueFor(conf) { return `hsl(${Math.round(conf * 120)} 60% 68%)`; }
const SRC_COLOR = { human: '#B9A6E8', 'human-distill': '#B9A6E8', 'agent-distill': '#7FB8D8', import: '#93A0B5' };
function rel(ts) { if (!ts) return ''; const d = (Date.now() - Date.parse(ts)) / 1000;
  if (d < 60) return 'just now'; if (d < 3600) return `${Math.floor(d/60)}m ago`;
  if (d < 86400) return `${Math.floor(d/3600)}h ago`; return `${Math.floor(d/86400)}d ago`; }
function ageMs(l) { return Date.now() - Date.parse(l.updated_at || l.created_at || 0); }
function escapeHtml(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// ---------- card DOM (front + back inside a .flipper) ----------
function faceHTML(l) {
  const conf = l.confidence ?? 0, src = SRC_COLOR[l.source] || '#93A0B5';
  return `
    <div class="face front">
      <div class="spine sev-${l.severity}"></div>
      <span class="pin">📌</span><span class="stamp">OBSOLETE</span>
      <div class="kicker">
        <span class="src" style="background:${src};box-shadow:0 0 8px ${src}77, 0 0 0 3px rgba(255,255,255,.05)" title="source: ${l.source}"></span>
        <span class="when">WHEN ${escapeHtml((l.trigger || 'general').replace(/^when\s+/i, ''))}</span>
      </div>
      <div class="lesson">${escapeHtml(l.lesson)}</div>
      <div class="foot">
        <span class="chip">${escapeHtml(l.scope || 'general')}</span>
        <span class="conf">${conf.toFixed(2)}<span class="bar"><i style="width:${Math.round(conf*100)}%;background:${hueFor(conf)}"></i></span></span>
      </div>
    </div>
    <div class="face back">
      <div class="spine sev-${l.severity}"></div>
      <div class="btop">
        <div class="bconf" style="color:${hueFor(conf)}">${Math.round(conf * 100)}<span>%</span></div>
        <div class="blbl">confidence<em>${(l.real_pass + l.real_fail) > 0 ? 'earned from real test runs, not opinion' : 'starts at a prior — moves on real test outcomes'}</em></div>
        <div class="bspark">${betaSparkline(l.alpha, l.beta, 96, 46)}</div>
      </div>
      <div class="brows">
        <div><span>test outcomes</span><b><i class="g">${l.real_pass || 0} ✓ pass</i> · <i class="r">${l.real_fail || 0} ✗ fail</i></b></div>
        <div><span>severity</span><b><i class="sdot sev-${l.severity}"></i> ${l.severity}</b></div>
        <div><span>source</span><b>${l.source} · learned ${rel(l.created_at)}</b></div>
      </div>
    </div>`;
}
function cardEl(l) {
  const el = document.createElement('div'); el.dataset.id = l.id;
  el.setAttribute('aria-label', `lesson: ${l.lesson}`);
  el.innerHTML = `<div class="flipper">${faceHTML(l)}</div>`;
  return el;
}
function updateFaces(nd, l) { nd.querySelector('.flipper').innerHTML = faceHTML(l);
  nd.setAttribute('aria-label', `lesson: ${l.lesson}`); }

function lifecycleClass(l, agingThreshold) {
  let c = '';
  if (l.status === 'obsolete') c = ' obsolete';
  else if (!state.knownIds.has(l.id) || ageMs(l) < 120000) c = ' life-new';
  else if (agingThreshold != null && Date.parse(l.updated_at || l.created_at) <= agingThreshold) c = ' life-age';
  if (l.pinned) c += ' pinned';
  return c;
}

// ---------- build deck DOM (only on data change) ----------
function buildDeck() {
  const deck = $('#deck'), n = state.lessons.length;
  if (!n) {
    pool.forEach(nd => nd.remove()); pool.clear();
    deck.innerHTML = '<div class="empty">No lessons yet — switch to Teach below, or run the agent.</div>';
    renderTrack(0, 0); return;
  }
  const emptyEl = deck.querySelector('.empty'); if (emptyEl) emptyEl.remove();
  const live = new Set(state.lessons.map(l => l.id));
  for (const [id, nd] of pool) if (!live.has(id)) { nd.remove(); pool.delete(id); }
  const times = state.lessons.map(x => Date.parse(x.updated_at || x.created_at)).sort((a, b) => a - b);
  const agingThreshold = times.length >= 4 ? times[Math.floor(times.length * 0.25)] : null;
  state.lessons.forEach(l => {
    let nd = pool.get(l.id);
    if (!nd) { nd = cardEl(l); deck.appendChild(nd); pool.set(l.id, nd); }
    else if (nd.dataset.rev !== String(l.rev)) updateFaces(nd, l);
    const wasFlipped = nd.classList.contains('flipped');
    nd.className = 'card' + lifecycleClass(l, agingThreshold) + (wasFlipped ? ' flipped' : '');
    nd.dataset.rev = String(l.rev);
  });
}

// ---------- position pass (style-only, per rAF frame) ----------
function wrapD(d, n) { d = ((d % n) + n) % n; return d > n / 2 ? d - n : d; }   // shortest signed distance on a ring
function geom(d) {
  const ad = Math.abs(d);
  const cd = Math.max(-CAP, Math.min(CAP, d)), a = Math.min(ad, CAP);
  const ang = cd * THETA * D2R;
  return {
    ty: LIFT * Math.sin(ang), tz: DEPTH * (Math.cos(ang) - 1), rx: -cd * THETA * ROLL,
    sc: 1 - 0.05 * a,
    op: ad > 4 ? 0 : Math.max(0, 1 - 0.27 * ad),   // card body: solid near, fades to 0 toward the edge
    txt: Math.max(0, 1 - 1.5 * ad),                // TEXT: only the centered card reads — no ghosting/shimmer
    a,
  };
}
function positionAllCards() {
  const n = state.lessons.length; if (!n) return;
  const actIdx = ((Math.round(state.activeF) % n) + n) % n;
  const baseY = (deckH - CARD_H) / 2;   // vertical center of the panel
  for (let i = 0; i < n; i++) {
    const nd = pool.get(state.lessons[i].id); if (!nd) continue;
    const d = wrapD(i - state.activeF, n);   // ring: cards loop end -> start
    if (Math.abs(d) > 4.6) { nd.style.visibility = 'hidden'; nd.style.willChange = 'auto'; continue; }
    const g = geom(d), isAct = i === actIdx;
    const tz = g.tz + (state.inspecting && isAct ? 55 : 0);   // pop the inspected card forward
    nd.style.visibility = 'visible';
    nd.style.transform = `translate3d(0, ${(baseY + g.ty).toFixed(1)}px, ${tz.toFixed(1)}px) rotateX(${g.rx.toFixed(2)}deg) scale(${g.sc.toFixed(3)})`;
    nd.style.opacity = (state.inspecting && !isAct) ? '0' : g.op.toFixed(3);   // fade peeks while inspecting one card
    nd.style.setProperty('--txt', (state.inspecting && !isAct) ? '0' : g.txt.toFixed(3));  // only the centered card shows text
    nd.style.zIndex = String(1000 - Math.round(g.a * 10));
    nd.style.willChange = Math.abs(d) < 1.5 ? 'transform' : 'auto';
    nd.style.pointerEvents = isAct ? 'auto' : 'none';
    nd.classList.toggle('is-active', isAct && Math.abs(d) < 0.5);   // the focused card lifts (CSS)
  }
  // reactive ambient glow — picks up the active card's confidence hue
  const glow = document.querySelector('#glow');
  if (glow) { const a = state.lessons[actIdx]; const h = hueFor(a ? (a.confidence ?? 0) : 0.5);
    glow.style.background = `radial-gradient(60% 45% at 50% 42%, ${h.replace(')', ' / 22%)').replace('hsl', 'hsla')}, transparent 70%)`; }
  renderTrack(n, actIdx);
}
function renderTrack(n, act) {
  const t = $('#track'), m = Math.min(n, 24); let h = '';
  for (let i = 0; i < m; i++) h += `<i class="${i === act ? 'at' : ''}"></i>`;
  t.innerHTML = h;
}

// ---------- rAF lerp loop ----------
function frame() {
  state.activeF += (state.targetF - state.activeF) * (reduceMotion ? 1 : 0.18);
  positionAllCards();
  if (Math.abs(state.targetF - state.activeF) < 0.0015 && !state.dragging) {
    const n = state.lessons.length;                        // normalize into [0,n) — seamless (positioning wraps)
    const norm = n ? ((Math.round(state.targetF) % n) + n) % n : 0;
    state.activeF = state.targetF = norm; positionAllCards(); state.raf = null;
  } else state.raf = requestAnimationFrame(frame);
}
function kick() { if (state.raf == null) state.raf = requestAnimationFrame(frame); }
function setTarget(v) { if (!state.lessons.length) return; state.targetF = v; kick(); }   // unbounded — ring wraps
function snap() { if (!state.lessons.length) return; state.targetF = Math.round(state.activeF); kick(); }
function activeIndex() { const n = state.lessons.length; return n ? ((Math.round(state.activeF) % n) + n) % n : 0; }
function flipActive() {
  const n = state.lessons.length; if (!n || state.flipLock) return;
  const nd = pool.get(state.lessons[activeIndex()].id); if (!nd) return;
  const willFlip = !nd.classList.contains('flipped');
  nd.classList.toggle('flipped');
  state.flipLock = true; setTimeout(() => state.flipLock = false, 540);
  if (willFlip) { state.inspecting = true; positionAllCards(); }            // hide peeks immediately
  else { setTimeout(() => { state.inspecting = false; positionAllCards(); }, 540); }  // restore peeks AFTER flip-back completes
}
function unflipAll() { if (!state.inspecting) return; pool.forEach(nd => nd.classList.remove('flipped')); state.inspecting = false; positionAllCards(); }

// ---------- data ----------
async function refresh(force = false) {
  let data; try { data = await api(`/ledger?status=${state.filter}`); } catch { return; }
  if (!force && data.etag === state.lastRendered && state.filter === state.lastFilter) return;
  const fresh = data.lessons.filter(l => !state.knownIds.has(l.id));
  state.lessons = data.lessons; state.byId = new Map(data.lessons.map(l => [l.id, l]));
  state.etag = data.etag; state.lastRendered = data.etag; state.lastFilter = state.filter;
  buildDeck();
  data.lessons.forEach(l => state.knownIds.add(l.id));
  const n = state.lessons.length;
  if (!state.booted) { state.booted = true; state.activeF = state.targetF = Math.floor((n - 1) / 2); }
  else if (fresh.length) setTarget(data.lessons.findIndex(l => l.id === fresh[fresh.length - 1].id), { rubber: false });
  else state.targetF = Math.max(0, Math.min(Math.max(0, n - 1), state.targetF));
  positionAllCards(); kick();
}

// ---------- console ----------
function logLine(text, cls = '') { const d = document.createElement('div');
  if (cls) d.className = cls; d.textContent = text; $('#log').appendChild(d); $('#log').scrollTop = $('#log').scrollHeight; }
const hdr = () => ({ 'Content-Type': 'application/json' });
const json = (o) => ({ method: 'POST', headers: hdr(), body: JSON.stringify(o) });
async function runCommand(raw) {
  const s = raw.trim(); if (!s) return;
  logLine('» ' + s, 'echo');
  try {
    if (s.startsWith('/')) {
      const [cmd, ...rest] = s.slice(1).split(/\s+/); const id = parseInt(rest[0], 10);
      if (cmd === 'note') { const l = await api('/notes', json({ text: rest.join(' ') })); logLine(`✓ learned #${l.id}`, 'ok'); logConflicts(l); }
      else if (cmd === 'pin') { await api(`/lessons/${id}/pin`, { method: 'POST' }); logLine(`✓ pinned #${id} → front`, 'ok'); }
      else if (cmd === 'demote') { const l = await api(`/lessons/${id}/demote`, { method: 'POST' }); logLine(`✓ demoted #${id} → ${l.confidence.toFixed(2)}`, 'ok'); }
      else if (cmd === 'tombstone') { await api(`/lessons/${id}/tombstone`, { method: 'POST' }); logLine(`✓ tombstoned #${id}`, 'ok'); }
      else if (cmd === 'revise') { logLine('… Qwen judging lessons against the change', 'echo');
        const r = await api('/revise', json({ change: rest.join(' ') }));
        r.results.forEach(x => logLine(`  #${x.lesson_id} ${x.action}${x.obsolete ? ' — ' + x.reason : ''}`, x.obsolete ? 'ok' : '')); }
      else throw new Error('unknown command: /' + cmd);
    } else {
      const text = s.replace(/^by the way,?\s*/i, '');
      if (state.agentStatus === 'running' || state.agentStatus === 'paused') {
        await api('/agent/inject', json({ text })); logLine('✓ note injected → agent interrupts & redoes with it', 'ok');
      } else { const l = await api('/notes', json({ text })); logLine(`✓ by-the-way note → lesson #${l.id} (agent obeys on next recall)`, 'ok'); logConflicts(l); }
    }
  } catch (e) { logLine('✗ ' + (e.message || 'failed'), 'err'); }
  refresh(true);
}

// ---------- agent loop ----------
function setAgentStatus(s) {
  state.agentStatus = s;
  const el = $('#agentStatus'); el.textContent = s; el.className = 'status ' + s;
  const show = (id, on) => $(id).hidden = !on;
  show('#btnStart', s === 'idle'); show('#btnPause', s === 'running');
  show('#btnResume', s === 'paused'); show('#btnStop', s === 'running' || s === 'paused');
  try { paintConsole(); } catch {}   // reflect Teach→Steer while the agent is busy
}
function highlightCode(code) {
  return escapeHtml(code).replace(/(tenant_id)/g, '<span class="filter">$1</span>')
    .replace(/(all_orders\(\)(?!\s*if))/g, '<span class="leak">$1</span>');
}
function renderAttempt(step, code, passed, recalled) {
  const badge = passed ? '<span class="badge green">✓ TEST GREEN</span>' : '<span class="badge red">✗ TEST RED</span>';
  const mem = recalled && recalled.length ? `recalled #${recalled.join(', #')}` : 'no memory recalled';
  $('#agentPanel').innerHTML = `<div class="attempt">${badge}<pre>${highlightCode(code || '')}</pre></div>
    <div class="agent-meta">attempt ${step} · ${mem} · hidden test = tenant isolation</div>`;
}
function agentThinking() { $('#agentPanel').innerHTML = `<div class="attempt"><span class="badge think">… writing</span><pre>agent is drafting get_orders …</pre></div>`; }
function onAgentStep(m) {
  if (m.status) setAgentStatus(m.status);
  const ph = m.phase;
  if (ph === 'recall') { agentThinking(); if (m.recalled) showRecalled(m.recalled); }
  else if (ph === 'result') renderAttempt(m.step, m.code, m.passed, m.recalled);
  else if (ph === 'interrupted') logLine('↻ agent interrupted → re-planning with your note', 'echo');
  else if (ph === 'note') logLine(`⇢ agent absorbed note → lesson #${m.lesson_id}`, 'ok');
  else if (ph === 'stopped') $('#agentPanel').innerHTML = '<div class="agent-empty">agent stopped.</div>';
}
async function agentCmd(action) { try { await api('/agent/' + action, { method: 'POST' }); } catch {} }

// ---------- chat ----------
function bubble(who, text) { const intro = $('#intro'); if (intro) intro.remove();
  const d = document.createElement('div'); d.className = 'msg ' + who;
  d.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`; $('#thread').appendChild(d); $('#thread').scrollTop = $('#thread').scrollHeight; return d; }
async function ask(q) {
  $('#cSend').disabled = true; bubble('user', q);
  const t = bubble('agent', '…');
  try { const r = await api('/chat', json({ message: q })); t.innerHTML = `<div class="who">agent</div>${escapeHtml(r.reply)}`; showRecalled(r.recalled); }
  catch { t.innerHTML = `<div class="who">agent</div>(error contacting agent)`; }
  $('#cSend').disabled = false;
}
function showRecalled(ids) {
  const strip = $('#recall');
  if (!ids || !ids.length) { strip.innerHTML = '<span style="color:var(--ink-faint)">no lessons recalled for that</span>'; return; }
  strip.innerHTML = `<span>recalled ${ids.length}:</span>`;
  ids.forEach(id => { const l = state.byId.get(id); if (!l) return;
    const s = document.createElement('span'); s.className = 'lz'; s.textContent = `#${id}`; s.title = l.lesson; s.onclick = () => jumpTo(id); strip.appendChild(s); });
  ids.forEach(id => flashCard(id, 'highlight'));
}
function jumpTo(id) { const i = state.lessons.findIndex(l => l.id === id); const n = state.lessons.length;
  if (i >= 0) { state.targetF = state.activeF + wrapD(i - state.activeF, n); kick(); } flashCard(id, 'highlight'); }
function flashCard(id, cls) { const el = pool.get(id); if (el) { el.classList.add(cls); setTimeout(() => el.classList.remove(cls), 1400); } }

async function loadAB() {
  try { const ab = await api('/ab'); if (ab.available === false) return;
    const a = ab.arm_a_no_memory, b = ab.arm_b_with_memory;
    $('#ab').innerHTML = `<span class="pill a">A · no memory ${a.green}/${a.k}</span><span class="pill b">B · with memory ${b.green}/${b.k}</span>`;
  } catch {}
}

// ---------- self-measurement (memory quality) ----------
function logConflicts(l) {
  const c = l && l._contradictions;
  if (!c || !c.conflicts || !c.conflicts.length) return;
  c.conflicts.forEach(x => {
    const verb = x.action === 'tombstoned-new' ? 'kept established' : 'superseded';
    logLine(`⚑ contradiction: #${x.existing_id} ${verb} — ${x.reason}`, 'warn');
  });
}
// count-up a metric value with easing + a brief pulse (high-end reveal on Measure)
function animateNumber(el, to, { decimals = 2, dur = 750, signed = false } = {}) {
  const from = 0, start = performance.now(), ease = t => 1 - Math.pow(1 - t, 3);
  el.classList.add('metric-pulse');
  (function step(now) {
    const t = Math.min(1, (now - start) / dur), v = from + (to - from) * ease(t);
    el.textContent = (signed && v > 0 ? '+' : '') + v.toFixed(decimals);
    if (t < 1) requestAnimationFrame(step);
    else { el.textContent = (signed && to >= 0 ? '+' : '') + to.toFixed(decimals);
           setTimeout(() => el.classList.remove('metric-pulse'), 420); }
  })(start);
}
async function loadMetrics() {
  try {
    const m = await api('/metrics');
    $('#mCal').textContent = m.grounded_outcomes ? m.calibration_gap.toFixed(2) : '—';
    $('#mGround').textContent = m.grounded_outcomes;
    $('#mWeights').textContent = `${m.weights.bm25}·${m.weights.vector}`;
  } catch {}
}
async function runEvaluate() {
  const btn = $('#btnMeasure'); btn.disabled = true; const was = btn.textContent; btn.textContent = 'measuring…';
  try {
    const r = await api('/evaluate', { method: 'POST' });
    if (!r.n) { logLine('need ≥2 lessons to measure recall', 'warn'); }
    else {
      const on = r.vector_on.recall_at_1, off = r.vector_off.recall_at_1;
      const lift = on - off;
      $('#mLift').className = lift > 0 ? 'lift-pos' : (lift < 0 ? 'lift-neg' : '');
      animateNumber($('#mRecall'), on, { decimals: 2 });
      animateNumber($('#mLift'), lift, { decimals: 2, signed: true });
      logLine(`measured on ${r.n} keyword-free queries · Recall@1 ${on.toFixed(2)} (semantic on) vs ${off.toFixed(2)} (off)`, 'ok');
    }
  } catch (e) { logLine('✗ measure failed: ' + (e.message || ''), 'err'); }
  btn.disabled = false; btn.textContent = was;
}
async function runTune() {
  const btn = $('#btnTune'); btn.disabled = true; const was = btn.textContent; btn.textContent = 'tuning…';
  try {
    const r = await api('/tune', { method: 'POST' });
    if (r.tuned) logLine(`✓ self-tuned weights → bm25 ${r.weights.bm25}·vec ${r.weights.vector} · Recall@1 ${r.baseline.recall_at_1.toFixed(2)}→${r.best.recall_at_1.toFixed(2)}`, 'ok');
    else if (!r.n) logLine('self-tune: need ≥2 lessons', 'warn');
    else logLine(`self-tune: baseline already optimal (Recall@1 ${r.baseline.recall_at_1.toFixed(2)}) — no change`, '');
    await loadMetrics();
  } catch (e) { logLine('✗ self-tune failed: ' + (e.message || ''), 'err'); }
  btn.disabled = false; btn.textContent = was;
}

// ---------- live ----------
function live() {
  try { const es = new EventSource('/events');
    es.onmessage = (e) => { const m = JSON.parse(e.data);
      if (m.type === 'ledger_changed') { refresh(true); flashCard(m.lesson_id, 'react'); loadMetrics(); }
      else if (m.type === 'agent_step') onAgentStep(m); };
    es.onerror = () => {};
  } catch {}
  setInterval(() => refresh(false), 2000);
}

// ---------- adaptive console: Ask ⇄ Teach (→ Steer while the agent runs) ----------
let mode = 'ask';
const HINTS = {
  ask: "ask me to write or fix code — I'll use what I've learned",
  teach: "teach or correct my memory — I'll obey it on the next recall",
  steer: "nudge me while I work — I interrupt and redo with your note",
};
const PLACEH = {
  ask: 'Ask me to write or fix code…',
  teach: "e.g. always filter orders by tenant_id — I'll remember it",
  steer: 'Nudge the running agent…',
};
function agentBusy() { return state.agentStatus === 'running' || state.agentStatus === 'paused'; }
function effMode() { return (mode === 'teach' && agentBusy()) ? 'steer' : mode; }
function paintConsole() {
  const em = effMode(), con = $('#console'); if (!con) return;
  con.classList.toggle('teach', mode === 'teach' && em !== 'steer');
  con.classList.toggle('steer', em === 'steer');
  $('#modeHint').textContent = HINTS[em];
  $('#cInput').placeholder = PLACEH[em];
  $('#cSig').textContent = em === 'ask' ? '›' : (em === 'steer' ? '⇢' : '»');
  $('#teachChips').hidden = (mode !== 'teach');
  document.querySelectorAll('.mode').forEach(b => {
    const on = b.dataset.mode === mode; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
  });
}
function setMode(m) { mode = m; paintConsole(); $('#cInput').focus(); }
async function consoleSend() {
  const inp = $('#cInput'), raw = inp.value.trim(); if (!raw) return;
  inp.value = '';
  if (raw.startsWith('/')) { await runCommand(raw); return; }   // power commands work in either mode
  if (mode === 'ask') await ask(raw);
  else await runCommand(raw);                                    // teach → note, or steer if the agent is busy
}
$('#cInput').addEventListener('keydown', e => { if (e.key === 'Enter') consoleSend(); });
$('#cSend').addEventListener('click', consoleSend);
document.querySelectorAll('.mode').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
document.querySelectorAll('#teachChips [data-cmd]').forEach(b => b.addEventListener('click', () => {
  const pre = { pin: '/pin ', demote: '/demote ', tombstone: '/tombstone ', revise: '/revise ' }[b.dataset.cmd];
  setMode('teach'); const i = $('#cInput'); i.value = pre; i.focus();
}));
document.querySelectorAll('.try-chip').forEach(b => b.addEventListener('click', () => {
  const t = b.dataset.try;
  if (t === 'run') { agentCmd('start'); return; }
  setMode(t); if (b.dataset.fill) $('#cInput').value = b.dataset.fill; $('#cInput').focus();
}));
document.querySelectorAll('[data-agent]').forEach(b => b.addEventListener('click', () => agentCmd(b.dataset.agent)));
$('#btnMeasure').addEventListener('click', runEvaluate);
$('#btnTune').addEventListener('click', runTune);
paintConsole();

// deck: wheel / drag / tap-to-flip
const dw = document.querySelector('.deck-wrap');
let wheelIdle = null, dnY = 0, dnF = 0, moved = 0;
dw.addEventListener('wheel', e => { e.preventDefault(); unflipAll();
  const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? window.innerHeight : 1;
  setTarget(state.targetF + e.deltaY * unit * 0.0022);
  clearTimeout(wheelIdle); wheelIdle = setTimeout(snap, 120);
}, { passive: false });
dw.addEventListener('pointerdown', e => {
  state.dragging = true; dnY = e.clientY; dnF = state.targetF; moved = 0;
  try { dw.setPointerCapture(e.pointerId); } catch {}
});
dw.addEventListener('pointermove', e => {
  if (!state.dragging) return; const dy = e.clientY - dnY; moved = Math.max(moved, Math.abs(dy));
  if (moved > 6) unflipAll();
  setTarget(dnF - dy / 96);
});
dw.addEventListener('pointerup', e => {
  if (!state.dragging) return; state.dragging = false;
  try { dw.releasePointerCapture(e.pointerId); } catch {}
  if (moved < 6) flipActive(); else snap();
});
dw.addEventListener('click', e => e.preventDefault());   // taps handled in pointerup

document.addEventListener('keydown', e => {
  if (document.activeElement.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { unflipAll(); setTarget(Math.round(state.targetF) - 1); e.preventDefault(); }
  else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { unflipAll(); setTarget(Math.round(state.targetF) + 1); e.preventDefault(); }
  else if (e.key === ' ') { flipActive(); e.preventDefault(); }
});

window.addEventListener('resize', () => { measureDeck(); positionAllCards(); });
measureDeck();
refresh(true); loadAB(); live(); loadMetrics();
api('/agent/status').then(s => setAgentStatus(s.status)).catch(() => {});
