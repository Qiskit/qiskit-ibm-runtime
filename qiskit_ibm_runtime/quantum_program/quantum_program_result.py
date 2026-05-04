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

from collections.abc import Iterable, Iterator, MutableMapping, Sequence
from dataclasses import dataclass, field
import datetime
from datetime import timezone
from typing import overload, TYPE_CHECKING, Any
import numpy as np

from .datatree import DataTree

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


@dataclass
class ChunkPart:
    """A description of the contents of a single part of an execution chunk."""

    idx_item: int
    """The index of an item in a quantum program."""

    size: int
    """The number of elements from the quantum program item that were executed.

    For example, if a quantum program item has shape ``(10, 5)``, then it has a total of ``50``
    elements, so that if this ``size`` is ``10``, it constitutes 20% of the total work for the item.
    """


@dataclass
class ChunkSpan:
    """Timing information about a single chunk of execution.

    .. note::

        This span may include some amount of non-circuit time.
    """

    start: datetime.datetime
    """The start time of the execution chunk in UTC."""

    stop: datetime.datetime
    """The stop time of the execution chunk in UTC."""

    parts: list[ChunkPart]
    """A description of which parts of a quantum program are contained in this chunk."""


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
    """Scheduled circuit timing information, if it is available."""

    stretch_values: list[StretchValues] | None = None
    """Stretch value resolution, if it is available."""


@dataclass
class Metadata:
    """Metadata about the execution of a quantum program run through the runtime executor."""

    chunk_timing: list[ChunkSpan] = field(default_factory=list)
    """Timing information about all executed chunks of a quantum program."""


class ChunkTiming:
    """A collection of chunk timing information for a :class:`QuantumProgramResult`.

    This class is a readonly list-like containing :class:`~.ChunkSpan` objects, where each span
    represents a single execution chunk on the backend and contains timing information and a
    description of which parts of the :class:`~.QuantumProgram` were executed in that chunk.

    To iterate over chunks:

    .. code-block:: python

        result = job.result()
        for chunk in chunk_timings:
            print(chunk)

    To draw the timings for a single result:

    .. code-block:: python

        chunk_timings.draw()

    To draw the timings for several results on one plot:

    .. code-block:: python

        from qiskit_ibm_runtime.visualization import draw_chunk_timings

        draw_chunk_timings(
            chunk_timings1,
            chunk_timings2,
            names=["job 1", "job 2"],
            common_start=True,
        )
    """

    def __init__(self, spans: Iterable[ChunkSpan]):
        self._spans = list(spans)

    def __len__(self) -> int:
        return len(self._spans)

    @overload
    def __getitem__(self, idxs: int) -> ChunkSpan: ...

    @overload
    def __getitem__(self, idxs: slice) -> ChunkTiming: ...

    def __getitem__(self, idxs):  # type: ignore[no-untyped-def]
        if isinstance(idxs, int):
            return self._spans[idxs]
        return ChunkTiming(self._spans[idxs])

    def __iter__(self) -> Iterator[ChunkSpan]:
        return iter(self._spans)

    def __repr__(self) -> str:
        return f"ChunkTiming({repr(self._spans)})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ChunkTiming) and self._spans == other._spans

    @property
    def start(self) -> datetime.datetime:
        """The start time of the earliest chunk, in UTC."""
        return min(span.start for span in self)

    @property
    def stop(self) -> datetime.datetime:
        """The stop time of the latest chunk, in UTC."""
        return max(span.stop for span in self)

    @property
    def duration(self) -> float:
        """The total duration from first start to last stop, in seconds."""
        return (self.stop - self.start).total_seconds()

    def draw(
        self,
        name: str | None = None,
        normalize_y: bool = False,
        line_width: int = 4,
        tz: timezone | None = None,
    ) -> PlotlyFigure:
        """Draw timing information on a bar plot.

        To draw chunk timings with additional options like ``common_start``, or to draw
        timings of several jobs on the same axis, consider calling
        :meth:`~qiskit_ibm_runtime.visualization.draw_chunk_timings` directly.

        Args:
            name: A label for this set of chunks.
            normalize_y: Whether to display the y-axis units as a percentage of work complete,
                rather than cumulative elements completed.
            line_width: The thickness of line segments.
            tz: The timezone to use for displaying times. ``None`` (default) uses the local system
                timezone. Pass ``datetime.timezone.utc`` to display times in UTC.

        Returns:
            A plotly figure.
        """
        from ..visualization import draw_chunk_timings

        return draw_chunk_timings(
            self, names=name, normalize_y=normalize_y, line_width=line_width, tz=tz
        )


class QuantumProgramItemResult(MutableMapping):
    """A container to store results for a single item of a :class:`QuantumProgram`.

    Args:
        result: A dictionary with array-valued data.
        metadata: The metadata produced for the individual item.
    """

    def __init__(
        self,
        result: dict[str, np.ndarray],
        metadata: ItemMetadata | None = None,
    ):
        self._result = result
        self.metadata = metadata or ItemMetadata()

    def __getitem__(self, key: str) -> np.ndarray:
        return self._result[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._result[key] = value

    def __delitem__(self, key: str) -> None:
        del self._result[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._result)

    def __len__(self) -> int:
        return len(self._result)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._result}, metadata={self.metadata})"


class QuantumProgramResult:
    """A container to store results from executing a :class:`QuantumProgram`.

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
        self._data = [
            datum
            if isinstance(datum, QuantumProgramItemResult)
            else QuantumProgramItemResult(datum)
            for datum in data
        ]
        self.metadata = metadata or Metadata()
        self.passthrough_data = passthrough_data

        # Semantic role indicating how execution results may be post-processed by runtime clients.
        # Reserved system values include 'sampler-v2' and 'estimator-v2', and are subject to change
        # without notice. Third party clients should not set or depend on this value.
        self._semantic_role: str | None = None

    def __iter__(self) -> Iterator[QuantumProgramItemResult]:
        yield from self._data

    def __getitem__(self, idx: int) -> QuantumProgramItemResult:
        return self._data[idx]

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<{len(self)} results>)"

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

            from qiskit_ibm_runtime.visualization import draw_chunk_timings

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
