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

"""Authentication helpers."""

import time
from typing import Dict

import warnings
from requests import PreparedRequest
from requests.auth import AuthBase

from ibm_cloud_sdk_core import IAMTokenManager
from ..utils.utils import cname_from_crn

CLOUD_IAM_URL = "https://iam.cloud.ibm.com/identity/token"
STAGING_CLOUD_IAM_URL = "https://iam.test.cloud.ibm.com/identity/token"


class CloudAuth(AuthBase):
    """Attaches IBM Cloud Authentication to the given Request object."""

    def __init__(self, api_key: str, crn: str):
        self.api_key = api_key
        self.crn = crn
        if cname_from_crn(crn) == "staging":
            self.iam_url = STAGING_CLOUD_IAM_URL
        else:
            self.iam_url = CLOUD_IAM_URL
        self._get_access_token()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CloudAuth):
            return all(
                [
                    self.api_key == other.api_key,
                    self.crn == other.crn,
                ]
            )
        return False

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers.update(self.get_headers())
        return r

    def _get_access_token(self) -> None:
        """Retrieve IBM Cloud bearer token and expiry."""
        self.access_token = None
        self.access_token_expiry = None
        try:
            start_time = time.time() - 60  # 60 second buffer
            response = IAMTokenManager(self.api_key, url=self.iam_url).request_token()
            self.access_token = response.get("access_token")
            self.access_token_expiry = start_time + response.get("expires_in")
        except Exception:  # pylint: disable=broad-except
            warnings.warn("Unable to retrieve IBM Cloud access token. API Key will be used instead")

    def get_headers(self) -> Dict:
        """Return authorization information to be stored in header."""
        if self.access_token:
            if time.time() >= self.access_token_expiry:
                self._get_access_token()  # refresh expired token
            return {"Service-CRN": self.crn, "Authorization": f"Bearer {self.access_token}"}
        return {"Service-CRN": self.crn, "Authorization": f"apikey {self.api_key}"}


class QuantumAuth(AuthBase):
    """Attaches IBM Quantum Authentication to the given Request object."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QuantumAuth):
            return self.access_token == other.access_token

        return False

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers.update(self.get_headers())
        return r

    def get_headers(self) -> Dict:
        """Return authorization information to be stored in header."""
        return {"X-Access-Token": self.access_token}
