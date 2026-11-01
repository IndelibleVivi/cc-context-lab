"""Private local output checks shared by generated-report commands.

This module must run before an output directory is created or any target is
opened. It proves only that Git does not track the destination; it cannot
remove private values from files placed at an otherwise private path.
"""

import sys
from pathlib import Path
import subprocess

from context_lab.artifacts import paths_alias


def _git_status(repo_root, path, arguments, git_runner):
    relative = path.relative_to(repo_root)
    checked = (git_runner or subprocess.run)(
        ['git', *arguments, '--', str(relative)],
        cwd=repo_root, capture_output=True, text=True)
    if checked.returncode not in (0, 1):
        raise ValueError(
            'cannot determine whether output is private; refusing to write')
    return checked.returncode == 0


def _git_tracked(repo_root, path, git_runner):
    relative = path.relative_to(repo_root)
    checked = (git_runner or subprocess.run)(
        ['git', 'ls-files', '--error-unmatch', '--',
         str(relative)],
        cwd=repo_root, capture_output=True, text=True)
    if checked.returncode not in (0, 1):
        raise ValueError(
            'cannot determine whether output is private; refusing to write')
    return checked.returncode == 0


def _system_alias(path):
    aliases = {'/var': '/private/var', '/tmp': '/private/tmp', '/etc': '/private/etc'}
    expected = aliases.get(str(path)) if sys.platform == 'darwin' else None
    return expected is not None and path.resolve() == Path(expected)


def ensure_private_output(output_dir, repo_root, targets=(), *, git_runner=None):
    """Require an external directory or consistently Git-ignored repo targets.

    ``targets`` must name every concrete output file. Each target must be a
    direct child of the resolved output directory. Callers remain responsible
    for comparing those targets with their inputs using ``paths_alias``. Git
    errors fail closed, and tracked files cannot be treated as private merely
    because an ignore pattern also matches them.
    """
    repo_root = Path(repo_root).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().absolute()
    if output_dir.is_symlink() and not _system_alias(output_dir):
        raise ValueError('output directory is a symbolic link: ' + str(output_dir))
    # Resolve lexical components without last-component symlink traversal.
    # ``Path.resolve`` is retained for comparison and alias checks.
    resolved_output = output_dir.resolve()
    if resolved_output.exists() and not resolved_output.is_dir():
        raise ValueError(
            'output directory is not a directory: ' + str(output_dir))
    # macOS exposes system-owned /var and /tmp aliases. Accept only their
    # standard exact destinations; user-created symlink routes still refuse.
    for parent in output_dir.parents:
        if not parent.is_symlink():
            continue
        if not _system_alias(parent):
            raise ValueError('output directory has a symbolic-link parent; use its resolved private path: ' + str(parent))

    checked_targets = []
    for target in targets:
        target = Path(target).expanduser().absolute()
        if target.is_symlink():
            raise ValueError('output target is a symbolic link: ' + str(target))
        resolved_target = target.resolve()
        if resolved_target.parent != resolved_output:
            raise ValueError(
                'output target is outside output directory: ' + str(target))
        if resolved_target.exists() and not resolved_target.is_file():
            raise ValueError(
                'output target is not a regular file: ' + str(target))
        checked_targets.append(resolved_target)
    for index, target in enumerate(checked_targets):
        if any(paths_alias(target, other)
               for other in checked_targets[index + 1:]):
            raise ValueError('output paths alias each other')

    try:
        resolved_output.relative_to(repo_root)
        inside_repo = True
    except ValueError:
        inside_repo = False
    if not inside_repo:
        # A lexical or resolved symlink route must never make an in-repo
        # destination look external.
        for path in [output_dir, *output_dir.parents]:
            try:
                path.resolve().relative_to(repo_root)
            except ValueError:
                continue
            if path.is_symlink() or path != path.resolve():
                raise ValueError(
                    'output route enters Git worktree through a symbolic link')
        return

    if _git_tracked(repo_root, resolved_output, git_runner):
        raise ValueError(
            'tracked files are not valid private output: ' + str(resolved_output))
    if not _git_status(
            repo_root, resolved_output,
            ('check-ignore', '--quiet', '--no-index'), git_runner):
        raise ValueError(
            'output inside the worktree must be Git-ignored; '
            'use .cache/ or an external directory')
    for target in checked_targets:
        if _git_tracked(repo_root, target, git_runner):
            raise ValueError(
                'tracked files are not valid private output: ' + str(target))
        if not _git_status(
                repo_root, target,
                ('check-ignore', '--quiet', '--no-index'), git_runner):
            raise ValueError(
                'every output target inside the worktree must be Git-ignored')
