# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Custom TestCases for IBM Provider."""

from __future__ import annotations

import inspect
import logging
import os
import warnings
from collections import defaultdict
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING
from unittest import TestCase  # noqa: TID251 -- IBMTestCase legitimatelly inherits from it.

import numpy as np
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2

from .decorators import integration_test_setup
from .utils import bell

if TYPE_CHECKING:
    from collections.abc import Iterator

    from plotly.graph_objects import Figure as PlotlyFigure

    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem

    from .decorators import IntegrationTestDependencies
    from .unit.executor_estimator.utils import SamplexCircuitScenario, TemplateCircuitScenario


class IBMTestCase(TestCase):
    """Custom TestCase for use with qiskit-ibm-runtime."""

    def assertDictPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that all keys in ``b`` are in ``a`` and have the same values."""

        def _dict_partially_equal(dict1: dict, dict2: dict) -> bool:
            """Determine whether all keys in dict2 are in dict1 and have same values."""
            for key, val in dict2.items():
                if isinstance(val, dict):
                    if not _dict_partially_equal(dict1.get(key, {}), val):
                        return False
                elif key not in dict1 or val != dict1[key]:
                    return False

            return True

        if not _dict_partially_equal(a, b):
            raise AssertionError(f"Dicts are not partially equal: {a}, {b}")

    def assertDictFlatPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that (when flattened) all keys in ``b`` are in ``a`` and have the same values."""

        def _flat_dict(in_dict, out_dict):
            """Flat the dictionaries, and compare.

            Flat the dictionaries, then determine whether all keys in dict2 are in dict1 and have
            the same values.
            """
            for key_, val_ in in_dict.items():
                if isinstance(val_, dict):
                    _flat_dict(val_, out_dict)
                else:
                    out_dict[key_] = val_

        flat_dict1: dict = {}
        flat_dict2: dict = {}
        _flat_dict(a, flat_dict1)
        _flat_dict(b, flat_dict2)

        for key, val in flat_dict2.items():
            if key not in flat_dict1 or flat_dict1[key] != val:
                raise AssertionError(f"Dicts are not partially equal when flattened: {a}, {b}")

    def assertDictKeysEqual(self, a: dict, b: dict, exclude_keys: list | None = None) -> None:
        """Assert recursively that ``a`` and ``b`` have the same keys, optionally excluding keys."""

        def _dict_keys_equal(dict1: dict, dict2: dict, exclude_keys: list | None = None) -> bool:
            """Recursively determine whether the dictionaries have the same keys.

            Args:
                dict1: First dictionary.
                dict2: Second dictionary.
                exclude_keys: A list of keys in dictionary 1 to be excluded.

            Returns:
                Whether the two dictionaries have the same keys.
            """
            exclude_keys = exclude_keys or []
            for key, val in dict1.items():
                if key in exclude_keys:
                    continue
                if key not in dict2:
                    return False
                if isinstance(val, dict):
                    if not _dict_keys_equal(val, dict2[key]):
                        return False

            return True

        if not _dict_keys_equal(a, b, exclude_keys):
            raise AssertionError(f"Dicts don't have the same keys: {a}, {b}")

    @contextmanager
    def assertWarnsStrict(
        self,
        warning: type[Warning],
        msg: str,
        num_appearances: int,
        attributed_to_caller: bool = True,
    ) -> Iterator[None]:
        """Assert that a warning matching the category and message appears a set number of times.

        Args:
            warning: The warning category to match.
            msg: A substring that must appear in the warning message.
            num_appearances: The exact number of matching warnings expected.
            attributed_to_caller: When ``True`` (default), also assert that each matching
                warning is blamed on this method's caller -- the frame that opened the
                ``with`` block. This verifies the emitting call sets ``stacklevel`` so the warning
                points at the user's own code, which is what makes it visible in scripts and
                Jupyter notebooks. Assumes the warning-emitting call is made directly inside the
                ``with`` block; set to ``False`` when the call is wrapped in a helper defined in
                another file.
        """
        # The caller is the frame that opened the ``with`` block: this generator frame (0),
        # contextlib's ``_GeneratorContextManager`` wrapper (1), then the caller (2).
        caller = inspect.stack()[2]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", warning)
            yield

        matching_warnings = [
            w for w in caught if issubclass(w.category, warning) and msg in str(w.message)
        ]
        all_warnings = [
            f"{w.category.__name__}: {w.message}" for w in caught if issubclass(w.category, Warning)
        ]
        self.assertEqual(
            len(matching_warnings),
            num_appearances,
            f"Expected {num_appearances} {warning.__name__} warnings containing "
            f"{msg!r}, found {len(matching_warnings)}. All warnings: {all_warnings}",
        )

        if attributed_to_caller:
            caller_file = os.path.abspath(caller.filename)
            for w in matching_warnings:
                self.assertEqual(
                    os.path.abspath(w.filename),
                    caller_file,
                    f"Warning {msg!r} was blamed on {w.filename}:{w.lineno}, not the caller's "
                    f"frame ({caller.filename}:{caller.lineno}). Its stacklevel must point at "
                    f"the user's code -- past any qiskit_ibm_runtime or pydantic internals -- "
                    f"so the warning is visible in scripts and Jupyter notebooks.",
                )


class IBMEstimatorPrepareTestCase(IBMTestCase):
    """TestCase with assertions for estimator prepare-function tests."""

    def assertSamplexArgumentsAreCorrect(
        self,
        item: SamplexItem,
        scenario: SamplexCircuitScenario,
        inject_noise: bool,
    ) -> None:
        """Assert that a :class:`~.SamplexItem`'s samplex arguments have the expected structure.

        Checks:

        * ``parameter_values`` is present iff ``scenario.has_parameter_values``.
        * Exactly ``scenario.num_basis_changes`` keys start with ``basis_changes.``.
        * Exactly ``scenario.num_basis_changes - 1`` ``basis_changes.*`` keys are
          all-zero arrays (mid-circuit measurement boxes), and exactly one is
          non-zero (the final measurement box).
        * When ``inject_noise`` is ``True`` (PEA, PEC): exactly
          ``scenario.num_noise_maps`` ``noise_scales.*`` keys and the same number
          of ``pauli_lindblad_maps.*`` keys exist.
        * When ``inject_noise`` is ``False`` (vanilla, ZNE): no ``noise_scales.*``
          or ``pauli_lindblad_maps.*`` keys exist.

        Args:
            item: The :class:`~.SamplexItem` to inspect.
            scenario: The :class:`SamplexCircuitScenario` whose PUB was used to
                produce ``item``.
            inject_noise: ``True`` for methods that inject noise (PEA, PEC);
                ``False`` for methods that do not (vanilla, ZNE).
        """
        keys = list(item.samplex_arguments)
        basis_keys = [k for k in keys if k.startswith("basis_changes.")]
        noise_keys = [k for k in keys if k.startswith("noise_scales.")]
        plm_keys = [k for k in keys if k.startswith("pauli_lindblad_maps.")]

        self.assertEqual(
            "parameter_values" in keys,
            scenario.has_parameter_values,
            msg=f"[{scenario.label}] parameter_values presence mismatch; keys={keys}",
        )
        if scenario.has_parameter_values:
            expected_pv = scenario.pub.parameter_values.as_array(scenario.pub.circuit.parameters)
            actual_pv = np.squeeze(np.asarray(item.samplex_arguments["parameter_values"]))
            self.assertTrue(
                np.array_equal(actual_pv, np.squeeze(expected_pv)),
                msg=(
                    f"[{scenario.label}] parameter_values mismatch; "
                    f"got {actual_pv!r}, expected {np.squeeze(expected_pv)!r}"
                ),
            )
        self.assertEqual(
            len(basis_keys),
            scenario.num_basis_changes,
            msg=(
                f"[{scenario.label}] expected {scenario.num_basis_changes} "
                f"basis_changes key(s), got {len(basis_keys)}; keys={keys}"
            ),
        )
        zero_bc_keys = [k for k in basis_keys if np.all(np.asarray(item.samplex_arguments[k]) == 0)]
        nonzero_bc_keys = [
            k for k in basis_keys if not np.all(np.asarray(item.samplex_arguments[k]) == 0)
        ]
        self.assertEqual(
            len(zero_bc_keys),
            scenario.num_basis_changes - 1,
            msg=(
                f"[{scenario.label}] expected {scenario.num_basis_changes - 1} all-zero "
                f"basis_changes key(s) (mid-circuit boxes), got {len(zero_bc_keys)}; "
                f"keys={basis_keys}"
            ),
        )
        self.assertEqual(
            len(nonzero_bc_keys),
            1,
            msg=(
                f"[{scenario.label}] expected exactly 1 non-zero basis_changes key "
                f"(final measurement box), got {len(nonzero_bc_keys)}; keys={basis_keys}"
            ),
        )
        if inject_noise:
            self.assertEqual(
                len(noise_keys),
                scenario.num_noise_maps,
                msg=(
                    f"[{scenario.label}] expected {scenario.num_noise_maps} noise_scales "
                    f"key(s), got {len(noise_keys)}; keys={keys}"
                ),
            )
            self.assertEqual(
                len(plm_keys),
                scenario.num_noise_maps,
                msg=(
                    f"[{scenario.label}] expected {scenario.num_noise_maps} "
                    f"pauli_lindblad_maps key(s), got {len(plm_keys)}; keys={keys}"
                ),
            )
        else:
            self.assertEqual(
                noise_keys,
                [],
                msg=f"[{scenario.label}] noise_scales must be absent; keys={keys}",
            )
            self.assertEqual(
                plm_keys,
                [],
                msg=f"[{scenario.label}] pauli_lindblad_maps must be absent; keys={keys}",
            )

    def assertTemplateCircuitIsCorrect(
        self,
        item: SamplexItem,
        scenario: TemplateCircuitScenario,
        enable_gates: bool,
        noise_factor: int = 1,
    ) -> None:
        """Assert that the template circuit inside a :class:`~.SamplexItem` has the expected shape.

        Checks:

        * ``item.circuit.num_clbits`` matches ``scenario.expected_num_clbits``.
        * ``item.circuit.num_parameters`` is consistent with the twirling options and
          ``noise_factor``.  When ``enable_gates=True``, gate-folding scales the gate-twirling
          parameters while the measurement-box parameters stay fixed.  ``noise_factor=1``
          is the unfolded baseline, so each additional unit adds
          ``scenario.num_parameters_per_noise_factor`` parameters::

              expected = num_circuit_parameters_gates_on
                         + num_parameters_per_noise_factor * (noise_factor - 1)

          When ``enable_gates=False`` the noise factor does not apply and the expected
          count is ``scenario.num_circuit_parameters_gates_off``.

        Args:
            item: The :class:`~.SamplexItem` to inspect.
            scenario: The :class:`TemplateCircuitScenario` whose PUB was used to
                produce ``item``.
            enable_gates: Whether gate twirling was enabled for this prepare call.
            noise_factor: The ZNE gate-folding noise factor (default ``1``, i.e. no
                folding).  Only meaningful when ``enable_gates=True``.
        """
        circuit = item.circuit
        if enable_gates:
            expected_num_params = (
                scenario.num_circuit_parameters_gates_on
                + scenario.num_parameters_per_noise_factor * (noise_factor - 1)
            )
        else:
            expected_num_params = scenario.num_circuit_parameters_gates_off

        self.assertEqual(
            circuit.num_clbits,
            scenario.expected_num_clbits,
            msg=(
                f"[{scenario.label}] template num_clbits mismatch; "
                f"got {circuit.num_clbits}, expected {scenario.expected_num_clbits}"
            ),
        )
        self.assertEqual(
            circuit.num_parameters,
            expected_num_params,
            msg=(
                f"[{scenario.label}] template num_parameters mismatch "
                f"(enable_gates={enable_gates}, noise_factor={noise_factor}); "
                f"got {circuit.num_parameters}, expected {expected_num_params}"
            ),
        )


class IBMVisualizationTestCase(IBMTestCase):
    """Test case for use with visualization-related features."""

    ARTIFACT_DIR = ".test_artifacts"

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        super().setUpClass()

        # Ensure the artifact directory exists
        os.makedirs(cls.ARTIFACT_DIR, exist_ok=True)

    def save_plotly_artifact(self, fig: PlotlyFigure, name: str | None = None) -> str:
        """Save a Plotly figure as an HTML artifact."""
        # nested folder path based on the test module, class, and method
        test_path = self.id().split(".")[1:]
        nested_dir = os.path.join(self.ARTIFACT_DIR, *test_path[:-1])
        name = test_path[-1]
        os.makedirs(nested_dir, exist_ok=True)

        # save figure
        artifact_path = os.path.join(nested_dir, f"{name}.html")
        fig.write_html(artifact_path)
        return artifact_path


class IBMIntegrationTestCase(IBMTestCase):
    """Custom integration test case for use with qiskit-ibm-runtime."""

    dependencies: IntegrationTestDependencies
    service: QiskitRuntimeService

    @classmethod
    @integration_test_setup()
    def setUpClass(cls, dependencies: IntegrationTestDependencies) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.dependencies = dependencies
        cls.service = dependencies.service

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.to_delete: defaultdict = defaultdict(list)
        self.to_cancel: defaultdict = defaultdict(list)

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()
        service = self.service

        # Cancel and delete jobs.
        for job in self.to_cancel[service.channel]:
            with suppress(Exception):
                job.cancel()


class IBMIntegrationJobTestCase(IBMIntegrationTestCase):
    """Custom integration test case for job-related tests."""

    log: logging.Logger
    program_ids: dict[str, str]

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        super().setUpClass()
        cls.log = logging.getLogger(cls.__name__)
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        cls.program_ids[service.channel] = "sampler"
        cls._find_sim_backends()

    @classmethod
    def _find_sim_backends(cls):
        """Find a simulator or test backend for each service."""
        backends = cls.service.backends()
        # Simulators or tests backends can be not available
        cls.sim_backends[cls.service.channel] = None
        for backend in backends:
            if backend.name.startswith("test_eagle"):
                cls.sim_backends[cls.service.channel] = backend.name
                break

    def _run_program(
        self,
        service,
        program_id=None,
        inputs=None,
        circuits=None,
        callback=None,
        backend=None,
        log_level=None,
        job_tags=None,
        max_execution_time=None,
        session_id=None,
        start_session=False,
    ):
        """Run a program."""
        self.log.debug("Running program on %s", service.channel)
        pid = program_id or self.program_ids[service.channel]
        backend_name = backend if backend is not None else self.sim_backends[service.channel]
        backend = service.backend(backend_name)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        inputs = (
            inputs
            if inputs is not None
            else {
                "circuits": pm.run(circuits) if circuits else pm.run(bell()),
            }
        )

        options = {
            "backend": backend_name,
            "log_level": log_level,
            "job_tags": job_tags,
            "max_execution_time": max_execution_time,
        }
        if pid == "sampler":
            sampler = SamplerV2(mode=backend)
            if job_tags:
                sampler.options.environment.job_tags = job_tags
            if circuits:
                job = sampler.run([pm.run(circuits) if circuits else pm.run(bell())])
            else:
                job = sampler.run([pm.run(bell())])
        else:
            job = service._run(
                program_id=pid,
                inputs=inputs,
                options=options,
                session_id=session_id,
                callback=callback,
                start_session=start_session,
            )
        self.log.info("Runtime job %s submitted.", job.job_id())
        self.to_cancel[service.channel].append(job)
        return job
