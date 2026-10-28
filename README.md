# Repository to host the Python documentation for OPM Flow

## Reading the documentation online

The documentation of the current master can found [here](https://opm.github.io/opm-python-documentation/master/index.html)

## Building the documentation locally

Requires Python 3.10 or newer and [poetry](https://python-poetry.org/docs/).

1. **Check out the branch you want to build, and commit your changes.**
   `sphinx-versioned` builds from git history rather than from the working
   tree, so uncommitted edits are invisible to it.

2. **Install the helper scripts and fetch the docstring files.**

   ```
   cd python/sphinx_docs
   poetry install
   poetry run opmdoc-download-files
   ```

   The API pages are generated from `docstrings_common.json` and
   `docstrings_simulators.json`, which live in `opm-common` and `opm-simulators`
   rather than in this repository. `opmdoc-download-files` fetches the current
   master copies. To build against a pull request in one of those repositories
   instead, pass its number: `opmdoc-download-files --opm-simulators 1234`.

   On a release branch (`release-*`), skip this download. Release branches build
   from snapshots of these files committed under `python/`, and
   `opmdoc-download-files` refuses to run there rather than overwrite them.

3. **Build, and open the result.**

   ```
   poetry run make docs
   poetry run opmdoc-view-doc
   ```

   `make docs` builds the branch you are on; `opmdoc-view-doc` opens it in your
   default browser, on Linux, macOS and Windows alike. Add `--branch=master` to
   open a different branch. The generated pages are written to
   `python/sphinx_docs/docs/_build/<branch>/` and open correctly straight from
   disk, so no web server is needed.

See [python/sphinx_docs/README.md](python/sphinx_docs/README.md) for the
individual scripts, and `.github/workflows/python_sphinx_docs.yml` for how the
published site is built.

## Building the documentation online on your fork
- Turn on github actions at `https://github.com/<your-github-username>/opm-python-documentation/actions`
- Add the docstrings_common.json and docstrings_simulators.json file you want to test to the python folder
- Push any changes to a branch of your fork, this should trigger a build of the documentation, where the built documentation is pushed to the branch `gh-pages-<name-of-your-branch>`
- Then you can turn on github pages for your fork at `https://github.com/<your-github-username>/opm-python-documentation/settings/pages`
- Select the branch `gh-pages-<name-of-your-branch>` as the source for your github page
- Then you can have a look at the documentation with your changes at `https://<your-github-username>.github.io/opm-python-documentation/<name-of-your-branch>/index.html`
- If everything looks fine, create a pull request for the master branch of this repository :)
