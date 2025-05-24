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

"""Sampler primitive."""

from __future__ import annotations

from typing import Dict, Optional, Union, Iterable
import logging


from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub, SamplerPubLike
from qiskit.providers import BackendV2


from .runtime_job_v2 import RuntimeJobV2
from .base_primitive import BasePrimitiveV2

# pylint: disable=unused-import,cyclic-import
from .session import Session
from .batch import Batch
from .utils import validate_classical_registers
from .options import SamplerOptions

logger = logging.getLogger(__name__)


class Sampler:
    """Base type for Sampler."""

    version = 0


class SamplerV2(BasePrimitiveV2[SamplerOptions], Sampler, BaseSamplerV2):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    This class supports version 2 of the Sampler interface, which uses different
    input and output formats than version 1.

    Qiskit Runtime Sampler primitive returns the sampled result according to the
    specified output type. For example, it returns a bitstring for each shot
    if measurement level 2 (bits) is requested.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.
    """

    _options_class = SamplerOptions

    version = 2

    def __init__(
        self,
        mode: Optional[Union[BackendV2, Session, Batch]] = None,
        options: Optional[Union[Dict, SamplerOptions]] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
            mode: The execution mode used to make the primitive query. It can be:

                * A :class:`Backend` if you are using job mode.
                * A :class:`Session` if you are using session execution mode.
                * A :class:`Batch` if you are using batch execution mode.

                Refer to the
                `Qiskit Runtime documentation
                <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_.
                for more information about the ``Execution modes``.

            options: Sampler options, see :class:`SamplerOptions` for detailed description.

        """
        self.options: SamplerOptions
        BaseSamplerV2.__init__(self)
        Sampler.__init__(self)

        BasePrimitiveV2.__init__(self, mode=mode, options=options)

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the primitive's default
                   shots value will be used, which can vary by implementation.

        Returns:
            Submitted job.
            The result of the job is an instance of
            :class:`qiskit.primitives.containers.PrimitiveResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        validate_classical_registers(coerced_pubs)

        return self._run(coerced_pubs)  # type: ignore[arg-type]

    def _validate_options(self, options: dict) -> None:
        """Validate that primitive inputs (options) are valid

        Raises:
            ValidationError: if validation fails.
        """

        pass

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "sampler"
