# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Decorators for using with IBM Provider unit tests.

    Environment variables used by the decorators:
        * QISKIT_IBM_RUNTIME_API_TOKEN: default API token to use.
        * QISKIT_IBM_RUNTIME_API_URL: default API url to use.
        * QISKIT_IBM_RUNTIME_HGP: default hub/group/project to use.
        * QISKIT_IBM_RUNTIME_PRIVATE_HGP: hub/group/project to use for private jobs.
        * QISKIT_IBM_RUNTIME_DEVICE: default device to use.
        * QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS: True if use staging credentials.
        * QISKIT_IBM_RUNTIME_STAGING_API_TOKEN: staging API token to use.
        * QISKIT_IBM_RUNTIME_STAGING_API_URL: staging API url to use.
        * QISKIT_IBM_RUNTIME_STAGING_HGP: staging hub/group/project to use.
        * QISKIT_IBM_RUNTIME_STAGING_DEVICE: staging device to use.
        * QISKIT_IBM_RUNTIME_STAGING_PRIVATE_HGP: staging hub/group/project to use for private jobs.
"""

import os
from functools import wraps
from unittest import SkipTest
from typing import Tuple, Optional

from qiskit.test.testing_options import get_test_options
from qiskit_ibm_runtime import least_busy
from qiskit_ibm_runtime import IBMRuntimeService
from qiskit_ibm_runtime.credentials import Credentials, discover_credentials
from qiskit_ibm_runtime.hub_group_project import HubGroupProject

from .mock.fake_runtime_service import FakeRuntimeService


def requires_qe_access(func):
    """Decorator that signals that the test uses the online API.

    It involves:
        * determines if the test should be skipped by checking environment
            variables.
        * if the `QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS` environment variable is
          set, it reads the credentials from an alternative set of environment
          variables.
        * if the test is not skipped, it reads `qe_token` and `qe_url` from
            environment variables or qiskitrc.
        * if the test is not skipped, it appends `qe_token` and `qe_url` as
            arguments to the test function.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @wraps(func)
    def _wrapper(obj, *args, **kwargs):
        if get_test_options()["skip_online"]:
            raise SkipTest("Skipping online tests")
        credentials = _get_credentials()
        kwargs.update({"qe_token": credentials.token, "qe_url": credentials.url})
        return func(obj, *args, **kwargs)

    return _wrapper


def requires_providers(func):
    """Decorator that signals the test uses the online API, via a public and premium hgp.

    This decorator delegates into the `requires_qe_access` decorator and appends a provider,
    an open access hub/group/project and a premium hub/group/project to the decorated function.

    Args:
        func (callable): Test function to be decorated.

    Returns:
        callable: The decorated function.
    """

    @wraps(func)
    @requires_qe_access
    def _wrapper(*args, **kwargs):
        qe_token = kwargs.pop("qe_token")
        qe_url = kwargs.pop("qe_url")
        service = IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)
        # Get open access hgp
        open_hgp = _get_open_hgp(service)
        if not open_hgp:
            raise SkipTest("Requires open access hub/group/project.")
        # Get a premium hgp
        premium_hub, premium_group, premium_project = _get_custom_hgp()
        if not all([premium_hub, premium_group, premium_project]):
            raise SkipTest(
                "Requires both the open access and premium hub/group/project."
            )
        kwargs.update(
            {
                "service": service,
                "hgps": {
                    "open_hgp": {
                        "hub": open_hgp.credentials.hub,
                        "group": open_hgp.credentials.group,
                        "project": open_hgp.credentials.project,
                    },
                    "premium_hgp": {
                        "hub": premium_hub,
                        "group": premium_group,
                        "project": premium_project,
                    },
                },
            }
        )
        return func(*args, **kwargs)

    return _wrapper


def requires_provider(func):
    """Decorator that signals the test uses the online API, via a custom hub/group/project.

    This decorator delegates into the `requires_qe_access` decorator, but
    instead of the credentials it appends a `provider` argument to the decorated
    function. It also appends the custom `hub`, `group` and `project` arguments.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @wraps(func)
    @requires_qe_access
    def _wrapper(*args, **kwargs):
        token = kwargs.pop("qe_token")
        url = kwargs.pop("qe_url")
        service = IBMRuntimeService(auth="legacy", token=token, url=url)
        hub, group, project = _get_custom_hgp()
        kwargs.update(
            {"service": service, "hub": hub, "group": group, "project": project}
        )
        return func(*args, **kwargs)

    return _wrapper


def requires_device(func):
    """Decorator that retrieves the appropriate backend to use for testing.

    It involves:
        * Enable the account using credentials obtained from the
            `requires_qe_access` decorator.
        * Use the backend specified by `QISKIT_IBM_RUNTIME_STAGING_DEVICE` if
            `QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS` is set, otherwise use the backend
            specified by `QISKIT_IBM_RUNTIME_DEVICE`.
        * if device environment variable is not set, use the least busy
            real backend.
        * appends arguments `backend` to the decorated function.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @wraps(func)
    @requires_qe_access
    def _wrapper(obj, *args, **kwargs):
        backend_name = (
            os.getenv("QISKIT_IBM_RUNTIME_STAGING_DEVICE", None)
            if os.getenv("QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS", "")
            else os.getenv("QISKIT_IBM_RUNTIME_DEVICE", None)
        )
        _backend = _get_backend(
            qe_token=kwargs.pop("qe_token"),
            qe_url=kwargs.pop("qe_url"),
            backend_name=backend_name,
        )
        kwargs.update({"backend": _backend})
        return func(obj, *args, **kwargs)

    return _wrapper


def requires_runtime_device(func):
    """Decorator that retrieves the appropriate backend to use for testing.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @wraps(func)
    @requires_qe_access
    def _wrapper(obj, *args, **kwargs):
        backend_name = (
            os.getenv("QISKIT_IBM_RUNTIME_STAGING_DEVICE", None)
            if os.getenv("QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS", "")
            else os.getenv("QISKIT_IBM_RUNTIME_DEVICE", None)
        )
        if not backend_name:
            raise SkipTest("Runtime device not specified")
        _backend = _get_backend(
            qe_token=kwargs.pop("qe_token"),
            qe_url=kwargs.pop("qe_url"),
            backend_name=backend_name,
        )
        kwargs.update({"backend": _backend})
        return func(obj, *args, **kwargs)

    return _wrapper


def _get_backend(qe_token, qe_url, backend_name):
    """Get the specified backend."""
    service = IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)
    _backend = None
    hub, group, project = _get_custom_hgp()
    if backend_name:
        _backend = service.get_backend(
            name=backend_name, hub=hub, group=group, project=project
        )
    else:
        _backend = least_busy(
            service.backends(
                simulator=False, min_num_qubits=5, hub=hub, group=group, project=project
            )
        )
    if not _backend:
        raise Exception("Unable to find a suitable backend.")
    return _backend


def _get_credentials():
    """Finds the credentials for a specific test and options.

    Returns:
        Credentials: set of credentials

    Raises:
        Exception: When the credential could not be set and they are needed
            for that set of options.
    """
    if os.getenv("QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS", ""):
        # Special case: instead of using the standard credentials mechanism,
        # load them from different environment variables. This assumes they
        # will always be in place, as is used by the CI setup.
        return Credentials(
            token=os.getenv("QISKIT_IBM_RUNTIME_STAGING_API_TOKEN"),
            url=os.getenv("QISKIT_IBM_RUNTIME_STAGING_API_URL"),
            auth_url=os.getenv("QISKIT_IBM_RUNTIME_STAGING_API_URL"),
        )
    # Attempt to read the standard credentials.
    discovered_credentials, _ = discover_credentials()
    if discovered_credentials:
        # Decide which credentials to use for testing.
        if len(discovered_credentials) > 1:
            try:
                # Attempt to use IBM Quantum credentials.
                return discovered_credentials[(None, None, None)]
            except KeyError:
                pass
        # Use the first available credentials.
        return list(discovered_credentials.values())[0]
    raise Exception("Unable to locate valid credentials.")


def _get_open_hgp(service: IBMRuntimeService) -> Optional[HubGroupProject]:
    """Get open hub/group/project

    Returns:
        Open hub/group/project or ``None``.
    """
    hgps = service._get_hgps()
    for hgp in hgps:
        if hgp.is_open:
            return hgp
    return None


def _get_custom_hgp() -> Tuple[str, str, str]:
    """Get a custom hub/group/project

    Gets the hub/group/project set in QISKIT_IBM_RUNTIME_STAGING_HGP for staging env or
        QISKIT_IBM_RUNTIME_HGP for production env.

    Returns:
        Tuple of custom hub/group/project or ``None`` if not set.
    """
    hub = None
    group = None
    project = None
    hgp = (
        os.getenv("QISKIT_IBM_RUNTIME_STAGING_HGP", None)
        if os.getenv("QISKIT_IBM_RUNTIME_USE_STAGING_CREDENTIALS", "")
        else os.getenv("QISKIT_IBM_RUNTIME_HGP", None)
    )
    if hgp:
        hub, group, project = hgp.split("/")
    return hub, group, project


def run_legacy_and_cloud(func):
    """Decorator that runs a test using both legacy and cloud services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        legacy_service = FakeRuntimeService(auth="legacy", token="some_token")
        cloud_service = FakeRuntimeService(auth="cloud", token="some_token")
        for service in [legacy_service, cloud_service]:
            with self.subTest(service=service.auth):
                kwargs["service"] = service
                func(self, *args, **kwargs)
    return _wrapper
