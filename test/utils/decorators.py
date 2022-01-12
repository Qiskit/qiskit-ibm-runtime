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
        * QISKIT_IBM_API_TOKEN: default API token to use.
        * QISKIT_IBM_API_URL: default API url to use.
        * QISKIT_IBM_HGP: default hub/group/project to use.
        * QISKIT_IBM_PRIVATE_HGP: hub/group/project to use for private jobs.
        * QISKIT_IBM_DEVICE: default device to use.
        * QISKIT_IBM_USE_STAGING_CREDENTIALS: True if use staging credentials.
        * QISKIT_IBM_STAGING_API_TOKEN: staging API token to use.
        * QISKIT_IBM_STAGING_API_URL: staging API url to use.
        * QISKIT_IBM_STAGING_HGP: staging hub/group/project to use.
        * QISKIT_IBM_STAGING_DEVICE: staging device to use.
        * QISKIT_IBM_STAGING_PRIVATE_HGP: staging hub/group/project to use for private jobs.
"""

import os
from functools import wraps
from unittest import SkipTest
from typing import Optional, List, Union

from qiskit.test.testing_options import get_test_options
from qiskit_ibm_runtime import IBMRuntimeService

from ..mock.fake_runtime_service import FakeRuntimeService


def requires_online_access(func):
    """Decorator that signals whether online access is needed."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        if get_test_options()["skip_online"]:
            raise SkipTest("Skipping online tests")
        return func(*args, **kwargs)

    return _wrapper


def requires_qe_access(func):
    """Test requires legacy access."""

    @wraps(func)
    def _wrapper(obj, *args, **kwargs):
        token, url, _ = _get_token_url_instance("legacy")
        kwargs.update({"qe_token": token, "qe_url": url})
        return func(obj, *args, **kwargs)

    return _wrapper


def requires_multiple_hgps(func):
    """Test requires a public and premium hgp."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        service = _get_service("legacy")
        hgps = list(service._hgps.keys())
        if len(hgps) < 2:
            raise SkipTest("Test require at least 2 hub/group/project.")

        # Get open access hgp
        open_hgp = hgps[-1]
        premium_hgp = hgps[0]
        kwargs.update(
            {
                "service": service,
                "open_hgp": open_hgp,
                "premium_hgp": premium_hgp,
            }
        )
        return func(*args, **kwargs)

    return _wrapper


def requires_legacy_service(func):
    """Test requires legacy online API."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        token, url, instance = _get_token_url_instance("legacy")
        service = IBMRuntimeService(
            auth="legacy", token=token, url=url, instance=instance
        )
        kwargs.update({"service": service, "instance": instance})
        return func(*args, **kwargs)

    return _wrapper


def requires_cloud_service(func):
    """Test requires cloud online API."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        token, url, instance = _get_token_url_instance("cloud")
        service = IBMRuntimeService(
            auth="cloud", token=token, url=url, instance=instance
        )
        kwargs.update({"service": service, "instance": instance})
        return func(*args, **kwargs)

    return _wrapper


def requires_cloud_legacy_services(func):
    """Test requires cloud online API."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        cloud_token, cloud_url, cloud_instance = _get_token_url_instance("cloud")
        cloud_service = IBMRuntimeService(
            auth="cloud", token=cloud_token, url=cloud_url, instance=cloud_instance
        )
        legacy_token, legacy_url, legacy_instance = _get_token_url_instance("legacy")
        legacy_service = IBMRuntimeService(
            auth="legacy", token=legacy_token, url=legacy_url, instance=legacy_instance
        )

        kwargs.update({"services": [cloud_service, legacy_service]})
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


def requires_cloud_legacy_devices(func):
    """Test requires both cloud and legacy devices."""

    @wraps(func)
    def _wrapper(obj, *args, **kwargs):

        devices = []
        token, url, instance = _get_token_url_instance("cloud")
        service = IBMRuntimeService(
            auth="cloud", token=token, url=url, instance=instance
        )
        # TODO use real device when cloud supports it
        devices.append(service.least_busy(min_num_qubits=5))

        token, url, instance = _get_token_url_instance("legacy")
        service = IBMRuntimeService(
            auth="legacy", token=token, url=url, instance=instance
        )
        devices.append(
            service.least_busy(simulator=False, min_num_qubits=5, instance=instance)
        )

        kwargs.update({"devices": devices})
        return func(obj, *args, **kwargs)

    return _wrapper


@requires_online_access
def _get_token_url_instance(auth):
    # TODO: Change this once we start using different environments
    if auth == "cloud":
        if os.getenv("QISKIT_IBM_USE_STAGING_CREDENTIALS", ""):
            return (
                os.getenv("QISKIT_IBM_STAGING_CLOUD_TOKEN"),
                os.getenv("QISKIT_IBM_STAGING_CLOUD_URL"),
                os.getenv("QISKIT_IBM_STAGING_CLOUD_CRN"),
            )

        return (
            os.getenv("QISKIT_IBM_CLOUD_TOKEN"),
            os.getenv("QISKIT_IBM_CLOUD_URL"),
            os.getenv("QISKIT_IBM_CLOUD_CRN"),
        )

    if os.getenv("QISKIT_IBM_USE_STAGING_CREDENTIALS", ""):
        # Special case: instead of using the standard credentials mechanism,
        # load them from different environment variables. This assumes they
        # will always be in place, as is used by the CI setup.
        return (
            os.getenv("QISKIT_IBM_STAGING_API_TOKEN"),
            os.getenv("QISKIT_IBM_STAGING_API_URL"),
            os.getenv("QISKIT_IBM_STAGING_HGP"),
        )

    return (
        os.getenv("QISKIT_IBM_API_TOKEN"),
        os.getenv("QISKIT_IBM_API_URL"),
        os.getenv("QISKIT_IBM_HGP"),
    )


def _get_service(auth: str) -> Union[List, IBMRuntimeService]:
    """Return service(s).

    Args:
        auth: Service type, ``cloud``, ``legacy``, or ``both``.

    Returns:
        Runtime service(s)
    """
    if auth in ["cloud", "legacy"]:
        token, url, instance = _get_token_url_instance(auth)
        return IBMRuntimeService(auth=auth, token=token, url=url, instance=instance)

    services = []
    for auth_ in ["cloud", "legacy"]:
        token, url, instance = _get_token_url_instance(auth_)
        services.append(
            IBMRuntimeService(auth=auth_, token=token, url=url, instance=instance)
        )
    return services


def _get_custom_hgp() -> Optional[str]:
    """Get a custom hub/group/project

    Gets the hub/group/project set in QISKIT_IBM_STAGING_HGP for staging env or
        QISKIT_IBM_HGP for production env.

    Returns:
        Custom hub/group/project or ``None`` if not set.
    """
    hgp = (
        os.getenv("QISKIT_IBM_STAGING_HGP", None)
        if os.getenv("QISKIT_IBM_USE_STAGING_CREDENTIALS", "")
        else os.getenv("QISKIT_IBM_HGP", None)
    )
    return hgp


def run_legacy_and_cloud_fake(func):
    """Decorator that runs a test using both legacy and cloud fake services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        legacy_service = FakeRuntimeService(
            auth="legacy", token="my_token", instance="h/g/p"
        )
        cloud_service = FakeRuntimeService(
            auth="cloud", token="my_token", instance="crn:123"
        )
        for service in [legacy_service, cloud_service]:
            with self.subTest(service=service.auth):
                kwargs["service"] = service
                func(self, *args, **kwargs)

    return _wrapper


def run_cloud_legacy_real(func):
    """Decorator that runs a test using both legacy and cloud real services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        for service in self.services:
            # for service, instance in [(legacy_service, legacy_instance)]:
            with self.subTest(service=service.auth):
                kwargs["service"] = service
                func(self, *args, **kwargs)

    return _wrapper
