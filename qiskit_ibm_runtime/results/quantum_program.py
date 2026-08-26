# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""QuantumProgramResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    import numpy as np

    from ..quantum_program.datatree import DataTree

from samplomatic.quantum_program import ChunkPart, ChunkSpan, ChunkTiming  # noqa: F401,TC002
from samplomatic.quantum_program import QuantumProgramItemResult as BaseQuantumProgramItemResult
from samplomatic.quantum_program import QuantumProgramResult as BaseQuantumProgramResult


@dataclass
class SchedulerTiming:
    """The timing of a scheduled circuit.

    All timing information is expressed in terms of multiples of the quantity ``dt``, time step
    duration of the control electronics, which can be queried in backend and target properties.
    """

    timing: str
    """A description of circuit timing in a comma-separated text format."""

    circuit_duration: int
    """The duration of the circuit in ``dt`` steps."""


@dataclass
class StretchValues:
    """Circuit stretch value resolutions.

    All timing information is expressed in terms of multiples of the quantity ``dt``, time step
    duration of the control electronics, which can be queried in backend and target properties.
    """

    name: str
    """The name of the stretch."""

    value: int
    """The resolved stretch value, up to the remainder, in units of ``dt``."""

    remainder: int
    """The time left over if ``value`` were to be used each stretch, in units of ``dt``."""

    expanded_values: list[tuple[int, int]]
    """A sequence of pairs ``(time, duration)`` indicating the time and duration of each delay.

    All units are ``dt``, where the ``time`` denotes the absolute time of a delay in the circuit
    schedule, and the ``duration`` denotes the total duration of the delay.
    """


@dataclass
class ItemMetadata:
    """Metadata about the execution of a single item of a quantum program."""

    scheduler_timing: SchedulerTiming | None = None
    """Scheduler circuit timing information, if it is available.

    When available, the timing information can be visualized using the
    :meth:`.qiskit_ibm_runtime.visualization.draw_circuit_schedule_timing` method
    as in the snippet below.

    .. code-block::python

        from qiskit_ibm_runtime.visualization import draw_circuit_schedule_timing

        # Retrieve the timings from the job item's metadata
        result = job.result()
        timings = result[0].metadata.scheduler_timing.timing

        # Create a figure from the metadata
        fig = draw_circuit_schedule_timing(
            circuit_schedule=timings,
            included_channels=None,
            filter_readout_channels=False,
            filter_barriers=False,
            width=1000,
        )

    .. note::
        This feature is experimental and subject to change without notice.
    """

    stretch_values: list[StretchValues] | None = None
    """Stretch value resolution, if it is available.

    .. note::
        This feature is experimental and subject to change without notice.
    """


@dataclass
class Metadata:
    """Metadata about the execution of a quantum program run through the runtime executor."""

    chunk_timing: list[ChunkSpan] = field(default_factory=list)
    """Timing information about all executed chunks of a quantum program."""


class QuantumProgramItemResult(BaseQuantumProgramItemResult):
    """A container to store results for a single item of a :class:`QuantumProgram`.

    Args:
        result: A dictionary with array-valued data.
        metadata: The metadata produced for the individual item.
    """

    def __init__(
        self,
        result: dict[str, np.ndarray],
        metadata: ItemMetadata | dict | None = None,
    ):
        super().__init__(result=result)
        self.metadata = metadata or ItemMetadata()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._result}, metadata={self.metadata})"


class QuantumProgramResult(BaseQuantumProgramResult):
    """A container to store results from executing a :class:`~.QuantumProgram`.

    Args:
        data: A list of dictionaries with array-valued data.
        metadata: A dictionary of metadata.
        passthrough_data: Arbitrary nested data passed through execution without modification.
    """

    def __init__(
        self,
        data: Sequence[dict[str, np.ndarray] | QuantumProgramItemResult],
        metadata: Metadata | None = None,
        passthrough_data: DataTree | None = None,
    ):
        super().__init__(
            data=[
                datum
                if isinstance(datum, QuantumProgramItemResult)
                else QuantumProgramItemResult(datum)
                for datum in data
            ],
            passthrough_data=passthrough_data,
        )
        self.metadata = metadata or Metadata()

        # Semantic role indicating how execution results may be post-processed by runtime clients.
        # Reserved system values include 'sampler-v2' and 'estimator-v2', and are subject to change
        # without notice. Third party clients should not set or depend on this value.
        self._semantic_role: str | None = None

    @property
    def timing(self) -> ChunkTiming:
        """Execution timing information of these results.

        A single executor job may be broken up into chunks of work that are executed serially.
        This property stores information about their timing. Most notably, for each chunk of
        execution, a start and stop timestamp are provided that bound the window in which the data
        was collected.

        To draw the timings for a single result:

        .. code-block:: python

            job.result().timing.draw()

        To draw the timings for several results on one plot:

        .. code-block:: python

            from samplomatic.visualization.draw_chunk_timings import draw_chunk_timings

            draw_chunk_timings(
                job1.result().timing,
                job2.result().timing,
                names=["job 1", "job 2"],
                common_start=True,
            )

        Returns:
            A :class:`~.ChunkTiming` collection.
        """
        return ChunkTiming(self.metadata.chunk_timing)

    def __getitem__(self, index: int | slice) -> QuantumProgramItemResult:
        return cast("QuantumProgramItemResult", super().__getitem__(index))

    def __iter__(self) -> Iterator[QuantumProgramItemResult]:
        return cast("Iterator[QuantumProgramItemResult]", super().__iter__())
