"""Exclusive GPU lease, gaming mode and GPU-endpoint health.

One lease named 'gpu' covers every GPU consumer (Ollama workers now, ComfyUI/audio later), so two
tools never load models onto the 12 GB card at the same time. Gaming mode refuses new leases,
unloads GPU models through the Ollama API and records whether VRAM was actually released."""
from __future__ import annotations
import json
import time
from contextlib import contextmanager
from datetime import timedelta
from urllib.parse import urlparse
from .state import (get_setting, set_setting, iso, parse, utcnow, record_health, emit,
                    set_worker_state, audit)

RESOURCE = 'gpu'


def device_of(profile):
    """Explicit 'device' wins; otherwise the SSH-tunnel port 11435 means the gaming PC GPU."""
    if profile.get('device') in ('gpu', 'cpu', 'cloud'):
        return profile['device']
    if str(profile.get('adapter', '')).startswith('cloud'):
        return 'cloud'
    port = urlparse(profile.get('endpoint', '')).port
    return 'gpu' if port == 11435 else 'cpu'


def gaming(db):
    return bool(get_setting(db, 'gaming_mode', False))


def lease_holder(db):
    row = db.execute('SELECT holder,kind,acquired,expires FROM gpu_lease WHERE resource=?', (RESOURCE,)).fetchone()
    if not row:
        return None
    if (parse(row[3]) or utcnow()) <= utcnow():
        return None
    return dict(zip(('holder', 'kind', 'acquired', 'expires'), row))


def acquire(db, holder, kind='llm', ttl_seconds=900):
    if gaming(db):
        return False
    now = utcnow()
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('SELECT holder,expires FROM gpu_lease WHERE resource=?', (RESOURCE,)).fetchone()
        if row and row[0] != holder and (parse(row[1]) or now) > now:
            db.rollback()
            return False
        db.execute('INSERT INTO gpu_lease VALUES (?,?,?,?,?) ON CONFLICT(resource) DO UPDATE SET '
                   'holder=excluded.holder,kind=excluded.kind,acquired=excluded.acquired,expires=excluded.expires',
                   (RESOURCE, holder, kind, iso(now), iso(now + timedelta(seconds=ttl_seconds))))
        db.commit()
        return True
    except BaseException:
        db.rollback()
        raise


def release(db, holder):
    with db:
        db.execute('DELETE FROM gpu_lease WHERE resource=? AND holder=?', (RESOURCE, holder))


@contextmanager
def lease(db, holder, kind='llm', ttl_seconds=900):
    if not acquire(db, holder, kind, ttl_seconds):
        raise GpuBusy('GPU unavailable (gaming mode or another GPU job holds the lease)')
    try:
        yield
    finally:
        release(db, holder)


class GpuBusy(RuntimeError):
    pass


def _fetch(url, payload=None, timeout=10):
    from .models import request_json
    return request_json(url, payload, timeout=timeout)


def endpoint_health(endpoint, fetch=_fetch):
    """Is the Ollama endpoint (local or SSH-tunnelled) answering? Never raises."""
    try:
        data = fetch(endpoint.rstrip('/') + '/api/version', None, 5)
        return True, 'Ollama ' + str(data.get('version', 'unknown'))
    except Exception as e:  # sleep, shutdown or broken tunnel all look like this
        return False, type(e).__name__


def loaded_models(endpoint, fetch=_fetch):
    data = fetch(endpoint.rstrip('/') + '/api/ps', None, 10)
    return [{'name': m.get('name') or m.get('model'), 'size_vram': int(m.get('size_vram') or 0)}
            for m in data.get('models', [])]


def gpu_endpoints(profiles):
    seen = {}
    for name, p in profiles.items():
        if device_of(p) == 'gpu':
            seen.setdefault(p['endpoint'].rstrip('/'), set()).add(p.get('model', ''))
    return seen


def enter_gaming(db, profiles, actor='owner', cancel_active=False, fetch=_fetch, wait_seconds=0, sleep=time.sleep):
    """Stop new GPU work, optionally interrupt active work, unload GPU models and verify VRAM.

    Returns a report dict. VRAM release is only reported as confirmed when /api/ps on every GPU
    endpoint answered and listed no loaded model; an unreachable endpoint is 'unconfirmed'."""
    set_setting(db, 'gaming_mode', True)
    emit(db, 'system', 'gpu.gaming', 'Gaming mode on: no new GPU work will start')
    active = lease_holder(db)
    deadline = time.monotonic() + wait_seconds
    while active and time.monotonic() < deadline:
        sleep(2)
        active = lease_holder(db)
    report = {'gaming_mode': True, 'active_job': bool(active), 'endpoints': []}
    if active:
        report['vram'] = 'waiting_for_active_job'
        if cancel_active:
            report['cancel_requested'] = False
            report['message'] = 'The active HTTP inference cannot be killed safely; gaming mode will unload it when the request exits.'
        audit(db, actor, 'gaming.on', True, detail=json.dumps(report))
        return report
    confirmed = True
    for endpoint, models in gpu_endpoints(profiles).items():
        entry = {'endpoint_port': urlparse(endpoint).port, 'unloaded': [], 'still_loaded': []}
        try:
            for m in loaded_models(endpoint, fetch):
                fetch(endpoint + '/api/generate', {'model': m['name'], 'keep_alive': 0}, 30)
                entry['unloaded'].append(m['name'])
            remaining = loaded_models(endpoint, fetch)
            entry['still_loaded'] = [m['name'] for m in remaining]
            entry['vram_bytes'] = sum(m['size_vram'] for m in remaining)
            confirmed = confirmed and not remaining
        except Exception as e:
            entry['error'] = type(e).__name__
            confirmed = False
        report['endpoints'].append(entry)
    report['vram'] = 'released' if confirmed else 'unconfirmed'
    record_health(db, 'gpu.vram_released', confirmed, report['vram'])
    for name, p in profiles.items():
        if device_of(p) == 'gpu':
            set_worker_state(db, name, 'unavailable')
    emit(db, 'system', 'gpu.unloaded', 'GPU models unloaded' if confirmed else 'GPU unload could not be confirmed')
    audit(db, actor, 'gaming.on', True, detail=json.dumps(report))
    return report


def exit_gaming(db, profiles, actor='owner', fetch=_fetch):
    set_setting(db, 'gaming_mode', False)
    ok_all = True
    for endpoint in gpu_endpoints(profiles):
        ok, detail = endpoint_health(endpoint, fetch)
        record_health(db, 'gpu.endpoint', ok, detail)
        ok_all = ok_all and ok
    for name, p in profiles.items():
        if device_of(p) == 'gpu':
            set_worker_state(db, name, 'idle' if ok_all else 'offline')
    emit(db, 'system', 'gpu.resumed', 'Gaming mode off: GPU work may resume' if ok_all
         else 'Gaming mode off, but the GPU endpoint is not answering')
    audit(db, actor, 'gaming.off', True, detail='endpoint ok' if ok_all else 'endpoint offline')
    return {'gaming_mode': False, 'endpoint_ok': ok_all}
