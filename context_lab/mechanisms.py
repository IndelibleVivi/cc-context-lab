"""Strict claim/source bindings for the three authored CC recipes.

The registry records fixed, already-reviewed project material. It does not
follow URLs or material references, inspect a runtime, or promote source
reading into request, lifecycle, or behavior evidence.
"""

from copy import deepcopy
from datetime import date
import ast
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from context_lab import observations

ROOT = Path(__file__).resolve().parents[1]
CATALOG_SCHEMA = 'cc-context-mechanisms/1'
PROJECTION_SCHEMA = 'cc-context-recipe-evidence/1'
MECHANISM_IDS = (
    'owned-core-boundary',
    'tool-schema-guidance',
    'revision-injection',
    'correction-lineage',
    'compact-retention',
    'resume-reload',
    'partial-absence',
)
LEVELS = (
    'authored_source',
    'synthetic_fixture',
    'public_source_inspection',
    'official_documentation',
    'historical_offline_check',
    'historical_target_types',
    'historical_local_composition',
    'unassessed',
)
SOURCE_KINDS = (
    'authored_source',
    'synthetic_fixture',
    'official_documentation_report',
    'public_source_pin',
    'offline_check_record',
    'target_runtime_artifact',
)
LOCATOR_KINDS = ('json_pointer', 'python_symbol', 'markdown_heading')
SOURCE_LEVELS = {
    'authored_source': {'authored_source', 'unassessed'},
    'synthetic_fixture': {'synthetic_fixture', 'unassessed'},
    'official_documentation_report': {'official_documentation', 'unassessed'},
    'public_source_pin': {'public_source_inspection', 'unassessed'},
    'offline_check_record': {'historical_offline_check', 'unassessed'},
    'target_runtime_artifact': {
        'historical_target_types',
        'historical_local_composition',
        'unassessed',
    },
}

CLAIM_FIELDS = ('id', 'statement', 'level', 'source_ids', 'limits')
SOURCE_FIELDS = (
    'id', 'title', 'kind', 'revision', 'observed_on', 'path', 'locator',
    'url', 'limits',
)
MECHANISM_FIELDS = ('id', 'claims', 'sources')


def _error(field, message):
    raise ValueError(field + ': ' + message)


def _object(value, field):
    if not isinstance(value, dict):
        _error(field, 'expected object')


def _exact_fields(value, fields, field):
    _object(value, field)
    missing = set(fields) - set(value)
    unknown = set(value) - set(fields)
    if missing or unknown:
        details = []
        if missing:
            details.append('missing fields: ' + ', '.join(sorted(missing)))
        if unknown:
            details.append('unknown fields: ' + ', '.join(sorted(unknown)))
        _error(field, '; '.join(details))


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _error(field, 'expected nonempty string')


def _strings(value, field):
    if not isinstance(value, list) or not value:
        _error(field, 'expected nonempty array')
    seen = set()
    for index, item in enumerate(value):
        _text(item, f'{field}/{index}')
        if item in seen:
            _error(f'{field}/{index}', 'duplicate value')
        seen.add(item)


def _unique_records(value, fields, field):
    if not isinstance(value, list) or not value:
        _error(field, 'expected nonempty array')
    for index, item in enumerate(value):
        _exact_fields(item, fields, f'{field}/{index}')
        _text(item['id'], f'{field}/{index}/id')
    ids = [item['id'] for item in value]
    if len(set(ids)) != len(ids):
        _error(field, 'duplicate ID')


def _date(value, field):
    _text(value, field)
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        _error(field, 'expected YYYY-MM-DD')
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(field + ': expected a real calendar date') from exc


def _repo_path(root, value, field):
    _text(value, field)
    if '\\' in value:
        _error(field, 'expected a POSIX repo-relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(
            part in ('', '.', '..') for part in value.split('/')):
        _error(field, 'must be a normalized repo-relative path')
    if ':' in value.split('/', 1)[0] or PureWindowsPath(value).is_absolute():
        _error(field, 'must not contain a drive or URI scheme')
    candidate = root / Path(*path.parts)
    if candidate.is_symlink():
        _error(field, 'source path must not be a symbolic link')
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError(
            field + ': path is missing or escapes repository root') from exc
    if not resolved.is_file():
        _error(field, 'expected a regular file')
    return resolved


def _decode_pointer(pointer, field):
    """Validate RFC 6901 string form without resolving external data."""
    if not isinstance(pointer, str):
        _error(field, 'expected RFC6901 string')
    if not pointer:
        return []
    if not pointer.startswith('/'):
        _error(field, 'must be empty or start with /')
    tokens = []
    for raw in pointer.split('/')[1:]:
        index = 0
        while index < len(raw):
            if raw[index] == '~':
                if index + 1 >= len(raw) or raw[index + 1] not in '01':
                    _error(field, 'invalid ~ escape in ' + repr(raw))
                index += 2
            else:
                index += 1
        tokens.append(raw.replace('~1', '/').replace('~0', '~'))
    return tokens


def _resolve_pointer(document, pointer, field):
    value = document
    for token in _decode_pointer(pointer, field):
        if isinstance(value, dict):
            if token not in value:
                _error(field, 'target is absent')
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                _error(field, 'invalid array index')
            index = int(token)
            if index >= len(value):
                _error(field, 'array index is out of range')
            value = value[index]
        else:
            _error(field, 'ancestor is not an object or array')
    return value


def _locator(path, value, field):
    _object(value, field)
    kind = value.get('kind')
    if kind not in LOCATOR_KINDS:
        _error(field + '/kind', 'expected one of ' + ', '.join(LOCATOR_KINDS))
    if kind == 'json_pointer':
        _exact_fields(value, ('kind', 'pointer'), field)
        try:
            document = observations.parse_capture_json(
                path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(field + ': cannot read strict UTF-8 JSON') from exc
        _resolve_pointer(document, value['pointer'], field + '/pointer')
    elif kind == 'python_symbol':
        _exact_fields(value, ('kind', 'symbol'), field)
        _text(value['symbol'], field + '/symbol')
        if path.suffix != '.py':
            _error(field, 'python_symbol requires a .py source path')
        symbol = value['symbol']
        for name in symbol.split('.'):
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                _error(field + '/symbol', 'expected a Python identifier path')
        try:
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            raise ValueError(field + ': cannot read UTF-8 source') from exc
        try:
            node = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ValueError(field + ': invalid Python source') from exc
        for name in symbol.split('.'):
            definitions = [child for child in getattr(node, 'body', [])
                           if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                           and child.name == name]
            if len(definitions) != 1:
                _error(field + '/symbol', 'symbol does not identify one declared function or class')
            node = definitions[0]
    else:
        _exact_fields(value, ('kind', 'heading'), field)
        _text(value['heading'], field + '/heading')
        try:
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            raise ValueError(field + ': cannot read UTF-8 source') from exc
        fence_char, fence_length, found = None, 0, False
        for line in source.splitlines():
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
            if fence_char:
                if marker and marker[1][0] == fence_char and len(marker[1]) >= fence_length and not marker[2].strip():
                    fence_char = None
                continue
            if marker:
                fence_char, fence_length = marker[1][0], len(marker[1])
                continue
            if re.fullmatch(r'#{1,6}\s+' + re.escape(value['heading']) + r'\s*', line):
                found = True
                break
        if not found:
            _error(field + '/heading', 'heading is not present verbatim')


def _revision(kind, value, field):
    _text(value, field)
    if kind in ('authored_source', 'synthetic_fixture', 'public_source_pin', 'official_documentation_report'):
        if not re.fullmatch(r'[0-9a-f]{40}', value):
            _error(field, 'expected a full Git revision')
    elif re.search(r'\s', value):
        _error(field, 'expected one exact artifact or documentation revision')


def _validate_source(root, source, field):
    _exact_fields(source, SOURCE_FIELDS, field)
    _text(source['id'], field + '/id')
    _text(source['title'], field + '/title')
    kind = source['kind']
    if kind not in SOURCE_KINDS:
        _error(field + '/kind', 'expected one of ' + ', '.join(SOURCE_KINDS))
    _revision(kind, source['revision'], field + '/revision')
    _date(source['observed_on'], field + '/observed_on')
    _strings(source['limits'], field + '/limits')
    if source['path'] is None:
        _error(field + '/path',
               'a fixed local report or snapshot path is required')
    path = _repo_path(root, source['path'], field + '/path')
    if source['locator'] is None:
        _error(field + '/locator', 'required for source and locator identity')
    _locator(path, source['locator'], field + '/locator')
    if kind == 'target_runtime_artifact':
        try:
            record = observations.parse_capture_json(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(field + ': expected a strict target-artifact JSON report') from exc
        if not isinstance(record, dict) or source['revision'] != record.get('artifact') or source['observed_on'] != record.get('checked_on'):
            _error(field, 'artifact identity and observation date must match the cited report')
    if source['url'] is not None:
        _text(source['url'], field + '/url')
        if not re.fullmatch(r'https?://[^\s]+', source['url']):
            _error(field + '/url', 'expected an HTTP(S) reference')
    if kind in ('authored_source', 'synthetic_fixture', 'official_documentation_report'):
        suffix = '/blob/' + source['revision'] + '/' + source['path']
        if not source['url'] or not source['url'].endswith(suffix):
            _error(field + '/url', 'fixed report URL must match its Git revision and repo-relative path')
    if kind == 'target_runtime_artifact' and (not source['url'] or not re.fullmatch(
            r'https?://[^?#]+/blob/[0-9a-f]{40}/' + re.escape(source['path']), source['url'])):
        _error(field + '/url', 'target artifact evidence requires a fixed Git URL for the cited report')


def _validate_catalog(catalog, root):
    observations._json_value(catalog, '$')
    _exact_fields(catalog, ('schema', 'levels', 'mechanisms'), '$')
    if catalog['schema'] != CATALOG_SCHEMA:
        _error('schema', 'expected ' + CATALOG_SCHEMA)
    _strings(catalog['levels'], 'levels')
    if tuple(catalog['levels']) != LEVELS:
        _error('levels', 'expected exact ordered evidence levels')
    mechanisms = catalog['mechanisms']
    _unique_records(mechanisms, MECHANISM_FIELDS, 'mechanisms')
    if tuple(item['id'] for item in mechanisms) != MECHANISM_IDS:
        _error('mechanisms', 'expected exact ordered mechanism IDs')

    source_ids = set()
    claim_ids = set()
    for index, mechanism in enumerate(mechanisms):
        label = f'mechanisms/{index}'
        claims = mechanism['claims']
        sources = mechanism['sources']
        _unique_records(claims, CLAIM_FIELDS, label + '/claims')
        _unique_records(sources, SOURCE_FIELDS, label + '/sources')
        local_sources = {}
        for source_index, source in enumerate(sources):
            source_label = f'{label}/sources/{source_index}'
            _validate_source(root, source, source_label)
            if source['id'] in source_ids:
                _error(source_label + '/id',
                       'source ID repeats across mechanisms')
            source_ids.add(source['id'])
            local_sources[source['id']] = source
        referenced_sources = set()
        for claim_index, claim in enumerate(claims):
            claim_label = f'{label}/claims/{claim_index}'
            if claim['id'] in claim_ids:
                _error(claim_label + '/id', 'claim ID repeats across mechanisms')
            claim_ids.add(claim['id'])
            _text(claim['statement'], claim_label + '/statement')
            if claim['level'] not in catalog['levels']:
                _error(claim_label + '/level', 'unknown evidence level')
            _strings(claim['source_ids'], claim_label + '/source_ids')
            _strings(claim['limits'], claim_label + '/limits')
            for source_id in claim['source_ids']:
                source = local_sources.get(source_id)
                if source is None:
                    _error(claim_label + '/source_ids',
                           'claim references an unknown source in this mechanism')
                if claim['level'] not in SOURCE_LEVELS[source['kind']]:
                    _error(claim_label + '/level',
                           'evidence level exceeds source kind ' + source['kind'])
                referenced_sources.add(source_id)
        orphans = set(local_sources) - referenced_sources
        if orphans:
            _error(label + '/sources',
                   'sources are not referenced by any claim: '
                   + ', '.join(sorted(orphans)))


def _root(root):
    value = ROOT if root is None else Path(root)
    try:
        base = value.resolve(strict=True)
    except OSError as exc:
        raise ValueError('root: directory is missing') from exc
    if not base.is_dir():
        _error('root', 'expected a directory')
    return base


def load_catalog(root=None):
    """Load, strictly validate, and return an independent registry snapshot."""
    base = _root(root)
    path = _repo_path(base, 'references/mechanisms.json', 'catalog')
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise ValueError('catalog: cannot read UTF-8 JSON') from exc
    try:
        catalog = observations.parse_capture_json(text)
    except ValueError as exc:
        raise ValueError('catalog: ' + str(exc)) from exc
    _validate_catalog(catalog, base)
    return deepcopy(catalog)


def validate_recipe_bindings(recipes, catalog, allow_partial=False):
    """Verify exact coverage and reject missing or orphan bindings.

    ``allow_partial`` is reserved for projecting one already-loaded recipe;
    the recipe catalog itself always validates the complete seven-ID set.
    """
    if not isinstance(recipes, list) or not recipes:
        _error('recipes', 'expected a nonempty array')
    _object(catalog, 'catalog')
    mechanisms = catalog.get('mechanisms')
    if not isinstance(mechanisms, list):
        _error('catalog/mechanisms', 'expected an array')
    catalog_by_id = {item['id']: item for item in mechanisms}
    if tuple(catalog_by_id) != MECHANISM_IDS:
        _error('catalog/mechanisms', 'expected exact ordered mechanism IDs')

    seen_recipes = set()
    seen_mechanisms = set()
    for recipe_index, recipe in enumerate(recipes):
        label = f'recipes/{recipe_index}'
        _object(recipe, label)
        _text(recipe.get('id'), label + '/id')
        if recipe['id'] in seen_recipes:
            _error(label + '/id', 'duplicate recipe ID')
        seen_recipes.add(recipe['id'])
        bound = recipe.get('mechanisms')
        if not isinstance(bound, list) or not bound:
            _error(label + '/mechanisms', 'expected nonempty array')
        for mechanism_index, mechanism in enumerate(bound):
            mechanism_label = f'{label}/mechanisms/{mechanism_index}'
            _object(mechanism, mechanism_label)
            mechanism_id = mechanism.get('id')
            _text(mechanism_id, mechanism_label + '/id')
            if mechanism_id in seen_mechanisms:
                _error(mechanism_label + '/id',
                       'duplicate mechanism binding')
            seen_mechanisms.add(mechanism_id)
            catalog_mechanism = catalog_by_id.get(mechanism_id)
            if catalog_mechanism is None:
                _error(mechanism_label + '/id',
                       'unknown mechanism ID')
            _strings(mechanism.get('sources'), mechanism_label + '/sources')
            # Reading paths explain the broader topic. Claim evidence is bound
            # independently by source IDs in the strictly validated registry.
    missing = set(MECHANISM_IDS) - seen_mechanisms
    if missing and not allow_partial:
        _error('recipes/mechanisms',
               'missing mechanism bindings: ' + ', '.join(sorted(missing)))
    if len(seen_mechanisms) != len(MECHANISM_IDS) and not allow_partial:
        _error('recipes/mechanisms', 'mechanism binding count is not exact')
    return True


def _json_text(value):
    return json.dumps(
        value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _fence(text):
    longest = max(
        (len(run) for run in re.findall(r'`+', text)), default=0)
    return '`' * max(3, longest + 1)


def _markdown_pointer(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _render_markdown(projection, json_text):
    lines = [
        '# Recipe mechanism evidence · ' + projection['recipe_id'], '',
        '> 固定 source 与逐条判断的可追溯投影。层级保持原样；'
        '历史 source、合成 fixture、composition 与真实 request/lifecycle/'
        'model behavior 不因绑定而升级。', '',
        '## 限制', '',
    ]
    lines.extend('- ' + caveat for caveat in projection['caveats'])
    lines.extend(['', '## Mechanisms', ''])
    sources = {source['id']: source for source in projection['sources']}
    for mechanism in projection['mechanisms']:
        lines.extend([
            '### ' + mechanism['id'] + ' · ' + mechanism['title'], '',
            mechanism['explanation'], '',
        ])
        for claim in mechanism['claims']:
            lines.extend([
                f"#### {claim['id']} · `{claim['level']}`", '',
                claim['statement'], '',
                'Sources: ' + ', '.join(
                    '`' + source_id + '`'
                    for source_id in claim['source_ids']),
                '',
            ])
            lines.extend('- ' + limit for limit in claim['limits'])
            lines.append('')
        lines.extend(['#### Fixed sources', ''])
        referenced = {
            source_id
            for claim in mechanism['claims']
            for source_id in claim['source_ids']
        }
        for source_id in sources:
            if source_id not in referenced:
                continue
            source = sources[source_id]
            lines.extend([
                f"##### {source['id']} · {source['title']}", '',
                f"- kind: `{source['kind']}`",
                f"- revision: `{source['revision']}`",
                f"- observed on: `{source['observed_on']}`",
                f"- path: `{source['path']}`",
                f"- locator: `{_markdown_pointer(source['locator'])}`",
                '- url: ' + (source['url'] or '未提供'),
            ])
            lines.extend('- ' + limit for limit in source['limits'])
            lines.append('')
    fence = _fence(json_text)
    lines.extend([
        '## Canonical projection', '',
        fence + 'json', json_text.rstrip('\n'), fence, '',
        '以上 JSON 是同一 projection 的 canonical 序列化。验证只读取固定 '
        'repo-relative 文件与声明 locator，不跟随 URL、material reference、'
        'request 路径或 runtime 状态。', '',
    ])
    return '\n'.join(lines)


def build_recipe_evidence(recipe, catalog=None, root=None):
    """Resolve one recipe to canonical projection, JSON, and Markdown text."""
    _object(recipe, 'recipe')
    recipe_id = recipe.get('id')
    _text(recipe_id, 'recipe/id')
    if recipe.get('native_status') != 'NOT_ASSESSED':
        _error('recipe/native_status', 'expected NOT_ASSESSED')
    base = _root(root)
    if catalog is None:
        catalog = load_catalog(base)
    else:
        _validate_catalog(catalog, base)
    validate_recipe_bindings([recipe], catalog, allow_partial=True)

    catalog_by_id = {item['id']: item for item in catalog['mechanisms']}
    mechanisms = []
    sources = []
    for bound in recipe['mechanisms']:
        fixed = catalog_by_id[bound['id']]
        mechanisms.append({
            'id': deepcopy(fixed['id']),
            'title': deepcopy(bound['title']),
            'explanation': deepcopy(bound['explanation']),
            'claims': deepcopy(fixed['claims']),
        })
        sources.extend(deepcopy(fixed['sources']))
    projection = {
        'schema': PROJECTION_SCHEMA,
        'recipe_id': recipe_id,
        'mechanisms': mechanisms,
        'sources': sources,
        'caveats': [
            '本投影只绑定已记录的公开 source、合成 fixture 与历史观察；'
            '不证明当前平台或指定 CC build 仍具有相同行为。',
            'source inspection、target-types/composition 与真实 request、'
            'lifecycle、provider 呈现和模型行为是不同证据层。',
            '三条 recipe 的 native_status 保持 NOT_ASSESSED；'
            '本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。',
            '证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。',
            '离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；'
            '不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。',
        ],
    }
    json_text = _json_text(projection)
    return {
        'projection': projection,
        'json': json_text,
        'markdown': _render_markdown(projection, json_text),
    }
