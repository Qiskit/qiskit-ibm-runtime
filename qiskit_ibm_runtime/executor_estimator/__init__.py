# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
================================================================================
Executor-based EstimatorV2 (:mod:`qiskit_ibm_runtime.executor_estimator`)
================================================================================

.. currentmodule:: qiskit_ibm_runtime.executor_estimator

Overview
========

:class:`qiskit_ibm_runtime.executor_estimator.EstimatorV2` is an implementation of the
Qiskit ``EstimatorV2`` interface built on
top of the :class:`~qiskit_ibm_runtime.executor.Executor` primitive. It estimates expectation
values of quantum observables by executing ISA circuits on an IBM Quantum backend.

The key difference between the legacy server-side :class:`~qiskit_ibm_runtime.EstimatorV2` and
this new implementation is that **all pre- and post-processing runs on the client machine**.
This includes circuit preparation (twirling, gate folding, dynamical decoupling,
and noise injection) as well as result post-processing (TREX rescaling, ZNE extrapolation, and PEC
quasi-probability weighting). Running these steps locally provides faster debugging feedback and
greater user control.

When a user submits a job through :meth:`~.EstimatorV2.run`, the underlying processing consists of:

1. Coercing the PUBs, resolving the resilience-level defaults, and determining the shot count.
2. Converting the PUBs into a
   :class:`~qiskit_ibm_runtime.quantum_program.QuantumProgram`, applying circuit transformations
   (twirling, gate folding, DD, noise injection) according to the specified options.
3. Calling :class:`~qiskit_ibm_runtime.executor.Executor` to submit the quantum program to the
   backend.
4. Upon job completion, estimating expectation values from the raw measurement data and applying
   error-mitigation post-processing as needed.

.. note::

    For large or complex workloads, the client-side preparation step can be resource intensive
    and may cause a delay before the job is submitted. Set the ``qiskit_ibm_runtime`` logger to
    ``INFO`` to monitor preparation progress::

        import logging
        logger = logging.getLogger("qiskit_ibm_runtime")
        logger.setLevel(logging.INFO)

Basic usage
===========

**Example 1 — Minimal (no error mitigation)**

.. code-block:: python

    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.executor_estimator import EstimatorV2

    # Select a backend.
    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    observable = SparsePauliOp("ZZ")

    # Transform the circuit and observable into ISA format.
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_qc = pm.run(qc)
    isa_obs = observable.apply_layout(isa_qc.layout)

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience_level = 0
    job = estimator.run([(isa_qc, isa_obs)])
    result = job.result()
    print(result[0].data.evs)   # expectation value

**Example 2 — Resilience level 2 (measurement error mitigation + gate-folding ZNE)**

.. code-block:: python

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience_level = 2  # TREX + ZNE (gate folding)
    job = estimator.run([(isa_qc, isa_obs)])
    result = job.result()
    print(result[0].data.evs)                 # zero-noise extrapolated expectation value
    print(result[0].data.evs_noise_factors)   # raw values at each noise amplification level

**Example 3 — PEC (requires explicit noise learning)**

Unlike the legacy server-side implementation, this client-side :class:`~.EstimatorV2` requires
explicit noise learning for the error mitigation methods that need a noise model (PEC and PEA).

Use :meth:`~.EstimatorV2.find_unique_layers` to extract the unique gate layers from your PUBs,
pass the layers to :class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3` to learn
their noise in a separate job, then assign the learned noise maps to
:attr:`~qiskit_ibm_runtime.options_models.ResilienceOptions.layer_noise_model`.

.. code-block:: python

    from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3

    pubs = [(isa_qc, isa_obs)]

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.pec_mitigation = True

    # Step 1 — extract the unique boxed gate layers from your PUBs.
    layers = estimator.find_unique_layers(pubs)

    # Step 2 — learn the noise model for those layers.
    nl_result = NoiseLearnerV3(mode=backend).run(layers).result()

    # Step 3 — convert the NoiseLearnerV3 result to Pauli-Lindblad maps and pass them
    # to the Estimator. The maps follow the same order as the input layers, so they can
    # be zipped positionally.
    pauli_lindblad_maps = nl_result.to_pauli_lindblad_maps()
    estimator.options.resilience.layer_noise_model = zip(layers, pauli_lindblad_maps)

    job = estimator.run(pubs)
    result = job.result()
    print(result[0].data.evs)

Inputs
======

Each call to :meth:`~.EstimatorV2.run` takes a list of PUBs (Primitive Unified Blocs). Each PUB
is in this format::

    (<single circuit>, <one or more observables>, <optional parameter values>, <optional precision>)

See `Estimator inputs and outputs
<https://quantum.cloud.ibm.com/docs/en/guides/estimator-input-output>`_
for more information on EstimatorV2 inputs and outputs.

Elements from observables and parameter values are combined by following NumPy broadcasting rules
as described in
`Primitive inputs and outputs <https://quantum.cloud.ibm.com/docs/guides/primitive-input-output>`_.


Options
=======

When instantiating :class:`~.EstimatorV2`, you can pass in options by using
:class:`~qiskit_ibm_runtime.options_models.EstimatorOptions` or a dictionary.
Commonly used options, such as ``resilience_level``, are at the first level. Other options are
grouped into categories, such as ``execution``. Specify the options in this format:
``options.<category>.<option> = <value>``. For example:
``options.dynamical_decoupling.enable = True``.

See `Introduction to options
<https://quantum.cloud.ibm.com/docs/en/guides/runtime-options-overview>`_
for an overview on specifying primitive options.
See `Specify Estimator options <https://quantum.cloud.ibm.com/docs/en/guides/estimator-options>`_
and `Configure noise management with Estimator
<https://quantum.cloud.ibm.com/docs/en/guides/estimator-noise-management>`_
for more information about Estimator options.

Outputs
=======

:meth:`~.EstimatorV2.run` returns a :class:`~qiskit_ibm_runtime.RuntimeJobV2`. Calling
``job.result()`` returns a :class:`~qiskit.primitives.PrimitiveResult` of
:class:`~qiskit_ibm_runtime.results.EstimatorPubResult` objects — one per input PUB::

    result = job.result()
    pub_result = result[0]        # EstimatorPubResult for the first PUB
    pub_result.data               # DataBin holding numerical arrays
    pub_result.metadata           # dictionary with per-PUB metadata
    result.metadata               # dictionary with job-level metadata

The contents of ``pub_result.data`` depend on the mitigation technique specified.

No mitigation / measurement mitigation only (resilience levels 0 and 1)
------------------------------------------------------------------------

All of the following fields have the shape ``pub_shape``, which is
``broadcast(param_shape, obs_shape)``.

* ``data.evs`` — Expectation values.
* ``data.stds`` — Standard deviations.
  Reflects the spread across twirling randomizations when twirling is enabled; equals
  ``ensemble_standard_error`` when twirling is disabled.
* ``data.ensemble_standard_error`` — Standard error under the i.i.d. shot-noise assumption
  (no drift contribution).

When measurement mitigation (TREX) is active, the ``evs`` values are corrected for readout
errors using a calibration circuit that is run automatically alongside the main circuits.

PEC
---

PEC produces the same three fields as the no-mitigation case: ``evs``, ``stds``, and
``ensemble_standard_error``. The gamma quasi-probability factor is applied internally during
post-processing and does not appear as a separate output field.

The ``stds`` values are scaled by the gamma factor, so they are typically larger than in the
no-mitigation case for the same shot count. This is the fundamental cost of PEC: unbiased
estimates come with increased variance proportional to the sampling overhead (``gamma^2``).

ZNE (gate folding) and PEA
---------------------------

When ``resilience.zne_mitigation=True``, the estimator runs the circuit at multiple noise
amplification levels and fits a curve to extrapolate to zero noise. The result contains both
the extrapolated estimate and the raw data at each noise level.

* ``data.evs`` — Zero-noise extrapolated expectation values (best heterogeneous fit — the
  extrapolator is chosen per term for multi-term observables). Shape: ``pub_shape``.
* ``data.stds`` — Standard deviations of the extrapolated values. Same shape as ``evs``.
  Derived from the spread over twirling randomizations when twirling is on.
* ``data.evs_noise_factors`` — Raw (non-extrapolated) expectation values at each noise
  amplification level. Shape: ``(*pub_shape, num_noise_factors)``.
* ``data.stds_noise_factors`` — Standard deviations at each noise factor.
  Same shape as ``evs_noise_factors``.
  Reflects the spread over twirling randomizations when twirling is on; equals
  ``ensemble_stds_noise_factors`` when twirling is off.
* ``data.ensemble_stds_noise_factors`` — Ensemble standard errors at each noise factor under
  the i.i.d. shot-noise assumption. Shape: ``(*pub_shape, num_noise_factors)``.
* ``data.evs_extrapolated`` — Expectation values from each requested extrapolator, evaluated
  at each point in ``resilience.zne.extrapolated_noise_factors``. These are forced homogeneous
  fits — the same extrapolator is applied to all terms of a multi-term observable — one fit per
  extrapolator. Shape: ``(*pub_shape, num_extrapolators, num_eval_points)``.
* ``data.stds_extrapolated`` — Standard deviations corresponding to ``evs_extrapolated``.
  Same shape.

.. note::

    For multi-term observables (for example, ``{"XX": 0.5, "XY": 0.5}``), ``evs`` and ``stds``
    use a heterogeneous fit: the best-fitting extrapolator is selected independently for each Pauli
    term. ``evs_extrapolated`` and ``stds_extrapolated`` use a homogeneous fit per extrapolator,
    which is useful for comparing models. If your analysis needs a single extrapolator applied
    consistently, split the multi-term observable into single-term observables so that each term
    is fit on its own.

ZNE results can be visualized with
:meth:`~qiskit_ibm_runtime.results.EstimatorPubResult.draw_zne_evs` and
:meth:`~qiskit_ibm_runtime.results.EstimatorPubResult.draw_zne_extrapolators` (requires
``plotly``).

Job-level metadata
------------------

``result.metadata`` is a ``dict`` containing:

* ``"options"`` — the finalized
  :class:`~qiskit_ibm_runtime.options_models.EstimatorOptions`, as a dictionary.
  Inactive resilience sub-options are pruned (for example, the ``zne`` sub-dictionary is omitted
  when ``zne_mitigation=False``).
* ``"target_precision"`` — the precision resolved from the PUBs and the ``precision`` argument of
  :meth:`~.EstimatorV2.run`, or ``None`` if neither specified one. In that case the shot count
  comes from ``default_shots``, falling back to ``default_precision``.
* ``"shots"`` — the total shot count used for execution.
* ``"executor"`` — the metadata of the underlying Executor result.

Migration guide
================

This client-side EstimatorV2 implementation is largely a drop-in replacement for the legacy one.
Follow the steps listed below to migrate to the new implementation, keeping in mind these
behavioral changes:

* **Pre- and post-processing happen on the client side.** In the legacy Estimator, all circuit
  transformations (twirling, gate folding, and noise injection), as well as result post-processing
  (ZNE extrapolation, TREX rescaling, and PEC weighting), are performed on the server side.
  In this client-side implementation, these steps run entirely on the client machine.

* **Noise learning is a separate step.** In the legacy Estimator, noise learning for PEC and PEA
  is integrated into the Estimator job itself and handled implicitly on the server side. In this
  new implementation, noise learning is a separate workflow that must be performed explicitly.

* **Executor jobs are submitted.** The client-side Estimator uses Executor to submit jobs, making
  them Executor jobs rather than Estimator jobs. Job attributes, such as
  :attr:`~qiskit_ibm_runtime.RuntimeJobV2.primitive_id` and
  :attr:`~qiskit_ibm_runtime.RuntimeJobV2.inputs`, return information about the Executor job.

**Step 1 — Update the imports.**

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2
    from qiskit_ibm_runtime.options import EstimatorOptions

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime.options_models import EstimatorOptions

**Step 2 — Perform noise learning explicitly (if using PEC or PEA).**

If your code uses PEC (``pec_mitigation=True``) or ZNE with PEA (``zne.amplifier="pea"``),
you need to perform noise learning explicitly using ``NoiseLearnerV3``.

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2

    pubs = [...]  # Your PUBs
    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.pec_mitigation = True  # or zne_mitigation + pea amplifier

    job = estimator.run(pubs)

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime import NoiseLearnerV3

    pubs = [...]  # Your PUBs
    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.pec_mitigation = True  # or zne_mitigation + pea amplifier

    # Identify the unique layers to learn.
    layers = estimator.find_unique_layers(pubs)

    # Learn the noise model for those layers (runs as a separate job).
    learner = NoiseLearnerV3(mode=backend)
    learner_job = learner.run(layers)
    learner_result = learner_job.result()

    # Convert the result to Pauli-Lindblad noise maps.
    pauli_lindblad_maps = learner_result.to_pauli_lindblad_maps()

    # Assign the learned noise maps so PEA/PEC uses them.
    # The result objects returned by NoiseLearnerV3 follow the same order as the input
    # layers, so the positional zip can be used here.
    estimator.options.resilience.layer_noise_model = zip(layers, pauli_lindblad_maps)

    # Now execute the target PUBs.
    job = estimator.run(pubs)

**Step 3 — Split one job into several (if the PUBs use different precision values).**

Mixed precisions are no longer supported: a job can no longer contain PUBs that request different
precision values, and :meth:`~.EstimatorV2.run` raises ``IBMInputValueError`` if it does. Group
the PUBs by precision and submit one job per group, using a :class:`~qiskit_ibm_runtime.Batch` so
the groups still run together.

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2

    # PUBs with different precision values.
    pubs = [(isa_circuit, isa_obs, None, 0.1), (isa_circuit1, isa_obs1, None, 0.5)]
    estimator = EstimatorV2(mode=backend)

    job = estimator.run(pubs)

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime import Batch

    # Group the PUBs by precision, one group per job.
    with Batch(backend=backend) as batch:
        estimator = EstimatorV2(mode=batch)

        jobs = [
            estimator.run([(isa_circuit, isa_obs)], precision=0.1),
            estimator.run([(isa_circuit1, isa_obs1)], precision=0.5),
        ]

    results = [job.result() for job in jobs]

Classes
=======
.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   Estimator
   EstimatorV2
"""

from .estimator import Estimator
from .estimator import Estimator as EstimatorV2
