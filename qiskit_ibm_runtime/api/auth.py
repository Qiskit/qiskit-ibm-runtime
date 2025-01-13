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

from typing import Dict

from requests import PreparedRequest, post
from requests.auth import AuthBase
from ..exceptions import IBMNotAuthorizedError

CLOUD_IAM_URL = "https://iam.cloud.ibm.com/identity/token"


class CloudAuth(AuthBase):
    """Attaches IBM Cloud Authentication to the given Request object."""

    def __init__(self, api_key: str, crn: str):
        self.api_key = api_key
        self.crn = crn
        self.access_token = self._get_access_token()

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

    def _get_access_token(self) -> str:
        """Return IBM Cloud access token."""
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"
            response = post(CLOUD_IAM_URL, headers=headers, data=data, timeout=10).json()
            return response["access_token"]
        except Exception as ex:  # pylint: disable=broad-except
            raise IBMNotAuthorizedError(
                "Unable to retrieve IBM Cloud access token. Please check your credentials"
            ) from ex

    def get_headers(self) -> Dict:
        """Return authorization information to be stored in header."""
        return {"Service-CRN": self.crn, "Authorization": f"Bearer {self.access_token}"}


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
