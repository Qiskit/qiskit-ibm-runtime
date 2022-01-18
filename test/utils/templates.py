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

"""Templates for use with unit tests."""

RUNTIME_PROGRAM = """
import random
import time
import warnings
import logging

from qiskit import transpile
from qiskit.circuit.random import random_circuit

logger = logging.getLogger("qiskit-test")

def prepare_circuits(backend):
    circuit = random_circuit(num_qubits=5, depth=4, measure=True,
                             seed=random.randint(0, 1000))
    return transpile(circuit, backend)

def main(backend, user_messenger, **kwargs):
    iterations = kwargs['iterations']
    sleep_per_iteration = kwargs.pop('sleep_per_iteration', 0)
    interim_results = kwargs.pop('interim_results', {})
    final_result = kwargs.pop("final_result", {})
    for it in range(iterations):
        time.sleep(sleep_per_iteration)
        qc = prepare_circuits(backend)
        user_messenger.publish({"iteration": it, "interim_results": interim_results})
        backend.run(qc).result()

    user_messenger.publish(final_result, final=True)
    print("this is a stdout message")
    warnings.warn("this is a stderr message")
    logger.info("this is an info log")
    """

RUNTIME_PROGRAM_METADATA = {
    "max_execution_time": 600,
    "description": "Qiskit test program",
}
PROGRAM_PREFIX = "qiskit-test"
