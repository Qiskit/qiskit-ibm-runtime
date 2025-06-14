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

import warnings
from requests import PreparedRequest
from requests.auth import AuthBase

from ibm_cloud_sdk_core import IAMTokenManager
from ..utils.utils import cname_from_crn

CLOUD_IAM_URL = "iam.cloud.ibm.com"
STAGING_CLOUD_IAM_URL = "iam.test.cloud.ibm.com"


class CloudAuth(AuthBase):
    """Attaches IBM Cloud Authentication to the given Request object."""

    def __init__(self, api_key: str, crn: str, private: bool = False):
        self.crn = crn
        self.api_key = api_key
        iam_url = (
            f"https://{'private.' if private else ''}"
            f"{STAGING_CLOUD_IAM_URL if cname_from_crn(crn) == 'staging' else CLOUD_IAM_URL}"
        )
        self.tm = IAMTokenManager(api_key, url=iam_url)

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

    def __deepcopy__(self, _memo: dict = None) -> "CloudAuth":
        cpy = CloudAuth(
            api_key=self.api_key,
            crn=self.crn,
        )
        return cpy

    def get_headers(self) -> Dict:
        """Return authorization information to be stored in header."""
        try:
            access_token = self.tm.get_token()
            return {"Service-CRN": self.crn, "Authorization": f"Bearer {access_token}"}
        except Exception as ex:  # pylint: disable=broad-except
            warnings.warn(
                f"Unable to retrieve IBM Cloud access token. API Key will be used instead. {ex}"
            )
            return {"Service-CRN": self.crn, "Authorization": f"apikey {self.api_key}"}
