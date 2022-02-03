# This code is part of Qiskit.
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

"""Integration tests.

Executed against an external system configured via the (token, instance, url) tuple.
Detailed coverage of happy and non-happy paths. They are long-running and unstable at times.
A successful test run gives a high level of confidence that client and APIs work well together.
"""
