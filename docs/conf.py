# This code is a Qiskit project.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# -- Path setup --------------------------------------------------------------
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

# -- Project information -----------------------------------------------------
project = 'Qiskit Runtime IBM Client'
project_copyright = '2022, Qiskit Development Team'
author = 'Qiskit Development Team'
language = 'en'

# The short X.Y version
version = ''
# The full version, including alpha/beta/rc tags
release = '0.29.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    # This is used by qiskit/documentation to generate links to github.com.
    "sphinx.ext.linkcode",
    'jupyter_sphinx',
    'sphinx_autodoc_typehints',
    'nbsphinx',
    'sphinxcontrib.katex',
    'matplotlib.sphinxext.plot_directive',
]
templates_path = ['_templates']

nbsphinx_timeout = 300
nbsphinx_execute = "never"
nbsphinx_widgets_path = ''

nbsphinx_prolog = """
{% set docname = env.doc2path(env.docname, base=None) %}
.. only:: html

    .. role:: raw-html(raw)
        :format: html

    .. note::
        This page was generated from `docs/{{ docname }}`__.

        __"""

vers = release.split(".")
link_str = f" https://github.com/Qiskit/qiskit-ibm-runtime/blob/stable/{vers[0]}.{vers[1]}/docs/"
nbsphinx_prolog += link_str + "{{ docname }}"

# ----------------------------------------------------------------------------------
# Intersphinx
# ----------------------------------------------------------------------------------

intersphinx_mapping = {
    "rustworkx": ("https://www.rustworkx.org/", None),
    "qiskit": ("https://docs.quantum.ibm.com/api/qiskit/", None),
    "qiskit-aer": ("https://qiskit.github.io/qiskit-aer/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# -----------------------------------------------------------------------------
# Autosummary
# -----------------------------------------------------------------------------

autosummary_generate = True

autodoc_default_options = {
    'inherited-members': None,
}


# If true, figures, tables and code-blocks are automatically numbered if they
# have a caption.
numfig = True

# A dictionary mapping 'figure', 'table', 'code-block' and 'section' to
# strings that are used for format of figure numbers. As a special character,
# %s will be replaced to figure number.
numfig_format = {
    'table': 'Table %s'
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["**site-packages", "_build", "**.ipynb_checkpoints"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'colorful'

# A boolean that decides whether module names are prepended to all object names
# (for object types where a “module” of some kind is defined), e.g. for
# py:function directives.
add_module_names = False

# A list of prefixes that are ignored for sorting the Python module index
# (e.g., if this is set to ['foo.'], then foo.bar is shown under B, not F).
# This can be handy if you document a project that consists of a single
# package. Works only for the HTML builder currently.
modindex_common_prefix = ['qiskit.']

# -- Options for HTML output -------------------------------------------------

# Even though alabaster isn't very pretty, we use it
# over the normal qiskit-ecosystem theme because it's
# faster to build and these docs are only necessary
# so the API docs can be integrated into docs.quantum.ibm.com.
html_theme = "alabaster"
html_title = f"{project} {release}"

html_last_updated_fmt = '%Y/%m/%d'
html_sourcelink_suffix = ''
autoclass_content = 'both'


# ----------------------------------------------------------------------------------
# Source code links
# ----------------------------------------------------------------------------------

def determine_github_branch() -> str:
    """Determine the GitHub branch name to use for source code links.

    We need to decide whether to use `stable/<version>` vs. `main` for dev builds.
    Refer to https://docs.github.com/en/actions/learn-github-actions/variables
    for how we determine this with GitHub Actions.
    """
    # If CI env vars not set, default to `main`. This is relevant for local builds.
    if "GITHUB_REF_NAME" not in os.environ:
        return "main"

    # PR workflows set the branch they're merging into.
    if base_ref := os.environ.get("GITHUB_BASE_REF"):
        return base_ref

    ref_name = os.environ["GITHUB_REF_NAME"]

    # Check if the ref_name is a tag like `1.0.0` or `1.0.0rc1`. If so, we need
    # to transform it to a Git branch like `stable/1.0`.
    version_without_patch = re.match(r"(\d+\.\d+)", ref_name)
    return (
        f"stable/{version_without_patch.group()}"
        if version_without_patch
        else ref_name
    )


GITHUB_BRANCH = determine_github_branch()


def linkcode_resolve(domain, info):
    if domain != "py":
        return None

    module_name = info["module"]
    module = sys.modules.get(module_name)
    if module is None or "qiskit_ibm_runtime" not in module_name:
        return None

    obj = module
    for part in info["fullname"].split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None
        is_valid_code_object = (
            inspect.isclass(obj) or inspect.ismethod(obj) or inspect.isfunction(obj)
        )
        if not is_valid_code_object:
            return None
    try:
        full_file_name = inspect.getsourcefile(obj)
    except TypeError:
        return None
    if full_file_name is None or "/qiskit_ibm_runtime/" not in full_file_name:
        return None
    file_name = full_file_name.split("/qiskit_ibm_runtime/")[-1]

    try:
        source, lineno = inspect.getsourcelines(obj)
    except (OSError, TypeError):
        linespec = ""
    else:
        ending_lineno = lineno + len(source) - 1
        linespec = f"#L{lineno}-L{ending_lineno}"
    return f"https://github.com/Qiskit/qiskit-ibm-runtime/tree/{GITHUB_BRANCH}/qiskit_ibm_runtime/{file_name}{linespec}"
