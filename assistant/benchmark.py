"""Benchmark and qualify local worker roles against their real Ollama endpoints.

For each local role this measures, with real requests:
  * warm-up (cold load) time and resident memory / VRAM reported by Ollama (/api/ps),
  * latency and tokens per second for a short structured task,
  * a long prompt near the configured num_ctx with a fact planted at the start (context recall),
  * JSON compliance: the answer must parse (after the standard recovery) and match expectations,
  * malformed-input handling: a request designed to tempt prose around the JSON.

Results are written to the private runtime (reports/benchmarks/). Nothing is marked qualified
automatically: `python -m assistant.benchmark qualify <role>` copies qualified=true into the
private workers.json only when a passing benchmark for the same model and context is < 7 days old.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from .core import runtime_root
from .models import request_json, parse_json
from .gpu import device_of

FILLER = ('The caravan crossed the dunes while the keepers counted relics and mended their banners. ' * 40)


def _chat(profile, prompt, fetch=request_json, num_predict=512):
    started = time.monotonic()
    data = fetch(profile['endpoint'].rstrip('/') + '/api/chat', {
        'model': profile['model'], 'stream': False, 'format': 'json',
        'keep_alive': profile.get('keep_alive', '10m'),
        'messages': [{'role': 'system', 'content': profile.get('instructions', '')},
                     {'role': 'user', 'content': prompt}],
        'options': {'num_ctx': profile.get('num_ctx', 8192), 'num_predict': num_predict, 'temperature': 0}},
        timeout=900)
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
        entry = {'case': case}
        try:
            text, metrics = _chat(profile, prompt, fetch)
            entry.update(metrics)
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
    age = time.time() - time.mktime(time.strptime(report['at'], '%Y-%m-%dT%H:%M:%SZ')) + time.timezone
    if age > max_age_days * 86400:
        raise ValueError('Benchmark is older than %d days; rerun it' % max_age_days)
    profile['qualified'] = True
    profile['qualification'] = {'at': report['at'], 'model': report['model'], 'num_ctx': report['num_ctx']}
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
    a = p.parse_args(argv)
    root = runtime_root()
    workers = json.loads((root / 'workers.json').read_text(encoding='utf-8'))
    if a.cmd == 'qualify':
        print(json.dumps(qualify(root, a.role), indent=2))
        return
    names = a.roles or [n for n, w in workers.items() if device_of(w) in ('cpu', 'gpu')]
    for name in names:
        result = run_role(name, workers[name])
        path = save(result, root)
        print(('PASS ' if result['passed'] else 'FAIL ') + name + ' ' + str(result.get('model')) + ' -> ' + str(path))


if __name__ == '__main__':
    main()
