"""Tests for the JSON -> Sphinx documentation extension.

The template format stores a method's docstring as a single JSON string with
embedded newlines. The extension has to hand those to docutils one line at a
time; feeding it the whole docstring as a single line makes docutils treat
reStructuredText field lists such as ``:param x:`` as ordinary text, so the
published page shows the markup instead of a parameter table.
"""

import shutil
from pathlib import Path

from sphinx.application import Sphinx


def build_docs(tmp_path: Path, test_file_path: Path, json_name: str) -> str:
    """Build a minimal Sphinx project that renders one docstrings JSON file.

    Returns the generated HTML.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    shutil.copy(test_file_path / json_name, srcdir / json_name)

    (srcdir / "conf.py").write_text(
        "extensions = ['opm_python_docs.sphinx_ext_docstrings']\n"
        f"opm_simulators_docstrings_path = r'{srcdir / json_name}'\n"
        f"opm_common_docstrings_path = r'{srcdir / json_name}'\n"
    )
    (srcdir / "index.rst").write_text(
        "Test\n"
        "====\n"
        "\n"
        ".. opm_simulators_docstrings::\n"
    )

    outdir = tmp_path / "out"
    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(tmp_path / "doctrees"),
        buildername="html",
    )
    app.build()
    return (outdir / "index.html").read_text()


def test_template_format_renders_field_lists(
    tmp_path: Path, test_file_path: Path
) -> None:
    """A ``:param:`` in a template-format docstring becomes a parameter table."""
    html = build_docs(tmp_path, test_file_path, "docstrings_simulators_template.json")

    # The rendered page must not contain the field-list markup as visible text.
    assert ":param report_step:" not in html
    assert ":type report_step:" not in html

    # It must contain a real parameter table instead.
    assert "field-list" in html
    assert "report_step" in html
    assert "Target report step to advance to." in html


def test_template_format_renders_constructor_field_lists(
    tmp_path: Path, test_file_path: Path
) -> None:
    """Constructors go through a separate code path and need the same handling."""
    html = build_docs(tmp_path, test_file_path, "docstrings_simulators_template.json")

    assert ":param filename:" not in html
    assert "Path to the deck file." in html
