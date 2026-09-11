"""Health checks, monitoring alerts, report rotation and the daily report.

Every check records ok/detail/last-success in the health table so the dashboard can show the
last successful evidence time. Checks never raise into the runner. Network checks are rate
limited. Nothing here updates source code or models."""
from __future__ import annotations
import json
import shutil
from datetime import datetime, timedelta, timezone
from . import state, gpu
from .backup import age_hours

REPORT_KEEP = 200


def _due(db, key, hours):
    last = state.parse(state.get_setting(db, key))
    return last is None or state.utcnow() - last >= timedelta(hours=hours)


def check_runner(store):
    beat = state.parse(state.get_setting(store.db, 'runner.heartbeat'))
    if beat is None:
        state.record_health(store.db, 'runner', False, 'no heartbeat recorded yet')
        return
    age = (state.utcnow() - beat).total_seconds()
    state.record_health(store.db, 'runner', age < 900, 'heartbeat %d s ago' % age)


def check_disk(store, config):
    usage = shutil.disk_usage(store.root)
    free_gb = usage.free / 1e9
    minimum = float(config.get('min_free_disk_gb', 20))
    ok = free_gb >= minimum
    state.record_health(store.db, 'disk', ok, '%.1f GB free (minimum %.0f GB)' % (free_gb, minimum))
    if not ok:
        state.mail(store.db, 'system', 'urgent', 'Low disk space on the assistant server',
                   'Free space is %.1f GB, below the configured %.0f GB minimum. New artifacts, backups and '
                   'model files may fail.' % (free_gb, minimum), dedupe_key='health:disk')


def check_memory(store, config):
    try:
        import psutil  # optional; not required
    except ImportError:
        state.record_health(store.db, 'memory', True, 'unknown (psutil not installed)')
        return
    vm = psutil.virtual_memory()
    ok = vm.percent < float(config.get('max_memory_percent', 90))
    state.record_health(store.db, 'memory', ok, '%d%% used' % vm.percent)


def check_backup(store, config):
    age = age_hours(store.db)
    limit = float(config.get('backup_max_age_hours', 36))
    if age is None:
        state.record_health(store.db, 'backup', False, 'no backup recorded')
    else:
        state.record_health(store.db, 'backup', age <= limit, 'last backup %.1f h ago' % age)
    if age is None or age > limit:
        state.mail(store.db, 'system', 'fyi', 'Backup is overdue',
                   'No verified backup in the last %.0f hours. Run: python -m assistant.backup create' % limit,
                   dedupe_key='health:backup')


def check_endpoints(store, profiles, probe=gpu.endpoint_health):
    seen = {}
    for name, p in profiles.items():
        if gpu.device_of(p) == 'cloud' or not p.get('endpoint'):
            continue
        dev = gpu.device_of(p)
        key = dev + ':' + p['endpoint']
        if key not in seen:
            if dev == 'gpu' and gpu.gaming(store.db):
                seen[key] = (None, 'gaming mode')
            else:
                seen[key] = probe(p['endpoint'])
        ok, detail = seen[key]
        if ok is None:
            state.set_worker_state(store.db, name, 'unavailable')
            continue
        current = state.worker_states(store.db).get(name, {}).get('state')
        if not ok:
            state.set_worker_state(store.db, name, 'offline')
        elif current in (None, 'offline'):
            state.set_worker_state(store.db, name, 'idle')
    for key, (ok, detail) in seen.items():
        if ok is not None:
            state.record_health(store.db, 'endpoint.' + key.split(':', 1)[0], ok,
                                ('tunnel/GPU ' if key.startswith('gpu') else 'server ') + detail)


def check_cloud(store, config, fetch=None):
    """Recheck free pricing and catalog fingerprints of configured routes every few hours."""
    if not any(r.get('provider') == 'openrouter' for r in config.get('cloud_routes', [])):
        return
    if not _due(store.db, 'cloud.catalog_check', float(config.get('catalog_recheck_hours', 6))):
        return
    from .models import request_json, verify_free_catalog
    from .catalog import fingerprint
    fetch = fetch or request_json
    state.set_setting(store.db, 'cloud.catalog_check', state.iso())
    try:
        catalog = fetch('https://openrouter.ai/api/v1/models', timeout=30)
    except Exception as e:
        state.record_health(store.db, 'cloud.catalog', False, 'catalog unreachable: ' + type(e).__name__)
        return
    state.record_health(store.db, 'cloud.catalog', True, 'catalog reachable')
    prints = state.get_setting(store.db, 'cloud.fingerprints', {}) or {}
    for route in config.get('cloud_routes', []):
        if route.get('provider') != 'openrouter':
            continue
        try:
            verify_free_catalog(route['model'], catalog)
            state.route_pricing(store.db, route, True)
        except ValueError as e:
            state.route_pricing(store.db, route, False, str(e))
            state.mail(store.db, 'system', 'urgent', 'Cloud route no longer verifiably free: ' + route['model'],
                       'The live catalog check failed (' + str(e) + '). The controller refuses this route until '
                       'the check passes again.', dedupe_key='cloud:price:' + route['model'])
            continue
        entry = next(m for m in catalog['data'] if m.get('id') == route['model'])
        fp = fingerprint(entry)
        if prints.get(route['model']) and prints[route['model']] != fp:
            state.mail(store.db, 'system', 'fyi', 'Model catalog entry changed: ' + route['model'],
                       'Context length, parameters or pricing metadata changed. Re-run qualification before relying '
                       'on earlier evaluation evidence.', dedupe_key='cloud:catalog:' + route['model'] + ':' + fp[:12])
        prints[route['model']] = fp
    state.set_setting(store.db, 'cloud.fingerprints', prints)


def check_failures(store):
    since = (state.utcnow() - timedelta(hours=24)).isoformat()
    blocked = store.db.execute("SELECT COUNT(*) FROM sevents WHERE kind='task.blocked' AND at>=?", (since,)).fetchone()[0]
    cost = store.db.execute("SELECT COUNT(*) FROM invocations WHERE outcome LIKE 'rejected_cost%' AND at>=?",
                            (since,)).fetchone()[0]
    subst = store.db.execute("SELECT COUNT(*) FROM invocations WHERE outcome LIKE 'rejected_model%' AND at>=?",
                             (since,)).fetchone()[0]
    state.record_health(store.db, 'failures', blocked < 3, '%d task(s) blocked in 24 h' % blocked)
    if blocked >= 3:
        state.mail(store.db, 'system', 'blocked', 'Repeated task failures',
                   '%d tasks were blocked in the last 24 hours. Check cloud availability and recent evidence.' % blocked,
                   dedupe_key='health:failures:' + since[:10])
    state.record_health(store.db, 'cloud.cost', cost == 0 and subst == 0,
                        '%d cost / %d model-substitution rejections in 24 h' % (cost, subst))
    if cost:
        state.mail(store.db, 'system', 'urgent', 'Unexpected cloud cost reported',
                   'A cloud call reported nonzero or missing cost evidence and its result was discarded. Check the '
                   'OpenRouter activity page and the invocation records.', dedupe_key='health:cost:' + since[:10])


def rotate_reports(store, keep=REPORT_KEEP):
    reports = sorted((store.root / 'reports').glob('report-*.md'))
    for old in reports[:-keep]:
        old.unlink(missing_ok=True)


def run_checks(store, config, profiles, probe=gpu.endpoint_health, fetch=None):
    for check in (lambda: check_runner(store), lambda: check_disk(store, config),
                  lambda: check_memory(store, config), lambda: check_backup(store, config),
                  lambda: check_endpoints(store, profiles, probe), lambda: check_cloud(store, config, fetch),
                  lambda: check_failures(store), lambda: rotate_reports(store)):
        try:
            check()
        except Exception as e:  # a broken check must never stop the runner
            state.record_health(store.db, 'health.internal', False, type(e).__name__)
    return state.health_rows(store.db)


def daily_report_if_due(store, hour=7):
    local = datetime.now().astimezone()
    today = local.date().isoformat()
    if local.hour < hour or state.get_setting(store.db, 'daily_report.last') == today:
        return None
    from .core import PROJECTS
    lines = ['# Daily assistant report — ' + today, '',
             'Drafts marked ready are cloud-reviewed only. Nothing is merged, deployed or published without you.', '',
             '## Health', '']
    for h in state.health_rows(store.db):
        lines.append('- %s %s — %s (last ok %s)' % ('OK ' if h['ok'] else 'FAIL', h['name'], h['detail'], h['last_ok'] or 'never'))
    lines += ['', '## Needs your attention', '']
    items = state.mailbox_items(store.db, PROJECTS)
    lines += ['- [%s] %s' % (m['priority'], m['subject']) for m in items] or ['- Nothing waiting.']
    lines += ['', '## Tasks', '']
    counts = {}
    for t in store.list():
        counts[t['status']] = counts.get(t['status'], 0) + 1
    lines += ['- %s: %d' % kv for kv in sorted(counts.items())] or ['- No tasks.']
    since = (state.utcnow() - timedelta(hours=24)).isoformat()
    calls = store.db.execute('SELECT provider, requested_model, outcome, COUNT(*) FROM invocations WHERE at>=? '
                             'GROUP BY 1,2,3', (since,)).fetchall()
    lines += ['', '## Cloud calls (24 h)', '']
    lines += ['- %s %s %s: %d' % tuple(r) for r in calls] or ['- None.']
    path = store.root / 'reports' / ('daily-' + today + '.md')
    path.parent.mkdir(exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    state.set_setting(store.db, 'daily_report.last', today)
    state.mail(store.db, 'system', 'fyi', 'Daily report ready (' + today + ')',
               'The daily report is in the private reports folder and on the dashboard.',
               dedupe_key='daily:' + today)
    return path
