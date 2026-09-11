'use strict';
// Dashboard client. All text is inserted with textContent (never innerHTML) so model output and
// task text cannot inject markup. Animation and notification failures are caught and ignored:
// they can never affect the controller, which runs in a separate process.

const S = { me: null, overview: null, tasks: [], selected: null, detail: null, events: [], cursor: 0,
  lastBeat: 0, es: null, refreshTimer: null, note: null, notifyOk: false, officeProject: '', preview: null };
const MAX_EVENTS = 300;
const $ = (id) => document.getElementById(id);
const APP_BASE = location.pathname.replace(/\/[^/]*$/, '').replace(/\/$/, '');
const appUrl = (path) => APP_BASE + (path.startsWith('/') ? path : '/' + path);

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    n.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return n;
}
const statusChip = (s) => el('span', { class: 'status s-' + s }, (s || 'unknown').replaceAll('_', ' '));
const when = (iso) => { if (!iso) return 'never'; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString(); };
const short = (id) => (id || '').slice(0, 8);

async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {}, credentials: 'same-origin' };
  if (opts.body !== undefined) {
    init.method = 'POST';
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(opts.body);
  }
  if (init.method === 'POST' && S.me && S.me.csrf) init.headers['X-CSRF-Token'] = S.me.csrf;
  let res;
  try { res = await fetch(appUrl(path), init); }
  catch (e) { showBanner('Cannot reach the assistant server. Showing last known data.'); throw e; }
  if (res.status === 401 && path !== '/api/login') { showLogin(); throw new Error('Sign in required'); }
  const type = res.headers.get('Content-Type') || '';
  const data = type.includes('json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
  return data;
}

function showBanner(text) { const b = $('banner'); b.textContent = text; b.hidden = !text; }
function toast(err) { showBanner(err instanceof Error ? err.message : String(err)); setTimeout(() => showBanner(''), 6000); }

// ---------------------------------------------------------------- auth
function showLogin() {
  $('app').hidden = true; $('login-view').hidden = false;
  if (S.es) { S.es.close(); S.es = null; }
}
$('login-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  try {
    await api('/api/login', { body: { user: f.get('user'), password: f.get('password') } });
    ev.target.reset(); $('login-error').textContent = '';
    await boot();
  } catch (e) { $('login-error').textContent = e.message; }
});
$('btn-logout').addEventListener('click', async () => { try { await api('/api/logout', { body: {} }); } finally { location.reload(); } });

// ---------------------------------------------------------------- dialogs
function ask(title, text, { input = false, placeholder = '', okLabel = 'OK', danger = false, optional = false } = {}) {
  return new Promise((resolve) => {
    const d = $('dlg');
    $('dlg-title').textContent = title; $('dlg-text').textContent = text;
    const i = $('dlg-input'); i.hidden = !input; i.value = ''; i.placeholder = placeholder; i.required = input && !optional;
    $('dlg-ok').textContent = okLabel; $('dlg-ok').className = danger ? 'danger' : 'primary';
    d.onclose = () => resolve(d.returnValue === 'ok' ? (input ? i.value.trim() : true) : null);
    d.showModal();
    (input ? i : $('dlg-ok')).focus();
  });
}
async function showText(title, path) {
  try {
    const body = await api(path);
    $('viewer-title').textContent = title; $('viewer-body').textContent = body;
    $('viewer').showModal();
  } catch (e) { toast(e); }
}

// ---------------------------------------------------------------- tabs
const PAGE_COPY = {
  office: ['Office', 'Your specialists, live. Select anyone to inspect their work.'],
  tasks: ['Tasks', 'Plans, assignments, review evidence and conversations.'],
  inbox: ['Needs you', 'Questions, approvals and blocked work waiting for you.'],
  knowledge: ['Knowledge', 'Search, review and maintain your assistant’s scoped memory.'],
  system: ['System', 'Health, cloud routes, permissions, backups and audit history.']
};
document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('.tabs button').forEach((x) => x.toggleAttribute('aria-current', x === b));
  document.querySelectorAll('.tab').forEach((t) => { t.hidden = t.id !== 'tab-' + b.dataset.tab; });
  $('page-title').textContent = PAGE_COPY[b.dataset.tab][0];
  $('page-subtitle').textContent = PAGE_COPY[b.dataset.tab][1];
  if (b.dataset.tab === 'knowledge') loadNotes();
  if (b.dataset.tab === 'system') renderSystem();
  if (b.dataset.tab === 'inbox') loadInbox();
}));

// ---------------------------------------------------------------- overview / header
function pill(text, cls, title) { return el('span', { class: 'pill ' + (cls || ''), title }, text); }
function renderHeader() {
  const o = S.overview; if (!o) return;
  const pills = $('pills'); pills.replaceChildren();
  pills.append(pill('Runner: ' + o.runner, o.runner === 'running' ? 'ok' : 'bad', 'Heartbeat ' + when(o.runner_heartbeat)));
  pills.append(pill(o.paused ? 'Paused' : 'Active', o.paused ? 'warn' : 'ok'));
  if (o.gaming) pills.append(pill('Gaming mode', 'warn', 'No new GPU work'));
  const h = Object.fromEntries((o.health || []).map((x) => [x.name, x]));
  for (const [key, label] of [['endpoint.gpu', 'GPU tunnel'], ['endpoint.cpu', 'Server model'], ['cloud.catalog', 'Cloud'], ['disk', 'Disk'], ['backup', 'Backup']]) {
    if (h[key]) pills.append(pill(label + (h[key].ok ? ' ok' : ' problem'), h[key].ok ? 'ok' : 'bad',
      h[key].detail + ' — checked ' + when(h[key].checked) + ', last ok ' + when(h[key].last_ok)));
  }
  $('btn-pause').textContent = o.paused ? 'Resume' : 'Pause';
  $('btn-gaming').textContent = o.gaming ? 'End gaming mode' : 'Gaming mode';
  $('mail-count').textContent = o.mailbox_open;
  $('nav-mail-count').textContent = o.mailbox_open;
  $('nav-mail-count').dataset.zero = String(!o.mailbox_open);
  const active = o.workforce.filter((w) => ['working', 'waiting', 'blocked'].includes(w.state)).length;
  $('nav-office-count').textContent = active;
  $('nav-office-count').dataset.zero = String(!active);
  const problems = (o.health || []).filter((h) => !h.ok).length + (o.runner === 'running' ? 0 : 1);
  $('nav-system-count').textContent = problems;
  $('nav-system-count').dataset.zero = String(!problems);
  const sideHealth = $('sidebar-health');
  sideHealth.className = 'sidebar-health ' + (o.runner === 'running' && !problems ? 'ok' : problems ? 'bad' : '');
  sideHealth.querySelector('strong').textContent = o.runner === 'running' ? (problems ? 'Attention needed' : 'Working normally') : 'Runner ' + o.runner;
  sideHealth.querySelector('small').textContent = o.runner_heartbeat ? 'heartbeat ' + when(o.runner_heartbeat) : 'no heartbeat received';
  $('office').classList.toggle('gaming', !!o.gaming);
  document.title = (o.mailbox_open ? '(' + o.mailbox_open + ') ' : '') + "Kort's Assistant";
  renderOffice();
}

$('btn-pause').addEventListener('click', async () => {
  const paused = S.overview && S.overview.paused;
  try { await api(paused ? '/api/control/resume' : '/api/control/pause', { body: {} }); await refreshOverview(); }
  catch (e) { toast(e); }
});
$('btn-gaming').addEventListener('click', async () => {
  const on = !(S.overview && S.overview.gaming);
  if (on) {
    const r = await ask('Gaming mode', 'New GPU work will stop immediately. If inference is already running, the assistant will keep the GPU reserved until that request ends, then unload the model safely.',
      { okLabel: 'Start gaming mode' });
    if (!r) return;
  }
  try {
    const rep = await api('/api/control/gaming', { body: { on, cancel_active: false } });
    toast(on ? 'Gaming mode on — VRAM: ' + rep.vram : (rep.endpoint_ok ? 'GPU work may resume' : 'Gaming mode off, but GPU endpoint is not answering'));
    await refreshOverview();
  } catch (e) { toast(e); }
});
$('btn-notify').addEventListener('click', async () => {
  try {
    if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission();
    S.notifyOk = 'Notification' in window && Notification.permission === 'granted';
  } catch (_) { /* notifications are optional */ }
  document.querySelector('[data-tab=inbox]').click();
});

// ---------------------------------------------------------------- tasks
async function refreshTasks() {
  const data = await api('/api/tasks'); S.tasks = data.tasks; renderTaskList();
  if (S.selected) await loadDetail(S.selected, true);
}
function renderTaskList() {
  const filter = $('filter-project').value; const ul = $('task-list'); ul.replaceChildren();
  for (const t of S.tasks.filter((x) => !filter || x.project === filter)) {
    const li = el('li', { tabindex: 0, 'aria-current': String(t.id === S.selected), onclick: () => loadDetail(t.id),
      onkeydown: (e) => { if (e.key === 'Enter') loadDetail(t.id); } },
      el('div', {}, statusChip(t.status), el('span', { class: 'muted' }, t.project + (t.subproject ? '/' + t.subproject : ''))),
      el('div', {}, t.goal.slice(0, 140)),
      t.waiting.length ? el('div', { class: 'muted' }, 'waiting: ' + t.waiting.join(', ')) : null,
      t.retry && t.retry.next_at ? el('div', { class: 'muted' }, 'retry #' + t.retry.count + ' after ' + when(t.retry.next_at)) : null);
    ul.append(li);
  }
  if (!ul.children.length) ul.append(el('li', { class: 'muted' }, 'No tasks yet.'));
}
$('filter-project').addEventListener('change', renderTaskList);

$('add-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  const after = String(f.get('after') || '').split(',').map((s) => s.trim()).filter(Boolean);
  try {
    const r = await api('/api/tasks', { body: { project: f.get('project'), subproject: f.get('subproject'), goal: f.get('goal'), after, confirm_plan: f.get('confirm_plan') === 'on' } });
    ev.target.goal.value = ''; ev.target.after.value = '';
    S.selected = r.id; await refreshTasks();
  } catch (e) { toast(e); }
});

async function loadDetail(id, quiet) {
  S.selected = id;
  try { S.detail = await api('/api/tasks/' + id); renderDetail(); renderTaskList(); }
  catch (e) { if (!quiet) toast(e); }
}

async function act(path, body, confirmText) {
  if (confirmText && !(await ask('Please confirm', confirmText, { okLabel: 'Confirm' }))) return;
  try { await api(path, { body: body || {} }); await refreshTasks(); await refreshOverview(); }
  catch (e) { toast(e); }
}

function renderDetail() {
  const t = S.detail; const box = $('task-detail'); box.replaceChildren();
  if (!t) return;
  const base = '/api/tasks/' + t.id;
  box.append(el('h2', {}, statusChip(t.status), ' ', t.project + (t.subproject ? '/' + t.subproject : ''), el('span', { class: 'muted' }, '  #' + short(t.id))));
  box.append(el('p', {}, t.goal));
  const controls = el('div', { class: 'row' });
  if (['planned', 'working', 'awaiting_cloud', 'waiting_dependency', 'blocked', 'draft_ready'].includes(t.status))
    controls.append(el('button', { class: 'danger', onclick: () => act(base + '/cancel', {}, 'Cancel this task? Work already produced is kept as evidence.') }, 'Cancel'));
  if (['blocked', 'awaiting_cloud'].includes(t.status)) controls.append(el('button', { onclick: () => act(base + '/retry') }, 'Retry'));
  if (t.status === 'draft_ready') {
    controls.append(el('button', { class: 'primary', onclick: async () => {
      const note = await ask('Approve result', 'Approving records your decision only. Nothing is merged, deployed or published automatically.', { input: true, placeholder: 'optional note', okLabel: 'Approve', optional: true });
      if (note !== null) act(base + '/approve', { note }); } }, 'Approve'));
    controls.append(el('button', { class: 'danger', onclick: async () => {
      const note = await ask('Reject result', 'Why is it rejected?', { input: true, okLabel: 'Reject', danger: true });
      if (note) act(base + '/reject', { note }); } }, 'Reject'));
  }
  if (t.status === 'owner_approved' && t.has_code && S.me.owner)
    controls.append(el('button', { onclick: async () => {
      try { const r = await api(base + '/export', { body: {} });
        toast(r.applies ? 'Patch exported to the private exports folder; rollback point ' + short(r.base) : 'Exported, but the source changed and the patch no longer applies — create a new task.');
        loadDetail(t.id); } catch (e) { toast(e); } } }, 'Export patch'));
  if (t.status === 'awaiting_plan_approval') {
    controls.append(el('button', { class: 'primary', onclick: () => act(base + '/plan', { approve: true }) }, 'Approve plan'));
    controls.append(el('button', { onclick: async () => { const n = await ask('Change the plan', 'What should be different?', { input: true, okLabel: 'Re-plan' });
      if (n) act(base + '/plan', { approve: false, note: n }); } }, 'Change plan'));
  }
  box.append(controls);
  if (t.questions.length) box.append(el('div', { class: 'job' }, el('h4', {}, 'The orchestrator needs your answer'),
    el('ul', {}, t.questions.map((q) => el('li', {}, q))), el('p', { class: 'muted' }, 'Reply in the conversation below.')));
  if (t.assumptions.length) box.append(el('details', { open: t.status === 'awaiting_plan_approval' }, el('summary', {}, 'Assumptions'),
    el('ul', {}, t.assumptions.map((a) => el('li', {}, a)))));
  const kv = el('div', { class: 'kv' });
  const add = (k, v) => { if (v !== null && v !== undefined && v !== '') kv.append(el('span', { class: 'muted' }, k), el('span', {}, v)); };
  add('Updated', when(t.updated));
  add('Planned by', t.plan_route ? t.plan_route.provider + ' / ' + t.plan_route.model : null);
  if (t.export) add('Exported', when(t.export.at) + ' · base ' + short(t.export.base) + ' → ' + short(t.export.head) + (t.export.applies ? ' · applies cleanly' : ' · CONFLICT with current source'));
  add('Blocker', t.blocker); add('Last error', t.last_error);
  if (t.owner_decision) add('Your decision', (t.owner_decision.approved ? 'Approved' : 'Rejected') + ' ' + when(t.owner_decision.at) + (t.owner_decision.note ? ' — ' + t.owner_decision.note : ''));
  if (t.retry && t.retry.next_at) add('Next retry', when(t.retry.next_at) + ' (attempt ' + t.retry.count + ')');
  box.append(kv);
  if (t.dependencies.length) {
    box.append(el('h3', {}, 'Depends on'));
    box.append(el('ul', {}, t.dependencies.map((d) => el('li', {}, statusChip(d.status), ' #' + short(d.id) + ' ', d.goal || ''))));
  }
  box.append(el('h3', {}, 'Plan and assignments'));
  const jobs = el('div', { class: 'jobs' });
  for (const j of t.job_list) {
    const card = el('div', { class: 'job' },
      el('h4', {}, statusChip(j.status), ' ', j.id, ' → ', j.worker_name),
      el('div', { class: 'muted' }, 'attempts ' + j.attempts + (j.max_attempts ? ' / ' + j.max_attempts : '') +
        (j.depends_on.length ? ' · after ' + j.depends_on.join(', ') : '') + (j.waiting ? ' · waiting: ' + j.waiting : '') +
        (j.execution_route ? ' · ran on ' + [j.execution_route.provider, j.execution_route.model, j.execution_route.device].filter(Boolean).join(' / ') : '')),
      el('p', {}, j.brief),
      el('details', {}, el('summary', {}, 'Acceptance criteria'), el('ul', {}, j.acceptance.map((a) => el('li', {}, a)))));
    if (j.reason || j.last_error) card.append(el('p', { class: 'error' }, 'Failure: ' + (j.reason || j.last_error)));
    if (j.review) {
      const r = j.review;
      card.append(el('details', { open: j.status === 'repair_requested' },
        el('summary', {}, 'Review evidence (' + (r.approved ? 'accepted' : 'changes requested') + ', ' + j.review_rounds + ' round(s))' +
          (j.review_route ? ' — ' + j.review_route.model : '')),
        el('ul', { class: 'checks' }, r.checks.map((c) => el('li', { class: c.passed ? 'pass' : 'fail' }, c.criterion + ': ' + c.evidence))),
        r.cause ? el('p', {}, 'Cause: ' + r.cause) : null,
        r.repairs.length ? el('p', {}, 'Requested repairs: ' + r.repairs.join('; ')) : null));
    }
    if (j.test_results.length) card.append(el('details', {}, el('summary', {}, 'Checks ' + (j.checks_passed ? 'passed' : 'did not all pass')),
      j.test_results.map((r) => el('div', {}, (r.passed ? '✔ ' : '✘ ') + r.command, el('pre', {}, r.output)))));
    if (j.owner_instructions.length) card.append(el('p', { class: 'muted' }, 'Your repair notes: ' + j.owner_instructions.map((o) => o.text).join(' | ')));
    const row = el('div', { class: 'row' });
    if (j.has_artifact) {
      row.append(el('button', { onclick: () => showText(j.id + ' artifact', base + '/artifact/' + j.id) }, 'Preview'));
      row.append(el('a', { class: 'btn', href: appUrl(base + '/artifact/' + j.id + '?download=1'), download: '' }, 'Download'));
    }
    if (['draft_ready', 'blocked', 'working', 'owner_rejected'].includes(t.status) && j.status !== 'verified_candidate')
      row.append(el('button', { onclick: async () => {
        const text = await ask('Request a repair', 'Tell the ' + j.worker_name + ' exactly what to change. The reviewer checks the result again.', { input: true, okLabel: 'Send repair' });
        if (text) act(base + '/repair', { job: j.id, instructions: text }); } }, 'Request repair'));
    card.append(row);
    jobs.append(card);
  }
  if (!t.job_list.length) jobs.append(el('p', { class: 'muted' }, 'No plan yet.'));
  box.append(jobs);
  if (t.invocations.length) {
    box.append(el('h3', {}, 'Cloud call records'));
    box.append(el('table', { class: 'tbl' }, el('tr', {}, ['When', 'Purpose', 'Model', 'Served by', 'Cost evidence', 'Outcome'].map((h) => el('th', {}, h))),
      t.invocations.map((i) => el('tr', {}, el('td', {}, when(i.at)), el('td', {}, i.purpose || ''), el('td', {}, i.requested_model),
        el('td', {}, (i.actual_models || []).join(', ')),
        el('td', {}, i.cost_evidence ? (i.cost_evidence.delta !== undefined ? 'usage Δ ' + i.cost_evidence.delta : (i.cost_evidence.method || i.cost_evidence.reason || '')) : ''),
        el('td', {}, i.outcome)))));
  }
  box.append(el('h3', {}, 'Conversation'));
  const convo = el('div', { class: 'convo', id: 'convo' }, el('p', { class: 'muted' }, 'Loading…'));
  const input = el('textarea', { rows: 2, placeholder: t.status === 'needs_input' ? 'Answer the questions…' : 'Message about this task', 'aria-label': 'Message' });
  const file = el('input', { type: 'file', accept: '.txt,.md,.csv,.json,.png,.jpg,.jpeg,.webp', 'aria-label': 'Attach a file', class: 'auto' });
  box.append(convo, input, el('div', { class: 'row' },
    el('button', { class: 'primary', onclick: async () => {
      if (!input.value.trim()) return;
      try { await api(base + '/messages', { body: { text: input.value } }); input.value = ''; await refreshTasks(); } catch (e) { toast(e); } } }, 'Send'),
    file, el('button', { onclick: async () => {
      const f = file.files[0]; if (!f) return;
      if (f.size > 2_000_000) return toast('Attachments are limited to 2 MB');
      const b64 = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1]); r.onerror = rej; r.readAsDataURL(f); });
      try { await api(base + '/attachments', { body: { name: f.name, content: b64 } }); file.value = ''; loadConversation(t.id); toast('Attached ' + f.name); } catch (e) { toast(e); } } }, 'Attach')));
  loadConversation(t.id);
  box.append(el('h3', {}, 'Timeline'));
  box.append(el('ol', { class: 'feed', reversed: true }, t.events.map((e) => el('li', {}, when(e.at) + ' — ' + e.message + (e.worker ? ' (' + e.worker + ')' : '')))));
}

async function loadConversation(id) {
  try {
    const { messages, attachments } = await api('/api/tasks/' + id + '/messages');
    const c = $('convo'); if (!c || S.selected !== id) return;
    c.replaceChildren(...messages.map((m) => el('div', { class: 'msg ' + m.role },
      el('div', { class: 'muted' }, (m.role === 'owner' ? (m.author || 'you') : 'assistant') + ' · ' + when(m.at)), el('div', { class: 'msgtext' }, m.text))));
    if (!messages.length) c.append(el('p', { class: 'muted' }, 'No messages yet.'));
    if (attachments.length) c.append(el('p', { class: 'muted' }, 'Attachments: ' + attachments.map((a) => a.name + ' (' + a.kind + ', ' + Math.ceil(a.size / 1024) + ' KB)').join(', ') +
      (attachments.some((a) => a.kind === 'image') ? ' — images are not shown to models until a vision route is qualified.' : '')));
    c.scrollTop = c.scrollHeight;
  } catch (_) {}
}
let searchTimer = null;
$('chat-search').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(async () => {
  const q = $('chat-search').value.trim(); const ul = $('search-results'); ul.replaceChildren();
  if (!q) return;
  try {
    const { results } = await api('/api/search?q=' + encodeURIComponent(q));
    for (const r of results) ul.append(el('li', { tabindex: 0, onclick: () => loadDetail(r.task_id) }, el('span', { class: 'muted' }, r.project + ' #' + short(r.task_id) + ' · '), r.text.slice(0, 120)));
    if (!results.length) ul.append(el('li', { class: 'muted' }, 'No matching messages'));
  } catch (e) { toast(e); } }, 300); });

// ---------------------------------------------------------------- workforce office
function renderOffice() {
  try {
    const o = S.overview; const box = $('office'); if (!o || !box) return;
    const callsign = (id, name) => ({ orchestrator: 'Atlas', reviewer: 'Judge', ui: 'Pixel',
      'visual-qa': 'Iris', debugger: 'Scout', operations: 'Ops', backend: 'Forge',
      'game-coder': 'Rune', optimizer: 'Tempo', narrative: 'Scribe', 'level-designer': 'Mapper',
      'personal-helper': 'Sage', environment: 'Moss', sprites: 'Flip', audio: 'Echo',
      'cloud-engineer': 'Nimbus', 'cloud-analyst': 'Oracle' }[id] || name);
    const roomFor = (w) => {
      if (w.display && ['cloud', 'review', 'world', 'server', 'forge', 'creative', 'lounge'].includes(w.display.room)) return w.display.room;
      if (w.id === 'orchestrator') return 'cloud';
      if (w.id === 'reviewer' || /review|optimizer|visual-qa/.test(w.id)) return 'review';
      if (/narrative|personal|analyst|level/.test(w.id)) return 'world';
      if (/operations|debugger/.test(w.id) || w.device === 'cpu') return 'server';
      if (/ui|environment|sprites|audio/.test(w.id)) return 'creative';
      if (/backend|coder|engineer/.test(w.id) || w.device === 'gpu') return 'forge';
      return 'lounge';
    };
    box.querySelectorAll('.agent-dock').forEach((dock) => dock.replaceChildren());
    const active = o.workforce.filter((w) => ['working', 'waiting', 'blocked'].includes(w.state)).length;
    const count = $('office-task-count'); if (count) count.textContent = active + ' ACTIVE';
    const status = $('office-status');
    if (status) status.textContent = o.runner === 'running' ? '● RUNTIME CONNECTED' : '○ RUNNER ' + String(o.runner).toUpperCase();
    for (const w of o.workforce.filter((x) => !S.officeProject || workerProjects(x.id).includes(S.officeProject) || x.id === 'orchestrator' || x.id === 'reviewer')) {
      const dock = box.querySelector('[data-room="' + roomFor(w) + '"] .agent-dock');
      if (!dock) continue;
      const bubble = S.preview ? previewBubble(w.id) : w.state === 'working' ? 'WORKING…' : w.state === 'blocked' ? 'NEEDS HELP!' :
        w.state === 'waiting' ? 'WAITING…' : w.state === 'offline' ? 'OFFLINE' : null;
      const open = () => showAgent(w, roomFor(w)); const display = (w.display && w.display.callsign) || callsign(w.id, w.name);
      const palette = w.display && /^[a-z0-9-]{1,20}$/.test(w.display.palette || '') ? w.display.palette : 'default';
      dock.append(el('button', { class: 'agent palette-' + palette + ' st-' + (S.preview ? previewState(w.id) : w.state), id: 'agent-' + w.id, 'data-worker': w.id,
        title: w.name + ' — open details', 'aria-label': w.name + ', ' + w.state,
        onclick: open },
        bubble ? el('span', { class: 'agent-bubble' }, bubble) : null,
        el('span', { class: 'pixel-person', 'aria-hidden': 'true' }),
        el('span', { class: 'agent-name' }, display),
        el('span', { class: 'agent-state' }, w.state)));
    }
  } catch (_) { /* display only */ }
}

function showAgent(w, room) {
  const modal = $('agent-viewer'); const body = $('agent-viewer-body');
  const labels = { cloud: 'Cloud HQ', review: 'Review Room', world: 'World Room', server: 'Server Room',
    forge: 'Forge Lab', creative: 'Creative Studio', lounge: 'Lounge' };
  const jobs = S.tasks.filter((t) => t.worker === w.id || t.worker_id === w.id || t.id === w.task_id);
  const events = S.events.filter((e) => e.worker === w.id);
  const accepted = events.filter((e) => /accept|approved/.test(e.kind)).length;
  const sentBack = events.filter((e) => /reject|repair/.test(e.kind)).length;
  const failures = events.filter((e) => /fail|blocked/.test(e.kind)).length;
  const task = S.tasks.find((t) => t.id === w.task_id);
  body.replaceChildren(el('div', { class: 'agent-profile' },
    el('div', { class: 'agent-profile-head' }, el('span', { class: 'pixel-person', 'aria-hidden': 'true' }),
      el('div', {}, el('span', { class: 'eyebrow' }, labels[room] || room), el('h2', {}, w.name), statusChip(w.state))),
    (w.state === 'blocked' || w.state === 'waiting') ? el('div', { class: 'agent-needs' }, el('h3', {}, w.state === 'blocked' ? 'NEEDS YOUR HELP' : 'WAITING'),
      el('p', {}, task ? task.goal : (w.state === 'blocked' ? 'Open the associated task for its blocker and evidence.' : 'This specialist is waiting for its next dependency or resource.'))) : null,
    el('div', { class: 'agent-profile-stats' },
      ...[[jobs.length, 'Jobs'], [accepted, 'Accepted'], [sentBack, 'Sent back'], [failures, 'Failures']].map(([n, label]) => el('div', {}, el('strong', {}, n), el('small', {}, label)))),
    el('div', { class: 'agent-profile-grid' },
      el('span', { class: 'muted' }, 'Role'), el('span', {}, w.adapter || 'specialist'),
      el('span', { class: 'muted' }, 'Machine'), el('span', {}, w.device || 'cloud'),
      el('span', { class: 'muted' }, 'Model'), el('span', {}, w.model || 'active cloud route'),
      el('span', { class: 'muted' }, 'Qualification'), el('span', {}, w.qualified ? 'qualified' : 'not yet qualified'),
      el('span', { class: 'muted' }, 'Assignment'), el('span', {}, w.task_id ? 'Task #' + short(w.task_id) + (w.job_id ? ', job ' + w.job_id : '') : 'No current assignment'),
      el('span', { class: 'muted' }, 'Last activity'), el('span', {}, when(w.updated))),
    el('div', { class: 'agent-profile-actions' },
      w.task_id ? el('button', { class: 'primary', onclick: () => { modal.close(); document.querySelector('[data-tab=tasks]').click(); loadDetail(w.task_id); } }, 'Open task & conversation') : null,
      el('button', { onclick: () => modal.close() }, 'Close'))));
  modal.showModal();
}

function workerProjects(id) {
  const profile = (S.overview && S.overview.workforce || []).find((w) => w.id === id);
  if (profile && Array.isArray(profile.projects)) return profile.projects;
  if (profile && profile.task_id) {
    const task = S.tasks.find((t) => t.id === profile.task_id); if (task) return [task.project];
  }
  return S.me ? S.me.projects : [];
}

const PREVIEW_STATES = ['working', 'waiting', 'blocked', 'idle'];
function previewState(id) { return PREVIEW_STATES[Math.abs([...id].reduce((n, c) => n + c.charCodeAt(0), 0) + S.preview.step) % PREVIEW_STATES.length]; }
function previewBubble(id) {
  const lines = { orchestrator: 'ASSIGNING…', reviewer: 'REVIEWING…', ui: 'POLISHING UI…', backend: 'BUILDING…',
    'game-coder': 'TESTING…', narrative: 'WRITING…', debugger: 'CHECKING…', 'visual-qa': 'LOOKING CLOSE…' };
  return lines[id] || (previewState(id) === 'blocked' ? 'NEEDS YOU!' : previewState(id).toUpperCase() + '…');
}

function stopPreview() {
  if (!S.preview) return;
  clearInterval(S.preview.timer); S.preview = null; $('preview-banner').hidden = true; $('btn-preview').disabled = false; renderOffice();
}
$('btn-preview').addEventListener('click', () => {
  if (S.preview) return; S.preview = { step: 0, timer: null }; $('preview-banner').hidden = false; $('btn-preview').disabled = true;
  S.preview.timer = setInterval(() => { if (document.hidden) return; S.preview.step++; renderOffice();
    animateHandoff(S.preview.step % 2 ? 'orchestrator' : 'ui', S.preview.step % 2 ? 'ui' : 'reviewer'); }, 1200); renderOffice();
});
$('btn-stop-preview').addEventListener('click', stopPreview);
$('office-project').addEventListener('change', (e) => { S.officeProject = e.target.value; renderOffice(); });

function animateHandoff(from, to) {
  try {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || $('tab-office').hidden) return;
    const a = $('agent-' + from); const b = $('agent-' + to); if (!a || !b) return;
    const ra = a.getBoundingClientRect(); const rb = b.getBoundingClientRect();
    const t = el('div', { class: 'handoff-runner', 'aria-hidden': 'true' },
      el('span', { class: 'pixel-person' }), el('span', { class: 'task-parcel' }));
    document.body.append(t);
    const start = `translate(${ra.left + ra.width / 2 - 16}px, ${ra.top + ra.height / 2 - 24}px)`;
    const end = `translate(${rb.left + rb.width / 2 - 16}px, ${rb.top + rb.height / 2 - 24}px)`;
    const motion = t.animate([{ transform: start }, { transform: start, offset: .15 }, { transform: end }],
      { duration: 950, easing: 'steps(10, end)' });
    motion.onfinish = () => t.remove(); motion.oncancel = () => t.remove();
  } catch (_) { /* animation failures never matter */ }
}

function onEvent(e) {
  S.events.push(e); if (S.events.length > MAX_EVENTS) S.events.splice(0, S.events.length - MAX_EVENTS);
  S.cursor = Math.max(S.cursor, e.id);
  const feed = $('feed');
  feed.prepend(el('li', {}, when(e.at) + ' — ' + e.message + (e.worker ? ' (' + e.worker + ')' : '') + (e.task_id ? ' #' + short(e.task_id) : '')));
  while (feed.children.length > 150) feed.lastChild.remove();
  if (e.kind === 'handoff') animateHandoff(e.worker, 'reviewer');
  if (e.kind === 'assign') animateHandoff('orchestrator', e.worker);
  if (e.kind === 'review.rejected' || e.kind === 'repair.requested') animateHandoff('reviewer', e.worker || '');
  if (['task.blocked', 'task.draft_ready'].includes(e.kind)) notify(e);
  scheduleRefresh();
}

function notify(e) {
  try {
    if (S.notifyOk && document.hidden) new Notification("Kort's Assistant", { body: e.message, tag: 'ka-' + e.task_id });
  } catch (_) { /* optional */ }
}

function scheduleRefresh() {
  clearTimeout(S.refreshTimer);
  S.refreshTimer = setTimeout(() => { refreshOverview().catch(() => {}); refreshTasks().catch(() => {}); }, 400);
}

// ---------------------------------------------------------------- live connection
function connect() {
  if (S.es) S.es.close();
  const es = new EventSource(appUrl('/api/stream?cursor=' + S.cursor));
  S.es = es;
  es.addEventListener('evt', (m) => { try { onEvent(JSON.parse(m.data)); } catch (_) {} });
  es.addEventListener('beat', (m) => { S.lastBeat = Date.now(); showBanner(''); try { S.cursor = Math.max(S.cursor, JSON.parse(m.data).cursor); } catch (_) {} });
  es.addEventListener('resync', () => { S.events = []; $('feed').replaceChildren(); scheduleRefresh(); });
  es.addEventListener('auth', () => { es.close(); showLogin(); });
  // EventSource reconnects by itself (retry: 3000) and resends Last-Event-ID.
}
setInterval(() => {
  if ($('app').hidden) return;
  if (S.lastBeat && Date.now() - S.lastBeat > 20000) {
    showBanner('Live connection lost — the view may be stale. Reconnecting…');
    connect(); S.lastBeat = Date.now();
  }
  const o = S.overview;
  if (o && o.runner !== 'running') showBanner('The task runner is ' + o.runner + '. Tasks will not progress until it runs.');
}, 5000);

// ---------------------------------------------------------------- inbox
async function loadInbox() {
  const box = $('inbox'); box.replaceChildren();
  try {
    const { items } = await api('/api/mailbox');
    if (!items.length) box.append(el('p', { class: 'muted' }, 'Nothing needs you right now.'));
    for (const m of items) {
      box.append(el('div', { class: 'job' },
        el('h4', {}, el('span', { class: 'status s-' + (m.priority === 'review' ? 'draft_ready' : m.priority === 'fyi' ? 'x' : 'blocked') }, m.priority), ' ', m.subject),
        el('p', {}, m.body), el('div', { class: 'muted' }, 'updated ' + when(m.updated)),
        el('div', { class: 'row' },
          m.task_id && m.task_id.length === 32 ? el('button', { onclick: () => { document.querySelector('[data-tab=tasks]').click(); loadDetail(m.task_id); } }, 'Open task') : null,
          el('button', { onclick: async () => { const r = await ask('Answer', m.subject, { input: true, okLabel: 'Send' });
            if (r) { try { await api('/api/mailbox/' + m.id + '/answer', { body: { response: r } }); loadInbox(); } catch (e) { toast(e); } } } }, 'Answer / dismiss'))));
    }
  } catch (e) { toast(e); }
}

// ---------------------------------------------------------------- knowledge
let noteTimer = null;
$('note-q').addEventListener('input', () => { clearTimeout(noteTimer); noteTimer = setTimeout(loadNotes, 300); });
async function loadNotes() {
  try {
    const { notes } = await api('/api/notes?q=' + encodeURIComponent($('note-q').value));
    const ul = $('note-list'); ul.replaceChildren();
    for (const n of notes) ul.append(el('li', { tabindex: 0, onclick: () => openNote(n.path), onkeydown: (e) => { if (e.key === 'Enter') openNote(n.path); } },
      el('div', {}, statusChip(n.status), n.conflicts ? el('span', { class: 'error' }, ' metadata conflict') : null),
      el('div', {}, n.path), el('div', { class: 'muted' }, n.producer + (n.updated ? ' · ' + n.updated : ''))));
    if (!notes.length) ul.append(el('li', { class: 'muted' }, 'No notes.'));
  } catch (e) { toast(e); }
}
async function openNote(path) {
  try { S.note = await api('/api/note?path=' + encodeURIComponent(path)); renderNote(false); } catch (e) { toast(e); }
}
function renderNote(editing) {
  const n = S.note; const box = $('note-detail'); box.replaceChildren();
  box.append(el('h2', {}, statusChip(n.status), ' ', n.path));
  const kv = el('div', { class: 'kv' });
  for (const [k, v] of [['Producer', n.producer], ['Sources', n.sources], ['Reviewer', n.reviewer], ['Supersedes', n.supersedes],
    ['Superseded by', n.metadata.superseded_by], ['Status reason', n.metadata.status_reason], ['Problems', n.metadata_errors.join('; ')]])
    if (v) kv.append(el('span', { class: 'muted' }, k), el('span', {}, v));
  box.append(kv);
  if (editing) {
    const ta = el('textarea', { class: 'note-edit', 'aria-label': 'Note text' }); ta.value = n.text;
    box.append(ta, el('div', { class: 'row' },
      el('button', { class: 'primary', onclick: async () => {
        try { await api('/api/note', { body: { path: n.path, text: ta.value, digest: n.digest } }); await openNote(n.path); toast('Saved; previous version kept in history.'); }
        catch (e) { toast(e); } } }, 'Save'),
      el('button', { onclick: () => renderNote(false) }, 'Cancel')));
    return;
  }
  box.append(el('pre', {}, n.body));
  box.append(el('div', { class: 'row' },
    el('button', { onclick: () => renderNote(true) }, 'Edit'),
    el('button', { onclick: async () => { const r = await ask('Mark disputed', 'What is wrong or conflicting?', { input: true, okLabel: 'Mark disputed' });
      if (r) statusChange('disputed', r); } }, 'Dispute'),
    el('button', { onclick: async () => { const r = await ask('Supersede', 'Path of the newer note that replaces this one (same project).', { input: true, okLabel: 'Supersede' });
      if (r) statusChange('superseded', 'Replaced', r); } }, 'Supersede'),
    n.status === 'approved' ? el('button', { onclick: async () => {
      try { const r = await api('/api/note/propose-skill', { body: { path: n.path } }); toast('Skill proposal drafted: ' + r.path); } catch (e) { toast(e); } } }, 'Propose as skill') : null));
  if (n.links.length) box.append(el('h3', {}, 'Links'), el('ul', {}, n.links.map((l) => el('li', {}, l))));
  box.append(el('h3', {}, 'Backlinks'), n.backlinks.length ? el('ul', {}, n.backlinks.map((b) => el('li', { tabindex: 0, onclick: () => openNote(b) }, b))) : el('p', { class: 'muted' }, 'None'));
  box.append(el('h3', {}, 'Revision history'), n.revisions.length ? el('ul', {}, n.revisions.map((r) =>
    el('li', {}, el('button', { onclick: () => showText(r, '/api/note/revision?path=' + encodeURIComponent(n.path) + '&revision=' + encodeURIComponent(r)) }, r)))) : el('p', { class: 'muted' }, 'No earlier versions'));
}
async function statusChange(status, reason, supersededBy) {
  try { await api('/api/note/status', { body: { path: S.note.path, status, reason, superseded_by: supersededBy || '' } }); await openNote(S.note.path); loadNotes(); }
  catch (e) { toast(e); }
}

// ---------------------------------------------------------------- system
function table(id, headers, rows) {
  const t = $(id); t.replaceChildren(el('tr', {}, headers.map((h) => el('th', {}, h))));
  for (const r of rows) t.append(el('tr', {}, r.map((c) => el('td', {}, c ?? ''))));
  if (!rows.length) t.append(el('tr', {}, el('td', { colspan: headers.length, class: 'muted' }, 'No records yet')));
}
async function renderSystem() {
  const o = S.overview; if (!o) return;
  table('health', ['Check', 'State', 'Detail', 'Last success'], o.health.map((h) => [h.name, h.ok ? 'ok' : 'PROBLEM', h.detail, when(h.last_ok)]));
  table('routes', ['Route', 'Free price', 'Cooldown until', 'Failures', 'Last ok', 'Last error'], o.routes.map((r) =>
    [r.route, r.pricing_ok === null ? 'unchecked' : (r.pricing_ok ? 'verified' : 'FAILED'), r.cooldown_until ? when(r.cooldown_until) : '', r.failures, when(r.last_ok), r.last_error]));
  table('calls', ['Provider', 'Model', 'Outcome', 'Count'], o.invocations_24h.map((c) => [c.provider, c.model, c.outcome, c.count]));
  const c = $('consent'); c.replaceChildren(el('p', { class: 'muted' }, 'A project sends notes to cloud models only when it is enabled both in config.json and here.'));
  for (const [p, on] of Object.entries(o.consent)) c.append(el('div', { class: 'row' }, el('strong', {}, p), on ? 'granted' : 'not granted',
    S.me.owner ? el('button', { onclick: () => act('/api/control/consent', { project: p, grant: !on }, (on ? 'Revoke' : 'Grant') + ' cloud context for ' + p + '?').then(renderSystem) }, on ? 'Revoke' : 'Grant') : null));
  try {
    const { rows } = await api('/api/audit');
    table('audit', ['When', 'Who', 'Action', 'Project', 'OK'], rows.slice(0, 80).map((r) => [when(r.at), r.actor, r.action, r.project || '', r.ok ? 'yes' : 'no']));
  } catch (_) {}
}
$('btn-backup').addEventListener('click', async () => {
  try { const r = await api('/api/control/backup', { body: {} }); toast('Backup written: ' + r.file); await refreshOverview(); renderSystem(); } catch (e) { toast(e); }
});

// ---------------------------------------------------------------- boot
async function refreshOverview() { S.overview = await api('/api/overview'); renderHeader(); }
async function boot() {
  S.me = await api('/api/me');
  if (!S.me.signed_in) return showLogin();
  $('login-view').hidden = true; $('app').hidden = false;
  document.body.classList.toggle('is-owner', !!S.me.owner);
  for (const sel of [$('add-project'), $('filter-project')]) {
    const keep = sel.id === 'filter-project' ? [sel.firstElementChild] : [];
    sel.replaceChildren(...keep, ...S.me.projects.map((p) => el('option', { value: p }, p)));
  }
  $('sidebar-user').textContent = S.me.user || 'signed in';
  const officeProject = $('office-project');
  officeProject.replaceChildren(el('option', { value: '' }, 'All projects'), ...S.me.projects.map((p) => el('option', { value: p }, p[0].toUpperCase() + p.slice(1))));
  await refreshOverview();
  // Show recent history, then follow live events from the newest cursor.
  try {
    const recent = await api('/api/events?cursor=' + Math.max(0, S.overview.latest_event - 100));
    recent.events.forEach((e) => { S.events.push(e); $('feed').prepend(el('li', {}, when(e.at) + ' — ' + e.message + (e.worker ? ' (' + e.worker + ')' : '') + (e.task_id ? ' #' + short(e.task_id) : ''))); });
  } catch (_) {}
  S.cursor = S.overview.latest_event;
  await refreshTasks();
  S.notifyOk = 'Notification' in window && Notification.permission === 'granted';
  connect();
}
boot().catch(() => showLogin());
