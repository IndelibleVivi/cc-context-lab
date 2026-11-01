#!/usr/bin/env python3
"""Bounded comparison projection; synthetic inputs, no runtime or network."""
from copy import deepcopy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_context_atlas as atlas


def capture(index, size=16, partial=False):
    raw = atlas.read_json('experiments/request-observation/fixtures/anthropic-a.json')
    raw['capture_id'] = 'request-' + str(index)
    raw['body']['messages'] = [{'role': 'user', 'content': str(index) + 'x' * size}]
    raw['body']['exact'] = 9007199254740993
    if partial:
        raw['evidence_scope'] = {'request_body': 'partial', 'observed_fields': list(raw['body'])}
    return atlas.request_observation.normalize_capture(raw)


class SelectedPairsTests(unittest.TestCase):
    def test_study_rebuild_keeps_the_original_input_mode(self):
        from test_context_study import plan
        cache = atlas.ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        for with_capture in (False, True):
            with self.subTest(with_capture=with_capture), tempfile.TemporaryDirectory(dir=cache) as directory:
                directory = Path(directory)
                study_file = directory / 'study.json'
                study_file.write_text(json.dumps(plan()))
                output = directory / 'atlas'
                command = [sys.executable, str(atlas.ROOT / 'scripts/build_context_atlas.py'),
                           '--study', str(study_file), '--out', str(output), '--data-only']
                if with_capture:
                    command += ['--capture', str(atlas.ROOT / 'experiments/request-observation/fixtures/anthropic-a.json'),
                                '--capture', str(atlas.ROOT / 'experiments/request-observation/fixtures/anthropic-b.json')]
                first = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(first.returncode, 0, first.stderr)
                data = json.loads((output / 'data.json').read_text())
                observations = data['request_observations']
                ids = [c['capture_id'] for c in observations['captures']]
                pairs_file = directory / 'pairs.json'
                pairs_file.write_text(json.dumps([ids[:2]]))
                rebuild = shlex.split(observations['rebuild_command'])
                self.assertIn('--study', rebuild)
                self.assertEqual(rebuild[rebuild.index('--study') + 1], str(study_file))
                rebuild[rebuild.index('--pairs') + 1] = str(pairs_file)
                second = subprocess.run(rebuild, cwd=atlas.ROOT, capture_output=True, text=True)
                self.assertEqual(second.returncode, 0, second.stderr)
                replay = json.loads((output / 'data.json').read_text())
                self.assertEqual(replay['study_plan'], data['study_plan'])
                self.assertEqual([c['capture_id'] for c in replay['request_observations']['captures']], ids)

    def test_only_selected_pairs_use_canonical_comparison(self):
        observations = [capture(i) for i in range(4)]
        pairs = [('request-0', 'request-1'), ('request-2', 'request-3')]
        with patch.object(atlas.request_observation, 'compare_observations',
                          wraps=atlas.request_observation.compare_observations) as compare:
            data = atlas.build_request_observations(normalized=observations, pairs=pairs)
        self.assertEqual(compare.call_count, 2)
        self.assertEqual(sum(len(v) for v in data['comparisons'].values()), 2)
        self.assertEqual(atlas.build_request_observations(normalized=observations)['comparisons'], {})

    def test_invalid_duplicate_or_self_pair_rejected(self):
        for pairs in [[('request-0', 'request-0')], [('request-0', 'missing')],
                      [('request-0', 'request-1')] * 2, [['request-0']]]:
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                atlas.build_request_observations(normalized=[capture(0), capture(1)], pairs=pairs)

    def test_selected_export_reconstructs_exact_canonical_result(self):
        observations = [capture(0), capture(1, partial=True)]
        data = atlas.build_request_observations(normalized=observations, pairs=[('request-0', 'request-1')])
        exported = atlas.expand_observation_export(data, 'request-0', 'request-1')
        expected = atlas.request_observation.compare_observations(*observations)
        self.assertEqual(json.loads(exported['json']), expected)
        self.assertEqual(exported['markdown'], atlas.request_observation.render_markdown(expected))
        self.assertIn('9007199254740993', exported['json'])
        self.assertNotIn('request_body', data['comparisons']['request-0']['request-1'])
        with self.assertRaises(ValueError):
            atlas.expand_observation_export(data, 'request-1', 'request-0')

    def test_one_capture_has_a_standalone_export_and_no_self_comparison(self):
        observation = capture(0)
        data = atlas.build_request_observations(normalized=[observation])
        exported = atlas.expand_observation_export(data, 'request-0')
        self.assertEqual(json.loads(exported['json']), observation)
        self.assertEqual(exported['markdown'], atlas.request_observation.render_markdown(observation))
        self.assertEqual(data['comparisons'], {})

    def test_bounded_pairs_grow_linearly_with_capture_count(self):
        sizes = []
        for count in (1, 2, 4, 8):
            observations = [capture(i, 65536) for i in range(count)]
            pairs = [('request-' + str(i), 'request-' + str(i + 1)) for i in range(count - 1)]
            data = atlas.build_request_observations(normalized=observations, pairs=pairs)
            sizes.append(len(json.dumps(data, ensure_ascii=False).encode()))
        self.assertLess(sizes[-1], sizes[0] * 10)
        self.assertLess(sizes[-1], 12_000_000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
