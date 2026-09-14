"""Recognizing the bundled synthetic sample-data CSVs (data/sample_*.csv)
so the GUI can warn before running -- or having just run -- against the
2-user demo dataset instead of a real SAP export. That mix-up is easy to
make silently: the GUI remembers whatever paths were last used, and
nothing about a stale sample-data path looks obviously wrong at a glance.

Kept tkinter-free (unlike gui.py) so it's covered by the pytest suite
without needing a display or Tk installed.
"""

import os

SAMPLE_FILENAMES = {"sample_role_tcodes.csv", "sample_user_roles.csv", "sample_composite_roles.csv"}


def is_sample_data_path(path, project_root):
    """True if `path` resolves to one of the bundled data/sample_*.csv
    files under `project_root` -- regardless of relative/absolute form,
    slash style, or path casing (Windows paths are case-insensitive).
    """
    if not path:
        return False
    resolved = os.path.normcase(os.path.normpath(os.path.abspath(path)))
    return any(
        resolved == os.path.normcase(os.path.normpath(os.path.abspath(os.path.join(project_root, "data", name))))
        for name in SAMPLE_FILENAMES
    )


def any_sample_data_paths(paths, project_root):
    """True if any of the given paths is a bundled sample CSV."""
    return any(is_sample_data_path(p, project_root) for p in paths)
