# This code is part of Qiskit.
#
# (C) Copyright IBM 2022, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
=======================================================
Fake Provider (:mod:`qiskit_ibm_runtime.fake_provider`)
=======================================================

.. currentmodule:: qiskit_ibm_runtime.fake_provider

Overview
========

The fake provider module contains fake providers and fake backends classes. The fake backends are
built to mimic the behaviors of IBM Quantum systems using system snapshots. The system snapshots
contain important information about the quantum system such as coupling map, basis gates, qubit
properties (T1, T2, error rate, etc.) which are useful for testing the transpiler and performing
noisy simulations of the system.

Example Usage
=============

Here is an example of using a fake backend for transpilation and simulation.

.. plot::
   :alt: Circuit diagram output by the previous code.
   :include-source:
   :context: close-figs

   from qiskit import QuantumCircuit
   from qiskit import transpile
   from qiskit.visualization import plot_histogram
   from qiskit_ibm_runtime import SamplerV2
   from qiskit_ibm_runtime.fake_provider import FakeManilaV2

   # Get a fake backend from the fake provider
   backend = FakeManilaV2()

   # Create a simple circuit
   circuit = QuantumCircuit(3)
   circuit.h(0)
   circuit.cx(0,1)
   circuit.cx(0,2)
   circuit.measure_all()
   circuit.draw('mpl', style="iqp")

.. plot::
   :alt: Circuit diagram output by the previous code.
   :include-source:
   :context: close-figs

   # Transpile the ideal circuit to a circuit that can be
   # directly executed by the backend
   transpiled_circuit = transpile(circuit, backend)
   transpiled_circuit.draw('mpl', style="iqp")

.. plot::
   :alt: Histogram output by the previous code.
   :include-source:
   :context: close-figs

   # Run the transpiled circuit using the simulated fake backend
   sampler = SamplerV2(backend)
   job = sampler.run([transpiled_circuit])
   pub_result = job.result()[0]
   counts = pub_result.data.meas.get_counts()
   plot_histogram(counts)

.. important::

    Please note that the simulation is done using a noise model generated from system snapshots
    obtained in the past (sometimes a few years ago) and the results are not representative of the
    latest behaviors of the real quantum system that the fake backend is mimicking. If you want
    to run noisy simulations with the latest backend snapshots, you can use the ``refresh()`` method.

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService
        from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

        # initialize service to access real backends
        service = QiskitRuntimeService()

        # call refresh to retrieve latest backend data
        # note that this overwrites your local qiskit-ibm-runtime files
        backend = FakeSherbrooke()
        backend.refresh(service)


Fake Providers
==============

Fake providers provide access to a list of fake backends.

.. autosummary::
    :toctree: ../stubs/
    :nosignatures:

    FakeProviderForBackendV2

Fake Backends
=============

Fake V2 Backends
----------------

Fake V2 backends are fake backends with IBM Quantum systems snapshots implemented with
:mod:`~qiskit.providers.backend.BackendV2` interface.  They are all subclasses of
:class:`FakeBackendV2`.

.. autosummary::
    :toctree: ../stubs/
    :nosignatures:

    FakeAlgiers
    FakeAlmadenV2
    FakeArmonkV2
    FakeAthensV2
    FakeAuckland
    FakeBelemV2
    FakeBoeblingenV2
    FakeBogotaV2
    FakeBrisbane
    FakeBrooklynV2
    FakeBurlingtonV2
    FakeCairoV2
    FakeCambridgeV2
    FakeCasablancaV2
    FakeCusco
    FakeEssexV2
    FakeFez
    FakeGeneva
    FakeGuadalupeV2
    FakeHanoiV2
    FakeJakartaV2
    FakeJohannesburgV2
    FakeKawasaki
    FakeKolkataV2
    FakeKyiv
    FakeKyoto
    FakeLagosV2
    FakeLimaV2
    FakeFractionalBackend
    FakeLondonV2
    FakeManhattanV2
    FakeManilaV2
    FakeMarrakesh
    FakeMelbourneV2
    FakeMontrealV2
    FakeMumbaiV2
    FakeNairobiV2
    FakeOsaka
    FakeOslo
    FakeOurenseV2
    FakeParisV2
    FakePeekskill
    FakePerth
    FakePrague
    FakePoughkeepsieV2
    FakeQuebec
    FakeQuitoV2
    FakeRochesterV2
    FakeRomeV2
    .. FakeRueschlikonV2 # no v2 version
    FakeSantiagoV2
    FakeSherbrooke
    FakeSingaporeV2
    FakeSydneyV2
    .. FakeTenerifeV2 # no v2 version
    .. FakeTokyoV2 # no v2 version
    FakeTorino
    FakeTorontoV2
    FakeValenciaV2
    FakeVigoV2
    FakeWashingtonV2
    FakeYorktownV2
"""

# Fake providers
from .fake_provider import FakeProviderForBackendV2

# Standard fake backends with IBM Quantum systems snapshots
from .backends import *
