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
import os
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
release = '0.18.1'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    # This is used by qiskit/documentation to generate links to github.com.
    "sphinx.ext.viewcode",
    'jupyter_sphinx',
    'sphinx_autodoc_typehints',
    'reno.sphinxext',
    'nbsphinx',
    'sphinxcontrib.katex',
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
