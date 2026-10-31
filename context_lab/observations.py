"""Lossless structural observations of explicitly supplied request captures.

This is not a provider SDK validator or an origin/lifecycle classifier. A JSON
pointer identifies a location in a body, never the identity of a context source.
No paths, URLs, headers, templates or server-side state are followed.
"""

from copy import deepcopy
from datetime import datetime
import json
import math
import re


RUNTIME_FIELDS = ('harness', 'version', 'entrypoint', 'mode', 'candidate', 'session_path')
CAPTURE_SCHEMA = 'harness-context-capture/1'
OBSERVATION_SCHEMA = 'harness-context-observation/1'
COMPARISON_SCHEMA = 'harness-context-comparison/1'
BODY_SCOPES = ('complete', 'partial')


def _error(field, message):
    raise ValueError(f'{field}: {message}')


def _json_value(value, field='$', ancestors=None):
    """Reject non-JSON Python values as well as non-finite/cyclic source data."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _error(field, 'must be a finite JSON number')
        return
    if type(value) not in (dict, list):
        _error(field, 'must be a JSON value')
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        _error(field, 'cyclic values are not JSON')
    ancestors.add(id(value))
    try:
        if isinstance(value, dict):
            for key, item in value.items():
                if type(key) is not str:
                    _error(field, 'object keys must be strings')
                _json_value(item, field + '/' + key.replace('~', '~0').replace('/', '~1'), ancestors)
        else:
            for index, item in enumerate(value):
                _json_value(item, f'{field}/{index}', ancestors)
    finally:
        ancestors.remove(id(value))


def parse_capture_json(text):
    """Read strict JSON without silently dropping duplicate object keys."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _error('$', f'duplicate JSON object key {key!r}')
            result[key] = value
        return result

    def constant(value):
        _error('$', 'invalid JSON numeric constant ' + value)

    try:
        capture = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError('$: invalid JSON: ' + str(exc)) from exc
    _json_value(capture)
    return capture


def _object(value, field):
    if not isinstance(value, dict):
        _error(field, 'must be an object')


def _text(value, field, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        _error(field, 'must be a nonempty string' + (' or null' if nullable else ''))


def _keys(value, allowed, field):
    unknown = set(value) - set(allowed)
    if unknown:
        _error(field, 'unknown manifest fields: ' + ', '.join(sorted(unknown)))


def _section(pointer, kind, value, role=None):
    return {'id': pointer, 'pointer': pointer, 'kind': kind, 'role': role,
            'origin': 'unknown', 'lifecycle': 'unknown', 'value': deepcopy(value)}


def _objects(value, field):
    if not isinstance(value, list):
        _error(field, 'must be an array')
    for index, item in enumerate(value):
        _object(item, f'{field}/{index}')


def _content(value, field):
    if not isinstance(value, (str, list)):
        _error(field, 'must be a string or array')
    if isinstance(value, list):
        _objects(value, field)


def _evidence_scope(capture, body, normalized=False):
    """Return an explicit top-level body scope; omission preserves v1 complete."""
    if 'evidence_scope' not in capture:
        return {'request_body': 'complete', 'observed_fields': None}
    scope = capture['evidence_scope']
    _object(scope, 'evidence_scope')
    if normalized:
        _keys(scope, ('request_body', 'observed_fields'), 'evidence_scope')
    elif (not isinstance(capture['evidence_scope'], dict)
          or capture['evidence_scope'].get('request_body') == 'partial'):
        _keys(scope, ('request_body', 'observed_fields'), 'evidence_scope')
    request_body = scope.get('request_body')
    if request_body not in BODY_SCOPES:
        _error('evidence_scope/request_body',
               'expected one of ' + ', '.join(BODY_SCOPES))
    if request_body == 'complete':
        _keys(scope, ('request_body', 'observed_fields')
              if normalized else ('request_body',), 'evidence_scope')
        return {'request_body': 'complete', 'observed_fields': None}
    _keys(scope, ('request_body', 'observed_fields'), 'evidence_scope')
    fields = scope.get('observed_fields')
    if not isinstance(fields, list) or not fields:
        _error('evidence_scope/observed_fields',
               'must be a nonempty array for partial request body evidence')
    seen = set()
    for index, field in enumerate(fields):
        _text(field, f'evidence_scope/observed_fields/{index}')
        if field in seen:
            _error(f'evidence_scope/observed_fields/{index}', 'duplicate field')
        seen.add(field)
    omitted = set(body) - seen
    if omitted:
        _error('evidence_scope/observed_fields',
               'must include every top-level body field present; missing: '
               + ', '.join(sorted(omitted)))
    return {'request_body': 'partial',
            'observed_fields': sorted(deepcopy(fields))}


def _body_field_observed(observation, field):
    scope = observation['evidence_scope']
    return (scope['request_body'] == 'complete'
            or field in scope['observed_fields'])


def _observed_fields(observation):
    scope = observation['evidence_scope']
    if scope['request_body'] == 'complete':
        return set(observation['request_body'])
    return set(scope['observed_fields'])


def _field_observed_on_both(a, b, field):
    return (_body_field_observed(a, field)
            and _body_field_observed(b, field))


def normalize_capture(capture, *, _normalized_replay=False):
    """Preserve the body and project native structural sections without inference."""
    _json_value(capture)
    _object(capture, '$')
    _keys(capture, ('schema', 'capture_id', 'evidence', 'runtime', 'wire_format',
                    'body', 'evidence_scope'), '$')
    if capture.get('schema') != CAPTURE_SCHEMA:
        _error('schema', 'expected ' + CAPTURE_SCHEMA)
    _text(capture.get('capture_id'), 'capture_id')
    evidence = capture.get('evidence')
    _object(evidence, 'evidence')
    _keys(evidence, ('kind', 'observed_at'), 'evidence')
    if evidence.get('kind') not in ('synthetic_fixture', 'captured_request'):
        _error('evidence/kind', 'expected synthetic_fixture or captured_request')
    if 'observed_at' not in evidence:
        _error('evidence/observed_at', 'required; use null when unknown')
    observed_at = evidence['observed_at']
    if observed_at is not None:
        _text(observed_at, 'evidence/observed_at')
        try:
            if 'T' not in observed_at:
                raise ValueError('missing time')
            datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
        except ValueError:
            _error('evidence/observed_at', 'must be an ISO datetime string or null')
    runtime = capture.get('runtime')
    _object(runtime, 'runtime')
    _keys(runtime, RUNTIME_FIELDS, 'runtime')
    _text(runtime.get('harness'), 'runtime/harness')
    for key in RUNTIME_FIELDS[1:]:
        if runtime.get(key) is not None and not isinstance(runtime[key], str):
            _error('runtime/' + key, 'must be a string or null')
    wire_format = capture.get('wire_format')
    if wire_format not in ('anthropic-messages', 'openai-responses'):
        _error('wire_format', 'expected anthropic-messages or openai-responses')
    body = capture.get('body')
    _object(body, 'body')
    evidence_scope = _evidence_scope(capture, body, _normalized_replay)
    partial_body = evidence_scope['request_body'] == 'partial'
    sections, unresolved = [], []
    limitations = [
        '证据种类与运行条件来自导入 manifest，未经独立 runtime 验证；合成 fixture 始终是合成证据。',
        '这里只读取请求结构，不是完整 provider SDK 校验；role 与数组位置不能证明真实人类来源或 current/history 生命周期。',
        '不读取 headers，不跟随文件路径、URL 或引用，不重建未展开内容；模型行为与外部交付均未评估。',
        '原始请求与报告可能含私人数据；默认输出仅保存在本地 .cache，不应提交到 Git。',
    ]
    if partial_body:
        fields = ', '.join('/' + field for field in evidence_scope['observed_fields'])
        limitations.extend([
            f'证据范围：request body 为 partial，仅声明观察顶层字段 {fields}；'
            '未列出的顶层字段是“未观察”，不是“不存在”。',
            '部分请求形状只覆盖导入材料声明的字段，不能证明 server/provider 注入、'
            '模型收到、完整 context 或真实生命周期。',
        ])
    if wire_format == 'anthropic-messages':
        for key in ('input', 'instructions', 'previous_response_id', 'conversation', 'prompt'):
            if key in body:
                _error('body/' + key, 'belongs to a different declared wire format')
        structural = {'system', 'messages', 'tools'}
        if 'system' in body:
            _content(body['system'], 'body/system')
            sections.append(_section('/system', 'instructions', body['system']))
        if 'messages' in body:
            _objects(body['messages'], 'body/messages')
            for index, item in enumerate(body['messages']):
                _text(item.get('role'), f'body/messages/{index}/role')
                _content(item.get('content'), f'body/messages/{index}/content')
                sections.append(_section(f'/messages/{index}', 'message', item, item['role']))
        elif not partial_body:
            _error('body/messages', 'required for complete Anthropic request body evidence')
    else:
        for key in ('messages', 'system'):
            if key in body:
                _error('body/' + key, 'belongs to a different declared wire format')
        structural = {'instructions', 'input', 'tools'}
        for key in ('previous_response_id', 'conversation', 'prompt'):
            if key in body and body[key] is not None:
                unresolved.append(f'/{key}: 引用的 server-side 或模板内容未重建；本地仅保留显式值。')
        if 'instructions' in body:
            if not isinstance(body['instructions'], (str, list)):
                _error('body/instructions', 'must be a string or array')
            sections.append(_section('/instructions', 'instructions', body['instructions']))
        if 'input' not in body:
            if not unresolved:
                if not partial_body:
                    _error('body/input', 'required unless previous_response_id, conversation or prompt references state')
        elif isinstance(body['input'], str):
            sections.append(_section('/input', 'message', body['input'], 'user'))
            limitations.append('Responses 的 string input 按接口简写标为 user；该标签不证明文本由真实人类产生。')
        else:
            _objects(body['input'], 'body/input')
            for index, item in enumerate(body['input']):
                role = item.get('role')
                if role is not None:
                    _text(role, f'body/input/{index}/role')
                kind = 'message' if role is not None and item.get('type', 'message') == 'message' else 'opaque'
                if kind == 'message':
                    _content(item.get('content'), f'body/input/{index}/content')
                sections.append(_section(f'/input/{index}', kind, item, role))
        if unresolved:
            limitations.append('存在 server-side/unexpanded context；本地 sections 不代表完整上下文，未虚构缺失历史。')
    if 'tools' in body:
        _objects(body['tools'], 'body/tools')
        for index, tool in enumerate(body['tools']):
            sections.append(_section(f'/tools/{index}', 'tool', tool))
    return {
        'schema': OBSERVATION_SCHEMA, 'capture_id': capture['capture_id'],
        'evidence': {**deepcopy(evidence), 'provenance': 'imported_manifest',
                     'model_behavior': 'NOT_ASSESSED', 'external_delivery': 'NOT_ASSESSED'},
        'runtime': {key: runtime.get(key) for key in RUNTIME_FIELDS},
        'evidence_scope': deepcopy(evidence_scope),
        'wire_format': wire_format, 'request_body': deepcopy(body), 'sections': sections,
        'request_parameters': {key: deepcopy(value) for key, value in body.items() if key not in structural},
        'limitations': limitations, 'unresolved_context': unresolved,
    }


def _equal(left, right):
    # JSON booleans are not numbers even though Python's True == 1.
    if type(left) is not type(right):
        return type(left) in (int, float) and type(right) in (int, float) and left == right
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def compare_observations(a, b):
    """Compare normalized observations by location, never causality or quality."""
    for label, observation in (('baseline', a), ('candidate', b)):
        _json_value(observation, label)
        _object(observation, label)
        if observation.get('schema') != OBSERVATION_SCHEMA:
            _error(label + '/schema', 'expected ' + OBSERVATION_SCHEMA)
        _object(observation.get('evidence'), label + '/evidence')
        # Re-read source data to reject malformed or misleading normalized inputs.
        capture = {
            'schema': CAPTURE_SCHEMA, 'capture_id': observation.get('capture_id'),
            'evidence': {key: observation.get('evidence', {}).get(key) for key in ('kind', 'observed_at')},
            'runtime': observation.get('runtime'), 'wire_format': observation.get('wire_format'),
            'body': observation.get('request_body'),
        }
        scope = observation.get('evidence_scope')
        if isinstance(scope, dict):
            capture['evidence_scope'] = scope
        checked = normalize_capture(capture, _normalized_replay=True)
        if not _equal(checked, observation):
            _error(label, 'must be an unmodified normalized observation')
    same_format = a['wire_format'] == b['wire_format']
    rows = []
    if same_format:
        baseline = {section['pointer']: section for section in a['sections']}
        candidate = {section['pointer']: section for section in b['sections']}
        for pointer in dict.fromkeys([*baseline, *candidate]):
            left, right = baseline.get(pointer), candidate.get(pointer)
            field = pointer.split('/', 2)[1] if pointer.startswith('/') else None
            left_observed = field is not None and _body_field_observed(a, field)
            right_observed = field is not None and _body_field_observed(b, field)
            if (left is None and not left_observed) or (
                    right is None and not right_observed):
                change = 'unobserved'
            else:
                change = ('added' if left is None else
                          'removed' if right is None else
                          'unchanged' if _equal(left, right) else 'modified')
            rows.append({'pointer': pointer, 'change': change,
                         'baseline_observed': left_observed,
                         'candidate_observed': right_observed,
                         'baseline': deepcopy(left), 'candidate': deepcopy(right)})
    else:
        for label, observation, change in (('baseline', a, 'removed'), ('candidate', b, 'added')):
            for section in observation['sections']:
                field = section['pointer'].split('/', 2)[1]
                baseline_observed = _body_field_observed(a, field)
                candidate_observed = _body_field_observed(b, field)
                rows.append({
                             'pointer': section['pointer'],
                             'change': ('unobserved'
                                        if not (baseline_observed
                                                and candidate_observed)
                                        else change),
                             'baseline_observed': baseline_observed,
                             'candidate_observed': candidate_observed,
                             'baseline': deepcopy(section) if label == 'baseline' else None,
                             'candidate': deepcopy(section) if label == 'candidate' else None})
    fields = sorted(_observed_fields(a) | _observed_fields(b))
    comparable_fields = [
        key for key in fields
        if _field_observed_on_both(a, b, key)
    ]
    unobserved_fields = [
        key for key in fields
        if not _field_observed_on_both(a, b, key)
    ]
    both_complete = (
        a['evidence_scope']['request_body'] == 'complete'
        and b['evidence_scope']['request_body'] == 'complete')
    same_scope = _equal(a['evidence_scope'], b['evidence_scope'])
    request_body_equal = (
        _equal(a['request_body'], b['request_body']) if both_complete else
        None if not comparable_fields else
        all((key in a['request_body']) == (key in b['request_body'])
            and (key not in a['request_body']
                 or _equal(a['request_body'][key], b['request_body'][key]))
            for key in comparable_fields)
    )
    return {
        'schema': COMPARISON_SCHEMA, 'baseline': deepcopy(a), 'candidate': deepcopy(b),
        'alignment': 'same_format_json_pointer' if same_format else 'cross_format_unaligned',
        'runtime_changes': [key for key in RUNTIME_FIELDS if not _equal(a['runtime'][key], b['runtime'][key])],
        'evidence_scope_alignment': (
            'complete' if both_complete else
            'same_partial_scope' if same_scope else
            'partial_scope_mismatch'),
        'comparable_top_level_fields': comparable_fields,
        'unobserved_top_level_fields': unobserved_fields,
        'changed_top_level_fields': [
            key for key in comparable_fields
            if ((key in a['request_body'])
                != (key in b['request_body'])
                or (key in a['request_body']
                    and not _equal(a['request_body'][key],
                                   b['request_body'][key])))
        ],
        'request_body_equal': request_body_equal,
        'request_body_equal_scope': (
            'complete' if both_complete else
            'comparable_observed_fields' if comparable_fields else
            'no_comparable_fields'),
        'sections': rows,
        'limitations': [
            '同格式仅按 JSON pointer 对齐；位置相同不代表来源身份相同，不构成单因果结论或 harness 质量排名。',
            ('跨格式不自动配对正文或声称 provider 语义等价；'
             + ('baseline 全部移除、candidate 全部新增。'
                if both_complete else
                '与另一侧未同时观察的 row 标为 unobserved，不声称删除或新增。'))
            if not same_format else
            '省略字段与显式空值分别比较；对象键顺序忽略，字符串空白与数组顺序保留。',
            ('至少一侧只观察部分 request body；只比较双方声明的 top-level 字段，'
             '其余字段标为未观察，不作为 added/removed 或完整相等结论。'
             if not both_complete else
             '双方均声明完整 request body；这只描述导入文件对象，不证明模型可见 context 完整。'),
            '比较保留双方完整证据与条件；导入声明不是独立 runtime 验证，模型行为与外部交付未评估。',
        ],
    }


def _json_block(value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    fence = '`' * max(3, max((len(run) for run in re.findall(r'`+', text)), default=0) + 1)
    return f'{fence}json\n{text}\n{fence}\n'


def _single_markdown(observation):
    partial = observation['evidence_scope']['request_body'] == 'partial'
    lines = [f"## Capture {json.dumps(observation['capture_id'], ensure_ascii=False)}\n",
             '### 证据层、范围与运行条件\n',
             _json_block({'evidence': observation['evidence'],
                          'evidence_scope': observation['evidence_scope'],
                          'runtime': observation['runtime'],
                          'wire_format': observation['wire_format']}),
             '### 限制与缺口\n']
    lines.extend('- ' + value + '\n' for value in observation['limitations'] + observation['unresolved_context'])
    lines.append('\n### ' + ('观察到的结构段\n' if partial else '完整结构段\n'))
    for section in observation['sections']:
        lines.extend([f"#### {section['pointer']} · {section['kind']}\n",
                      f"role={json.dumps(section['role'])}；origin=unknown；lifecycle=unknown。\n",
                      _json_block(section['value'])])
    lines.extend([
        '### ' + ('观察到的其余请求参数\n' if partial else '其余请求参数\n'),
        _json_block(observation['request_parameters']),
        '### ' + ('声明的部分原始 request body（不是完整请求）\n' if partial
                  else '完整原始 request body\n'),
        _json_block(observation['request_body']),
    ])
    return '\n'.join(lines)


def render_markdown(report):
    """Render exact section JSON values, evidence conditions and known gaps."""
    if report.get('schema') == OBSERVATION_SCHEMA:
        return '# 请求 context 结构观察\n\n' + _single_markdown(report) + '\n'
    if report.get('schema') != COMPARISON_SCHEMA:
        _error('schema', 'expected an observation or comparison')
    lines = ['# 请求 context 结构比较\n',
             _json_block({key: report[key] for key in (
                 'alignment', 'evidence_scope_alignment', 'runtime_changes',
                 'comparable_top_level_fields', 'unobserved_top_level_fields',
                 'changed_top_level_fields', 'request_body_equal',
                 'request_body_equal_scope')}),
             '## 比较限制\n']
    lines.extend('- ' + value + '\n' for value in report['limitations'])
    lines.append('\n## 逐位置变化\n')
    for row in report['sections']:
        lines.append(f"- {row['pointer']}: {row['change']}\n")
    lines.extend(['\n## Baseline\n', _single_markdown(report['baseline']),
                  '\n## Candidate\n', _single_markdown(report['candidate'])])
    return '\n'.join(lines) + '\n'
