# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit runtime service."""

from __future__ import annotations

import math
import copy
import logging
import warnings
from dataclasses import asdict
from typing import Callable, Dict, List, Literal, Optional, Union

from qiskit.primitives import (
    BackendEstimatorV2,
    BackendSamplerV2,
)
from qiskit.primitives.primitive_job import PrimitiveJob
from qiskit.providers.backend import BackendV2
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from .fake_backend import FakeBackendV2  # pylint: disable=cyclic-import
from .fake_provider import FakeProviderForBackendV2  # pylint: disable=unused-import, cyclic-import
from .local_runtime_job import LocalRuntimeJob
from ..ibm_backend import IBMBackend
from ..runtime_options import RuntimeOptions

logger = logging.getLogger(__name__)


class QiskitRuntimeLocalService:
    """Class for local testing mode."""

    def __init__(self) -> None:
        """QiskitRuntimeLocalService constructor.


        Returns:
            An instance of QiskitRuntimeService.

        """

    def backend(
        self, name: str = None, instance: str = None  # pylint: disable=unused-argument
    ) -> FakeBackendV2:
        """Return a single fake backend matching the specified filters.

        Args:
            name: The name of the backend.

        Returns:
            Backend: A backend matching the filtering.
        """
        return self.backends(name=name)[0]

    def backends(
        self,
        name: Optional[str] = None,
        min_num_qubits: Optional[int] = None,
        dynamic_circuits: Optional[bool] = None,
        filters: Optional[Callable[[FakeBackendV2], bool]] = None,
    ) -> List[FakeBackendV2]:
        """Return all the available fake backends, subject to optional filtering.

        Args:
            name: Backend name to filter by.
            min_num_qubits: Minimum number of qubits the fake backend has to have.
            dynamic_circuits: Filter by whether the fake backend supports dynamic circuits.
            filters: More complex filters, such as lambda functions.
                For example::

                    from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService

                    QiskitRuntimeService.backends(
                        filters=lambda backend: (backend.online_date.year == 2021)
                    )
                    QiskitRuntimeLocalService.backends(
                        filters=lambda backend: (backend.num_qubits > 30 and backend.num_qubits < 100)
                    )

        Returns:
            The list of available fake backends that match the filters.

        Raises:
            QiskitBackendNotFoundError: If none of the available fake backends matches the given
                filters.
        """
        backends = FakeProviderForBackendV2().backends(name)
        err = QiskitBackendNotFoundError("No backend matches the criteria.")

        if name:
            if name == "aer_simulator":
                # pylint: disable=import-outside-toplevel
                from qiskit_aer import AerSimulator

                backends = [AerSimulator()]
            else:
                for b in backends:
                    if b.name == name:
                        backends = [b]
                        break
                else:
                    raise err

        if min_num_qubits:
            backends = [b for b in backends if b.num_qubits >= min_num_qubits]

        if dynamic_circuits is not None:
            backends = [b for b in backends if b._supports_dynamic_circuits() == dynamic_circuits]

        backends = filter_backends(backends, filters=filters)

        if not backends:
            raise err

        return backends

    def least_busy(
        self,
        min_num_qubits: Optional[int] = None,
        filters: Optional[Callable[[FakeBackendV2], bool]] = None,
    ) -> FakeBackendV2:
        """Mimics the :meth:`QiskitRuntimeService.least_busy` method by returning a randomly-chosen
        fake backend.

        Args:
            min_num_qubits: Minimum number of qubits the fake backend has to have.
            filters: More complex filters, such as lambda functions, that can be defined as for the
                :meth:`backends` method.

        Returns:
            A fake backend.
        """
        return self.backends(min_num_qubits=min_num_qubits, filters=filters)[0]

    def _run(
        self,
        program_id: Literal["sampler", "estimator"],
        inputs: Dict,
        options: Union[RuntimeOptions, Dict],
    ) -> PrimitiveJob:
        """Execute the runtime program.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment.

        Returns:
            A job representing the execution.

        Raises:
            ValueError: If input is invalid.
            NotImplementedError: If using V2 primitives.
        """
        if isinstance(options, Dict):
            qrt_options = copy.deepcopy(options)
        else:
            qrt_options = asdict(options)

        backend = qrt_options.pop("backend", None)

        if program_id not in ["sampler", "estimator"]:
            raise ValueError("Only sampler and estimator are supported in local testing mode.")
        if isinstance(backend, IBMBackend):
            raise ValueError(
                "Local testing mode is not supported when a cloud-based backend is used."
            )
        if isinstance(backend, str):
            raise ValueError(
                "Passing a backend name is not supported in local testing mode. "
                "Please pass a backend instance."
            )
        if "resilience_level" in inputs:
            warnings.warn("The resilience_level option has no effect in local testing mode.")

        inputs = copy.deepcopy(inputs)

        primitive_inputs = {"pubs": inputs.pop("pubs")}
        return self._run_backend_primitive_v2(
            backend=backend,
            primitive=program_id,
            options=inputs.get("options", {}),
            inputs=primitive_inputs,
        )

    def _run_backend_primitive_v2(
        self,
        backend: BackendV2,
        primitive: Literal["sampler", "estimator"],
        options: dict,
        inputs: dict,
    ) -> PrimitiveJob:
        """Run V2 backend primitive.

        Args:
            backend: The backend to run the primitive on.
            primitive: Name of the primitive.
            options: Primitive options to use.
            inputs: Primitive inputs.

        Returns:
            The job object of the result of the primitive.
        """
        options_copy = copy.deepcopy(options)

        prim_options = {}
        sim_options = options_copy.get("simulator", {})
        if seed_simulator := sim_options.pop("seed_simulator", None):
            prim_options["seed_simulator"] = seed_simulator
        if primitive == "sampler":
            # Create a dummy primitive to check which options it supports
            dummy_prim = BackendSamplerV2(backend=backend)
            use_run_options = hasattr(dummy_prim.options, "run_options")

            run_options = {}
            if use_run_options and "run_options" in options_copy:
                run_options = options_copy.pop("run_options")
            if use_run_options and "noise_model" in sim_options:
                run_options["noise_model"] = sim_options.pop("noise_model")

            if default_shots := options_copy.pop("default_shots", None):
                prim_options["default_shots"] = default_shots
            if use_run_options and (
                meas_type := options_copy.get("execution", {}).pop("meas_type", None)
            ):
                if meas_type == "classified":
                    run_options["meas_level"] = 2
                elif meas_type == "kerneled":
                    run_options["meas_level"] = 1
                    run_options["meas_return"] = "single"
                elif meas_type == "avg_kerneled":
                    run_options["meas_level"] = 1
                    run_options["meas_return"] = "avg"
                else:
                    # Put unexepcted meas_type back so it is in the warning below
                    options_copy["execution"]["meas_type"] = meas_type

                if not options_copy["execution"]:
                    del options_copy["execution"]

            if run_options:
                prim_options["run_options"] = run_options

            primitive_inst = BackendSamplerV2(backend=backend, options=prim_options)
        else:
            if default_shots := options_copy.pop("default_shots", None):
                inputs["precision"] = 1 / math.sqrt(default_shots)
            if default_precision := options_copy.pop("default_precision", None):
                prim_options["default_precision"] = default_precision
            primitive_inst = BackendEstimatorV2(backend=backend, options=prim_options)

        if not sim_options:
            # Pop to avoid warning below if all contents were popped above
            options_copy.pop("simulator", None)
        if options_copy:
            warnings.warn(f"Options {options_copy} have no effect in local testing mode.")

        primitive_job = primitive_inst.run(**inputs)

        local_runtime_job = LocalRuntimeJob(
            function=primitive_job._function,
            future=primitive_job._future,
            backend=backend,
            primitive=primitive,
            inputs=inputs,
        )

        return local_runtime_job
