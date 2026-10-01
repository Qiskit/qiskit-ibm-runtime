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

import logging
import os
from collections import defaultdict
from contextlib import suppress
from typing import TYPE_CHECKING
from unittest import TestCase  # noqa: TID251 -- IBMTestCase legitimatelly inherits from it.

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2

from .asserts import (
    assert_dict_flat_partially_equal,
    assert_dict_keys_equal,
    assert_dict_partially_equal,
    assert_warns_strict,
)
from .decorators import integration_test_setup
from .utils import bell

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from plotly.graph_objects import Figure as PlotlyFigure

    from qiskit_ibm_runtime import QiskitRuntimeService

    from .decorators import IntegrationTestDependencies


def save_plotly_artifact(test_id: str, fig: PlotlyFigure, artifact_dir: str) -> str:
    """Save a Plotly figure as an HTML artifact, nested under `artifact_dir` by `test_id`.

    Args:
        test_id: the dotted id of the test (`package.module.Class.method`).
        fig: the figure to save.
        artifact_dir: the root directory for the artifacts.

    Returns:
        The path of the saved artifact.
    """
    # nested folder path based on the test module, class, and method
    test_path = test_id.split(".")[1:]
    nested_dir = os.path.join(artifact_dir, *test_path[:-1])
    name = test_path[-1]
    os.makedirs(nested_dir, exist_ok=True)

    # save figure
    artifact_path = os.path.join(nested_dir, f"{name}.html")
    fig.write_html(artifact_path)
    return artifact_path


class IBMTestCase(TestCase):
    """Custom TestCase for use with qiskit-ibm-runtime."""

    def assertDictPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that all keys in ``b`` are in ``a`` and have the same values."""
        assert_dict_partially_equal(a, b)

    def assertDictFlatPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that (when flattened) all keys in ``b`` are in ``a`` and have the same values."""
        assert_dict_flat_partially_equal(a, b)

    def assertDictKeysEqual(self, a: dict, b: dict, exclude_keys: list | None = None) -> None:
        """Assert recursively that ``a`` and ``b`` have the same keys, optionally excluding keys."""
        assert_dict_keys_equal(a, b, exclude_keys)

    def assertWarnsStrict(
        self,
        warning: type[Warning],
        msg: str,
        num_appearances: int,
        attributed_to_caller: bool = True,
    ) -> AbstractContextManager[None]:
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
        return assert_warns_strict(warning, msg, num_appearances, attributed_to_caller)


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
        return save_plotly_artifact(self.id(), fig, self.ARTIFACT_DIR)


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
    sim_backends: dict[str, str | None]

    @classmethod
    def setUpClass(cls) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.log = logging.getLogger(cls.__name__)
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        cls.program_ids[service.channel] = "sampler"
        cls._find_sim_backends()

    @classmethod
    def _find_sim_backends(cls) -> None:
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
