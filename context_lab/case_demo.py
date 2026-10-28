"""Authored synthetic case builder over a caller-supplied companion fixture.

The captures below are deliberately written by this module. They are not
projected from a canonical study run or copied from an observed trace.
"""

from copy import deepcopy

from context_lab.cases import validate_case


def _fixture_event(fixture, event_id):
    for event in fixture.get('timeline', []):
        if event.get('id') == event_id:
            return event
    raise ValueError('fixture.timeline: missing required event ' + event_id)


def _capture(capture_id, body):
    return {
        'schema': 'harness-context-capture/1',
        'capture_id': capture_id,
        'evidence': {'kind': 'synthetic_fixture', 'observed_at': None},
        'runtime': {
            'harness': 'synthetic-companion-fixture',
            'version': 'synthetic',
            'entrypoint': 'authored-case-demo',
            'mode': 'offline',
            'candidate': 'authored-context-case',
            'session_path': None,
        },
        'wire_format': 'anthropic-messages',
        'body': body,
    }


def _tool(required):
    return [{
        'name': 'synthetic_weather',
        'description': 'Synthetic weather lookup used only by this authored case.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'location': {'type': 'object'},
                'units': {'type': 'string'},
            },
            'required': list(required),
        },
    }]


def _body(core, tools, messages, scenario_id):
    return {
        'model': 'synthetic-model-placeholder',
        'system': [{'type': 'text', 'text': core}],
        'messages': deepcopy(messages),
        'tools': deepcopy(tools),
        'synthetic_case_association': {
            'fixture_scenario_id': scenario_id,
            'authorship': 'explicitly authored by context_lab.case_demo',
            'canonical_study_generation': False,
            'actual_observed_trace': False,
        },
    }


def make_demo_case(fixture):
    """Create a fresh self-contained case from a canonical companion fixture."""
    if not isinstance(fixture, dict):
        raise ValueError('fixture: expected object')
    scenario_id = fixture.get('scenario_id')
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError('fixture.scenario_id: expected nonempty string')

    weather = _fixture_event(fixture, 'amb_weather_1').get('text')
    weather_update = _fixture_event(fixture, 'amb_env_2').get('text')
    correction = _fixture_event(fixture, 'mem_corr_2').get('text')
    human = _fixture_event(fixture, 'msg_1').get('body')
    for label, value in (
            ('amb_weather_1.text', weather),
            ('amb_env_2.text', weather_update),
            ('mem_corr_2.text', correction),
            ('msg_1.body', human)):
        if not isinstance(value, str) or not value:
            raise ValueError('fixture.timeline: missing text for ' + label)

    core = 'owned-core synthetic demo: keep the same companion responsibility.'
    initial_messages = [
        {'role': 'user', 'content': human},
        {'role': 'assistant', 'content': weather},
    ]
    update_messages = [
        {'role': 'user', 'content': human},
        {'role': 'assistant', 'content': weather},
        {'role': 'user', 'content': correction},
        {'role': 'assistant', 'content': weather_update},
    ]
    forge_messages = [
        {'role': 'user', 'content': human},
        {'role': 'assistant', 'content': weather},
        {'role': 'user', 'content': 'Synthetic Forge transition after the update.'},
        {'role': 'assistant', 'content': weather_update},
    ]
    fresh_messages = [
        {'role': 'user', 'content': 'Synthetic Forge transition after the update.'},
        {
            'role': 'assistant',
            'content': (
                'Fresh session carryover: owned core plus the corrected soy '
                'latte preference; the old weather body is not carried.'),
        },
    ]

    steps = [
        {
            'id': 'initial_baseline',
            'label': '初始 · same history baseline',
            'capture': _capture(
                'gen-initial-baseline',
                _body(core, _tool(['location']), initial_messages, scenario_id)),
        },
        {
            'id': 'initial_candidate',
            'label': '初始 · same history candidate',
            'capture': _capture(
                'gen-initial-candidate',
                _body(core, _tool(['location', 'units']), initial_messages,
                      scenario_id)),
        },
        {
            'id': 'update_baseline',
            'label': '更新与纠正后 · same history baseline',
            'capture': _capture(
                'gen-update-baseline',
                _body(core, _tool(['location', 'units']), update_messages,
                      scenario_id)),
        },
        {
            'id': 'update_candidate',
            'label': '更新与纠正后 · same history candidate',
            'capture': _capture(
                'gen-update-candidate',
                _body(core, _tool(['location', 'units']), update_messages,
                      scenario_id)),
        },
        {
            'id': 'forge_baseline',
            'label': 'Forge 后 · 保留旧窗口 evidence',
            'capture': _capture(
                'gen-forge-baseline',
                _body(core, _tool(['location', 'units']), forge_messages,
                      scenario_id)),
        },
        {
            'id': 'forge_candidate',
            'label': 'Forge 后 · fresh carryover candidate',
            'capture': _capture(
                'gen-forge-candidate',
                _body(core, _tool(['location', 'units']), fresh_messages,
                      scenario_id)),
        },
        {
            'id': 'missing_evidence',
            'label': '刻意缺失的显式 evidence 步骤',
            'capture': None,
        },
    ]
    requirements = [
        {
            'id': 'req_core',
            'text': '请求中保留同一份自有 core。',
            'level': 'request_structure',
        },
        {
            'id': 'req_weather',
            'text': '更新后的天气正文进入请求。',
            'level': 'request_structure',
        },
        {
            'id': 'req_recall',
            'text': '纠正保留原始文本，不做隐式改写或归一化。',
            'level': 'request_structure',
        },
        {
            'id': 'req_history',
            'text': '旧天气仍可在声明的历史消息中找到。',
            'level': 'request_structure',
        },
        {
            'id': 'req_carryover',
            'text': 'fresh 窗口的 carryover 明确存在。',
            'level': 'request_structure',
        },
        {
            'id': 'req_tools',
            'text': '工具 schema 在捕获中保持。',
            'level': 'request_structure',
        },
        {
            'id': 'req_behavior',
            'text': '模型是否正确理解和善用这些 context。',
            'level': 'model_behavior',
        },
        {
            'id': 'req_delivery',
            'text': '外部用户是否收到并正确理解消息。',
            'level': 'external_delivery',
        },
    ]
    comparisons = [
        {'id': 'cmp_initial', 'baseline': 'initial_baseline',
         'candidate': 'initial_candidate'},
        {'id': 'cmp_update', 'baseline': 'update_baseline',
         'candidate': 'update_candidate'},
        {'id': 'cmp_forge', 'baseline': 'forge_baseline',
         'candidate': 'forge_candidate'},
    ]
    checks = [
        {
            'id': 'core_retained',
            'requirement_id': 'req_core',
            'step_id': 'forge_candidate',
            'pointer': '/system/0/text',
            'operator': 'contains_text',
            'expected': 'owned-core synthetic demo',
        },
        {
            # Intentional structural failure: the initial baseline schema
            # omits the declared units field.
            'id': 'initial_schema_failure',
            'requirement_id': 'req_tools',
            'step_id': 'initial_baseline',
            'pointer': '/tools/0/input_schema/required',
            'operator': 'equals',
            'expected': ['location', 'units'],
        },
        {
            'id': 'weather_updated',
            'requirement_id': 'req_weather',
            'step_id': 'update_candidate',
            'pointer': '/messages/3/content',
            'operator': 'contains_text',
            'expected': weather_update,
        },
        {
            'id': 'recall_original',
            'requirement_id': 'req_recall',
            'step_id': 'update_baseline',
            'pointer': '/messages/2/content',
            'operator': 'equals',
            'expected': correction,
        },
        {
            'id': 'old_weather_historical',
            'requirement_id': 'req_history',
            'step_id': 'forge_baseline',
            'pointer': '/messages/1/content',
            'operator': 'contains_text',
            'expected': weather,
        },
        {
            'id': 'fresh_carryover',
            'requirement_id': 'req_carryover',
            'step_id': 'forge_candidate',
            'pointer': '/messages/1/content',
            'operator': 'contains_text',
            'expected': 'Fresh session carryover: owned core plus',
        },
        {
            'id': 'tool_schema_preserved',
            'requirement_id': 'req_tools',
            'step_id': 'forge_candidate',
            'pointer': '/tools/0/input_schema/required',
            'operator': 'equals',
            'expected': ['location', 'units'],
        },
        {
            'id': 'missing_capture_is_not_absent',
            'requirement_id': 'req_core',
            'step_id': 'missing_evidence',
            'pointer': '/system/0/text',
            'operator': 'contains_text',
            'expected': 'owned-core synthetic demo',
        },
    ]
    study_plan = {
        'schema': 'cc-context-study/1',
        'title': '同一问题下的 same/fresh 合成对照',
        'question': (
            '同一 companion 情境在 same history 与 fresh carryover 下，'
            '哪些显式 context 仍被提交？'),
        'preserve': [
            '自有 core 与工具 schema',
            '纠正后的偏好文本',
            '旧天气只在声明的历史位置保留',
        ],
        'fixture': deepcopy(fixture),
        'baseline': {
            'policy_id': 'P1_fixed_interval',
            'placement_id': 'PL_main_defer',
            'history_mode': 'same',
        },
        'candidate': {
            'policy_id': 'P1_fixed_interval',
            'placement_id': 'PL_main_defer',
            'history_mode': 'fresh',
        },
    }
    return validate_case({
        'schema': 'harness-context-case/1',
        'case_id': 'companion-context-forge-synthetic-demo',
        'title': 'Companion context 更新、纠正与 Forge carryover',
        'question': (
            '同一个研究问题及保留要求下，初始、更新与 Forge 后的显式请求'
            '结构分别保留了什么？'),
        'requirements': requirements,
        'study_plan': study_plan,
        'steps': steps,
        'comparisons': comparisons,
        'checks': checks,
    })
