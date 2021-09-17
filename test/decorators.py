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
from typing import Optional

from qiskit.test.testing_options import get_test_options
from qiskit_ibm import least_busy
from qiskit_ibm import IBMProvider
from qiskit_ibm.credentials import (Credentials,
                                    discover_credentials)


def requires_qe_access(func):
    """Decorator that signals that the test uses the online API.

    It involves:
        * determines if the test should be skipped by checking environment
            variables.
        * if the `QISKIT_IBM_USE_STAGING_CREDENTIALS` environment variable is
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
        if get_test_options()['skip_online']:
            raise SkipTest('Skipping online tests')

        credentials = _get_credentials()
        kwargs.update({'qe_token': credentials.token,
                       'qe_url': credentials.url})

        return func(obj, *args, **kwargs)

    return _wrapper


def requires_providers(func):
    """Decorator that signals the test uses the online API, via a public and premium provider.

    This decorator delegates into the `requires_qe_access` decorator, but
    instead of the credentials it appends a dictionary, containing the open access project
    `public_provider` and a `premium_provider`, to the decorated function.

    Args:
        func (callable): Test function to be decorated.

    Returns:
        callable: The decorated function.
    """
    @wraps(func)
    @requires_qe_access
    def _wrapper(*args, **kwargs):
        qe_token = kwargs.pop('qe_token')
        qe_url = kwargs.pop('qe_url')

        # Get the open access project public provider.
        public_provider = IBMProvider(qe_token, qe_url)
        # Get a premium provider.
        premium_provider = _get_custom_provider(qe_token, qe_url)

        if premium_provider is None:
            raise SkipTest('Requires both the public provider and a premium provider.')

        kwargs.update({
            'providers': {'public_provider': public_provider,
                          'premium_provider': premium_provider}
        })

        return func(*args, **kwargs)

    return _wrapper


def requires_provider(func):
    """Decorator that signals the test uses the online API, via a provider.

    This decorator delegates into the `requires_qe_access` decorator, but
    instead of the credentials it appends a `provider` argument to the decorated
    function.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """
    @wraps(func)
    @requires_qe_access
    def _wrapper(*args, **kwargs):
        token = kwargs.pop('qe_token')
        url = kwargs.pop('qe_url')
        _enable_account(token, url)
        provider = _get_custom_provider(token, url) or list(IBMProvider._providers.values())[0]
        kwargs.update({'provider': provider})

        return func(*args, **kwargs)

    return _wrapper


def requires_private_provider(func):
    """Decorator that signals the test requires a provider for private jobs.

    This decorator appends a `provider` argument to the decorated function.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """
    @wraps(func)
    @requires_qe_access
    def _wrapper(*args, **kwargs):
        token = kwargs.pop('qe_token')
        url = kwargs.pop('qe_url')
        _enable_account(token, url)

        # Get the private hub/group/project.
        hgp = os.getenv('QISKIT_IBM_STAGING_PRIVATE_HGP', None) \
            if os.getenv('QISKIT_IBM_USE_STAGING_CREDENTIALS', '') \
            else os.getenv('QISKIT_IBM_PRIVATE_HGP', None)
        if not hgp:
            raise SkipTest('Requires private provider.')

        hgp = hgp.split('/')
        provider = IBMProvider(token=token, url=url, hub=hgp[0], group=hgp[1], project=hgp[2])
        kwargs.update({'provider': provider})

        return func(*args, **kwargs)

    return _wrapper


def requires_device(func):
    """Decorator that retrieves the appropriate backend to use for testing.

    It involves:
        * Enable the account using credentials obtained from the
            `requires_qe_access` decorator.
        * Use the backend specified by `QISKIT_IBM_STAGING_DEVICE` if
            `QISKIT_IBM_USE_STAGING_CREDENTIALS` is set, otherwise use the backend
            specified by `QISKIT_IBM_DEVICE`.
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

        backend_name = os.getenv('QISKIT_IBM_STAGING_DEVICE', None) \
            if os.getenv('QISKIT_IBM_USE_STAGING_CREDENTIALS', '') \
            else os.getenv('QISKIT_IBM_DEVICE', None)

        _backend = _get_backend(qe_token=kwargs.pop('qe_token'),
                                qe_url=kwargs.pop('qe_url'),
                                backend_name=backend_name)
        kwargs.update({'backend': _backend})
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

        backend_name = os.getenv('QISKIT_IBM_STAGING_RUNTIME_DEVICE', None) \
            if os.getenv('QISKIT_IBM_USE_STAGING_CREDENTIALS', '') \
            else os.getenv('QISKIT_IBM_RUNTIME_DEVICE', None)
        if not backend_name:
            raise SkipTest("Runtime device not specified")
        _backend = _get_backend(qe_token=kwargs.pop('qe_token'),
                                qe_url=kwargs.pop('qe_url'),
                                backend_name=backend_name)
        kwargs.update({'backend': _backend})
        return func(obj, *args, **kwargs)

    return _wrapper


def _get_backend(qe_token, qe_url, backend_name):
    """Get the specified backend."""
    _enable_account(qe_token, qe_url)

    _backend = None
    provider = _get_custom_provider(qe_token, qe_url) or list(IBMProvider._providers.values())[0]

    if backend_name:
        # Put desired provider as the first in the list.
        providers = [provider] + IBMProvider._get_providers()
        for provider in providers:
            backends = provider.backends(name=backend_name)
            if backends:
                _backend = backends[0]
                break
    else:
        _backend = least_busy(provider.backends(
            simulator=False, min_num_qubits=5))

    if not _backend:
        raise Exception('Unable to find a suitable backend.')

    return _backend


def _get_credentials():
    """Finds the credentials for a specific test and options.

    Returns:
        Credentials: set of credentials

    Raises:
        Exception: When the credential could not be set and they are needed
            for that set of options.
    """
    if os.getenv('QISKIT_IBM_USE_STAGING_CREDENTIALS', ''):
        # Special case: instead of using the standard credentials mechanism,
        # load them from different environment variables. This assumes they
        # will always be in place, as is used by the CI setup.
        return Credentials(
            token=os.getenv('QISKIT_IBM_STAGING_API_TOKEN'),
            url=os.getenv('QISKIT_IBM_STAGING_API_URL'),
            auth_url=os.getenv('QISKIT_IBM_STAGING_API_URL')
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

    raise Exception('Unable to locate valid credentials.')


def _get_custom_provider(token: str, url: str) -> Optional[IBMProvider]:
    """Find the provider for the specific hub/group/project, if any.

    Returns:
        Custom provider or ``None`` if default is to be used.
    """
    hgp = os.getenv('QISKIT_IBM_STAGING_HGP', None) \
        if os.getenv('QISKIT_IBM_USE_STAGING_CREDENTIALS', '') \
        else os.getenv('QISKIT_IBM_HGP', None)
    if hgp:
        hgp = hgp.split('/')
        return IBMProvider(token=token, url=url, hub=hgp[0], group=hgp[1], project=hgp[2])
    return None  # No custom provider.


def _enable_account(qe_token: str, qe_url: str) -> None:
    """Enable the account if one is not already active.

    Args:
        qe_token: API token.
        qe_url: API URL.
    """
    active_account = IBMProvider.active_account()
    if active_account:
        if active_account.get('token', '') == qe_token:
            return
        IBMProvider._disable_account()
    IBMProvider(qe_token, qe_url)
