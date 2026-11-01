#!/usr/bin/env python3
"""Synthetic imported-run viewing, portable snapshots and selected exports."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_context_atlas as atlas
from context_lab import cc_run_view as view


def fixture(directory):
    capture = atlas.read_json('experiments/request-observation/fixtures/anthropic-a.json')
    capture['capture_id'] = 'synthetic:a'
    capture['body']['exact'] = 9007199254740993
    text = json.dumps(capture, ensure_ascii=False) + '\n'
    attempt = dict(attempt_id='synthetic:a', source_id='a', capture_file='a.capture.json',
        capture_sha256=hashlib.sha256(text.encode()).hexdigest(),
        index_association={'status': 'unindexed', 'record_ids': []},
        selected_response_presence='unassessed', evidence_scope={'request_body': 'complete', 'observed_fields': None})
    run = dict(schema='cc-run-evidence/2', run_id='synthetic', runtime=capture['runtime'],
        target={'id': 'synthetic-target', 'fingerprint': 'synthetic-declaration'},
        attempts=[attempt], sources=[{'id': 'a', 'kind': 'request'}], index_records=[],
        responses=[], events=[], content_losses=[{'source_id': 'a', 'kind': 'request', 'reason': 'redacted', 'path': '/messages'}],
        dangling_references=[{'recorded_reference': 'DO_NOT_READ'}], limits={'model_behavior': 'not_assessed'})
    path = Path(directory) / 'run.json'
    path.write_text(json.dumps(run))
    (path.parent / 'a.capture.json').write_text(text)
    return path, run, capture


class RunViewTests(unittest.TestCase):
    def test_sidecar_and_snapshot_have_identical_captures_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path, run, capture = fixture(directory)
            loaded = view.load_run(path)
            snapshot_path = Path(directory) / 'snapshot.json'
            snapshot_path.write_text(json.dumps(loaded[3]))
            # Embedded capture text is already counted by the snapshot bytes.
            with patch.object(view, 'MAX_BUNDLE_BYTES', snapshot_path.stat().st_size + 1):
                replay = view.load_run(snapshot_path)
            self.assertEqual(loaded[0:2], replay[0:2])
            self.assertEqual(replay[0]['content_losses'], run['content_losses'])
            self.assertEqual(replay[1], [capture])
            self.assertEqual(len(replay[2]), 1)
            projected = view.project_run(*[replay[i] for i in (0, 3)])
            self.assertIn('9007199254740993', projected['bundle_json'])
            self.assertIn('synthetic-target', projected['conditions_text'])
            self.assertIn('redacted', projected['gaps_text'])
            self.assertIn('NOT_ASSESSED', projected['conditions_text'])
            self.assertIn('9007199254740993', projected['markdown'])
            self.assertIn('a.capture.json', projected['markdown'])
            self.assertNotIn('9007199254740993', projected['evidence_markdown'])

    def test_digest_change_refuses_mixed_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _, _ = fixture(directory)
            (path.parent / 'a.capture.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                view.load_run(path)

    def test_recorded_paths_are_never_opened_and_generated_names_are_bounded(self):
        for name in ('../a.capture.json', '/a.capture.json', 'nested/a.capture.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path, run, _ = fixture(directory)
                run['attempts'][0]['capture_file'] = name
                path.write_text(json.dumps(run))
                with self.assertRaisesRegex(ValueError, 'filenames'):
                    view.load_run(path)

    def test_capture_symlink_and_duplicate_identity_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path, run, _ = fixture(directory)
            original = path.parent / 'a.capture.json'
            original.rename(path.parent / 'original.json')
            original.symlink_to('original.json')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                view.load_run(path)
            run['attempts'] *= 2
            snapshot = {'schema': view.SNAPSHOT_SCHEMA, 'run': run, 'captures': {'a.capture.json': (path.parent / 'original.json').read_text()}}
            path.write_text(json.dumps(snapshot))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                view.load_run(path)

    def test_extra_embedded_capture_and_wrong_runtime_are_refused(self):
        for change in ('extra', 'runtime'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path, _, _ = fixture(directory)
                snapshot = view.load_run(path)[3]
                if change == 'extra':
                    snapshot['captures']['extra.capture.json'] = '{}'
                else:
                    snapshot['run']['runtime']['version'] = 'different'
                path.write_text(json.dumps(snapshot))
                with self.assertRaises(ValueError):
                    view.load_run(path)

    def test_run_projection_contains_only_selected_pair_and_keeps_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            path, run, _ = fixture(directory)
            data = atlas.build_data(run_bundle=view.load_run(path))
            self.assertIsNone(data['context_case'])
            self.assertEqual(data['request_observations']['comparisons'], {})
            self.assertEqual(json.loads(data['request_observations']['run_evidence_json']), run)
            self.assertEqual(len(data['request_observations']['captures']), 1)
            html = atlas.compose_html(data)
            self.assertIn('run-requests', html)
            self.assertIn('cc-run-snapshot/1', html)

    def test_response_or_event_only_run_does_not_fabricate_a_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path, run, _ = fixture(directory)
            run['attempts'] = []
            run['events'] = [{'event_id': 'explicit-event', 'sequence': 9007199254740993, 'source': 'declared'}]
            path.write_text(json.dumps(run))
            loaded = view.load_run(path)
            projection = view.project_run(loaded[0], loaded[3])
            self.assertEqual(projection['requests'], [])
            self.assertIn('9007199254740993', projection['gaps_text'])
            self.assertIn('explicit-event', projection['bundle_json'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
