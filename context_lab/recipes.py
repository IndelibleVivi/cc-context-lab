"""Strict catalog access for the three authored Claude Code recipes.

The catalog selects existing case and documentation files. It does not install
context, run native Claude Code, or duplicate case evaluation.
"""

from copy import deepcopy
from pathlib import Path, PurePosixPath

from context_lab import cases, observations


ROOT = Path(__file__).resolve().parents[1]
CATALOG_SCHEMA = 'cc-context-recipes/1'
RECIPE_IDS = ('owned-core', 'dynamic-state', 'compact-resume')
STATUSES = ('PASS', 'FAIL', 'NOT_ASSESSED')


def _error(message):
    raise ValueError(message)


def _exact_fields(value, fields, label):
    if not isinstance(value, dict):
        _error(label + ': expected object')
    missing = set(fields) - set(value)
    unknown = set(value) - set(fields)
    details = []
    if missing:
        details.append('missing fields: ' + ', '.join(sorted(missing)))
    if unknown:
        details.append('unknown fields: ' + ', '.join(sorted(unknown)))
    if details:
        _error(label + ': ' + '; '.join(details))


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        _error(label + ': expected nonempty string')


def _repo_file(root, value, label):
    _text(value, label)
    if '\\' in value:
        _error(label + ': expected a POSIX repo-relative path')
    if value.startswith('/') or any(
            part in ('', '.', '..') for part in value.split('/')):
        _error(label + ': must be a normalized repo-relative path')
    path = PurePosixPath(value)
    try:
        resolved = (root / Path(*path.parts)).resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError(
            label + ': path is missing or outside repository root') from exc
    if not resolved.is_file():
        _error(label + ': expected a regular file')
    return resolved


def _read_strict(path, label):
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise ValueError(
            label + ': cannot read UTF-8 JSON: ' + str(exc)) from exc
    try:
        return observations.parse_capture_json(text)
    except ValueError as exc:
        raise ValueError(label + ': ' + str(exc)) from exc


def _status_map(value, label):
    if not isinstance(value, dict) or not value:
        _error(label + ': expected a nonempty object')
    for key, status in value.items():
        _text(key, label + ' key')
        if status not in STATUSES:
            _error(label + '/' + key + ': expected ' + ', '.join(STATUSES))
    return value


def _validate_mechanisms(value, root, label):
    if not isinstance(value, list) or not value:
        _error(label + ': expected a nonempty array')
    seen = set()
    for index, item in enumerate(value):
        item_label = f'{label}/{index}'
        _exact_fields(
            item, ('id', 'title', 'explanation', 'sources'), item_label)
        for key in ('id', 'title', 'explanation'):
            _text(item[key], item_label + '/' + key)
        if item['id'] in seen:
            _error(item_label + '/id: duplicate ID')
        seen.add(item['id'])
        sources = item['sources']
        if not isinstance(sources, list) or not sources:
            _error(item_label + '/sources: expected a nonempty array')
        for source_index, source in enumerate(sources):
            _repo_file(
                root, source, f'{item_label}/sources/{source_index}')


def _validate_recipe(value, root, label):
    _exact_fields(
        value,
        ('id', 'title', 'question', 'summary', 'case_path', 'guide_path',
         'mechanisms', 'procedure', 'expected_checks',
         'expected_requirements', 'native_status'),
        label,
    )
    for key in ('id', 'title', 'question', 'summary'):
        _text(value[key], label + '/' + key)
    _repo_file(root, value['case_path'], label + '/case_path')
    _repo_file(root, value['guide_path'], label + '/guide_path')
    _validate_mechanisms(value['mechanisms'], root, label + '/mechanisms')
    procedure = value['procedure']
    if not isinstance(procedure, list) or not procedure:
        _error(label + '/procedure: expected a nonempty array')
    for index, step in enumerate(procedure):
        _text(step, f'{label}/procedure/{index}')
    _status_map(value['expected_checks'], label + '/expected_checks')
    _status_map(
        value['expected_requirements'], label + '/expected_requirements')
    if value['native_status'] != 'NOT_ASSESSED':
        _error(label + '/native_status: expected NOT_ASSESSED')


def _validate_expectations(recipe, case, label):
    report = cases.run_case(case)
    actual_checks = {row['id']: row['status'] for row in report['checks']}
    actual_requirements = {
        row['id']: row['status'] for row in report['requirements']
    }
    expected_checks = recipe['expected_checks']
    expected_requirements = recipe['expected_requirements']
    if set(expected_checks) != set(actual_checks):
        _error(
            label + '/expected_checks: IDs must exactly match case checks; '
            'missing: '
            + ', '.join(sorted(set(actual_checks) - set(expected_checks)))
            + '; unknown: '
            + ', '.join(sorted(set(expected_checks) - set(actual_checks)))
        )
    if set(expected_requirements) != set(actual_requirements):
        _error(
            label + '/expected_requirements: IDs must exactly match case '
            'requirements; missing: '
            + ', '.join(
                sorted(set(actual_requirements) - set(expected_requirements)))
            + '; unknown: '
            + ', '.join(
                sorted(set(expected_requirements) - set(actual_requirements)))
        )
    for check_id, expected in expected_checks.items():
        if actual_checks[check_id] != expected:
            _error(
                f'{label}/expected_checks/{check_id}: expected {expected}, '
                f'case produced {actual_checks[check_id]}'
            )
    for requirement_id, expected in expected_requirements.items():
        if actual_requirements[requirement_id] != expected:
            _error(
                f'{label}/expected_requirements/{requirement_id}: expected '
                f'{expected}, case produced {actual_requirements[requirement_id]}'
            )
    behavior = [
        row for row in report['requirements']
        if row['level'] == 'model_behavior'
    ]
    if not behavior or any(
            row['status'] != 'NOT_ASSESSED' for row in behavior):
        _error(
            label
            + ': case must retain an unassessed model_behavior requirement')
    if not any(row['status'] == 'FAIL' for row in report['checks']):
        _error(label + ': case must retain at least one deliberate FAIL check')


def _root(root):
    value = ROOT if root is None else Path(root)
    try:
        return value.resolve(strict=True)
    except OSError as exc:
        raise ValueError('root: directory is missing') from exc


def load_catalog(root=None):
    """Load and validate the complete catalog without mutating the checkout."""
    base = _root(root)
    catalog_path = _repo_file(
        base, 'references/recipes.json', 'catalog')
    catalog = _read_strict(catalog_path, 'catalog')
    _exact_fields(catalog, ('schema', 'recipes'), '$')
    if catalog['schema'] != CATALOG_SCHEMA:
        _error('schema: expected ' + CATALOG_SCHEMA)
    recipes = catalog['recipes']
    if not isinstance(recipes, list):
        _error('recipes: expected an array')
    ids = []
    for index, recipe in enumerate(recipes):
        label = f'recipes/{index}'
        _validate_recipe(recipe, base, label)
        ids.append(recipe['id'])
    if tuple(ids) != RECIPE_IDS:
        _error(
            'recipes: expected exact ordered IDs ' + ', '.join(RECIPE_IDS))
    for index, recipe in enumerate(recipes):
        label = f'recipes/{index}'
        case_path = _repo_file(
            base, recipe['case_path'], label + '/case_path')
        case = _read_strict(case_path, label + '/case_path')
        try:
            case = cases.validate_case(case)
        except ValueError as exc:
            raise ValueError(label + '/case_path: ' + str(exc)) from exc
        _validate_expectations(recipe, case, label)
    return deepcopy(catalog)


def load_recipe_case(recipe_id, root=None):
    """Return one strictly parsed, validated case selected by catalog ID."""
    if not isinstance(recipe_id, str) or recipe_id not in RECIPE_IDS:
        _error('recipe_id: unknown recipe')
    catalog = load_catalog(root)
    base = _root(root)
    recipe = next(
        row for row in catalog['recipes'] if row['id'] == recipe_id)
    path = _repo_file(
        base, recipe['case_path'], recipe_id + '/case_path')
    case = _read_strict(path, recipe_id + '/case_path')
    try:
        return cases.validate_case(case)
    except ValueError as exc:
        raise ValueError(recipe_id + '/case_path: ' + str(exc)) from exc
