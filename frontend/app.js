// Regress-Guard UI — vanilla ES module, no build step.
const $ = (s) => document.querySelector(s);
const api = (p, o) => fetch(p, o).then(r => r.ok ? r.json() : Promise.reject(r));

const state = {
  lessons: [], byId: new Map(), etag: -1, active: 0, filter: 'active',
  knownIds: new Set(), lastRendered: -2, lastFilter: null, react: null,
};

// ---------- Beta PDF sparkline (mathematically honest confidence) ----------
function betaSparkline(alpha, beta, w = 132, h = 62) {
  const a = Math.max(alpha, 0.001), b = Math.max(beta, 0.001);
  const N = 48, xs = [], ys = [];
  let ymax = 1e-9;
  for (let i = 0; i <= N; i++) {
    const x = (i + 0.5) / (N + 1);
    // unnormalized Beta shape: x^(a-1) * (1-x)^(b-1)  (log-space for stability)
    const logv = (a - 1) * Math.log(x) + (b - 1) * Math.log(1 - x);
    const v = Math.exp(logv);
    xs.push(x); ys.push(v); if (v > ymax) ymax = v;
  }
  const pts = xs.map((x, i) => `${(x * w).toFixed(1)},${(h - (ys[i] / ymax) * (h - 6) - 3).toFixed(1)}`);
  const mean = a / (a + b);
  const hue = Math.round(mean * 120);
  const col = `hsl(${hue} 70% 58%)`;
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <polyline points="${pts.join(' ')}" fill="none" stroke="${col}" stroke-width="2"/>
    <line x1="${(mean * w).toFixed(1)}" y1="2" x2="${(mean * w).toFixed(1)}" y2="${h}"
      stroke="${col}" stroke-dasharray="2 3" stroke-width="1" opacity=".6"/>
    <text x="${(mean * w).toFixed(1)}" y="${h - 1}" fill="${col}" font-size="9"
      font-family="monospace" text-anchor="middle">${mean.toFixed(2)}</text>
  </svg>`;
}

function hueFor(conf) { return `hsl(${Math.round(conf * 120)} 65% 52%)`; }
function rel(ts) {
  if (!ts) return '';
  const d = (Date.now() - Date.parse(ts)) / 1000;
  if (d < 60) return 'just now'; if (d < 3600) return `${Math.floor(d/60)}m ago`;
  if (d < 86400) return `${Math.floor(d/3600)}h ago`; return `${Math.floor(d/86400)}d ago`;
}

// ---------- card DOM ----------
function cardEl(l, pos) {
  const el = document.createElement('div');
  el.className = 'card' + (l.status === 'obsolete' ? ' obsolete' : '') + (l.pinned ? ' pinned' : '');
  el.dataset.id = l.id; el.dataset.hue = '1';
  el.style.setProperty('--pos', pos);
  el.style.setProperty('--tint', hueFor(l.confidence));
  const conf = (l.confidence ?? 0), fillW = Math.round(conf * 100);
  el.innerHTML = `
    <div class="face front">
      <div class="spine sev-${l.severity}"></div>
      <span class="pin">📌</span><span class="stamp">OBSOLETE</span>
      <div class="kicker">when: ${escapeHtml(l.trigger || '—')}</div>
      <div class="lesson">${escapeHtml(l.lesson)}</div>
      <div class="foot">
        <span class="chip">${escapeHtml(l.scope || 'general')}</span>
        <span class="conf">${conf.toFixed(2)}
          <span class="bar"><i style="width:${fillW}%;background:${hueFor(conf)}"></i></span></span>
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

// ---------- deck render (fanned stack) ----------
function posFor(offset) {
  if (offset === 0) return 'translateY(0) scale(1) rotateZ(0deg)';
  if (offset < 0) return `translateY(${offset * 46}px) scale(.95) rotateZ(0deg)`; // passed: slide up & out
  return `translateY(${offset * 12}px) scale(${(1 - offset * 0.04).toFixed(3)}) rotateZ(${(offset * 0.5).toFixed(2)}deg)`;
}
function render() {
  const deck = $('#deck'); deck.innerHTML = '';
  const L = state.lessons;
  $('#count').textContent = `${L.length ? state.active + 1 : 0} / ${L.length}`;
  if (!L.length) { deck.innerHTML = '<div class="empty">no lessons yet — teach one via the console, or run the demo.</div>'; return; }
  state.active = Math.max(0, Math.min(state.active, L.length - 1));
  L.forEach((l, i) => {
    const offset = i - state.active;
    const el = cardEl(l, posFor(offset));
    el.style.zIndex = 100 - Math.abs(offset);
    el.style.opacity = offset < 0 ? 0 : (offset > 3 ? 0 : 1);
    if (!state.knownIds.has(l.id)) el.classList.add('new');
    if (state.react && state.react.id === l.id) el.classList.add('react');
    deck.appendChild(el);
  });
  L.forEach(l => state.knownIds.add(l.id));
  state.react = null;
}

// ---------- data ----------
async function refresh(force = false) {
  let data;
  try { data = await api(`/ledger?status=${state.filter}`); } catch { return; }
  if (!force && data.etag === state.lastRendered && state.filter === state.lastFilter) return;
  // a freshly-added card should become the active one
  const newOnes = data.lessons.filter(l => !state.knownIds.has(l.id));
  state.lessons = data.lessons; state.byId = new Map(data.lessons.map(l => [l.id, l]));
  state.etag = data.etag; state.lastRendered = data.etag; state.lastFilter = state.filter;
  if (newOnes.length) state.active = data.lessons.findIndex(l => l.id === newOnes[newOnes.length - 1].id);
  render();
}

// ---------- console ----------
function logLine(text, cls = '') { const d = document.createElement('div');
  if (cls) d.className = cls; d.textContent = text; $('#log').appendChild(d);
  $('#log').scrollTop = $('#log').scrollHeight; }

async function runCommand(raw) {
  const s = raw.trim(); if (!s) return;
  logLine('» ' + s, 'echo');
  try {
    if (s.startsWith('/')) {
      const [cmd, ...rest] = s.slice(1).split(/\s+/);
      const id = parseInt(rest[0], 10);
      if (cmd === 'note') { const l = await api('/notes', json({ text: rest.join(' '), pinned: false }));
        logLine(`✓ learned #${l.id}`, 'ok'); }
      else if (cmd === 'pin') { await api(`/lessons/${id}/pin`, { method: 'POST' }); logLine(`✓ pinned #${id} → front`, 'ok'); }
      else if (cmd === 'unpin') { await api(`/lessons/${id}/unpin`, { method: 'POST' }); logLine(`✓ unpinned #${id}`, 'ok'); }
      else if (cmd === 'demote') { const l = await api(`/lessons/${id}/demote`, { method: 'POST' }); logLine(`✓ demoted #${id} → ${l.confidence.toFixed(2)}`, 'ok'); }
      else if (cmd === 'tombstone') { await api(`/lessons/${id}/tombstone`, { method: 'POST' }); logLine(`✓ tombstoned #${id}`, 'ok'); }
      else if (cmd === 'edit') { const m = s.match(/\/edit\s+(\d+)\s+(\w+)=(.+)/); if (!m) throw new Error('usage: /edit N field=value');
        await api(`/lessons/${m[1]}`, { method: 'PATCH', headers: hdr(), body: JSON.stringify({ [m[2]]: m[3] }) }); logLine(`✓ edited #${m[1]}`, 'ok'); }
      else throw new Error('unknown command: /' + cmd);
    } else {
      const text = s.replace(/^by the way,?\s*/i, '');
      if (state.agentStatus === 'running' || state.agentStatus === 'paused') {
        await api('/agent/inject', json({ text }));
        logLine('✓ note injected → agent interrupts & redoes with it', 'ok');
      } else {
        const l = await api('/notes', json({ text }));
        logLine(`✓ by-the-way note → lesson #${l.id} (agent will obey on next recall)`, 'ok');
      }
    }
  } catch (e) { logLine('✗ ' + (e.message || 'failed'), 'err'); }
  refresh(true);
}
const hdr = () => ({ 'Content-Type': 'application/json' });
const json = (o) => ({ method: 'POST', headers: hdr(), body: JSON.stringify(o) });

// ---------- chat / recall theater ----------
function bubble(who, text) { const d = document.createElement('div'); d.className = 'msg ' + who;
  d.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`; $('#thread').appendChild(d);
  $('#thread').scrollTop = $('#thread').scrollHeight; return d; }

async function ask() {
  const inp = $('#ask'), q = inp.value.trim(); if (!q) return;
  inp.value = ''; $('#send').disabled = true;
  bubble('user', q);
  const thinking = bubble('agent', '…');
  try {
    const r = await api('/chat', json({ message: q }));
    thinking.innerHTML = `<div class="who">agent</div>${escapeHtml(r.reply)}`;
    showRecalled(r.recalled);
  } catch { thinking.innerHTML = `<div class="who">agent</div>(error contacting agent)`; }
  $('#send').disabled = false;
}
function showRecalled(ids) {
  const strip = $('#recall');
  if (!ids || !ids.length) { strip.innerHTML = '<span style="color:var(--ink-faint)">no lessons recalled for that</span>'; return; }
  strip.innerHTML = `<span>recalled ${ids.length}:</span>`;
  ids.forEach(id => { const l = state.byId.get(id); if (!l) return;
    const s = document.createElement('span'); s.className = 'lz'; s.textContent = `#${id}`;
    s.title = l.lesson; s.onclick = () => jumpTo(id); strip.appendChild(s); });
  ids.forEach(id => flashCard(id, 'highlight'));
}
function jumpTo(id) { const i = state.lessons.findIndex(l => l.id === id); if (i >= 0) { state.active = i; render(); flashCard(id, 'highlight'); } }
function flashCard(id, cls) { const el = document.querySelector(`.card[data-id="${id}"]`);
  if (el) { el.classList.add(cls); setTimeout(() => el.classList.remove(cls), 1400); } }

// ---------- A/B pills ----------
async function loadAB() {
  try { const ab = await api('/ab'); if (ab.available === false) return;
    const a = ab.arm_a_no_memory, b = ab.arm_b_with_memory;
    $('#ab').innerHTML = `<span class="pill a">A · no memory ${a.green}/${a.k}</span>
      <span class="pill b">B · with memory ${b.green}/${b.k}</span>`;
  } catch {}
}

// ---------- agent loop ----------
function setAgentStatus(s) {
  state.agentStatus = s;
  const el = $('#agentStatus'); el.textContent = s; el.className = 'status ' + s;
}
function highlightCode(code) {
  return escapeHtml(code)
    .replace(/(tenant_id)/g, '<span class="filter">$1</span>')
    .replace(/(all_orders\(\)(?!\s*if))/g, '<span class="leak">$1</span>');
}
function renderAttempt(step, code, passed, recalled) {
  const badge = passed ? '<span class="badge green">✓ TEST GREEN</span>'
                       : '<span class="badge red">✗ TEST RED</span>';
  const mem = recalled && recalled.length ? `recalled #${recalled.join(', #')}` : 'no memory recalled';
  $('#agentPanel').innerHTML =
    `<div class="attempt">${badge}<pre>${highlightCode(code || '')}</pre></div>
     <div class="agent-meta">attempt ${step} · ${mem} · hidden test = tenant isolation</div>`;
}
function agentThinking() {
  $('#agentPanel').innerHTML = `<div class="attempt"><span class="badge think">… writing</span>
    <pre>agent is drafting get_orders …</pre></div>`;
}
function onAgentStep(m) {
  if (m.status) setAgentStatus(m.status);
  const ph = m.phase;
  if (ph === 'recall') { agentThinking(); if (m.recalled) { showRecalled(m.recalled); } }
  else if (ph === 'result') renderAttempt(m.step, m.code, m.passed, m.recalled);
  else if (ph === 'interrupted') logLine('↻ agent interrupted → re-planning with your note', 'echo');
  else if (ph === 'note') logLine(`⇢ agent absorbed note → lesson #${m.lesson_id}`, 'ok');
  else if (ph === 'stopped') $('#agentPanel').innerHTML = '<div class="agent-empty">agent stopped.</div>';
}
async function agentCmd(action) { try { await api('/agent/' + action, { method: 'POST' }); } catch {} }

// ---------- live: SSE + poll fallback ----------
function live() {
  try {
    const es = new EventSource('/events');
    es.onmessage = (e) => { const m = JSON.parse(e.data);
      if (m.type === 'ledger_changed') { state.react = { id: m.lesson_id, action: m.action }; refresh(true); }
      else if (m.type === 'agent_step') onAgentStep(m); };
    es.onerror = () => {};
  } catch {}
  setInterval(() => refresh(false), 2000); // fallback + safety net
}

// ---------- wire ----------
$('#cmd').addEventListener('keydown', e => { if (e.key === 'Enter') { runCommand(e.target.value); e.target.value = ''; } });
$('#ask').addEventListener('keydown', e => { if (e.key === 'Enter') ask(); });
$('#send').addEventListener('click', ask);
$('#prev').addEventListener('click', () => { state.active = Math.max(0, state.active - 1); render(); });
$('#next').addEventListener('click', () => { state.active = Math.min(state.lessons.length - 1, state.active + 1); render(); });
$('#filter').addEventListener('change', e => { state.filter = e.target.value; refresh(true); });
document.addEventListener('keydown', e => {
  if (document.activeElement.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') $('#prev').click(); if (e.key === 'ArrowRight') $('#next').click();
});

document.querySelectorAll('[data-agent]').forEach(b =>
  b.addEventListener('click', () => agentCmd(b.dataset.agent)));

refresh(true); loadAB(); live();
api('/agent/status').then(s => setAgentStatus(s.status)).catch(() => {});
