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

"""Utilities for working with IBM Quantum backends."""

from typing import List, Dict, Union, Optional
import logging
import traceback

import dateutil.parser
from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping

from qiskit.circuit import CONTROL_FLOW_OP_NAMES

from ..models import (
    BackendProperties,
    QasmBackendConfiguration,
)

from .converters import utc_to_local_all
from .utils import is_fractional_gate

logger = logging.getLogger(__name__)


def configuration_from_server_data(
    raw_config: Dict,
    instance: str = "",
    use_fractional_gates: Optional[bool] = False,
) -> Optional[QasmBackendConfiguration]:
    """Create a backend configuration instance from raw server data.

    Args:
        raw_config: Raw configuration.
        instance: Service instance.
        use_fractional_gates: Set True to allow for the backends to include
            fractional gates. See :meth:`~.QiskitRuntimeService.backends`
            for further details.

    Returns:
        Backend configuration.
    """
    # Make sure the raw_config is of proper type
    if not isinstance(raw_config, dict):
        logger.warning(  # type: ignore[unreachable]
            "An error occurred when retrieving backend "
            "information. Some backends might not be available."
        )
        return None
    try:
        decode_backend_configuration(raw_config)
        filter_raw_configuration(raw_config, use_fractional_gates=use_fractional_gates)
        return QasmBackendConfiguration.from_dict(raw_config)
    except Exception:  # pylint: disable=broad-except
        logger.warning(
            'Remote backend "%s" for service instance %s could not be instantiated due '
            "to an invalid server-side configuration",
            raw_config.get("backend_name", raw_config.get("name", "unknown")),
            repr(instance),
        )
        logger.debug("Invalid device configuration: %s", traceback.format_exc())
    return None


def filter_raw_configuration(
    raw_config: dict, use_fractional_gates: Optional[bool] = False
) -> None:
    """Filter unwanted entries from raw configuration data

    Args:
        use_fractional_gates: Set True to allow for the backends to include
            fractional gates. See :meth:`~.QiskitRuntimeService.backends`
                for further details.
    """
    if use_fractional_gates is None:
        return

    gate_map = get_standard_gate_name_mapping()
    if use_fractional_gates:
        raw_config["conditional"] = False
        if "supported_instructions" in raw_config:
            raw_config["supported_instructions"] = [
                i for i in raw_config["supported_instructions"] if i not in CONTROL_FLOW_OP_NAMES
            ]
        if "supported_features" in raw_config:
            raw_config["supported_features"] = [
                g for g in raw_config["supported_features"] if g != "qasm3"
            ]
    else:
        if "basis_gates" in raw_config:
            raw_config["basis_gates"] = [
                g
                for g in raw_config["basis_gates"]
                if g not in gate_map or not is_fractional_gate(gate_map[g])
            ]
        if "gates" in raw_config:
            raw_config["gates"] = [
                g
                for g in raw_config["gates"]
                if g.get("name") not in gate_map or not is_fractional_gate(gate_map[g.get("name")])
            ]
        if "supported_instructions" in raw_config:
            raw_config["supported_instructions"] = [
                i
                for i in raw_config["supported_instructions"]
                if i not in gate_map or not is_fractional_gate(gate_map[i])
            ]


def properties_from_server_data(
    properties: Dict, use_fractional_gates: Optional[bool] = False
) -> BackendProperties:
    """Decode backend properties.

    Args:
        properties: Raw properties data.
        use_fractional_gates: Set True to allow for the backends to include
            fractional gates. See :meth:`~.QiskitRuntimeService.backends`
            for further details.

    Returns:
        A ``BackendProperties`` instance.
    """
    gate_map = get_standard_gate_name_mapping()

    if "gates" in properties and isinstance(properties["gates"], list):
        if use_fractional_gates is not None and not use_fractional_gates:
            properties["gates"] = [
                g
                for g in properties["gates"]
                if g.get("name") not in gate_map or not is_fractional_gate(gate_map[g.get("name")])
            ]

    if isinstance(properties["last_update_date"], str):
        properties["last_update_date"] = dateutil.parser.isoparse(properties["last_update_date"])
        for qubit in properties["qubits"]:
            for nduv in qubit:
                nduv["date"] = dateutil.parser.isoparse(nduv["date"])
        for gate in properties["gates"]:
            for param in gate["parameters"]:
                param["date"] = dateutil.parser.isoparse(param["date"])
        for gen in properties["general"]:
            gen["date"] = dateutil.parser.isoparse(gen["date"])

    properties = utc_to_local_all(properties)
    return BackendProperties.from_dict(properties)


def decode_backend_configuration(config: Dict) -> None:
    """Decode backend configuration.

    Args:
        config: A ``QasmBackendConfiguration`` in dictionary format.
    """
    config["online_date"] = dateutil.parser.isoparse(config["online_date"])

    if "u_channel_lo" in config:
        for u_channel_list in config["u_channel_lo"]:
            for u_channel_lo in u_channel_list:
                u_channel_lo["scale"] = _to_complex(u_channel_lo["scale"])


# TODO: remove this when no longer needed server-side
_decode_backend_configuration = decode_backend_configuration


def _to_complex(value: Union[List[float], complex]) -> complex:
    """Convert the input value to type ``complex``.

    Args:
        value: Value to be converted.

    Returns:
        Input value in ``complex``.

    Raises:
        TypeError: If the input value is not in the expected format.
    """
    if isinstance(value, list) and len(value) == 2:
        return complex(value[0], value[1])
    elif isinstance(value, complex):
        return value

    raise TypeError("{} is not in a valid complex number format.".format(value))
