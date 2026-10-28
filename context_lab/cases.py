"""Durable, self-contained research cases over explicit request captures.

Cases keep one question and its requirements together with declared stages,
optional canonical study snapshots, scoped request-structure checks and
explicit A/B comparisons. They do not trace, schedule, call a model or judge
semantic correctness.
"""

from copy import deepcopy
import json
import re

from context_lab import observations

CASE_SCHEMA = 'harness-context-case/1'
RESULT_SCHEMA = 'harness-context-case-result/1'
STUDY_RESULT_SCHEMA = 'cc-context-study-result/1'
LEVELS = ('request_structure', 'model_behavior', 'external_delivery')
OPERATORS = ('exists', 'absent', 'equals', 'contains_text')


def _error(field, message):
    raise ValueError(field + ': ' + message)


def _object(value, field):
    if not isinstance(value, dict):
        _error(field, 'expected object')


def _exact_fields(value, fields, field):
    _object(value, field)
    unknown = set(value) - set(fields)
    missing = set(fields) - set(value)
    if unknown or missing:
        details = []
        if missing:
            details.append('missing fields: ' + ', '.join(sorted(missing)))
        if unknown:
            details.append('unknown fields: ' + ', '.join(sorted(unknown)))
        _error(field, '; '.join(details))


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _error(field, 'expected nonempty string')


def _array(value, field, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        _error(field, 'expected ' + ('nonempty ' if nonempty else '') + 'array')


def _unique_records(items, field, fields, nonempty=False):
    _array(items, field, nonempty)
    ids = set()
    for index, item in enumerate(items):
        label = f'{field}/{index}'
        _exact_fields(item, fields, label)
        _text(item['id'], label + '/id')
        if item['id'] in ids:
            _error(label + '/id', 'duplicate ID')
        ids.add(item['id'])
    return ids


def _decode_pointer(pointer):
    """Validate RFC6901 string form for a pointer relative to a JSON body."""
    if not isinstance(pointer, str):
        _error('pointer', 'expected RFC6901 string')
    if not pointer:
        return []
    if not pointer.startswith('/'):
        _error('pointer', 'must be empty or start with /')
    # # and * are ordinary key characters in string-form pointers.
    # A leading URI fragment was already rejected; no token is expanded.
    tokens = []
    for raw in pointer.split('/')[1:]:
        index = 0
        while index < len(raw):
            if raw[index] == '~':
                if index + 1 >= len(raw) or raw[index + 1] not in '01':
                    _error('pointer', 'invalid ~ escape in ' + repr(raw))
                index += 2
            else:
                index += 1
        tokens.append(raw.replace('~1', '/').replace('~0', '~'))
    return tokens


def _validate_check(check, field, requirement_by_id, step_ids):
    _exact_fields(check, ('id', 'requirement_id', 'step_id', 'pointer',
                          'operator', 'expected'), field)
    for key in ('id', 'requirement_id', 'step_id'):
        _text(check[key], field + '/' + key)
    requirement = requirement_by_id.get(check['requirement_id'])
    if requirement is None:
        _error(field + '/requirement_id', 'unknown requirement')
    if requirement['level'] != 'request_structure':
        _error(field + '/requirement_id',
               'only request_structure requirements may have checks')
    if check['step_id'] not in step_ids:
        _error(field + '/step_id', 'unknown step')
    _decode_pointer(check['pointer'])
    operator = check['operator']
    if operator not in OPERATORS:
        _error(field + '/operator', 'expected one of ' + ', '.join(OPERATORS))
    expected = check['expected']
    if operator in ('exists', 'absent'):
        if expected is not None:
            _error(field + '/expected', 'must be null for ' + operator)
    elif operator == 'contains_text':
        if not isinstance(expected, str) or not expected:
            _error(field + '/expected', 'expected nonempty literal string')
    else:
        observations._json_value(expected, field + '/expected')


def validate_case(manifest):
    """Validate the frozen case structure and return an independent snapshot."""
    observations._json_value(manifest, '$')
    _exact_fields(manifest, ('schema', 'case_id', 'title', 'question',
                             'requirements', 'study_plan', 'steps',
                             'comparisons', 'checks'), '$')
    if manifest['schema'] != CASE_SCHEMA:
        _error('schema', 'expected ' + CASE_SCHEMA)
    for key in ('case_id', 'title', 'question'):
        _text(manifest[key], key)

    _unique_records(
        manifest['requirements'], 'requirements', ('id', 'text', 'level'), True)
    requirement_by_id = {}
    for index, requirement in enumerate(manifest['requirements']):
        label = f'requirements/{index}'
        _text(requirement['text'], label + '/text')
        if requirement['level'] not in LEVELS:
            _error(label + '/level', 'expected one of ' + ', '.join(LEVELS))
        requirement_by_id[requirement['id']] = requirement

    if manifest['study_plan'] is not None:
        _object(manifest['study_plan'], 'study_plan')

    step_ids = _unique_records(
        manifest['steps'], 'steps', ('id', 'label', 'capture'), True)
    capture_ids = set()
    for index, step in enumerate(manifest['steps']):
        label = f'steps/{index}'
        _text(step['label'], label + '/label')
        capture = step['capture']
        if capture is None:
            continue
        observations.normalize_capture(capture)
        capture_id = capture['capture_id']
        if capture_id in capture_ids:
            _error(label + '/capture/capture_id',
                   'duplicate capture ID among nonnull steps')
        capture_ids.add(capture_id)

    _unique_records(
        manifest['comparisons'], 'comparisons', ('id', 'baseline', 'candidate'))
    for index, comparison in enumerate(manifest['comparisons']):
        label = f'comparisons/{index}'
        _text(comparison['baseline'], label + '/baseline')
        _text(comparison['candidate'], label + '/candidate')
        if comparison['baseline'] not in step_ids:
            _error(label + '/baseline', 'unknown step')
        if comparison['candidate'] not in step_ids:
            _error(label + '/candidate', 'unknown step')
        if comparison['baseline'] == comparison['candidate']:
            _error(label, 'baseline and candidate must differ')

    _unique_records(
        manifest['checks'], 'checks',
        ('id', 'requirement_id', 'step_id', 'pointer', 'operator', 'expected'))
    for index, check in enumerate(manifest['checks']):
        _validate_check(check, f'checks/{index}', requirement_by_id, step_ids)
    return deepcopy(manifest)


def _resolve_pointer(body, pointer):
    """Return (state, value), where state is present/absent/blocked."""
    tokens = _decode_pointer(pointer)
    value = body
    if not tokens:
        return 'present', value
    for index, token in enumerate(tokens):
        final = index == len(tokens) - 1
        if isinstance(value, dict):
            if token not in value:
                return ('absent' if final else 'blocked'), None
            value = value[token]
        elif isinstance(value, list):
            # RFC6901 array indices are canonical nonnegative integers. "-"
            # is an append operation, not an existing or missing member.
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                return 'blocked', None
            # Compare decimal widths before conversion; arbitrarily large
            # canonical indices are out of range, not Python int errors.
            last = str(len(value) - 1)
            if not value or len(token) > len(last) or (len(token) == len(last) and token > last):
                return ('absent' if final else 'blocked'), None
            value = value[int(token)]
        else:
            return 'blocked', None
    return 'present', value


def _evaluate_check(check, observations_by_step):
    observation = observations_by_step.get(check['step_id'])
    if observation is None:
        return {
            **deepcopy(check), 'status': 'NOT_ASSESSED', 'actual_present': None,
            'actual': None,
            'reason': '该步骤没有 capture 证据；不能把缺失提交物当成请求中缺少字段。',
        }
    state, actual = _resolve_pointer(
        observation['request_body'], check['pointer'])
    if state == 'blocked':
        reason = (
            '指针遍历被缺失祖先、类型不匹配或无效数组索引阻断；'
            '只检查显式 request body，无法判断该位置是否缺少。')
        return {
            **deepcopy(check), 'status': 'NOT_ASSESSED', 'actual_present': None,
            'actual': None, 'reason': reason,
        }
    present = state == 'present'
    operator = check['operator']
    expected = check['expected']
    if operator == 'exists':
        passed = present
    elif operator == 'absent':
        passed = not present
    elif operator == 'equals':
        passed = present and observations._equal(actual, expected)
    else:
        passed = present and isinstance(actual, str) and expected in actual
    status = 'PASS' if passed else 'FAIL'
    if operator == 'exists':
        reason = '显式 body 中该位置存在。' if passed else '显式 body 中该位置不存在。'
    elif operator == 'absent':
        reason = '显式 body 中该位置不存在。' if passed else '显式 body 中该位置存在。'
    elif operator == 'equals':
        if not present:
            reason = '显式 body 中该位置不存在，因此不满足 equals。'
        elif passed:
            reason = '显式 body 中的值与 expected 分类型相等。'
        else:
            reason = '显式 body 中的值与 expected 不相等；空白、Unicode 与数组顺序均未归一化。'
    elif not present:
        reason = '显式 body 中该位置不存在，因此不满足 contains_text。'
    elif not isinstance(actual, str):
        reason = '解析结果不是字符串；contains_text 不回退到递归字符串化。'
    elif passed:
        reason = '解析出的字符串按原样包含 expected。'
    else:
        reason = '解析出的字符串按原样不包含 expected；没有隐式文本归一化。'
    return {
        **deepcopy(check), 'status': status, 'actual_present': present,
        'actual': deepcopy(actual), 'reason': reason,
    }


def run_case(manifest, study_runner=None):
    """Run one validated case without inference, model calls or transport."""
    case = validate_case(manifest)
    study = None
    if case['study_plan'] is not None:
        if study_runner is None:
            raise ValueError('study_plan requires a study_runner callback')
        study_result = study_runner(deepcopy(case['study_plan']))
        if not isinstance(study_result, dict):
            raise ValueError('study_runner: expected canonical study result object')
        if study_result.get('schema') != STUDY_RESULT_SCHEMA:
            raise ValueError(
                'study_runner/schema: expected ' + STUDY_RESULT_SCHEMA)
        observations._json_value(study_result, 'study_runner')
        study = deepcopy(study_result)

    observations_by_step = {}
    steps = []
    for step in case['steps']:
        observation = (
            observations.normalize_capture(step['capture'])
            if step['capture'] is not None else None)
        observations_by_step[step['id']] = observation
        steps.append({
            'id': step['id'], 'label': step['label'],
            'observation': observation,
        })

    comparisons = []
    for declared in case['comparisons']:
        baseline = observations_by_step[declared['baseline']]
        candidate = observations_by_step[declared['candidate']]
        if baseline is None or candidate is None:
            comparisons.append({
                **deepcopy(declared), 'status': 'NOT_ASSESSED',
                'comparison': None,
            })
        else:
            comparisons.append({
                **deepcopy(declared), 'status': 'COMPARED',
                'comparison': observations.compare_observations(
                    baseline, candidate),
            })

    checks = [
        _evaluate_check(check, observations_by_step)
        for check in case['checks']
    ]
    checks_by_requirement = {}
    for check in checks:
        checks_by_requirement.setdefault(check['requirement_id'], []).append(
            check['id'])

    requirements = []
    counts = {'PASS': 0, 'FAIL': 0, 'NOT_ASSESSED': 0}
    for requirement in case['requirements']:
        check_ids = list(checks_by_requirement.get(requirement['id'], []))
        if requirement['level'] != 'request_structure':
            status = 'NOT_ASSESSED'
        else:
            statuses = [
                check['status'] for check in checks
                if check['requirement_id'] == requirement['id']
            ]
            if not statuses:
                status = 'NOT_ASSESSED'
            elif 'FAIL' in statuses:
                status = 'FAIL'
            elif 'NOT_ASSESSED' in statuses:
                status = 'NOT_ASSESSED'
            else:
                status = 'PASS'
        counts[status] += 1
        requirements.append({
            **deepcopy(requirement), 'status': status, 'check_ids': check_ids,
        })

    limitations = [
        '步骤顺序是研究者声明，不是推断出的真实运行时间、因果或生命周期顺序。',
        'capture 与研究问题的关联仅为 association declared only（作者声明），不是由 trace、study engine 或 observation 自动建立。',
        'PASS/FAIL 只是作者声明的有界结构判断，不自动证明 requirement、模型正确理解、readiness 或部署结论。',
        '所有检查只覆盖显式 request body。字段缺失只表示该提交物中未出现，不能证明服务端历史、archive 或全局上下文已删除。',
        '未提供的 capture、被阻断的指针和缺失一侧的比较均标为 NOT_ASSESSED；没有编造证据或比较。',
        'capture 的 evidence/runtime 来自自包含导入 manifest；不跟随路径、URL 或引用，也不推断 origin/lifecycle。',
        '模型行为与外部交付均未评估；真实 request、模型语义、scheduler 与外部消息不在本 case 的证据范围。',
    ]
    return {
        'schema': RESULT_SCHEMA,
        'case': deepcopy(case),
        'study': study,
        'steps': steps,
        'comparisons': comparisons,
        'checks': checks,
        'requirements': requirements,
        'summary': {
            'passed': counts['PASS'],
            'failed': counts['FAIL'],
            'not_assessed': counts['NOT_ASSESSED'],
        },
        'evidence': {
            'model_behavior': 'NOT_ASSESSED',
            'external_delivery': 'NOT_ASSESSED',
            'chronology': 'DECLARED_NOT_VERIFIED',
        },
        'limitations': limitations,
    }


def _json_block(value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    longest = max((len(run) for run in re.findall(r'`+', text)), default=0)
    fence = '`' * max(3, longest + 1)
    return f'{fence}json\n{text}\n{fence}\n'


def render_markdown(report):
    """Render a Chinese research report; assertions remain research-declared."""
    if not isinstance(report, dict) or report.get('schema') != RESULT_SCHEMA:
        _error('schema', 'expected ' + RESULT_SCHEMA)
    case = report['case']
    lines = [
        '# ' + case['title'], '',
        '> 研究 case · 无模型推理、自动 trace、scheduler 或外部交付。',
        '', '## 研究问题', '', case['question'], '',
        '## 保留要求与有界状态', '',
    ]
    for requirement in report['requirements']:
        lines.append(
            f"- `{requirement['id']}` [{requirement['status']}] "
            f"({requirement['level']}) {requirement['text']}；"
            f" checks: {', '.join(requirement['check_ids']) or '无'}")
    lines.extend([
        '', '## 证据层级与限制', '',
        '- evidence/model_behavior: NOT_ASSESSED',
        '- evidence/external_delivery: NOT_ASSESSED',
        '- evidence/chronology: DECLARED_NOT_VERIFIED',
    ])
    lines.extend('- ' + item for item in report['limitations'])

    lines.extend(['', '## 声明的步骤与证据', ''])
    for step in report['steps']:
        observation = step['observation']
        lines.extend([
            f"### {step['id']} · {step['label']}", '',
            '该步骤没有提供 capture：显式缺失证据，不能当作请求字段不存在。'
            if observation is None else
            '该步骤提供一份自包含 capture；以下仅投影其显式 request body。',
            '',
        ])
        if observation is None:
            continue
        lines.extend([
            _json_block({
                'evidence': observation['evidence'],
                'runtime': observation['runtime'],
                'wire_format': observation['wire_format'],
                'unresolved_context': observation['unresolved_context'],
            }),
            '### 完整原始 request body', '',
            _json_block(observation['request_body']),
        ])

    lines.extend(['## 请求结构检查', ''])
    for check in report['checks']:
        lines.extend([
            f"### {check['id']} · {check['status']}", '',
            f"- requirement: `{check['requirement_id']}`",
            f"- step: `{check['step_id']}`",
            f"- pointer（相对 request body）: `{check['pointer']}`",
            f"- operator: `{check['operator']}`",
            '- expected:', '', _json_block(check['expected']),
            f"- actual present: `{json.dumps(check['actual_present'])}`",
            ('- actual: `<MISSING>`' if check['actual_present'] is False else
             '- actual: `<NOT_ASSESSED>`' if check['actual_present'] is None else
             '- actual: `null`' if check['actual'] is None else
             '- actual:\n\n' + _json_block(check['actual'])),
            f"- reason: {check['reason']}", '',
        ])

    lines.extend(['## 显式 A/B 比较', ''])
    if not report['comparisons']:
        lines.extend(['未声明比较。', ''])
    for comparison in report['comparisons']:
        lines.extend([
            f"### {comparison['id']} · {comparison['status']}", '',
            f"- baseline: `{comparison['baseline']}`",
            f"- candidate: `{comparison['candidate']}`", '',
        ])
        if comparison['comparison'] is None:
            lines.extend(['缺失一侧或两侧证据；没有生成比较。', ''])
        else:
            lines.append(_json_block(comparison['comparison']))

    lines.extend(['## 可选 canonical study', ''])
    if report['study'] is None:
        lines.extend(['本 case 未附加 study snapshot。', ''])
    else:
        lines.append(_json_block(report['study']))

    summary = report['summary']
    lines.extend([
        '## 汇总', '',
        f"requirements: PASS {summary['passed']} · FAIL {summary['failed']} · "
        f"NOT_ASSESSED {summary['not_assessed']}。",
        '',
        '这里只计数 requirement 的有界状态，不是 readiness、部署或整体成功判断。',
        '所有断言均由研究者声明；case engine 没有自动判断 requirement 语义是否正确。',
        '',
    ])
    return '\n'.join(lines)
