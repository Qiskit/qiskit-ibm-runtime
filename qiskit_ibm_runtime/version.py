# This code is part of Qiskit.
#
# (C) Copyright IBM 2021, 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Contains the package version.

Example::
    from qiskit_ibm_runtime.version import __version__
    print(__version__)
"""

import os
import subprocess
import importlib.resources  # <-- Use importlib.resources
import logging              # <-- Add logging for warnings
from typing import List

# Get logger for this module
logger = logging.getLogger(__name__)

# Define ROOT_DIR based on the location of *this file* for git checks if needed
# Note: This ROOT_DIR is mainly for the git commands below, not for VERSION.txt reading
ROOT_DIR_VERSION_PY = os.path.dirname(os.path.abspath(__file__))


def _minimal_ext_cmd(cmd: List[str]) -> bytes:
    """Helper function to run external commands."""
    # construct minimal environment
    env = {}
    for k in ["SYSTEMROOT", "PATH"]:
        version_env = os.environ.get(k)
        if version_env is not None:
            env[k] = version_env
    # LANGUAGE is used on win32
    env["LANGUAGE"] = "C"
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    # Construct path relative to the main package directory if possible
    # This assumes version.py is one level down from the main package root during dev
    # Or relative to the top-level project dir containing .git
    project_root = os.path.dirname(os.path.dirname(ROOT_DIR_VERSION_PY))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=project_root, # Run git command from project root
    )
    out, err = proc.communicate()
    if proc.returncode > 0:
        # Log stderr but don't raise OSError immediately for git checks
        logger.debug("Git command '%s' failed with stderr: %s", ' '.join(cmd), err.decode('utf-8', errors='replace'))
        return b"" # Return empty bytes on failure
    return out


def git_version() -> str:
    """Get the current git head sha1."""
    # Determine if we're at main
    try:
        out = _minimal_ext_cmd(["git", "rev-parse", "HEAD"])
        git_revision = out.strip().decode("ascii")
        if not git_revision: # Handle case where git command failed silently
             return "Unknown"
    except Exception as e: # Catch broader exceptions during git call
        logger.debug("Could not get git revision: %s", e)
        git_revision = "Unknown"

    return git_revision

# --- Read VERSION using importlib.resources (The Fix) ---
try:
    # Reads VERSION.txt packaged *within* the 'qiskit_ibm_runtime' distribution
    # Assumes VERSION.txt is at the same level as __init__.py in the installed package
    VERSION = importlib.resources.read_text("qiskit_ibm_runtime", "VERSION.txt", encoding="utf-8").strip()
    logger.debug("Successfully read VERSION %s from package resources.", VERSION)
except (ImportError, FileNotFoundError, ModuleNotFoundError, NotADirectoryError) as e: # Catch more potential errors
    logger.warning(
        "Could not read version from packaged VERSION.txt using importlib.resources: %s. "
        "Build/installation might be incomplete. Setting version to '0.0.0'.", e
    )
    VERSION = "0.0.0" # Fallback version
# --- End of VERSION reading fix ---


def get_version_info() -> str:
    """Get the full version string, appending git commit info for dev installs."""
    # Start with the VERSION read from the packaged file (or fallback)
    full_version = VERSION

    # Check if this looks like a development install (e.g., editable install)
    # by checking for the presence of a .git directory higher up.
    project_root_for_git = os.path.dirname(os.path.dirname(ROOT_DIR_VERSION_PY))
    if not os.path.exists(os.path.join(project_root_for_git, ".git")):
        # Not a git repository install, return VERSION as is
        return full_version

    # If it IS a git repo, try to get commit info to append
    try:
        # Check if the current commit is tagged as a release
        release_tags = _minimal_ext_cmd(["git", "tag", "-l", "--points-at", "HEAD"])
        if not release_tags:
            # Not a release tag, append dev info
            git_revision = git_version()
            if git_revision != "Unknown":
                 # Append .dev0+<short_hash> only if VERSION itself doesn't already indicate dev
                 if ".dev" not in full_version:
                    full_version += ".dev0+" + git_revision[:7]
                 # else: # Potentially handle case where VERSION might already be like '0.xx.0.dev...'
                 #     pass # Or append git hash anyway? Depends on project convention.
    except Exception as e:
        # Ignore errors during git checks for dev versions, just return VERSION
        logger.debug("Could not get git tag/revision info for dev version: %s", e)

    return full_version


# Set the package-level version variable
__version__ = get_version_info()