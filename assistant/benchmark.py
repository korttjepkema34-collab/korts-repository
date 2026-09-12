"""Benchmark and qualify local worker roles against their real Ollama endpoints.

For each local role this measures, with real requests:
  * warm-up (cold load) time and resident memory / VRAM reported by Ollama (/api/ps),
  * latency and tokens per second for a short structured task,
  * a long prompt near the configured num_ctx with a fact planted at the start (context recall),
  * JSON compliance: the answer must parse (after the standard recovery) and match expectations,
  * malformed-input handling: a request designed to tempt prose around the JSON.

Results are written to the private runtime (reports/benchmarks/). Nothing is marked qualified
automatically: `python -m assistant.benchmark qualify <role>` copies qualified=true into the
private workers.json only when a passing benchmark for the same effective profile is < 7 days old.
"""
from __future__ import annotations
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from .core import runtime_root
from .models import request_json, parse_json, local_request, local_profile_fingerprint
from .gpu import device_of

FILLER = ('The caravan crossed the dunes while the keepers counted relics and mended their banners. ' * 40)


def _chat(profile, prompt, fetch=request_json):
    started = time.monotonic()
    url, payload, timeout = local_request(profile, prompt)
    data = fetch(url, payload, timeout=timeout)
    elapsed = time.monotonic() - started
    evals = data.get('eval_count') or 0
    eval_s = (data.get('eval_duration') or 0) / 1e9
    return data.get('message', {}).get('content', ''), {
        'seconds': round(elapsed, 2), 'prompt_tokens': data.get('prompt_eval_count'),
        'output_tokens': evals, 'tokens_per_second': round(evals / eval_s, 2) if eval_s else None}


def cases(num_ctx):
    # ~4 characters per token; leave room for the answer.
    repeats = max(1, int((num_ctx * 0.7 * 4) / len(FILLER)))
    long_text = 'SECRET CODE: amber-falcon-42.\n' + FILLER * repeats
    return [
        ('structured', 'Return JSON {"items":["a","b","c"],"count":3} exactly, nothing else.',
         lambda x: x.get('count') == 3 and x.get('items') == ['a', 'b', 'c']),
        ('reasoning', 'Jobs: build needs design; test needs build; docs independent. Return JSON '
         '{"order":["design","build","test"]} listing dependent jobs in a valid order.',
         lambda x: x.get('order') == ['design', 'build', 'test']),
        ('long_context', long_text + '\nWhat was the secret code at the very start? Return JSON {"code":"..."}',
         lambda x: str(x.get('code', '')).strip().lower() == 'amber-falcon-42'),
        ('malformed_pressure', 'Explain your reasoning at length first, then give JSON {"approved":false} because the '
         'test exit code was 1. Your final answer must still be valid JSON.',
         lambda x: x.get('approved') is False),
    ]


def run_role(name, profile, fetch=request_json):
    endpoint = profile['endpoint'].rstrip('/')
    result = {'role': name, 'model': profile.get('model'), 'device': device_of(profile),
              'num_ctx': profile.get('num_ctx', 8192), 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'cases': []}
    try:
        result['profile_fingerprint'] = local_profile_fingerprint(profile)
        started = time.monotonic()
        fetch(endpoint + '/api/generate', {'model': profile['model'], 'prompt': '', 'keep_alive': '10m'}, timeout=900)
        result['warmup_seconds'] = round(time.monotonic() - started, 2)
        loaded = fetch(endpoint + '/api/ps', timeout=30).get('models', [])
        entry = next((m for m in loaded if (m.get('name') or m.get('model')) == profile['model']), {})
        result['memory_bytes'] = entry.get('size')
        result['vram_bytes'] = entry.get('size_vram')
        result['loaded_context'] = entry.get('context_length')
    except Exception as e:
        result['error'] = 'endpoint unavailable: ' + type(e).__name__
        result['passed'] = False
        return result
    for case, prompt, check in cases(result['num_ctx']):
        entry = {'case': case, 'prompt': prompt}
        try:
            text, metrics = _chat(profile, prompt, fetch)
            entry.update(metrics)
            entry['response'] = text
            try:
                entry['passed'] = bool(check(parse_json(text)))
                entry['recovered_json'] = not text.strip().startswith('{')
            except (ValueError, AttributeError):
                entry['passed'] = False
                entry['error'] = 'invalid JSON'
        except Exception as e:
            entry['passed'] = False
            entry['error'] = type(e).__name__
        result['cases'].append(entry)
    result['passed'] = all(c['passed'] for c in result['cases'])
    return result


def save(result, root=None):
    d = Path(root or runtime_root()) / 'reports' / 'benchmarks'
    d.mkdir(parents=True, exist_ok=True)
    p = d / (result['role'] + '-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    p.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return p


def latest(root, role):
    d = Path(root) / 'reports' / 'benchmarks'
    files = sorted(d.glob(role + '-*.json')) if d.is_dir() else []
    return json.loads(files[-1].read_text(encoding='utf-8')) if files else None


def evidence_for(root, role, profile, max_age_days=7):
    """Newest passing benchmark whose fingerprint matches this exact profile, if any.

    Reports are kept per run, so evidence for a model a role used previously is still on
    disk. That is what makes switching back cheap: the role recovers its qualification
    without a fresh benchmark, but only from evidence that matches it exactly.
    """
    d = Path(root) / 'reports' / 'benchmarks'
    if not d.is_dir():
        return None
    want = local_profile_fingerprint(profile)
    for f in sorted(d.glob(role + '-*.json'), reverse=True):
        try:
            report = json.loads(f.read_text(encoding='utf-8'))
        except ValueError:
            continue
        if not report.get('passed') or report.get('profile_fingerprint') != want:
            continue
        try:
            measured = datetime.strptime(report['at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if 0 <= time.time() - measured.timestamp() <= max_age_days * 86400:
            return report
    return None


def endpoint_of(profile):
    """Which machine a profile runs on. One Ollama endpoint is one machine."""
    return (profile.get('endpoint') or '').rstrip('/')


def _requalify(root, role, profile, max_age_days):
    """Re-decide qualification from evidence that matches this profile exactly."""
    report = evidence_for(root, role, profile, max_age_days)
    if report:
        profile['qualified'] = True
        profile['qualification'] = {'at': report['at'], 'model': report['model'],
                                    'num_ctx': report['num_ctx'],
                                    'profile_fingerprint': report['profile_fingerprint']}
    else:
        profile['qualified'] = False
        profile.pop('qualification', None)
    return profile


def switch_model(root, role, model, max_age_days=7):
    """Put a machine on a model, moving every specialist that runs there with it.

    A machine holds one model in memory at a time. Leaving two specialists on one endpoint
    pointed at different models does not give you two models; it gives you one machine
    evicting and reloading several gigabytes between jobs, which is slower than either
    model and fails in a way that looks like the model being bad. So the endpoint is the
    unit of choice: switching a specialist switches its machine.

    Qualification is still decided per specialist, because each role is benchmarked on its
    own cases. A role that has no recent passing benchmark for the new model comes back
    plainly unqualified rather than quietly trusted; the owner sees that and can benchmark
    it. Roles on other machines are untouched.
    """
    root = Path(root)
    workers_path = root / 'workers.json'
    workers = json.loads(workers_path.read_text(encoding='utf-8'))
    profile = workers.get(role)
    if not isinstance(profile, dict):
        raise ValueError('Unknown specialist')
    if model not in (profile.get('approved_models') or []):
        raise ValueError('That model is not approved for this specialist')
    endpoint = endpoint_of(profile)
    if not endpoint:
        raise ValueError('That specialist does not run on a local machine')
    moved = []
    for name, p in workers.items():
        if not isinstance(p, dict) or endpoint_of(p) != endpoint:
            continue
        if model not in (p.get('approved_models') or []):
            raise ValueError('%s runs on the same machine but does not approve %s' % (name, model))
        p['model'] = model
        _requalify(root, name, p, max_age_days)
        moved.append(name)
    tmp = workers_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(workers, indent=2), encoding='utf-8')
    tmp.replace(workers_path)
    result = dict(profile)
    result['moved'] = sorted(moved)
    result['unqualified'] = sorted(n for n in moved if workers[n].get('qualified') is not True)
    return result


def qualify(root, role, max_age_days=7):
    root = Path(root)
    workers_path = root / 'workers.json'
    workers = json.loads(workers_path.read_text(encoding='utf-8'))
    profile = workers[role]
    report = latest(root, role)
    if not report or not report.get('passed'):
        raise ValueError('No passing benchmark for this role; run the benchmark first')
    if report['model'] != profile.get('model') or report['num_ctx'] != profile.get('num_ctx', 8192):
        raise ValueError('Latest benchmark used a different model or context size')
    if report.get('profile_fingerprint') != local_profile_fingerprint(profile):
        raise ValueError('Latest benchmark lacks matching profile evidence; rerun it')
    measured = datetime.strptime(report['at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    age = time.time() - measured.timestamp()
    if not 0 <= age <= max_age_days * 86400:
        raise ValueError('Benchmark timestamp is future-dated or older than %d days; rerun it' % max_age_days)
    profile['qualified'] = True
    profile['qualification'] = {'at': report['at'], 'model': report['model'], 'num_ctx': report['num_ctx'],
                                'profile_fingerprint': report['profile_fingerprint']}
    tmp = workers_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(workers, indent=2), encoding='utf-8')
    tmp.replace(workers_path)
    return profile


def main(argv=None):
    p = argparse.ArgumentParser(description='Benchmark or qualify local worker roles')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('roles', nargs='*', help='default: every local role')
    q = sub.add_parser('qualify')
    q.add_argument('role')
    m = sub.add_parser('use', help='switch a role onto one of its approved models')
    m.add_argument('role')
    m.add_argument('model')
    a = p.parse_args(argv)
    root = runtime_root()
    workers = json.loads((root / 'workers.json').read_text(encoding='utf-8'))
    if a.cmd == 'qualify':
        print(json.dumps(qualify(root, a.role), indent=2))
        return
    if a.cmd == 'use':
        print(json.dumps(switch_model(root, a.role, a.model), indent=2))
        return
    names = a.roles or [n for n, w in workers.items() if device_of(w) in ('cpu', 'gpu')]
    for name in names:
        result = run_role(name, workers[name])
        path = save(result, root)
        print(('PASS ' if result['passed'] else 'FAIL ') + name + ' ' + str(result.get('model')) + ' -> ' + str(path))


if __name__ == '__main__':
    main()
