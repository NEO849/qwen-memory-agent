// Regress-Guard UI — vanilla ES module, no build step.
// Deck = 3D Rolodex arc: persistent node pool + one rAF lerp loop (idle = 0 CPU).
// Design law: one field -> one channel. lifecycle=card body · confidence=meter · severity=spine.
const $ = (s) => document.querySelector(s);
// fetch with a 25s client timeout so a stalled backend surfaces the existing error paths
// (button re-enables, "error contacting agent") instead of hanging a spinner forever.
const api = (p, o = {}) => {
  const ac = new AbortController(); const t = setTimeout(() => ac.abort(), 25000);
  return fetch(p, { ...o, signal: ac.signal })
    .then(r => r.ok ? r.json() : Promise.reject(r))
    .finally(() => clearTimeout(t));
};

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
      ${l.kind === 'anti_pattern' ? '<span class="anti-ribbon" title="a known past regression — the memory actively blocks repeating it">⛔ DO-NOT</span>' : ''}
      ${l.author === 'synthesis' ? '<span class="meta-badge" title="a synthesized meta-lesson (ExpeL) — starts at the prior, earns confidence from real tests">✦ meta</span>' : ''}
      <div class="kicker">
        <span class="src" style="background:${src};box-shadow:0 0 8px ${src}77, 0 0 0 3px rgba(255,255,255,.05)" title="source: ${l.source}"></span>
        <span class="when">WHEN ${escapeHtml((l.trigger || 'general').replace(/^when\s+/i, ''))}</span>
        ${l.sanitized > 0 ? `<span class="shield" title="${l.sanitized} embedded injection directive${l.sanitized === 1 ? '' : 's'} neutralized before this lesson can reach the model">🛡 ${l.sanitized}</span>` : ''}
      </div>
      <div class="lesson">${escapeHtml(l.lesson)}</div>
      <div class="foot">
        <span class="chip">${escapeHtml(l.scope || 'general')}</span>
        <span class="conf${(l.real_pass + l.real_fail) > 0 ? ' earned' : ' is-prior'}">${conf.toFixed(2)}<span class="bar"><i style="width:${Math.round(conf*100)}%;background:${hueFor(conf)}"></i></span></span>
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
        <div><span>severity</span><b><i class="sdot sev-${l.severity}"></i> ${l.severity}${l.kind === 'anti_pattern' ? ' · anti-pattern' : ''}</b></div>
        <div><span>source</span><b>${l.source} · learned ${rel(l.created_at)}</b></div>
        ${(l.recall_count > 0) ? `<div><span>recalled</span><b>${l.recall_count}× · last ${rel(l.last_recalled_at)}</b></div>` : ''}
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
    deck.innerHTML = '<div class="empty">No lessons yet — teach a rule below, or hit ▶ Run to earn one.</div>';
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
    nd.className = 'card' + lifecycleClass(l, agingThreshold)
      + (l.kind === 'anti_pattern' ? ' anti' : '') + (wasFlipped ? ' flipped' : '');
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
      else if (cmd === 'anti') { const l = await api('/notes', json({ text: rest.join(' '), kind: 'anti_pattern', severity: 'high' }));
        logLine(`⛔ recorded anti-pattern #${l.id} — I'll block this regression`, 'ok'); logConflicts(l); }
      else throw new Error('unknown command: /' + cmd);
    } else {
      const text = s.replace(/^by the way,?\s*/i, '');
      if (state.agentStatus === 'running' || state.agentStatus === 'paused') {
        await api('/agent/inject', json({ text })); logLine("✓ steered — I'll re-plan with your note", 'ok');
      } else { const l = await api('/notes', json({ text }));
        if (l._deduped) logLine(`↺ merged into #${l.merged_into} (duplicate — salience up, confidence still from tests)`, 'ok');
        else { logLine(`✓ saved your note → lesson #${l.id} (I'll use it next answer)`, 'ok'); logConflicts(l); } }
    }
  } catch (e) { logLine('✗ ' + (e.message || 'failed'), 'err'); }
  refresh(true);
}

// ---------- agent loop ----------
function setAgentStatus(s) {
  state.agentStatus = s;
  const el = $('#agentStatus'); el.textContent = s; el.className = 'status ' + s;
  const show = (id, on) => $(id).hidden = !on;
  show('#btnStart', s === 'idle' || s === 'stopped' || s === 'done'); show('#btnPause', s === 'running');
  show('#btnResume', s === 'paused'); show('#btnStop', s === 'running' || s === 'paused');
  try { paintTeach(); } catch {}   // the left input becomes "steer" while the agent is busy
}
function highlightCode(code) {
  return escapeHtml(code).replace(/(tenant_id)/g, '<span class="filter">$1</span>')
    .replace(/(all_orders\(\)(?!\s*if))/g, '<span class="leak">$1</span>');
}
// agent runs stream into the conversation as messages (it's the AI, working)
let runBubble = null;
function threadAppend(el) { const intro = $('#intro'); if (intro) intro.remove();
  $('#thread').appendChild(el); $('#thread').scrollTop = $('#thread').scrollHeight; }
function agentThinking() {
  runBubble = document.createElement('div'); runBubble.className = 'msg run agent';
  runBubble.innerHTML = `<div class="who">agent · run</div><span class="run-badge think">… writing</span><pre>drafting get_orders …</pre>`;
  threadAppend(runBubble);
}
function renderAttempt(step, code, passed, recalled) {
  if (!runBubble) agentThinking();
  const badge = passed ? '<span class="run-badge green">✓ test green</span>' : '<span class="run-badge red">✗ test red</span>';
  const mem = recalled && recalled.length ? `recalled #${recalled.join(', #')}` : 'no memory recalled';
  runBubble.innerHTML = `<div class="who">agent · run</div>${badge}<pre>${highlightCode(code || '')}</pre>` +
    `<div class="run-meta">attempt ${step} · ${mem} · hidden test: tenant isolation</div>`;
  runBubble = null;   // the next attempt gets a fresh bubble → the thread shows red → green
  $('#thread').scrollTop = $('#thread').scrollHeight;
}
function sysLine(text, cls = '') { const d = document.createElement('div'); d.className = 'sys ' + cls; d.textContent = text; threadAppend(d); }
function onAgentStep(m) {
  if (m.status) setAgentStatus(m.status);
  const ph = m.phase;
  if (ph === 'recall') { agentThinking(); if (m.recalled) showRecalled(m.recalled); }
  else if (ph === 'result') renderAttempt(m.step, m.code, m.passed, m.recalled);
  else if (ph === 'interrupted') sysLine('↻ re-planning with your note');
  else if (ph === 'note') sysLine(`⇢ saved your note → lesson #${m.lesson_id}`, 'ok');
  else if (ph === 'stopped') sysLine('agent stopped.');
}
async function agentCmd(action) { try { await api('/agent/' + action, { method: 'POST' }); } catch {} }

// ---------- chat ----------
function bubble(who, text) { const intro = $('#intro'); if (intro) intro.remove();
  const d = document.createElement('div'); d.className = 'msg ' + who;
  d.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`; $('#thread').appendChild(d); $('#thread').scrollTop = $('#thread').scrollHeight; return d; }
async function ask(q) {
  $('#askSend').disabled = true; bubble('user', q);
  const t = bubble('agent', '…');
  try {
    const streamed = await askStream(q, t);       // Qwen token streaming (if enabled)
    if (!streamed) await askOnce(q, t);            // fall back to /chat (flag off / no stream)
  } catch { try { await askOnce(q, t); } catch { t.innerHTML = `<div class="who">agent</div>(error contacting agent)`; } }
  $('#askSend').disabled = false;
}
async function askOnce(q, t) {
  const r = await api('/chat', json({ message: q }));
  t.innerHTML = `<div class="who">agent</div>${escapeHtml(r.reply)}`;
  showRecalled(r.recalled, r.sanitized_total, r.inhibited, r.used_tool, r.tool_query);
}
// Stream the answer token-by-token over SSE. The `meta` event lands first, so the globe/deck
// light up with the recalled lessons WHILE the answer is still typing — memory + use, live.
async function askStream(q, t) {
  let res;
  try { res = await fetch('/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: q }) }); }
  catch { return false; }
  if (!res.ok || !res.body) return false;          // 404 when STREAMING_ENABLED is off -> fallback
  const reader = res.body.getReader(); const dec = new TextDecoder();
  let buf = '', text = '';
  const paint = (caret) => { t.innerHTML = `<div class="who">agent</div>${escapeHtml(text)}${caret ? '<span class="caret"></span>' : ''}`; $('#thread').scrollTop = $('#thread').scrollHeight; };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split('\n\n'); buf = parts.pop();
    for (const ev of parts) {
      const dataLine = ev.split('\n').find(l => l.startsWith('data:'));
      if (!dataLine) continue;
      let data; try { data = JSON.parse(dataLine.slice(5).trim()); } catch { continue; }
      if (ev.startsWith('event: meta')) showRecalled(data.recalled, data.sanitized_total, data.inhibited, data.used_tool, data.tool_query);
      else if (data.delta) { text += data.delta; paint(true); }
    }
  }
  paint(false);
  return true;
}
function showRecalled(ids, sanitizedTotal = 0, inhibited = [], usedTool = false, toolQuery = '') {
  const strip = $('#recall');
  if (!ids || !ids.length) { strip.hidden = true; strip.innerHTML = ''; return; }
  strip.hidden = false;
  const lead = usedTool
    ? `<span class="tool-call">🔧 Qwen called <code>recall(${toolQuery ? '“' + escapeHtml(toolQuery.slice(0, 40)) + '”' : ''})</code> →</span> `
    : '';
  strip.innerHTML = `${lead}<span>answered using ${ids.length} lesson${ids.length === 1 ? '' : 's'}:</span>`;
  ids.forEach(id => { const l = state.byId.get(id); if (!l) return;
    const s = document.createElement('span'); s.className = 'lz'; s.textContent = `#${id}`; s.title = l.lesson; s.onclick = () => jumpTo(id); strip.appendChild(s); });
  if (sanitizedTotal > 0) {
    const s = document.createElement('span'); s.className = 'shield-note';
    s.textContent = `🛡 ${sanitizedTotal} directive${sanitizedTotal === 1 ? '' : 's'} neutralized`;
    s.title = 'Embedded injection directives in the recalled lessons were stripped before reaching the model.';
    strip.appendChild(s);
  }
  if (inhibited && inhibited.length) {
    const s = document.createElement('span'); s.className = 'anti-note';
    s.textContent = `⛔ blocked ${inhibited.length} known regression${inhibited.length === 1 ? '' : 's'}`;
    s.title = 'A recalled anti-pattern warned the agent not to repeat a past regression.';
    strip.appendChild(s);
  }
  ids.forEach(id => flashCard(id, 'highlight'));
  pulseGlobe(ids);                       // ← light up the SAME lessons live on the globe (chat + agent)
}
// bridge: tell the persistent globe iframe which lessons were just recalled (only real recall IDs)
function pulseGlobe(ids) {
  const f = $('#graphFrame');
  if (f && f.contentWindow && ids && ids.length)
    f.contentWindow.postMessage({ type: 'recall-pulse', ids }, location.origin);
}
function jumpTo(id) { const i = state.lessons.findIndex(l => l.id === id); const n = state.lessons.length;
  if (i >= 0) { state.targetF = state.activeF + wrapD(i - state.activeF, n); kick(); } flashCard(id, 'highlight'); }
function flashCard(id, cls) { const el = pool.get(id); if (el) { el.classList.add(cls); setTimeout(() => el.classList.remove(cls), 1400); } }

// The 0/5 → 5/5 statement now lives in ONE place only — the Proof tab (playProof).
// The redundant stage-head badge and chat landing-hero comparison were removed by design.
async function loadAB() { /* single source of truth: the Proof tab */ }

// Graph totals hoisted OUT of the in-graph info card into a horizontal strip above the globe.
async function loadGraphStats() {
  try {
    const g = await api('/graph'); const s = g.stats || {};
    const el = $('#graphMetrics'); if (!el) return;
    const cell = (v, l, warn) => `<div class="gm${warn ? ' warn' : ''}"><b>${v ?? 0}</b><span>${l}</span></div>`;
    el.innerHTML = cell(s.lessons, 'lessons') + cell(s.links, 'links')
      + cell(s.orphans, 'orphans', s.orphans > 0) + cell(s.obsolete, 'forgotten');
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
  if (reduceMotion) { el.textContent = (signed && to >= 0 ? '+' : '') + to.toFixed(decimals); return; }
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
    const set = (id, v) => { const e = $(id); if (e) e.textContent = v; };
    set('#mCal', m.grounded_outcomes ? m.calibration_gap.toFixed(2) : '—');
    set('#mGround', m.grounded_outcomes);
    set('#mWeights', `${m.weights.bm25}·${m.weights.vector}`);
    if (m.health_pct != null) set('#mHealth', `${Math.round(m.health_pct * 100)}%`);
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
      if (m.type === 'ledger_changed') { refresh(true); flashCard(m.lesson_id, 'react'); loadMetrics();
        clearTimeout(window._grT); window._grT = setTimeout(() => {   // nudge the globe to re-read structure (no camera reset)
          const gf = $('#graphFrame'); if (gf && gf.contentWindow) gf.contentWindow.postMessage({ type: 'graph-refresh' }, location.origin); loadGraphStats(); }, 400); }
      else if (m.type === 'agent_step') onAgentStep(m); };
    es.onerror = () => {};
  } catch {}
  setInterval(() => refresh(false), 2000);
}

// ---------- LEFT = the memory · RIGHT = chat/graph ----------
function agentBusy() { return state.agentStatus === 'running' || state.agentStatus === 'paused'; }
function paintTeach() {
  const sec = document.querySelector('.teach'); if (!sec) return;
  const busy = agentBusy();
  sec.classList.toggle('steer', busy);
  $('#teachSub').textContent = busy ? "· steers me while I'm running" : "· I'll use it on my next answer";
  $('#teachInput').placeholder = busy ? "Steer me — I'll re-plan with your note…" : 'Teach a rule, or correct me…';
  $('#tSig').textContent = busy ? '⇢' : '»';
  $('#teachSend').textContent = busy ? 'Steer' : 'Teach';
}
// teach a rule (guard) or a "don't" (anti-pattern). Plain text only; no command syntax leaks into the field.
async function teachSubmit(kind) {
  const i = $('#teachInput'), raw = i.value.trim(); if (!raw) return; i.value = '';
  try {
    if (kind === 'anti') {
      const l = await api('/notes', json({ text: raw, kind: 'anti_pattern', severity: 'high' }));
      logLine(`⛔ recorded anti-pattern #${l.id} — I'll block this regression`, 'ok'); logConflicts(l); refresh(true);
    } else {
      await runCommand(raw);   // note, or steer/inject when the agent is running
    }
  } catch (e) { logLine('✗ ' + (e.message || 'failed'), 'err'); }
}
$('#teachInput').addEventListener('keydown', e => { if (e.key === 'Enter') teachSubmit('guard'); });
$('#teachSend').addEventListener('click', () => teachSubmit('guard'));
$('#teachDont').addEventListener('click', () => teachSubmit('anti'));

// card actions act DIRECTLY on the selected (centered) card — no command text in any field
function activeCardId() { return state.lessons.length ? state.lessons[activeIndex()].id : null; }
document.querySelectorAll('#cardActs [data-card]').forEach(b => b.addEventListener('click', async () => {
  const id = activeCardId();
  if (id == null) { logLine('scroll to a card first', 'warn'); return; }
  const cmd = b.dataset.card;
  try {
    if (cmd === 'pin') { await api(`/lessons/${id}/pin`, { method: 'POST' }); logLine(`✓ pinned #${id}`, 'ok'); }
    else if (cmd === 'demote') { const l = await api(`/lessons/${id}/demote`, { method: 'POST' }); logLine(`✓ demoted #${id} → ${l.confidence.toFixed(2)}`, 'ok'); }
    else if (cmd === 'tombstone') { await api(`/lessons/${id}/tombstone`, { method: 'POST' }); logLine(`✓ forgot #${id}`, 'ok'); }
    else if (cmd === 'revise') { flashCard(id, 'highlight'); const inp = $('#teachInput'); inp.value = '/revise '; inp.focus(); logLine('describe the change after /revise, then Enter', 'echo'); return; }
  } catch (e) { logLine('✗ ' + (e.message || 'failed'), 'err'); }
  refresh(true);
}));

async function askSend() { const i = $('#askInput'), q = i.value.trim(); if (!q) return; i.value = ''; await ask(q); }
$('#askInput').addEventListener('keydown', e => { if (e.key === 'Enter') askSend(); });
$('#askSend').addEventListener('click', askSend);
document.querySelectorAll('[data-agent]').forEach(b => b.addEventListener('click', () => agentCmd(b.dataset.agent)));
$('#btnMeasure').addEventListener('click', runEvaluate);
$('#btnTune').addEventListener('click', runTune);
$('#btnSynth').addEventListener('click', runSynthesize);

// centre toggle — Chat vs the Proof moment. The knowledge globe is a PERSISTENT right pane
// (always visible), so 'memory' and 'use' are on screen together — no switching away to see it.
function setView(v) {
  document.querySelectorAll('.vbtn').forEach(x => { const on = x.dataset.view === v; x.classList.toggle('on', on); x.setAttribute('aria-selected', on); });
  $('#viewChat').hidden = v !== 'chat';
  $('#viewDuel').hidden = v !== 'duel';
  $('#viewProof').hidden = v !== 'proof';
  if (v === 'proof') { playProof(); }        // the signature moment plays on open
}
document.querySelectorAll('.vbtn').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
$('#btnReplay') && $('#btnReplay').addEventListener('click', playProof);
$('#btnDuel') && $('#btnDuel').addEventListener('click', runDuel);
{ const gf = $('#graphFrame'); if (gf) gf.src = '/graph.html?n=4'; }   // load the persistent globe once
loadGraphStats();                                                     // populate the metric strip above it
paintTeach();
// Land on the signature 🏆 Proof moment and auto-play it once — a cold visitor sees 0→5/5 first
// (jurors decide in the first 30s); Chat is one click away. playProof respects reduced-motion.
// Deferred to a macrotask so every top-level const (api, reduceMotion, …) is initialized first.
setTimeout(() => { try { if ($('#viewProof')) setView('proof'); } catch (_) {} }, 0);

// ---------- the signature "proof" moment: same AI twice, only difference is memory ----------
// Reflow the one long list-comprehension into clean, black-style multi-line Python so it fits the
// column without ugly wrapping — reads like a real formatter, not a random line-break.
function formatProofCode(code) {
  return String(code || '').split('\n').flatMap(ln => {
    const m = ln.match(/^(\s*)return \[(.+?) for (.+?) in (.+?) if (.+)\]\s*$/);
    if (!m) return [ln];
    const [, ind, item, v, iter, cond] = m, pad = ind + '    ';
    const rows = [ind + 'return [', pad + item, pad + 'for ' + v + ' in', pad + '    ' + iter];
    const cm = cond.match(/^(.+?)\s*==\s*(.+)$/);
    if (cm) { rows.push(pad + 'if ' + cm[1], pad + '   == ' + cm[2]); } else { rows.push(pad + 'if ' + cond); }
    rows.push(ind + ']');
    return rows;
  }).join('\n');
}

// A tiny, safe Python highlighter (left-to-right tokenizer, no nested-span bugs). Full editor-grade
// colouring PLUS the decisive difference pulsing — this is the first + most-watched moment.
function proofHighlight(code) {
  const s = formatProofCode(code);
  const KW = /^(def|return|for|in|if|elif|else|not|and|or|is|None|True|False|import|from|as|with|lambda|while|try|except|finally|raise|pass|yield|class|await|async)\b/;
  const esc = t => escapeHtml(t);
  let out = '', i = 0, m;
  while (i < s.length) {
    const r = s.slice(i);
    if (m = r.match(/^\s+/)) { out += esc(m[0]); i += m[0].length; continue; }
    // the whole story is this one difference — make it pulse
    if (m = r.match(/^(order\['tenant_id'\]|user\['tenant_id'\])/)) { out += `<span class="tok-win">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(/^user\['id'\]/)) { out += `<span class="tok-lose">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(/^#[^\n]*/)) { out += `<span class="cm">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(/^('[^']*'|"[^"]*")/)) { out += `<span class="str">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(/^\d+\.?\d*/)) { out += `<span class="num">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(KW)) { out += `<span class="kw">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (m = r.match(/^[A-Za-z_]\w*/)) { const n = m[0]; out += `<span class="${/^\s*\(/.test(s.slice(i + n.length)) ? 'fn' : 'id'}">${esc(n)}</span>`; i += n.length; continue; }
    out += `<span class="pn">${esc(s[i])}</span>`; i += 1;
  }
  return out;
}
const _sleep = ms => new Promise(r => setTimeout(r, ms));
let _proofRunning = false;
async function playProof() {
  if (_proofRunning) return; _proofRunning = true;
  const btn = $('#btnReplay'); if (btn) btn.disabled = true;
  const H = (id, h) => { const e = $(id); if (e) e.innerHTML = h; };
  const T = (id, t) => { const e = $(id); if (e) e.textContent = t; };
  H('#codeA', ''); H('#codeB', ''); H('#testsA', ''); H('#testsB', '');
  T('#scoreA', '–'); T('#scoreB', '–'); T('#proofPunch', '');
  const _pd = $('#proofDelta'); if (_pd) _pd.hidden = true;
  const armA = $('#armA'), armB = $('#armB');
  if (armA) armA.className = 'arm arm-a'; if (armB) armB.className = 'arm arm-b';
  let ab; try { ab = await api('/ab'); } catch { if (btn) btn.disabled = false; _proofRunning = false; return; }
  if (!ab || ab.available === false) { T('#proofPunch', 'run `python -m harness.ab_runner --k 5` once to capture the proof'); if (btn) btn.disabled = false; _proofRunning = false; return; }
  const a = ab.arm_a_no_memory, b = ab.arm_b_with_memory, rm = reduceMotion;
  await _sleep(rm ? 0 : 300); H('#codeA', proofHighlight(a.sample_code));
  await _sleep(rm ? 0 : 550); H('#codeB', proofHighlight(b.sample_code));
  await _sleep(rm ? 0 : 650);
  let ga = 0, gb = 0;
  for (let i = 0; i < Math.max(a.k, b.k); i++) {
    if (i < a.k) { const p = i < a.green; if (p) ga++; $('#testsA').insertAdjacentHTML('beforeend', `<span class="t ${p ? 'g' : 'r'}">${p ? '✓' : '✗'}</span>`); T('#scoreA', `${ga}/${a.k}`); }
    if (i < b.k) { const p = i < b.green; if (p) gb++; $('#testsB').insertAdjacentHTML('beforeend', `<span class="t ${p ? 'g' : 'r'}">${p ? '✓' : '✗'}</span>`); T('#scoreB', `${gb}/${b.k}`); }
    await _sleep(rm ? 0 : 260);
  }
  if (armA) armA.classList.add(a.green >= b.green ? 'win' : 'lose');
  if (armB) armB.classList.add(b.green >= a.green ? 'win' : 'lose');
  await _sleep(rm ? 0 : 250);
  // the single big number: pass-rate lift, counting up at the climax
  const delta = Math.round(((b.green / b.k) - (a.green / a.k)) * 100);
  const dEl = $('#proofDelta'), dNum = $('#proofDeltaNum');
  if (dEl && dNum) {
    dEl.hidden = false;
    if (rm) { dNum.textContent = delta; }
    else {
      const steps = 22, dur = 620; let s = 0;
      const tick = () => { s++; dNum.textContent = Math.round(delta * s / steps);
        if (s < steps) setTimeout(tick, dur / steps); else dNum.textContent = delta; };
      tick();
    }
  }
  await _sleep(rm ? 0 : 700);
  T('#proofPunch', 'That green is earned — from real tests, not opinion.');
  if (btn) btn.disabled = false; _proofRunning = false;
}

// ---------- LIVE DUEL: one prompt → plain AI vs AI+memory, 5 hidden tests, counters tick live ----------
let _duelES = null, _duelRunning = false, _duelK = 5;
function runDuel() {
  if (_duelRunning) return; _duelRunning = true;
  const btn = $('#btnDuel'); if (btn) { btn.disabled = true; btn.textContent = 'running… (live, ~20s)'; }
  ['#duelPlainTests', '#duelMemTests', '#duelPlainCode', '#duelMemCode'].forEach(s => { const e = $(s); if (e) e.innerHTML = ''; });
  const sp = $('#duelPlainScore'), sm = $('#duelMemScore');
  if (sp) sp.textContent = '0/5'; if (sm) sm.textContent = '0/5';
  $('#duelPlain') && $('#duelPlain').classList.remove('win', 'lose');
  $('#duelMem') && $('#duelMem').classList.remove('win', 'lose');
  $('#duelPunch') && ($('#duelPunch').textContent = 'Same task, same model, temperature 0. The only difference is the lesson Regress-Guard recalls.');
  try { _duelES && _duelES.close(); } catch (_) {}
  const es = new EventSource('/duel?k=5'); _duelES = es;
  const finish = () => { try { es.close(); } catch (_) {} _duelES = null; _duelRunning = false;
    if (btn) { btn.disabled = false; btn.textContent = '▶ Run 5 live'; } };
  es.onmessage = (e) => {
    let m; try { m = JSON.parse(e.data); } catch (_) { return; }
    if (m.type === 'start') { _duelK = m.k || 5; }
    else if (m.type === 'round') {
      const pane = m.arm === 'plain' ? 'Plain' : 'Mem';
      if (m.code) { const c = $('#duel' + pane + 'Code'); if (c) c.innerHTML = proofHighlight(m.code); }
      const t = $('#duel' + pane + 'Tests'); if (t) t.insertAdjacentHTML('beforeend', `<span class="t ${m.passed ? 'g' : 'r'}">${m.passed ? '✓' : '✗'}</span>`);
      const s = $('#duel' + pane + 'Score'); if (s) s.textContent = `${m.green}/${_duelK}`;
    } else if (m.type === 'done') {
      finish();
      const pw = m.plain_green, mw = m.memory_green;
      $('#duelPlain') && $('#duelPlain').classList.add(pw >= mw ? 'win' : 'lose');
      $('#duelMem') && $('#duelMem').classList.add(mw >= pw ? 'win' : 'lose');
      const p = $('#duelPunch'); if (p) p.textContent = `Live: ${pw}/${m.k} without memory · ${mw}/${m.k} with the recalled lesson.`;
    }
  };
  es.onerror = () => { if (_duelRunning) { const p = $('#duelPunch'); if (p) p.textContent = 'the model calls are rate-limited or slow — try again in a moment (or use the 🏆 Proof replay).'; } finish(); };
}

// ---------- pattern crystallization (synthesis) ----------
async function runSynthesize() {
  const btn = $('#btnSynth'); btn.disabled = true; const was = btn.textContent; btn.textContent = 'synthesizing…';
  try {
    const r = await api('/synthesize', { method: 'POST' });
    if (!r.proposals || !r.proposals.length) logLine('✦ no cluster of ≥3 lessons in one scope yet — teach a few in the same scope', 'warn');
    else r.proposals.forEach(logSynthProposal);
  } catch (e) { logLine('✗ synthesize failed: ' + (e.message || ''), 'err'); }
  btn.disabled = false; btn.textContent = was;
}
function logSynthProposal(p) {
  const d = document.createElement('div'); d.className = 'synth-prop';
  d.innerHTML = `✦ meta from ${p.children.length} lessons in "${escapeHtml(p.scope)}": ${escapeHtml(p.lesson)} `;
  const b = document.createElement('button'); b.className = 'synth-accept'; b.textContent = 'accept';
  b.onclick = async () => {
    b.disabled = true;
    try {
      const m = await api('/synthesize/accept', json({ trigger: p.trigger, lesson: p.lesson, scope: p.scope, severity: p.severity, children: p.children }));
      logLine(`✓ crystallized → meta-lesson #${m.id} (starts at the 0.5 prior — earns confidence from real tests)`, 'ok');
      d.remove(); refresh(true);
    } catch (e) { logLine('✗ accept failed: ' + (e.message || ''), 'err'); b.disabled = false; }
  };
  d.appendChild(b); $('#log').appendChild(d); $('#log').scrollTop = $('#log').scrollHeight;
}

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
