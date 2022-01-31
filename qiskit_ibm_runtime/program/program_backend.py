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

"""Base class for program backend."""

import logging
from typing import Union, List, Dict
from abc import abstractmethod, ABC

from qiskit.pulse import Schedule
from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.job import JobV1 as Job
from qiskit.circuit import QuantumCircuit

logger = logging.getLogger(__name__)


class ProgramBackend(Backend, ABC):
    """Base class for a program backend.

    The ``main()`` function of your runtime program will receive an instance
    of this class as the first parameter. You can then use the instance
    to submit circuits to the target backend.
    """

    @abstractmethod
    def run(
        self,
        circuits: Union[
            QuantumCircuit, Schedule, List[Union[QuantumCircuit, Schedule]]
        ],
        **run_config: Dict
    ) -> Job:
        """Run on the backend.

        Runtime circuit execution is synchronous, and control will not go
        back until the execution finishes. You can use the `timeout` parameter
        to set a timeout value to wait for the execution to finish. Note that if
        the execution times out, circuit execution results will not be available.

        Args:
            circuits: An individual or a
                list of :class:`~qiskit.circuits.QuantumCircuit` or
                :class:`~qiskit.pulse.Schedule` objects to run on the backend.
            **run_config: Extra arguments used to configure the run.

        Returns:
            The job to be executed.
        """
        # pylint: disable=arguments-differ
        pass
