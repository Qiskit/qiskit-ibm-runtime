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
# type: ignore

r"""

.. estimator-desc:

========================
Overview of EstimatorV2
========================
:class:`~BaseEstimatorV2` is a primitive that estimates expectation values for provided quantum
circuit and observable combinations.

Following construction, an estimator is used by calling its :meth:`~.BaseEstimatorV2.run` method
with a list of pubs (Primitive Unified Blocs). Each pub contains three values that, together,
define a computation unit of work for the estimator to complete:

* a single :class:`~qiskit.circuit.QuantumCircuit`, possibly parametrized, whose final state we
  define as :math:`\psi(\theta)`,
* one or more observables (specified as any :class:`~.ObservablesArrayLike`, including
  :class:`~.Pauli`, :class:`~.SparsePauliOp`, ``str``) that specify which expectation values to
  estimate, denoted :math:`H_j`, and
* a collection parameter value sets to bind the circuit against, :math:`\theta_k`.
Running an estimator returns a :class:`~qiskit.providers.JobV1` object, where calling
the method :meth:`qiskit.providers.JobV1.result` results in expectation value estimates and metadata
for each pub:

.. math::
    \langle\psi(\theta_k)|H_j|\psi(\theta_k)\rangle
The observables and parameter values portion of a pub can be array-valued with arbitrary dimensions,
where standard broadcasting rules are applied, so that, in turn, the estimated result for each pub
is in general array-valued as well. For more information, please check
`here <https://github.com/Qiskit/RFCs/blob/master/0015-estimator-interface.md#arrays-and
-broadcasting->`_.

Here is an example of how the estimator is used.

.. code-block:: python

    from qiskit.primitives.statevector_estimator import Estimator
    from qiskit.circuit.library import RealAmplitudes
    from qiskit.quantum_info import SparsePauliOp
    psi1 = RealAmplitudes(num_qubits=2, reps=2)
    psi2 = RealAmplitudes(num_qubits=2, reps=3)
    H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
    H2 = SparsePauliOp.from_list([("IZ", 1)])
    H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

    theta1 = [0, 1, 1, 2, 3, 5]
    theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
    theta3 = [1, 2, 3, 4, 5, 6]
    estimator = Estimator()

    # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
    job = estimator.run([(psi1, hamiltonian1, [theta1])])
    job_result = job.result() # It will block until the job finishes.

    print(f"The primitive-job finished with result {job_result}"))
    # calculate [ [<psi1(theta1)|H1|psi1(theta1)>,
    #              <psi1(theta3)|H3|psi1(theta3)>],
    #             [<psi2(theta2)|H2|psi2(theta2)>] ]
    job2 = estimator.run(
        [(psi1, [hamiltonian1, hamiltonian3], [theta1, theta3]), (psi2, hamiltonian2, theta2)]
    )
    job_result = job2.result()
    print(f"The primitive-job finished with result {job_result}")
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TypeVar, Iterable

from qiskit.providers import JobV1 as Job

import numpy as np
from numpy.typing import NDArray

from .estimator_pub import EstimatorPub, EstimatorPubLike

T = TypeVar("T", bound=Job)  # pylint: disable=invalid-name


class BaseEstimatorV2:
    """Estimator base class version 2.
    An estimator estimates expectation values for provided quantum circuit and
    observable combinations.
    An Estimator implementation must treat the :meth:`.run` method ``precision=None``
    kwarg as using a default ``precision`` value.  The default value and methods to
    set it can be determined by the Estimator implementor.
    """

    @staticmethod
    def _make_data_bin(pub: EstimatorPub) -> DataBin:
        # provide a standard way to construct estimator databins to ensure that names match
        # across implementations
        return make_data_bin(
            (("evs", NDArray[np.float64]), ("stds", NDArray[np.float64])), pub.shape
        )

    @abstractmethod
    def run(
        self, pubs: Iterable[EstimatorPubLike], precision: float | None = None
    ) -> BasePrimitiveJob[PrimitiveResult[PubResult]]:
        """Estimate expectation values for each provided pub (Primitive Unified Bloc).
        Args:
            pubs: An iterable of pub-like objects, such as tuples ``(circuit, observables)`` or
                  ``(circuit, observables, parameter_values)``.
            precision: The target precision for expectation value estimates of each
                       run :class:`.EstimatorPub` that does not specify its own
                       precision. If None the estimator's default precision value
                       will be used.
        Returns:
            A job object that contains results.
        """
        pass
