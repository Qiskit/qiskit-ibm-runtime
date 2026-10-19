# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Calibrator options."""

from __future__ import annotations

from .base import BaseOptionsModel
from .environment import EnvironmentOptions


class ReadoutAngleOptions(BaseOptionsModel):
    """Options for readout angle calibration."""

    enable: bool = True
    """Whether to perform readout angle calibration."""


class OneAndTwoQubitOptions(BaseOptionsModel):
    """Options for one-and-two-qubit calibration."""

    enable: bool = False
    """Whether to perform one-and-two-qubit calibration."""


class TwoQubitOptions(BaseOptionsModel):
    """Options for two-qubit calibration."""

    enable: bool = False
    """Whether to perform two-qubit calibration."""


class TwoQubitFractionalOptions(BaseOptionsModel):
    """Options for two-qubit fractional calibration."""

    enable: bool = False
    """Whether to perform two-qubit fractional calibration."""


class TlsBiasOptions(BaseOptionsModel):
    """Options for TLS bias calibration."""

    enable: bool = False
    """Whether to perform TLS bias calibration."""


class CalibratorOptions(BaseOptionsModel):
    """Options for the Calibrator."""

    environment: EnvironmentOptions = EnvironmentOptions()
    """Options related to the execution environment."""

    experimental: dict = {}
    """Experimental options that are passed to the executor."""

    readout_angle: ReadoutAngleOptions = ReadoutAngleOptions()
    """Options for readout angle calibration."""

    one_and_two_qubit: OneAndTwoQubitOptions = OneAndTwoQubitOptions()
    """Options for one-and-two-qubit calibration."""

    two_qubit: TwoQubitOptions = TwoQubitOptions()
    """Options for two-qubit calibration."""

    two_qubit_fractional: TwoQubitFractionalOptions = TwoQubitFractionalOptions()
    """Options for two-qubit fractional calibration."""

    tls_bias: TlsBiasOptions = TlsBiasOptions()
    """Options for TLS bias calibration."""
