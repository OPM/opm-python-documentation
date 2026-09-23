"""Tests for the docstrings download command.

The documentation build reads its JSON files from a directory that depends on
the branch name (see docs/conf.py): release branches use the snapshots
committed under python/, every other branch uses python/master-tmp/.
opmdoc-download-files has to write into the same directory, or the build fails
with a FileNotFoundError on a file the user has just downloaded.
"""

from pathlib import Path

import pytest
from pytest_mock.plugin import MockerFixture

from opm_python_docs import download_files


@pytest.mark.parametrize(
    "branch, expected",
    [
        ("master", "python/master-tmp"),
        ("some-feature-branch", "python/master-tmp"),
        ("release-2026.04", "python"),
    ],
)
def test_docstrings_dir_follows_the_branch(
    tmp_path: Path, mocker: MockerFixture, branch: str, expected: str
) -> None:
    (tmp_path / "python").mkdir()
    mocker.patch.object(download_files.helpers, "get_git_root", return_value=tmp_path)
    mocker.patch.object(
        download_files.helpers, "get_current_branch", return_value=branch
    )

    assert download_files.docstrings_dir() == tmp_path / expected


def test_docstrings_dir_creates_master_tmp(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """A fresh clone has no python/master-tmp, so it must be created."""
    (tmp_path / "python").mkdir()
    mocker.patch.object(download_files.helpers, "get_git_root", return_value=tmp_path)
    mocker.patch.object(
        download_files.helpers, "get_current_branch", return_value="master"
    )

    assert not (tmp_path / "python" / "master-tmp").exists()
    assert download_files.docstrings_dir().is_dir()
