"""Explicit, bounded import of locally supplied Claude Code run artifacts.

The manifest is the only source inventory. Index filenames are opaque recorded
declarations, never paths to open. Inputs are hashed before interpretation and
outputs are fully serialized before the shared writer is called.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from context_lab import artifacts, observations
from context_lab.io_policy import ensure_private_output


SELECTION_SCHEMA_V1 = 'cc-source-selection/1'
SELECTION_SCHEMA = 'cc-source-selection/2'
SELECTION_SCHEMAS = (SELECTION_SCHEMA_V1, SELECTION_SCHEMA)
RUN_SCHEMA_V1 = 'cc-run-evidence/1'
RUN_SCHEMA = 'cc-run-evidence/2'
MAX_MANIFEST_BYTES = 512 * 1024
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SOURCES = 128
MAX_INDEX_RECORDS = 10000
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
INDEX_FIELDS = (
    'timestamp', 'session_id', 'query_source', 'model', 'request_id',
    'message_id', 'message_uuid', 'request_file', 'response_file',
)
V1_SELECTION_FIELDS = {'schema', 'run_id', 'evidence_kind', 'runtime', 'sources'}
V2_SELECTION_FIELDS = V1_SELECTION_FIELDS | {'target', 'content_losses'}
SOURCE_FIELDS = {'id', 'kind', 'path', 'sha256'}
SOURCE_OPTIONAL_FIELDS = {'recorded_path', 'evidence_scope', 'metadata'}
SOURCE_KINDS_V1 = ('request', 'response', 'index')
SOURCE_KINDS = SOURCE_KINDS_V1 + ('event',)
LOSS_REASONS = ('unobserved', 'truncated', 'redacted', 'spilled_reference', 'unknown')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, field, nullable=False):
    if nullable and value is None:
        return
    _require(isinstance(value, str) and bool(value.strip()),
             field + ' must be a nonempty string' + (' or null' if nullable else ''))


def _exact_fields(value, fields, label):
    _require(isinstance(value, dict), label + ' must be an object')
    unknown = set(value) - set(fields)
    missing = set(fields) - set(value)
    if unknown or missing:
        details = []
        if missing:
            details.append('missing: ' + ', '.join(sorted(missing)))
        if unknown:
            details.append('unknown: ' + ', '.join(sorted(unknown)))
        raise ValueError(label + ' fields ' + '; '.join(details))


def _digest(value, field):
    _require(isinstance(value, str) and DIGEST.fullmatch(value),
             field + ' must be 64 lowercase hexadecimal digits')


def _json_value(value, field='$'):
    observations._json_value(value, field)


def _validate_target(target, selection_schema):
    if target is None:
        return None
    _require(selection_schema == SELECTION_SCHEMA,
             'target requires selection schema ' + SELECTION_SCHEMA)
    _exact_fields(target, {'id', 'fingerprint'}, 'target')
    _text(target['id'], 'target/id')
    _text(target['fingerprint'], 'target/fingerprint')
    return deepcopy(target)


def _validate_loss(loss, index):
    label = f'content_losses/{index}'
    _exact_fields(loss, {'kind', 'reason', 'source_id', 'path'}, label)
    _text(loss['source_id'], label + '/source_id')
    _require(isinstance(loss['kind'], str) and loss['kind'] in
             ('request', 'response', 'event', 'index'),
             label + '/kind has an unsupported value')
    _require(isinstance(loss['reason'], str) and loss['reason'] in LOSS_REASONS,
             label + '/reason has an unsupported value')
    from context_lab.cases import _decode_pointer
    _decode_pointer(loss['path'])
    return deepcopy(loss)


def _validate_content_losses(losses, selection_schema, source_kinds):
    if losses is None:
        return []
    _require(selection_schema == SELECTION_SCHEMA,
             'content_losses requires selection schema ' + SELECTION_SCHEMA)
    _require(isinstance(losses, list), 'content_losses must be an array')
    checked, seen = [], set()
    for index, loss in enumerate(losses):
        checked_loss = _validate_loss(loss, index)
        sid = checked_loss['source_id']
        _require(sid in source_kinds, 'content_losses source_id is not selected: ' + sid)
        _require(source_kinds[sid] == checked_loss['kind'],
                 'content_losses kind does not match source')
        key = (sid, checked_loss['path'], checked_loss['reason'])
        _require(key not in seen, 'duplicate content loss')
        seen.add(key)
        checked.append(checked_loss)
    return checked


def parse_selection(raw):
    """Read a strict selection manifest and normalize its declared contracts."""
    selection = observations.parse_capture_json(raw.decode('utf-8'))
    _require(isinstance(selection, dict), 'selection must be an object')
    schema = selection.get('schema')
    _require(schema in SELECTION_SCHEMAS, 'unsupported selection schema')
    if schema == SELECTION_SCHEMA_V1:
        _exact_fields(selection, V1_SELECTION_FIELDS, 'selection')
    else:
        _require(set(selection) >= V1_SELECTION_FIELDS,
                 'selection is missing required fields')
        _require(set(selection) <= V2_SELECTION_FIELDS,
                 'selection has unknown fields')
    _require(isinstance(selection['run_id'], str)
             and ID.fullmatch(selection['run_id']), 'invalid run_id')
    _require(selection['evidence_kind'] in
             ('synthetic_fixture', 'captured_request'), 'invalid evidence_kind')
    runtime = selection['runtime']
    _require(isinstance(runtime, dict)
             and set(runtime) == set(observations.RUNTIME_FIELDS),
             'runtime must contain exactly the six canonical runtime fields')
    _require(runtime['harness'] == 'Claude Code',
             'this importer is Claude Code-specific')
    _text(runtime['harness'], 'runtime/harness')
    for field in observations.RUNTIME_FIELDS[1:]:
        _require(runtime[field] is None or isinstance(runtime[field], str),
                 'runtime/' + field + ' must be a string or null')

    sources = selection['sources']
    _require(isinstance(sources, list) and 0 < len(sources) <= MAX_SOURCES,
             'invalid source count')
    ids = set()
    kinds = {}
    for index, source in enumerate(sources):
        label = f'sources/{index}'
        _require(isinstance(source, dict), label + ' must be an object')
        required = SOURCE_FIELDS
        allowed = SOURCE_FIELDS | SOURCE_OPTIONAL_FIELDS
        _require(required <= set(source) and set(source) <= allowed,
                 label + ' has invalid fields')
        sid = source['id']
        _require(isinstance(sid, str) and ID.fullmatch(sid)
                 and sid not in ids, label + '/id is invalid or duplicate')
        ids.add(sid)
        kind = source['kind']
        allowed_kinds = SOURCE_KINDS_V1 if schema == SELECTION_SCHEMA_V1 else SOURCE_KINDS
        _require(kind in allowed_kinds, label + '/kind is unsupported')
        kinds[sid] = kind
        _require(isinstance(source['path'], str) and source['path'],
                 label + '/path must be a nonempty string')
        _digest(source['sha256'], label + '/sha256')
        if 'recorded_path' in source:
            _text(source['recorded_path'], label + '/recorded_path')
        if 'evidence_scope' in source:
            _require(kind == 'request', 'scope is only valid for request sources')
            _require(isinstance(source['evidence_scope'], dict),
                     label + '/evidence_scope must be an object')
        if 'metadata' in source:
            _require(kind == 'event', 'metadata is only valid for event sources')
            _json_value(source['metadata'], label + '/metadata')
            _require(isinstance(source['metadata'], dict),
                     label + '/metadata must be an object')
        if schema == SELECTION_SCHEMA_V1:
            _require(kind in SOURCE_KINDS_V1, 'v1 selection cannot contain event sources')

    _require(any(kind in ('request', 'response', 'event') for kind in kinds.values()),
             'select at least one request, response or event')
    target = _validate_target(selection.get('target'), schema)
    losses = _validate_content_losses(
        selection.get('content_losses'), schema, kinds)
    for loss in losses:
        _require(loss['source_id'] in kinds, 'content loss source is not selected')
        _require(kinds[loss['source_id']] == loss['kind'],
                 'content loss source kind does not match')

    return deepcopy(selection)


def _bounded_regular(path, limit):
    """Read one named regular file without blocking on FIFOs or following links."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        _require(stat.S_ISREG(info.st_mode), 'input is not a regular file')
        _require(info.st_size <= limit, 'input exceeds byte limit')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            payload = stream.read(limit + 1)
        _require(len(payload) <= limit, 'input exceeds byte limit')
        return payload, (info.st_dev, info.st_ino)
    finally:
        os.close(fd)


def _selected_bytes(base, relative):
    """Traverse only named POSIX components below the selection directory."""
    _require(isinstance(relative, str) and relative and '\\' not in relative,
             'source path must be a nonempty POSIX relative path')
    parts = relative.split('/')
    _require(not PurePosixPath(relative).is_absolute()
             and all(part not in ('', '.', '..') for part in parts),
             'source path traversal or absolute path is not allowed')
    fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        file_fd = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            _require(stat.S_ISREG(info.st_mode),
                     'selected source is not a regular file')
            _require(info.st_size <= MAX_SOURCE_BYTES,
                     'selected source exceeds byte limit')
            with os.fdopen(os.dup(file_fd), 'rb') as stream:
                payload = stream.read(MAX_SOURCE_BYTES + 1)
            _require(len(payload) <= MAX_SOURCE_BYTES,
                     'selected source exceeds byte limit')
            return payload, (info.st_dev, info.st_ino)
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def _json_text(value):
    text = json.dumps(
        value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    text.encode('utf-8')
    return text


def _match_reference(reference, kind, sources):
    if reference is None:
        return {'status': 'missing_reference', 'source_ids': [],
                'basis': 'index_declaration_only'}
    if not isinstance(reference, str):
        return {'status': 'invalid_reference', 'source_ids': [],
                'basis': 'index_declaration_only'}
    matched = [source['id'] for source in sources
               if source['kind'] == kind and reference in {
                   source['path'], source.get('recorded_path')}]
    return {'status': 'matched' if len(matched) == 1 else
            ('ambiguous' if matched else 'not_selected'),
            'source_ids': matched, 'basis': 'index_declaration_only'}


def _event_record(source, value, line_number):
    _require(isinstance(value, dict), 'event file must be a JSON object')
    event_id = value.get('id')
    sequence = value.get('sequence')
    _require(event_id is not None
             or (isinstance(sequence, int) and not isinstance(sequence, bool)),
             'event must preserve a nonnull id or integer sequence')
    return {
        'source_id': source['id'],
        'source_path': source['path'],
        'source_sha256': source['sha256'],
        'line': line_number,
        'id': deepcopy(value.get('id')),
        'sequence': deepcopy(value.get('sequence')),
        'source': deepcopy(value.get('source')),
        'process': deepcopy(value.get('process')),
        'timestamp': deepcopy(value.get('timestamp')),
        'metadata': deepcopy(value),
        'metadata_basis': 'raw_event_object_with_own_identity_and_timestamp',
    }


def _index_records(source, text, sources):
    records = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        _require(len(records) < MAX_INDEX_RECORDS, 'index record limit exceeded')
        entry = observations.parse_capture_json(line)
        _require(isinstance(entry, dict), 'index line must be an object')
        records.append({
            'record_id': f'{source["id"]}:{line_number}',
            'source_id': source['id'], 'line': line_number,
            'metadata': deepcopy(entry),
            'unknown_field_names': sorted(set(entry) - set(INDEX_FIELDS)),
            'request_match': _match_reference(
                entry.get('request_file'), 'request', sources),
            'response_match': _match_reference(
                entry.get('response_file'), 'response', sources),
        })
    return records


def _load_bundle(selection_path):
    selection_raw, selection_identity = _bounded_regular(
        selection_path, MAX_MANIFEST_BYTES)
    selection = parse_selection(selection_raw)
    base = selection_path.parent.resolve()
    inputs = [selection_path]
    identities = {selection_identity}
    payloads = {}
    total = 0
    for source in selection['sources']:
        payload, identity = _selected_bytes(base, source['path'])
        _require(identity not in identities, 'duplicate/aliased source file')
        identities.add(identity)
        total += len(payload)
        _require(total <= MAX_TOTAL_BYTES,
                 'selected sources exceed aggregate byte limit')
        _require(hashlib.sha256(payload).hexdigest() == source['sha256'],
                 'SHA256 mismatch for source ' + source['id'])
        payloads[source['id']] = payload
        inputs.append(base / source['path'])
    # Every selected path has been traversed without symlinks and every byte
    # digest checked before any source JSON is decoded or interpreted.
    loaded = {
        source['id']: payloads[source['id']].decode('utf-8')
        for source in selection['sources']
    }
    return selection, selection_raw, loaded, inputs


def _run_projection(selection, selection_raw, loaded):
    schema = selection['schema']
    sources = selection['sources']
    requests = [s for s in sources if s['kind'] == 'request']
    responses = [s for s in sources if s['kind'] == 'response']
    indexes = [s for s in sources if s['kind'] == 'index']
    events = [s for s in sources if s['kind'] == 'event']

    response_objects = {}
    for source in responses:
        value = observations.parse_capture_json(loaded[source['id']])
        _require(isinstance(value, dict), 'response file must be a JSON object')
        response_objects[source['id']] = value

    records = []
    events_out = []
    for source in indexes:
        records.extend(_index_records(source, loaded[source['id']], sources))
        _require(len(records) <= MAX_INDEX_RECORDS, 'aggregate index record limit exceeded')
    for source in events:
        value = observations.parse_capture_json(loaded[source['id']])
        events_out.append(_event_record(source, value, 1))

    associations = {}
    for source in requests:
        relevant = [
            record for record in records
            if source['id'] in record['request_match']['source_ids']
        ]
        unique = len(relevant) == 1 \
            and relevant[0]['request_match']['status'] == 'matched'
        associations[source['id']] = {
            'status': 'matched' if unique else
                      ('ambiguous' if relevant else 'unindexed'),
            'basis': 'index_recorded_declaration' if relevant else 'none',
            'record_ids': [record['record_id'] for record in relevant],
        }

    request_id_counts = {}
    response_source_counts = {}
    for record in records:
        request_id = record['metadata'].get('request_id')
        if request_id is not None:
            key = json.dumps(
                request_id, sort_keys=True, ensure_ascii=False)
            request_id_counts[key] = request_id_counts.get(key, 0) + 1
        for sid in record['response_match']['source_ids']:
            response_source_counts[sid] = response_source_counts.get(sid, 0) + 1

    for record in records:
        conflicts = []
        response_match = record['response_match']
        message_id = record['metadata'].get('message_id')
        consistency = {
            'status': 'not_assessed', 'consistent': None,
            'basis': 'index_message_id_vs_selected_response_id',
        }
        if response_match['status'] == 'matched' and message_id is not None:
            response = response_objects[response_match['source_ids'][0]]
            response_id = response.get('id')
            if response_id is not None:
                consistent = observations._equal(message_id, response_id)
                consistency.update(
                    status='consistent' if consistent else 'mismatch',
                    consistent=consistent,
                    index_message_id=deepcopy(message_id),
                    selected_response_id=deepcopy(response_id))
                if not consistent:
                    conflicts.append('response_content_mismatch')
        record['response_content_consistency'] = consistency
        request_id = record['metadata'].get('request_id')
        if request_id is not None and request_id_counts[
                json.dumps(request_id, sort_keys=True, ensure_ascii=False)] > 1:
            conflicts.append('repeated_request_id')
        response_ids = response_match['source_ids']
        if any(response_source_counts[sid] > 1 for sid in response_ids):
            conflicts.append('shared_response_reference')
        if (record['request_match']['status'] == 'ambiguous'
                or response_match['status'] == 'ambiguous'):
            conflicts.append('ambiguous_source_alias')
        for sid in record['request_match']['source_ids']:
            if associations[sid]['status'] == 'ambiguous':
                conflicts.append('multiple_or_ambiguous_index_records')
        record['conflicts'] = sorted(set(conflicts))
        record['association_status'] = 'conflict' if conflicts else 'recorded_only'

    for sid, association in associations.items():
        relevant = [
            record for record in records
            if sid in record['request_match']['source_ids']]
        if any('response_content_mismatch' in record['conflicts']
               for record in relevant):
            association['status'] = 'conflict'
        elif any(record['conflicts'] for record in relevant):
            association['status'] = 'ambiguous'

    capture_contents = []
    attempts = []
    for source in requests:
        sid = source['id']
        body = observations.parse_capture_json(loaded[sid])
        _require(isinstance(body, dict), 'request file must be a JSON object')
        capture = {
            'schema': observations.CAPTURE_SCHEMA,
            'capture_id': selection['run_id'] + ':' + sid,
            'evidence': {
                'kind': selection['evidence_kind'], 'observed_at': None},
            'runtime': deepcopy(selection['runtime']),
            'wire_format': 'anthropic-messages', 'body': body,
        }
        if 'evidence_scope' in source:
            capture['evidence_scope'] = deepcopy(source['evidence_scope'])
        normalized = observations.normalize_capture(capture)
        serialized = _json_text(capture)
        filename = sid + '.capture.json'
        capture_contents.append((filename, serialized))
        association = associations[sid]
        relevant = [
            record for record in records
            if record['record_id'] in association['record_ids']]
        selected_response_ids = sorted({
            rid for record in relevant
            for rid in record['response_match']['source_ids']})
        if association['status'] == 'matched' and relevant:
            response = deepcopy(relevant[0]['response_match'])
        else:
            response = {
                'status': association['status'] if selected_response_ids
                else 'unassessed',
                'source_ids': selected_response_ids,
            }
        if selected_response_ids:
            presence, missing = 'present', False
        elif (association['status'] == 'matched' and relevant
              and response['status'] == 'not_selected'):
            presence, missing = 'not_selected', True
        else:
            presence, missing = 'unassessed', None
        attempts.append({
            'attempt_id': selection['run_id'] + ':' + sid,
            'attempt_identity_basis':
                'one_selected_request_artifact_not_runtime_retry_identity',
            'source_id': sid, 'source_sha256': source['sha256'],
            'capture_file': filename,
            'capture_sha256': hashlib.sha256(
                serialized.encode('utf-8')).hexdigest(),
            'evidence_scope': normalized['evidence_scope'],
            'index_association': association,
            'response_association': response,
            'selected_response_presence': presence,
            'missing_selected_response': missing,
        })

    selected_response_presence = {}
    for source in responses:
        related = [
            record for record in records
            if source['id'] in record['response_match']['source_ids']]
        selected_response_presence[source['id']] = {
            'selected': True,
            'association_record_ids': [
                record['record_id'] for record in related],
        }

    dangling = [
        {'record_id': record['record_id'], 'field': kind + '_file',
         'recorded_reference': deepcopy(
             record['metadata'].get(kind + '_file')),
         'status': record[kind + '_match']['status']}
        for record in records for kind in ('request', 'response')
        if record[kind + '_match']['status'] in
        ('not_selected', 'missing_reference', 'invalid_reference')
    ]
    run_schema = RUN_SCHEMA_V1 if schema == SELECTION_SCHEMA_V1 else RUN_SCHEMA
    run = {
        'schema': run_schema,
        'run_id': selection['run_id'],
        'selection_schema': schema,
        'selection_sha256': hashlib.sha256(selection_raw).hexdigest(),
        'declared_evidence_kind': selection['evidence_kind'],
        'runtime': deepcopy(selection['runtime']),
        'target': deepcopy(selection.get('target')),
        'content_losses': deepcopy(selection.get('content_losses', [])),
        'sources': deepcopy(sources),
        'attempts': attempts,
        'responses': [
            {'source_id': source['id'], 'source_sha256': source['sha256'],
             'source_path': source['path'], 'body': deepcopy(response_objects[source['id']]),
             'association_record_ids': selected_response_presence[
                 source['id']]['association_record_ids']}
            for source in responses],
        'events': events_out,
        'index_records': records,
        'dangling_references': dangling,
        'limits': {
            'adapter_validation':
                'documented_shape_synthetic_tested_not_native_format_verified',
            'runtime_provenance':
                'importer_declaration_not_independently_verified',
            'target_fingerprint':
                'declared_string_not_hash_checked_against_native_binary',
            'index_association': 'recorded_only_not_provider_receipt',
            'redaction_possible': True,
            'content_losses': 'declared_not_inferred_from_source_bytes',
            'model_visibility': 'not_observed',
            'retry_identity': 'not_inferred',
            'chronology': 'not_inferred',
            'event_order': 'selection_source_order_not_global_time_order',
            'provider_delivery': 'not_assessed',
            'model_behavior': 'not_assessed',
            'acquisition_performed': False,
            'native_binary_executed': False,
            'model_called': False,
            'log_discovery': False,
            'unselected_refs_loaded': False,
        },
    }
    return run, capture_contents


def import_run(repo_root, selection_path, output_dir):
    """Import one explicit selection; return ``(run, output_targets)``."""
    repo_root = Path(repo_root).resolve()
    _require((repo_root / 'context_lab' / 'observations.py').is_file(),
             'repo_root is not a lab source tree')
    selection_path = Path(selection_path)
    output_dir = Path(output_dir)
    selection, selection_raw, loaded, inputs = _load_bundle(selection_path)
    run, captures = _run_projection(
        selection, selection_raw, loaded)
    contents = [(output_dir / filename, text) for filename, text in captures]
    contents.append((output_dir / 'run.json', _json_text(run)))
    targets = [target for target, _ in contents]
    ensure_private_output(output_dir, repo_root, targets)
    for target in targets:
        for incoming in inputs:
            _require(not artifacts.paths_alias(incoming, target),
                     'input/output alias is not allowed: ' + str(target))
    artifacts.write_reports(contents, output_dir)
    return run, targets
