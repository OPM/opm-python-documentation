"""Tests for the docstrings download command.

docs/conf.py reads the docstring JSON files from python/master-tmp/ on every
branch except release branches, so opmdoc-download-files has to write there,
or the build fails with a FileNotFoundError on a file the user has just
downloaded.

Release branches are different: they build from snapshots committed under
python/, taken from the release's own sources. Downloading master's files
there would overwrite that snapshot, so on a release branch the command must
refuse and write nothing.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_mock.plugin import MockerFixture

from opm_python_docs import download_files


def _fake_repo(tmp_path: Path, mocker: MockerFixture, branch: str) -> Path:
    (tmp_path / "python").mkdir()
    mocker.patch.object(download_files.helpers, "get_git_root", return_value=tmp_path)
    mocker.patch.object(
        download_files.helpers, "get_current_branch", return_value=branch
    )
    return tmp_path


@pytest.mark.parametrize("branch", ["master", "some-feature-branch"])
def test_docstrings_dir_is_master_tmp(
    tmp_path: Path, mocker: MockerFixture, branch: str
) -> None:
    root = _fake_repo(tmp_path, mocker, branch)
    assert download_files.docstrings_dir() == root / "python" / "master-tmp"


def test_docstrings_dir_creates_master_tmp(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """A fresh clone has no python/master-tmp, so it must be created."""
    root = _fake_repo(tmp_path, mocker, "master")
    assert not (root / "python" / "master-tmp").exists()
    assert download_files.docstrings_dir().is_dir()


def test_main_downloads_into_master_tmp(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    root = _fake_repo(tmp_path, mocker, "master")
    response = mocker.Mock(content=b"{}")
    get = mocker.patch.object(download_files.requests, "get", return_value=response)

    result = CliRunner().invoke(download_files.main, [])

    assert result.exit_code == 0, result.output
    assert get.call_count == 3
    written = sorted(p.name for p in (root / "python" / "master-tmp").iterdir())
    assert written == ["docstrings_common.json", "docstrings_simulators.json", "dune.module"]


def test_main_refuses_on_a_release_branch(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """The committed release snapshot must not be replaced by master's files."""
    root = _fake_repo(tmp_path, mocker, "release-2026.04")
    snapshot = root / "python" / "docstrings_simulators.json"
    snapshot.write_text("release snapshot")
    get = mocker.patch.object(download_files.requests, "get")

    result = CliRunner().invoke(download_files.main, [])

    assert result.exit_code != 0
    assert "release branch" in result.output
    get.assert_not_called()
    assert snapshot.read_text() == "release snapshot"
    assert not (root / "python" / "master-tmp").exists()
