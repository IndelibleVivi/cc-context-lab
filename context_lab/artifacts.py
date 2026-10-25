"""Local report writing shared by the lab's CLI and Atlas exporters.

Encoding and target checks precede all writes; replacements are atomic per
file, not a multi-file transaction. No paths from report data are followed.
"""
import os
from pathlib import Path
import tempfile


def paths_alias(left, right):
    if left.resolve() == right.resolve():
        return True
    try:
        return os.path.samefile(left, right)
    except FileNotFoundError:
        return False


def write_reports(contents, output_dir):
    # Complete encoding before mkdir or opening any destination. Replacing a
    # hardlink creates a new inode here; it never overwrites the other link.
    prepared = [(Path(target), text.encode('utf-8')) for target, text in contents]
    for target, _ in prepared:
        if target.parent.resolve() != output_dir.resolve():
            raise ValueError('artifact target is outside output directory')
        if target.is_symlink():
            raise ValueError('output is a symbolic link: ' + str(target))
        if target.exists() and not target.is_file():
            raise ValueError('output is not a regular file: ' + str(target))
    for i, (target, _) in enumerate(prepared):
        if any(paths_alias(target, other) for other, _ in prepared[i + 1:]):
            raise ValueError('output paths alias each other')
    output_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for target, payload in prepared:
            with tempfile.NamedTemporaryFile(mode='wb', dir=output_dir,
                                             prefix='.context-artifact-', suffix='.tmp', delete=False) as handle:
                staged.append((Path(handle.name), target))
                handle.write(payload)
        for temporary, target in staged:
            os.replace(temporary, target)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
