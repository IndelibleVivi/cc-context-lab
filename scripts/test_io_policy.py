#!/usr/bin/env python3
"""Privacy preflight in disposable Git fixtures; never reads real captures."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from context_lab import io_policy


class OutputPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / '.gitignore').write_text('.cache/\n')

    def tearDown(self):
        self.temp.cleanup()

    def test_external_temp_directory_accepts_native_system_aliases(self):
        out = self.base / 'external'
        io_policy.ensure_private_output(out, self.repo, [out / 'report.json'])
        self.assertFalse(out.exists())

    def test_ignored_directory_and_each_untracked_target_are_allowed(self):
        out = self.repo / '.cache' / 'reports'
        io_policy.ensure_private_output(out, self.repo, [out / 'a.json', out / 'b.md'])
        self.assertFalse(out.exists())

    def test_unignored_output_refuses_before_directory_creation(self):
        out = self.repo / 'docs' / 'private'
        with self.assertRaisesRegex(ValueError, 'Git-ignored'):
            io_policy.ensure_private_output(out, self.repo, [out / 'report.json'])
        self.assertFalse(out.exists())

    def test_force_tracked_ignored_target_is_never_private_output(self):
        out = self.repo / '.cache' / 'reports'
        out.mkdir(parents=True)
        target = out / 'report.json'
        target.write_text('KEEP TRACKED')
        subprocess.run(['git', '-C', str(self.repo), 'add', '-f', str(target)], check=True)
        with self.assertRaisesRegex(ValueError, 'tracked'):
            io_policy.ensure_private_output(out, self.repo, [target])
        self.assertEqual(target.read_text(), 'KEEP TRACKED')

    def test_symlink_route_cannot_disguise_repo_output_as_external(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.repo)
        with self.assertRaisesRegex(ValueError, 'symbolic-link|Git-ignored'):
            io_policy.ensure_private_output(alias / 'public-output', self.repo)
        self.assertFalse((self.repo / 'public-output').exists())

    def test_custom_symlink_parents_and_final_targets_are_rejected(self):
        actual = self.base / 'actual'
        actual.mkdir()
        alias = self.base / 'alias'
        alias.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'symbolic-link'):
            io_policy.ensure_private_output(alias / 'out', self.repo)
        target = actual / 'report.json'
        target.symlink_to(self.base / 'absent-victim')
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            io_policy.ensure_private_output(actual, self.repo, [target])
        self.assertFalse((self.base / 'absent-victim').exists())

    def test_unknown_git_status_is_refused(self):
        out = self.repo / '.cache' / 'reports'
        with patch.object(io_policy.subprocess, 'run', return_value=subprocess.CompletedProcess([], 128)):
            with self.assertRaisesRegex(ValueError, 'cannot determine'):
                io_policy.ensure_private_output(out, self.repo)
        self.assertFalse(out.exists())

    def test_alias_targets_and_outside_target_refuse_before_writes(self):
        out = self.base / 'external'
        out.mkdir()
        a, b = out / 'a', out / 'b'
        a.write_text('KEEP')
        os.link(a, b)
        with self.assertRaisesRegex(ValueError, 'alias'):
            io_policy.ensure_private_output(out, self.repo, [a, b])
        with self.assertRaisesRegex(ValueError, 'outside'):
            io_policy.ensure_private_output(out, self.repo, [self.base / 'outside'])
        self.assertEqual(a.read_text(), 'KEEP')


if __name__ == '__main__':
    unittest.main(verbosity=2)
