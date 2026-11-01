"""Read an explicitly selected imported run for Atlas, retaining its caveats.

Only importer-generated capture filenames are resolved beside a sidecar.
Recorded raw-log paths, URLs, body_ref and event references are never opened.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from context_lab import observations

SNAPSHOT_SCHEMA = 'cc-run-snapshot/1'
RUN_SCHEMAS = ('cc-run-evidence/1', 'cc-run-evidence/2')
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_CAPTURE_BYTES = MAX_BUNDLE_BYTES


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _read(path, limit):
    # Reuse the importer's bounded nonblocking regular-file reader. Import
    # lazily so the independent observation projection remains usable alone.
    from context_lab.cc_runs import _bounded_regular
    return _bounded_regular(path, limit)[0]


def _validate_metadata(run):
    """Validate fields consumed by the viewer; retain unknown metadata as data."""
    for field in ('sources', 'index_records', 'responses', 'events', 'content_losses', 'dangling_references'):
        if not isinstance(run.get(field, []), list) or any(not isinstance(v, dict) for v in run.get(field, [])):
            raise ValueError('run/' + field + ' must contain objects')
    sources = run.get('sources', [])
    source_ids = [s.get('id') for s in sources]
    if any(not isinstance(i, str) for i in source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError('invalid or duplicate run source ID')
    records = run.get('index_records', [])
    record_ids = [r.get('record_id') for r in records]
    if any(not isinstance(i, str) for i in record_ids) or len(set(record_ids)) != len(record_ids):
        raise ValueError('invalid or duplicate run index record ID')
    if any(not isinstance(r.get('metadata'), dict) for r in records):
        raise ValueError('run index metadata must be an object')
    for attempt in run['attempts']:
        if not isinstance(attempt, dict) or attempt.get('source_id') not in source_ids:
            raise ValueError('run attempt references an unknown source')
        association = attempt.get('index_association')
        if (not isinstance(association, dict) or not isinstance(association.get('status'), str)
                or not isinstance(association.get('record_ids'), list)
                or any(not isinstance(i, str) or i not in record_ids for i in association['record_ids'])):
            raise ValueError('invalid run index association')
        if attempt.get('selected_response_presence') not in ('present', 'not_selected', 'unassessed'):
            raise ValueError('invalid run response presence')


def load_run(path):
    """Return run, raw captures, input paths, and a portable frozen snapshot."""
    path = Path(path)
    raw = _read(path, MAX_BUNDLE_BYTES)
    envelope = observations.parse_capture_json(raw.decode('utf-8'))
    if not isinstance(envelope, dict):
        raise ValueError('run must be an object')
    embedded = None
    if envelope.get('schema') == SNAPSHOT_SCHEMA:
        if set(envelope) != {'schema', 'run', 'captures'} or not isinstance(envelope['captures'], dict):
            raise ValueError('invalid run snapshot')
        run, embedded = envelope['run'], envelope['captures']
    else:
        run = envelope
    if (not isinstance(run, dict) or run.get('schema') not in RUN_SCHEMAS
            or not isinstance(run.get('run_id'), str)
            or not isinstance(run.get('attempts'), list)
            or not isinstance(run.get('limits'), dict)):
        raise ValueError('unsupported or incomplete run evidence')
    if len(run['attempts']) > 128:
        raise ValueError('run capture limit exceeded')
    _validate_metadata(run)
    captures, serialized, inputs, seen_ids = [], {}, [path], set()
    total = len(raw)
    for attempt in run['attempts']:
        if not isinstance(attempt, dict):
            raise ValueError('run attempt must be an object')
        filename, digest = attempt.get('capture_file'), attempt.get('capture_sha256')
        if not isinstance(filename, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.capture\.json', filename):
            raise ValueError('only importer-generated local capture filenames are allowed')
        if filename in serialized:
            raise ValueError('duplicate run capture filename')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid capture digest')
        if embedded is not None:
            text = embedded.get(filename)
            if not isinstance(text, str):
                raise ValueError('snapshot is missing a capture')
            payload = text.encode('utf-8')
        else:
            capture_path = path.parent / filename
            if capture_path.is_symlink():
                raise ValueError('run capture cannot be a symlink')
            payload = _read(capture_path, MAX_CAPTURE_BYTES)
            inputs.append(capture_path)
        if embedded is None:
            total += len(payload)
        if len(payload) > MAX_CAPTURE_BYTES or total > MAX_BUNDLE_BYTES:
            raise ValueError('run bundle byte limit exceeded')
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError('run capture digest mismatch: ' + filename)
        text = payload.decode('utf-8')
        capture = observations.parse_capture_json(text)
        normalized = observations.normalize_capture(capture)
        cid = normalized['capture_id']
        if cid != attempt.get('attempt_id') or cid in seen_ids:
            raise ValueError('run attempt and capture identities disagree or repeat')
        if not observations._equal(capture['runtime'], run.get('runtime')):
            raise ValueError('run and capture runtime declarations disagree')
        if not observations._equal(normalized['evidence_scope'], attempt.get('evidence_scope')):
            raise ValueError('run and capture evidence scopes disagree')
        seen_ids.add(cid)
        serialized[filename] = text
        captures.append(capture)
    if embedded is not None and set(embedded) != set(serialized):
        raise ValueError('snapshot contains unreferenced captures')
    snapshot = dict(schema=SNAPSHOT_SCHEMA, run=deepcopy(run), captures=serialized)
    return run, captures, inputs, snapshot


def project_run(run, snapshot):
    """Project recorded group labels and exact Python text; infer no ordering."""
    records = {r['record_id']: r for r in run.get('index_records', [])}
    requests = []
    for attempt in run['attempts']:
        refs = attempt['index_association']['record_ids']
        linked = [records[r] for r in refs if r in records]
        metadata = linked[0].get('metadata', {}) if len(linked) == 1 else {}
        group = ' · '.join(k.removesuffix('_id') + ' ' + (_json(metadata[k]) if metadata.get(k) is not None else '未记录')
                           for k in ('session_id', 'process_id', 'agent_id'))
        if len(linked) > 1:
            group = '关联有歧义 · 不自动分配 session/process/agent'
        requests.append(dict(id=attempt['attempt_id'], capture_id=attempt['attempt_id'], group=group,
            label='关联 ' + attempt['index_association']['status'] + ' · 响应材料 ' +
                  attempt['selected_response_presence'] + ' · query_source=' + _json(metadata.get('query_source')),
            scope_text=('部分 request body · 仅观察 ' + '、'.join(attempt['evidence_scope']['observed_fields'])
                        if attempt['evidence_scope']['request_body'] == 'partial' else '完整 request body 文件对象；provider 呈现仍未观察'),
            exact_text=_json(dict(attempt=attempt, index_records=linked,
                source=next((s for s in run.get('sources', []) if s['id'] == attempt['source_id']), None)))))
    conditions = dict(declared_runtime=run.get('runtime'), declared_target=run.get('target'),
                      provenance='importer_declaration_not_independently_verified',
                      provider_rendering='not_observed', model_behavior='NOT_ASSESSED')
    gaps = {k: v for k, v in run.items() if k in ('content_losses', 'responses', 'events', 'dangling_references', 'limits')}
    # Index conflicts remain visible even when no request matched the record.
    gaps['unresolved_index_records'] = [r for r in run.get('index_records', [])
        if r.get('conflicts') or r.get('request_match', {}).get('status') != 'matched']
    text = _json(gaps)
    fence = '`' * max(3, max((len(r) for r in re.findall(r'`+', _json(run))), default=0) + 1)
    markdown = '# CC run evidence\n\n导入声明不是 runtime 认证；时序、provider 呈现与模型行为不推定。\n\n' + fence + 'json\n' + _json(run) + '\n' + fence + '\n'
    bundle_text = _json(snapshot)
    bundle_fence = '`' * max(3, max((len(r) for r in re.findall(r'`+', bundle_text)), default=0) + 1)
    bundle_markdown = '# CC run snapshot\n\n固定 sidecar、captures 与未评估项；不是原始日志归档或 native 认证。\n\n' + bundle_fence + 'json\n' + bundle_text + '\n' + bundle_fence + '\n'
    return dict(run_id=run['run_id'], title=run['run_id'] + ' · ' + str(len(requests)) +
        ' 份 request artifacts · 列表顺序不是实际时序', conditions_text=_json(conditions),
        requests=requests, gap_summary=(str(len(run.get('dangling_references', []))) + ' 个未选/缺失引用 · ' +
            str(len(run.get('content_losses', []))) + ' 项声明的内容损失 · ' +
            str(len(run.get('responses', []))) + ' 份响应材料 · ' + str(len(run.get('events', []))) + ' 条 event。'
            '关联只代表提交的材料声明；未匹配请求不等于请求失败，响应存在不等于送达。'),
        gaps_text=text, run_json=_json(run),
        bundle_json=bundle_text + '\n', evidence_markdown=markdown, markdown=bundle_markdown)
