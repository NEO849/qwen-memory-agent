// Regress-Guard UI — vanilla ES module, no build step.
// Design law: one field -> one channel. lifecycle=card body · confidence=meter · severity=spine.
const $ = (s) => document.querySelector(s);
const api = (p, o) => fetch(p, o).then(r => r.ok ? r.json() : Promise.reject(r));

const state = {
  lessons: [], byId: new Map(), etag: -1, active: 0, filter: 'active',
  knownIds: new Set(), lastRendered: -2, lastFilter: null, react: null,
  fanned: false, agentStatus: 'idle',
};

// ---------- Beta PDF sparkline (mathematically honest confidence) ----------
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
// pastel confidence hue (same honest h=conf*120 math, calmer skin)
function hueFor(conf) { return `hsl(${Math.round(conf * 120)} 60% 68%)`; }
const SRC_COLOR = { human: '#B9A6E8', 'human-distill': '#B9A6E8', 'agent-distill': '#7FB8D8', import: '#93A0B5' };
function rel(ts) { if (!ts) return ''; const d = (Date.now() - Date.parse(ts)) / 1000;
  if (d < 60) return 'just now'; if (d < 3600) return `${Math.floor(d/60)}m ago`;
  if (d < 86400) return `${Math.floor(d/3600)}h ago`; return `${Math.floor(d/86400)}d ago`; }
function ageMs(l) { return Date.now() - Date.parse(l.updated_at || l.created_at || 0); }

// lifecycle bucket (the ONLY full-card colour). At most a few cards are coloured.
function lifecycle(l, agingThreshold) {
  if (l.status === 'obsolete') return 'obsolete';
  if (!state.knownIds.has(l.id) || ageMs(l) < 120000) return 'life-new';   // fresh (<2 min or unseen)
  if (agingThreshold != null && Date.parse(l.updated_at || l.created_at) <= agingThreshold) return 'life-age';
  return '';   // settled = neutral default
}

// ---------- card DOM ----------
function cardEl(l, pos, lifeClass) {
  const el = document.createElement('div');
  el.className = 'card' + (lifeClass ? ' ' + lifeClass : '') + (l.status === 'obsolete' ? ' obsolete' : '') + (l.pinned ? ' pinned' : '');
  el.dataset.id = l.id;
  el.style.setProperty('--pos', pos);
  const conf = l.confidence ?? 0;
  el.innerHTML = `
    <div class="face front">
      <div class="spine sev-${l.severity}"></div>
      <span class="pin">📌</span><span class="stamp">OBSOLETE</span>
      <div class="kicker">
        <span class="src" style="background:${SRC_COLOR[l.source] || '#93A0B5'}" title="source: ${l.source}"></span>
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
      <h4>confidence · Beta(${l.alpha.toFixed(0)}, ${l.beta.toFixed(0)})</h4>
      <div class="spark">${betaSparkline(l.alpha, l.beta)}</div>
      <div class="meta">
        <div>scope: ${escapeHtml(l.scope || 'general')} · sev: ${l.severity}</div>
        <div>source: ${l.source} · rev ${l.rev}</div>
        <div>learned ${rel(l.created_at)} · updated ${rel(l.updated_at)}</div>
      </div>
    </div>`;
  el.addEventListener('click', () => el.classList.toggle('flipped'));
  return el;
}
function escapeHtml(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// ---------- deck: browsable stack (active on top, peeks fanned behind) ----------
function posFor(r) {
  if (r === 0) return 'translateY(0) scale(1) rotateZ(0deg)';
  const off = state.fanned ? 40 : 24;
  return `translateY(${r*off}px) scale(${(1 - r*0.04).toFixed(3)}) rotateZ(${(r*0.6).toFixed(2)}deg)`;
}
const PEEK_OPACITY = [1, 0.5, 0.28, 0.12];
function render() {
  const deck = $('#deck'); deck.innerHTML = '';
  const L = state.lessons, n = L.length;
  $('#count').textContent = `${n ? state.active + 1 : 0} / ${n}`;
  renderTrack(n);
  if (!n) { deck.innerHTML = '<div class="empty">No lessons yet — teach one with “+ Teach a rule”, or run the agent.</div>'; return; }
  state.active = ((state.active % n) + n) % n;
  // aging = oldest ~25% by updated_at
  const times = L.map(x => Date.parse(x.updated_at || x.created_at)).sort((a,b)=>a-b);
  const agingThreshold = times.length >= 4 ? times[Math.floor(times.length*0.25)-0] : null;
  const order = [];
  for (let r = 0; r < n; r++) order.push({ l: L[(state.active + r) % n], r });   // 0=active, then behind
  order.reverse().forEach(({ l, r }) => {                                          // paint back-to-front
    const el = cardEl(l, posFor(r), lifecycle(l, agingThreshold));
    el.style.zIndex = 100 - r;
    el.style.opacity = r < PEEK_OPACITY.length ? PEEK_OPACITY[r] : 0;
    el.style.pointerEvents = r === 0 ? 'auto' : 'none';
    if (r === 0 && !state.knownIds.has(l.id)) el.classList.add('enter');
    if (r === 0 && state.react && state.react.id === l.id) el.classList.add('react');
    deck.appendChild(el);
  });
  L.forEach(l => state.knownIds.add(l.id));
  state.react = null;
}
function renderTrack(n) {
  const t = $('#track'); const m = Math.min(n, 24); let h = '';
  for (let i = 0; i < m; i++) h += `<i class="${i === state.active ? 'at' : ''}"></i>`;
  t.innerHTML = h;
}

// ---------- data ----------
async function refresh(force = false) {
  let data; try { data = await api(`/ledger?status=${state.filter}`); } catch { return; }
  if (!force && data.etag === state.lastRendered && state.filter === state.lastFilter) return;
  const fresh = data.lessons.filter(l => !state.knownIds.has(l.id));
  state.lessons = data.lessons; state.byId = new Map(data.lessons.map(l => [l.id, l]));
  state.etag = data.etag; state.lastRendered = data.etag; state.lastFilter = state.filter;
  if (fresh.length) state.active = data.lessons.findIndex(l => l.id === fresh[fresh.length - 1].id);
  render();
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
      if (cmd === 'note') { const l = await api('/notes', json({ text: rest.join(' ') })); logLine(`✓ learned #${l.id}`, 'ok'); }
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
      } else { const l = await api('/notes', json({ text })); logLine(`✓ by-the-way note → lesson #${l.id} (agent obeys on next recall)`, 'ok'); }
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
function bubble(who, text) { const d = document.createElement('div'); d.className = 'msg ' + who;
  d.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`; $('#thread').appendChild(d); $('#thread').scrollTop = $('#thread').scrollHeight; return d; }
async function ask() {
  const inp = $('#ask'), q = inp.value.trim(); if (!q) return;
  inp.value = ''; $('#send').disabled = true; bubble('user', q);
  const t = bubble('agent', '…');
  try { const r = await api('/chat', json({ message: q })); t.innerHTML = `<div class="who">agent</div>${escapeHtml(r.reply)}`; showRecalled(r.recalled); }
  catch { t.innerHTML = `<div class="who">agent</div>(error contacting agent)`; }
  $('#send').disabled = false;
}
function showRecalled(ids) {
  const strip = $('#recall');
  if (!ids || !ids.length) { strip.innerHTML = '<span style="color:var(--ink-faint)">no lessons recalled for that</span>'; return; }
  strip.innerHTML = `<span>recalled ${ids.length}:</span>`;
  ids.forEach(id => { const l = state.byId.get(id); if (!l) return;
    const s = document.createElement('span'); s.className = 'lz'; s.textContent = `#${id}`; s.title = l.lesson; s.onclick = () => jumpTo(id); strip.appendChild(s); });
  ids.forEach(id => flashCard(id, 'highlight'));
}
function jumpTo(id) { const i = state.lessons.findIndex(l => l.id === id); if (i >= 0) { state.active = i; render(); flashCard(id, 'highlight'); } }
function flashCard(id, cls) { const el = document.querySelector(`.card[data-id="${id}"]`); if (el) { el.classList.add(cls); setTimeout(() => el.classList.remove(cls), 1400); } }

async function loadAB() {
  try { const ab = await api('/ab'); if (ab.available === false) return;
    const a = ab.arm_a_no_memory, b = ab.arm_b_with_memory;
    $('#ab').innerHTML = `<span class="pill a">A · no memory ${a.green}/${a.k}</span><span class="pill b">B · with memory ${b.green}/${b.k}</span>`;
  } catch {}
}

// ---------- live ----------
function live() {
  try { const es = new EventSource('/events');
    es.onmessage = (e) => { const m = JSON.parse(e.data);
      if (m.type === 'ledger_changed') { state.react = { id: m.lesson_id, action: m.action }; refresh(true); }
      else if (m.type === 'agent_step') onAgentStep(m); };
    es.onerror = () => {};
  } catch {}
  setInterval(() => refresh(false), 2000);
}

// ---------- wire ----------
$('#cmd').addEventListener('keydown', e => { if (e.key === 'Enter') { runCommand(e.target.value); e.target.value = ''; } });
document.querySelectorAll('#acts [data-cmd]').forEach(b => b.addEventListener('click', () => {
  const c = b.dataset.cmd, pre = { note: 'by the way, ', pin: '/pin ', demote: '/demote ', tombstone: '/tombstone ', revise: '/revise ' }[c];
  const i = $('#cmd'); i.value = pre; i.focus();
}));
$('#ask').addEventListener('keydown', e => { if (e.key === 'Enter') ask(); });
$('#send').addEventListener('click', ask);
$('#prev').addEventListener('click', () => { state.active--; render(); });
$('#next').addEventListener('click', () => { state.active++; render(); });
document.querySelectorAll('#filter [data-f]').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#filter [data-f]').forEach(x => x.classList.toggle('on', x === b));
  state.filter = b.dataset.f; refresh(true);
}));
document.querySelectorAll('[data-agent]').forEach(b => b.addEventListener('click', () => agentCmd(b.dataset.agent)));
const dw = document.querySelector('.deck-wrap');
dw.addEventListener('mouseenter', () => { state.fanned = true; render(); });
dw.addEventListener('mouseleave', () => { state.fanned = false; render(); });
document.addEventListener('keydown', e => {
  if (document.activeElement.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') $('#prev').click();
  else if (e.key === 'ArrowRight') $('#next').click();
  else if (e.key === ' ') { const c = document.querySelector('.card'); if (c) { c.classList.toggle('flipped'); e.preventDefault(); } }
});

refresh(true); loadAB(); live();
api('/agent/status').then(s => setAgentStatus(s.status)).catch(() => {});
