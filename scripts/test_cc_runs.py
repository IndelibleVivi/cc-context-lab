#!/usr/bin/env python3
"""Canonical importer safety/fidelity; adapted from the authored engineering seed."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('import_cc_run.py')
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from context_lab import cc_runs
RUNTIME = {'harness': 'Claude Code', 'version': 'synthetic-build',
           'entrypoint': 'synthetic-file-mode', 'mode': 'synthetic',
           'candidate': 'synthetic-rule', 'session_path': None}


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cc-bundle-test-')
        self.root = Path(self.temp.name)
        self.selected = self.root / 'selected'
        self.selected.mkdir()
        self.selection = self.selected / 'selection.json'
        self.out = self.root / 'out'
        self.sources = []
        self.manifest = {'schema': 'cc-source-selection/1', 'run_id': 'synthetic-run',
                         'evidence_kind': 'synthetic_fixture', 'runtime': dict(RUNTIME),
                         'sources': self.sources}

    def tearDown(self):
        self.temp.cleanup()

    def source(self, sid, kind, value, *, raw=False, **extra):
        path = self.selected / (sid + ('.jsonl' if kind == 'index' else '.json'))
        payload = value.encode('utf-8') if raw else (json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8')
        path.write_bytes(payload)
        entry = {'id': sid, 'kind': kind, 'path': path.name,
                 'sha256': hashlib.sha256(payload).hexdigest(), **extra}
        self.sources.append(entry)
        return entry, path

    def save(self):
        self.selection.write_text(json.dumps(self.manifest), encoding='utf-8')

    def invoke(self, expected=0, *, save=True, out=None, repo=None, timeout=15):
        if save:
            self.save()
        result = subprocess.run([sys.executable, str(SCRIPT), '--selection', str(self.selection), '--out', str(out or self.out)],
                                capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return result

    def read(self, name='run.json'):
        return json.loads((self.out / name).read_text())

    def basic(self):
        return self.source('r1', 'request', {'model': 'synthetic', 'messages': [],
                                           'system': 'SYNTHETIC CORE',
                                           'large_integer': 9007199254740993,
                                           'explicit_null': None})

    def test_lossless_unindexed_attempt_and_no_promotion(self):
        self.basic()
        self.source('retry_like', 'request', {'model': 'synthetic', 'messages': []})
        self.source('response', 'response', {'id': 'synthetic-message', 'type': 'message'})
        self.source('index', 'index', json.dumps({'timestamp': '2026-11-01T00:00:00Z',
                    'session_id': 'synthetic-session', 'query_source': 'synthetic-primary',
                    'model': 'synthetic', 'request_id': 'synthetic-request',
                    'message_id': 'synthetic-message', 'message_uuid': 'synthetic-uuid',
                    'request_file': 'r1.json', 'response_file': 'response.json'}) + '\n', raw=True)
        self.invoke()
        run = self.read()
        self.assertEqual(len(run['attempts']), 2)
        self.assertEqual(run['attempts'][0]['index_association']['status'], 'matched')
        self.assertEqual(run['attempts'][1]['index_association']['status'], 'unindexed')
        self.assertEqual(run['attempts'][1]['selected_response_presence'], 'unassessed')
        self.assertIsNone(run['attempts'][1]['missing_selected_response'])
        capture = self.read('r1.capture.json')
        self.assertEqual(capture['body']['large_integer'], 9007199254740993)
        self.assertIsNone(capture['body']['explicit_null'])
        self.assertNotIn('not_present', capture['body'])
        self.assertEqual(capture['evidence']['kind'], 'synthetic_fixture')
        self.assertIsNone(capture['evidence']['observed_at'])
        self.assertEqual(run['limits']['provider_delivery'], 'not_assessed')
        self.assertEqual(run['limits']['model_visibility'], 'not_observed')
        self.assertEqual(run['limits']['retry_identity'], 'not_inferred')
        self.assertFalse(run['limits']['native_binary_executed'])
        self.assertNotIn('body', run)
        self.invoke()  # same selection can replace previous generated files

    def test_captured_kind_is_only_a_declaration(self):
        self.basic()
        self.manifest['evidence_kind'] = 'captured_request'
        self.invoke()
        self.assertEqual(self.read('r1.capture.json')['evidence']['kind'], 'captured_request')
        self.assertEqual(self.read()['limits']['runtime_provenance'], 'importer_declaration_not_independently_verified')
        self.assertFalse(self.read()['limits']['model_called'])

    def test_partial_scope_does_not_invent_missing_messages(self):
        self.source('partial', 'request', {'system': 'synthetic', 'tools': []},
                    evidence_scope={'request_body': 'partial', 'observed_fields': ['system', 'tools']})
        self.invoke()
        capture = self.read('partial.capture.json')
        self.assertNotIn('messages', capture['body'])
        self.assertEqual(capture['evidence_scope']['request_body'], 'partial')

    def test_partial_scope_must_cover_all_present_fields(self):
        self.source('partial', 'request', {'system': 'synthetic', 'tools': []},
                    evidence_scope={'request_body': 'partial', 'observed_fields': ['system']})
        self.invoke(2)
        self.assertFalse(self.out.exists())

    def test_duplicate_raw_keys_rejected(self):
        self.source('r1', 'request', '{"messages":[],"model":"a","model":"b"}', raw=True)
        self.invoke(2)
        self.assertFalse(self.out.exists())

    def test_duplicate_selection_keys_rejected(self):
        self.basic()
        self.save()
        self.selection.write_text(self.selection.read_text().replace('"run_id":', '"run_id":"duplicate","run_id":', 1))
        self.invoke(2, save=False)

    def test_duplicate_index_keys_rejected(self):
        self.basic()
        self.source('index', 'index', '{"request_file":"r1.json","request_file":"other"}\n', raw=True)
        self.invoke(2)

    def test_duplicate_response_keys_rejected(self):
        self.basic()
        self.source('response', 'response', '{"id":"a","id":"b"}', raw=True)
        self.invoke(2)

    def test_manifest_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.selection)
        result = self.invoke(2, save=False, timeout=2)
        self.assertIn('not a regular file', result.stderr)
        self.assertFalse(self.out.exists())

    def test_source_fifo_is_rejected_without_blocking(self):
        entry, path = self.basic()
        path.unlink()
        os.mkfifo(path)
        result = self.invoke(2, timeout=2)
        self.assertIn('not a regular file', result.stderr)
        self.assertFalse(self.out.exists())

    def test_response_message_id_mismatch_is_not_matched(self):
        self.basic()
        self.source('response', 'response', {'id': 'msg-B', 'type': 'message'})
        self.source('index', 'index', json.dumps({'request_file': 'r1.json',
                    'response_file': 'response.json', 'message_id': 'msg-A'}) + '\n', raw=True)
        self.invoke()
        run = self.read()
        record = run['index_records'][0]
        self.assertEqual(record['response_match']['status'], 'matched')
        self.assertEqual(record['association_status'], 'conflict')
        self.assertIn('response_content_mismatch', record['conflicts'])
        self.assertIs(record['response_content_consistency']['consistent'], False)
        self.assertEqual(record['response_content_consistency']['selected_response_id'], 'msg-B')
        self.assertEqual(run['attempts'][0]['index_association']['status'], 'conflict')
        self.assertEqual(run['attempts'][0]['response_association']['status'], 'conflict')
        self.assertEqual(run['attempts'][0]['response_association']['source_ids'], ['response'])
        self.assertEqual(run['attempts'][0]['selected_response_presence'], 'present')
        self.assertIs(run['attempts'][0]['missing_selected_response'], False)
        self.assertTrue((self.out / 'r1.capture.json').is_file())

    def test_missing_response_id_is_not_confirmed_consistent(self):
        self.basic()
        self.source('response', 'response', {'type': 'message'})
        self.source('index', 'index', json.dumps({'request_file': 'r1.json',
                    'response_file': 'response.json', 'message_id': 'msg-A'}) + '\n', raw=True)
        self.invoke()
        consistency = self.read()['index_records'][0]['response_content_consistency']
        self.assertEqual(consistency['status'], 'not_assessed')
        self.assertIsNone(consistency['consistent'])

    def test_hash_drift_preserves_prior_output(self):
        _, path = self.basic()
        self.invoke()
        before = (self.out / 'run.json').read_bytes()
        path.write_text('{"messages":[],"changed":true}')
        self.invoke(2)
        self.assertEqual((self.out / 'run.json').read_bytes(), before)

    def test_traversal_rejected(self):
        entry, _ = self.basic()
        entry['path'] = '../selected/r1.json'
        self.invoke(2)

    def test_absolute_source_rejected(self):
        entry, path = self.basic()
        entry['path'] = str(path)
        self.invoke(2)

    def test_symlink_file_and_component_rejected(self):
        entry, path = self.basic()
        link = self.selected / 'link.json'
        link.symlink_to(path)
        entry['path'] = link.name
        self.invoke(2)
        directory_link = self.selected / 'alias'
        directory_link.symlink_to(self.selected, target_is_directory=True)
        entry['path'] = 'alias/r1.json'
        self.invoke(2)

    def test_duplicate_physical_files_rejected(self):
        entry, path = self.basic()
        hard = self.selected / 'hard.json'
        os.link(path, hard)
        self.sources.append({**entry, 'id': 'r2', 'path': hard.name})
        self.invoke(2)

    def test_dangling_index_refs_are_never_loaded(self):
        self.basic()
        (self.selected / 'unselected.json').write_text('NOT VALID JSON')
        self.source('index', 'index', json.dumps({'request_file': 'unselected.json',
                    'response_file': 'https://invalid.example/never-follow'}) + '\n', raw=True)
        self.invoke()
        run = self.read()
        self.assertEqual(len(run['dangling_references']), 2)
        self.assertEqual(run['attempts'][0]['index_association']['status'], 'unindexed')
        self.assertFalse(run['limits']['unselected_refs_loaded'])

    def test_recorded_alias_match_is_exact(self):
        entry, _ = self.basic()
        entry['recorded_path'] = '/SYNTHETIC/logs/request.json'
        self.source('index', 'index', json.dumps({'request_file': '/SYNTHETIC/logs/request.json',
                    'response_file': 'not-selected.json'}) + '\n', raw=True)
        self.invoke()
        self.assertEqual(self.read()['attempts'][0]['index_association']['status'], 'matched')
        self.assertTrue(self.read()['attempts'][0]['missing_selected_response'])

    def test_ambiguous_alias_is_not_joined(self):
        entry, _ = self.basic()
        entry['recorded_path'] = 'shared-alias'
        self.source('r2', 'request', {'messages': []}, recorded_path='shared-alias')
        self.source('index', 'index', '{"request_file":"shared-alias","response_file":null}\n', raw=True)
        self.invoke()
        self.assertTrue(all(a['index_association']['status'] == 'ambiguous' for a in self.read()['attempts']))
        self.assertTrue(all(a['response_association']['status'] == 'unassessed' for a in self.read()['attempts']))

    def test_duplicate_index_rows_are_not_deduplicated(self):
        self.basic()
        row = json.dumps({'request_id': 'same', 'request_file': 'r1.json', 'response_file': None})
        self.source('index', 'index', row + '\n' + row + '\n', raw=True)
        self.invoke()
        run = self.read()
        self.assertEqual(len(run['index_records']), 2)
        self.assertEqual(run['attempts'][0]['index_association']['status'], 'ambiguous')
        self.assertIn('repeated_request_id', run['index_records'][0]['conflicts'])

    def test_duplicate_index_retains_selected_response_presence(self):
        self.basic()
        self.source('response', 'response', {'id': 'same-message', 'type': 'message'})
        row = json.dumps({'request_id': 'same-request', 'message_id': 'same-message',
                          'request_file': 'r1.json', 'response_file': 'response.json'})
        self.source('index', 'index', row + '\n' + row + '\n', raw=True)
        self.invoke()
        run = self.read()
        self.assertTrue(all(r['response_match']['status'] == 'matched' for r in run['index_records']))
        attempt = run['attempts'][0]
        self.assertEqual(attempt['index_association']['status'], 'ambiguous')
        self.assertEqual(attempt['response_association']['status'], 'ambiguous')
        self.assertEqual(attempt['response_association']['source_ids'], ['response'])
        self.assertEqual(attempt['selected_response_presence'], 'present')
        self.assertIs(attempt['missing_selected_response'], False)

    def test_input_output_alias_rejected(self):
        entry, path = self.basic()
        target = self.selected / 'r1.capture.json'
        path.rename(target)
        entry['path'] = target.name
        result = self.invoke(2, out=self.selected)
        self.assertIn('input/output alias', result.stderr)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), entry['sha256'])

    def test_output_symlink_target_rejected(self):
        self.basic()
        self.out.mkdir()
        unrelated = self.root / 'unrelated.json'
        unrelated.write_text('untouched')
        (self.out / 'run.json').symlink_to(unrelated)
        self.invoke(2)
        self.assertEqual(unrelated.read_text(), 'untouched')
        self.assertFalse((self.out / 'r1.capture.json').exists())

    def test_external_looking_output_cannot_bypass_repo_boundary(self):
        self.basic()
        alias = self.root / 'repo-alias'
        alias.symlink_to(REPO, target_is_directory=True)
        result = self.invoke(2, out=alias / 'not-ignored-output')
        self.assertRegex(result.stderr, 'Git-ignored|symbolic-link parent')
        self.assertFalse((REPO / 'not-ignored-output').exists())

    def test_per_file_size_cap(self):
        entry, path = self.basic()
        payload = b' ' * (16 * 1024 * 1024 + 1)
        path.write_bytes(payload)
        entry['sha256'] = hashlib.sha256(payload).hexdigest()
        self.invoke(2)
        self.assertFalse(self.out.exists())


    def test_v2_response_only_keeps_body_and_declares_unknown_request(self):
        self.manifest['schema'] = 'cc-source-selection/2'
        body = {'id': 'response-only', 'usage': {'input_tokens': 9007199254740993}, 'future': None}
        self.source('response', 'response', body)
        result = self.invoke()
        self.assertEqual(json.loads(result.stdout)['schema'], 'cc-run-evidence/2')
        run = self.read()
        self.assertEqual(run['attempts'], [])
        self.assertEqual(run['responses'][0]['body'], body)
        self.assertEqual(run['responses'][0]['association_record_ids'], [])
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ['run.json'])

    def test_v2_events_target_losses_and_process_sequences_are_preserved(self):
        self.manifest['schema'] = 'cc-source-selection/2'
        self.manifest['target'] = {'id': 'synthetic-target', 'fingerprint': 'operator-declared'}
        self.manifest['content_losses'] = [{'source_id': 'e1', 'kind': 'event', 'reason': 'spilled_reference', 'path': '/body_ref'}]
        a = {'id': 'event-a', 'sequence': 9007199254740993, 'source': 'synthetic-observer',
             'process': 'process-a', 'timestamp': '2026-11-01T00:01:00Z', 'body_ref': 'https://invalid.example/never-follow'}
        b = {'id': 'event-b', 'sequence': 1, 'process': 'process-b', 'timestamp': '2026-11-01T00:00:00Z'}
        self.source('e1', 'event', a)
        self.source('e2', 'event', b)
        self.invoke()
        run = self.read()
        self.assertEqual(run['target'], self.manifest['target'])
        self.assertEqual(run['content_losses'], self.manifest['content_losses'])
        self.assertEqual([r['metadata'] for r in run['events']], [a, b])
        self.assertEqual(run['attempts'], [])
        self.assertEqual(run['limits']['chronology'], 'not_inferred')

    def test_loss_pointer_and_selected_source_identity_are_validated(self):
        self.manifest['schema'] = 'cc-source-selection/2'
        self.basic()
        for pointer, source_id in [('/~bad', 'r1'), ('not-a-pointer', 'r1'), ('/messages', 'missing')]:
            with self.subTest(pointer=pointer, source_id=source_id):
                self.manifest['content_losses'] = [{'source_id': source_id, 'kind': 'request', 'reason': 'redacted', 'path': pointer}]
                self.invoke(2)
                self.assertFalse(self.out.exists())
        self.manifest['content_losses'][0].update(path='', source_id='r1')
        self.invoke()
        self.assertEqual(self.read()['content_losses'][0]['path'], '')

    def test_empty_index_and_unknown_metadata_values_remain_distinct(self):
        self.basic()
        self.source('empty', 'index', '', raw=True)
        self.source('index', 'index', json.dumps({'request_file': 'r1.json', 'process_id': 'declared-process',
                    'future': {'exact': 9007199254740993, 'null': None}}) + '\n', raw=True)
        self.invoke()
        record = self.read()['index_records'][0]
        self.assertIn('future', record['unknown_field_names'])
        self.assertEqual(record['metadata']['future']['exact'], 9007199254740993)
        self.assertEqual(record['metadata']['process_id'], 'declared-process')

    def test_ids_compare_by_json_type_without_bool_number_coercion(self):
        self.basic()
        self.source('response', 'response', {'id': 1})
        self.source('index', 'index', json.dumps({'request_file': 'r1.json', 'response_file': 'response.json', 'message_id': True}) + '\n', raw=True)
        self.invoke()
        self.assertEqual(self.read()['attempts'][0]['index_association']['status'], 'conflict')

    def test_utf8_encoding_failure_preserves_all_old_outputs(self):
        entry, path = self.basic()
        self.invoke()
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        payload = b'{"messages":[],"system":"\\ud800"}'
        path.write_bytes(payload)
        entry['sha256'] = hashlib.sha256(payload).hexdigest()
        self.invoke(2)
        self.assertEqual({p.name: p.read_bytes() for p in self.out.iterdir()}, before)
        self.assertEqual(path.read_bytes(), payload)

    def test_index_record_limit_is_aggregate_across_selected_sources(self):
        self.basic()
        self.source('index1', 'index', '{"request_file":"r1.json"}\n', raw=True)
        self.source('index2', 'index', '{"request_file":"r1.json"}\n', raw=True)
        self.save()
        with patch.object(cc_runs, 'MAX_INDEX_RECORDS', 1):
            with self.assertRaisesRegex(ValueError, 'aggregate index'):
                cc_runs.import_run(REPO, self.selection, self.out)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
