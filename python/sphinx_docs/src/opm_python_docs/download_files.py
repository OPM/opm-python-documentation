#! /usr/bin/env python3

import logging
from pathlib import Path

import requests

import click

from opm_python_docs import helpers

URL_SIMULATORS = "https://raw.githubusercontent.com/OPM/opm-simulators/master/python/docstrings_simulators.json"
URL_COMMON = "https://raw.githubusercontent.com/OPM/opm-common/master/python/docstrings_common.json"
URL_DUNE_MODULE = "https://raw.githubusercontent.com/OPM/opm-simulators/master/dune.module"


def docstrings_dir() -> Path:
    """Return the directory the documentation build reads downloaded files from.

    docs/conf.py reads python/master-tmp/ on every branch except release
    branches, which use snapshots committed under python/ instead. Nothing is
    downloaded on a release branch; see main().
    """
    target = helpers.get_git_root() / "python" / "master-tmp"
    target.mkdir(parents=True, exist_ok=True)
    return target

def convert_pr_to_commit_hash(repo: str, pr_number: int) -> str:
    """Convert a PR number to a commit hash."""
    url = f"https://api.github.com/repos/OPM/{repo}/pulls/{pr_number}"
    response = requests.get(url)
    response.raise_for_status()
    commit_hash = response.json()["head"]["sha"]
    return commit_hash

def download_docstring_file(url: str, pr_number: int|None) -> None:
    """Download a docstrings file from a URL (either opm-simulators or opm-common)."""
    if "opm-simulators" in url:
        repo = "opm-simulators"
        filename = "docstrings_simulators.json"
    else:
        repo = "opm-common"
        filename = "docstrings_common.json"
    if pr_number is not None:
        commit_hash = convert_pr_to_commit_hash(repo, pr_number)
        url = url.replace("/master/", f"/{commit_hash}/")
    logging.info(f"Downloading docstrings file from {url}")
    response = requests.get(url)
    response.raise_for_status()  # Raises 404 if the file is not found
    save_path = docstrings_dir() / filename
    with open(str(save_path), "wb") as file:
        file.write(response.content)
    logging.info(f"Saved docstrings file to {save_path}")

def download_dune_module() -> None:
    """Download the dune.module file from the opm-simulators repository."""
    logging.info("Downloading dune.module file")
    response = requests.get(URL_DUNE_MODULE)
    response.raise_for_status()
    save_path = docstrings_dir() / "dune.module"
    with open(save_path, "wb") as file:
        file.write(response.content)
    logging.info(f"Saved dune.module file to {save_path}")

# CLI command: opmdoc-download-files
#
# SHELL USAGE:
#
#  opmdoc-download-files --opm-simulators <pr-number> --opm-common <pr-number>
#
# DESCRIPTION:
#
#  Downloads the docstring JSON files from opm-simulators and opm-common. Also downloads
#  the dune.module from opm-simulators. By default, the files are downloaded from the
#  master branches. If a PR number is provided, the files are downloaded from the corresponding
#  PR branch.
#
# EXAMPLES:
#
#  opmdoc-download-files   # Downloads the docstrings files and dune.module file from master branches
#
#  opmdoc-download-files \
#     --opm-simulators 1234 \
#     --opm-common 5678 # Downloads the docstrings files from PR 1234 and 5678 and dune.module from master
#
#
@click.command()
@click.option("--opm-simulators", type=int, help="PR number for opm-simulators")
@click.option("--opm-common", type=int, help="PR number for opm-common")
def main(opm_simulators: int|None, opm_common: int|None) -> None:
    logging.basicConfig(level=logging.INFO)
    branch = helpers.get_current_branch()
    if branch.startswith("release-"):
        # The committed snapshot in python/ must not be replaced by master's files.
        raise click.ClickException(
            f"'{branch}' is a release branch. Release branches build from the "
            "docstring snapshots committed in python/, so there is nothing to "
            "download. To update a release snapshot, take the files from the "
            "release's own branch or tag in opm-common and opm-simulators."
        )
    download_docstring_file(URL_SIMULATORS, pr_number=opm_simulators)
    download_docstring_file(URL_COMMON, pr_number=opm_common)
    download_dune_module()

if __name__ == '__main__':
    main()
