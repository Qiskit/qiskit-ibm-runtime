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

:class:`~.EstimatorV2` is an implementation of the Qiskit ``EstimatorV2`` interface built on
top of the :class:`~qiskit_ibm_runtime.executor.Executor` primitive. It estimates expectation
values of quantum observables by executing ISA circuits on an IBM Quantum backend.

The key difference between the legacy server-side :class:`~qiskit_ibm_runtime.EstimatorV2` and
this new implementation is that **all pre- and post-processing run on the
client machine**. This includes circuit preparation (twirling, gate folding, dynamical decoupling,
and noise injection) as well as result post-processing (TREX rescaling, ZNE extrapolation, and PEC
quasi-probability weighting). Running these steps locally provides faster debugging feedback and
greater user control.

When a user submits a job via :meth:`~.EstimatorV2.run`, the underlying processing includes:

1. Coercing the PUBs, resolving the resilience-level defaults, and determining the shot count.
2. Converting PUBs into
   :class:`~qiskit_ibm_runtime.quantum_program.QuantumProgram`, applying circuit transformations
   (twirling, gate folding, DD, noise injection) according to the specified options.
3. Calling :class:`~qiskit_ibm_runtime.executor.Executor` to submit the quantum program to the backend.
4. Upon job completion, estimating expectation values from raw measurement data and applying error-mitigation
   post-processing as needed.

.. note::

    For moderate and complex workloads the client-side preparation step can be resource intensive
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
explicit noise learning for error mitigation methods that require noise models (PEC and PEA).

Use :meth:`~.EstimatorV2.find_unique_layers` to extract the unique gate layers from your PUBs,
pass the layers to :class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3` to learn
their noise in a separate job, then assign the noise model to :attr:`~.ResilienceOptions.noise_model`.

.. code-block:: python

    from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3

    pubs = [(isa_qc, isa_obs)]

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.pec_mitigation = True

    # Step 1 — extract the unique boxed gate layers from your PUBs
    layers = estimator.find_unique_layers(pubs)

    # Step 2 — learn the noise model for those layers
    nl_result = NoiseLearnerV3(mode=backend).run(noise_layers).result()

    # Step 3 — convert the NoiseLearnerV3 result to Pauli-Lindblad noise model and pass to EstimatorV2
    pauli_lindblad_maps = noise_result.to_pauli_lindblad_maps()
    estimator.options.resilience.layer_noise_model = zip(layers, pauli_lindblad_maps)

    job = estimator.run(pubs)
    result = job.result()
    print(result[0].data.evs)

Inputs
======

Each call to :meth:`~.EstimatorV2.run` takes a list of PUBs (Primitive Unified Blocs). Each PUB
is in this format::

    (<single circuit>, <one or more observables>, <optional one or more parameter values>, <optional precision>)

See `Estimator inputs and outputs <https://quantum.cloud.ibm.com/docs/en/guides/estimator-input-output>`_
for more information on EstimatorV2 inputs and outputs.

Elements from observables and parameter values are combined by following NumPy broadcasting rules
as described in
`Primitive inputs and outputs <https://quantum.cloud.ibm.com/docs/guides/primitive-input-output>`_.


Options
=======

When calling :class:`~.EstimatorV2`, you can pass in options by using :class:`~.EstimatorOptions` or a dictionary.
Commonly-used options, such as ``resilience_level``, are at the first level. Other options are
grouped into categories, such as ``execution``. Specify the options in this format:
``options.option.sub-option.sub-sub-option = choice``. For example: ``options.dynamical_decoupling.enable = True``.

See `Introduction to options <https://quantum.cloud.ibm.com/docs/en/guides/runtime-options-overview>`_
for an overview on specifying primitive options.
See `Specify Estimator options <https://quantum.cloud.ibm.com/docs/en/guides/estimator-options>`_
and `Configure noise management with Estimator <https://quantum.cloud.ibm.com/docs/en/guides/estimator-noise-management>`_
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

All of these fields have the same shape of ``broadcast(param_shape, obs_shape)``.

* **``data.evs``** — Expectation values.
* **``data.stds``** — Standard deviations.
  Reflects the spread across twirling randomisations when twirling is enabled; equals
  ``ensemble_standard_error`` when twirling is disabled.
* **``data.ensemble_standard_error``** — Standard error under the i.i.d. shot-noise assumption
  (no drift contribution).

When measurement mitigation (TREX) is active, the ``evs`` values are corrected for readout
errors using a calibration circuit that is run automatically alongside the main circuits.

PEC
---

PEC produces the same three fields as the no-mitigation case: ``evs``, ``stds``, and
``ensemble_standard_error``. The gamma quasi-probability factor is applied internally during
post-processing and does not appear as a separate output field.

The ``stds`` values are scaled by the gamma factor, so they are typically larger than the
no-mitigation case for the same shot count. This is the fundamental cost of PEC: unbiased
estimates come with increased variance proportional to the sampling overhead (``gamma^2``).

ZNE (gate folding) and PEA
---------------------------

When ``resilience.zne_mitigation=True`` the estimator runs the circuit at multiple noise
amplification levels and fits a curve to extrapolate to zero noise. The result contains both
the extrapolated estimate and the raw data at each noise level.

* **``data.evs``** — Zero-noise extrapolated expectation values (best heterogeneous fit — the
  extrapolator is chosen per-term for multi-term observables). Shape: ``broadcast(param_shape, obs_shape)``.
* **``data.stds``** — Standard deviations of the extrapolated values. Same shape as ``evs``.
  Derived from the spread over twirling randomisations when twirling is on.
* **``data.evs_noise_factors``** — Raw (non-extrapolated) expectation values at each noise
  amplification level. Shape: ``(*pub_shape, num_noise_factors)``.
* **``data.stds_noise_factors``** — Standard deviations at each noise factor.
  Same shape as ``evs_noise_factors``.
  Reflects the spread over twirling randomisations when twirling is on; equals
  ``ensemble_stds_noise_factors`` when twirling is off.
* **``data.ensemble_stds_noise_factors``** — Ensemble standard errors at each noise factor under
  the i.i.d. shot-noise assumption. Shape: ``(*pub_shape, num_noise_factors)``.
* **``data.evs_extrapolated``** — Expectation values from each requested extrapolator, evaluated
  at each point in ``resilience.zne.extrapolated_noise_factors``. These are forced homogeneous
  fits — the same extrapolator is applied to all terms of a multi-term observable — one fit per
  extrapolator. Shape: ``(*pub_shape, num_extrapolators, num_eval_points)``.
* **``data.stds_extrapolated``** — Standard deviations corresponding to ``evs_extrapolated``.
  Same shape.

.. note::

    For multi-term observables (e.g. ``{"XX": 0.5, "XY": 0.5}``) ``evs`` and ``stds`` use a
    heterogeneous fit: the best-fitting extrapolator is selected independently for each Pauli
    term. ``evs_extrapolated`` and ``stds_extrapolated`` use a homogeneous fit per extrapolator,
    which is useful for comparing models. If your analysis requires a clean distinction between
    these two modes, use single-term observables alongside your multi-term ones.

ZNE results can be visualised with
:meth:`~qiskit_ibm_runtime.results.EstimatorPubResult.draw_zne_evs` and
:meth:`~qiskit_ibm_runtime.results.EstimatorPubResult.draw_zne_extrapolators` (requires
``plotly``).

Job-level metadata
-----------------------

``result.metadata`` is a ``dict`` containing:

* The finalised :class:`~.EstimatorOptions` — inactive resilience sub-options are pruned (for
  example, the ``zne`` sub-dict is omitted when ``zne_mitigation=False``).
* **``"target_precision"``** — the resolved precision for this run, or ``None`` when the shot
  count was specified directly via ``default_shots``.
* **``"shots"``** — the total shot count used for execution.

Differences from the legacy EstimatorV2
========================================

The main differences between the legacy :class:`~qiskit_ibm_runtime.EstimatorV2` and the
new client-side :class:`~.EstimatorV2` are:

* **Pre- and post-processing happen on the client-side.** In the legacy Estimator all circuit transformations
  (twirling, gate folding, and noise injection), as well as result post-processing (ZNE extrapolation,
  TREX rescaling, and PEC weighting) are performed on the server-side.
  In this client-side implementation, these steps run entirely on the client machines.

* **Noise learning is a separate step** — In the legacy Estimator, noise learning for PEC and PEA
  is integrated into the Estimator job itself and handled implicitly on the server side. In this
  new implementation, however, noise learning is a separate workflow that needs to be performed explicitly.

* **Different import paths.**
    * Use ``from qiskit_ibm_runtime.executor_estimator import EstimatorV2`` to import the client-side Estimator.
    * Use ``from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions`` to import the
      option class for the new Estimator.

* **Mixed precisions is not supported.** In this client-side implmentation, a job can no longer
  contain PUBs that request different precision values.

* **Executor jobs are submitted.** The client-side Estimator uses Executor to submit jobs, making
  them Execuor jobs rather than Estimator jobs. Job attributes, such as
  :attr:`~qiskit_ibm_runtime.RuntimeJobV2.primitive_id` and :attr:`~qiskit_ibm_runtime.RuntimeJobV2.inputs`
  will return information on the Executor job.


Migration guide
================

This client-side EstimatorV2 implementation is largely a drop-in replacement of the legacy one, but
there are a few niche paths that require code changes. Follow the steps listed below to migrate to
the new implementation.

**Step 1 — Update the imports.**

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2
    from qiskit_ibm_runtime.options import EstimatorOptions

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

**Step 2 — Perform expclitly noise learning (if using PEC or PEA)**

If your code uses PEC (``pec_mitigation=True``) or ZNE with PEA (``zne.amplifier="pea"``),
you need to perform noise-learning explicitly using ``NoiseLearnerV3``.

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2

    pubs = [...]  # Your PUBs
    estimator = EstimatorV2(backend, options)
    estimator.options.resilience.pec_mitigation = True  # or zne_mitigation + pea amplifier

    job = estimator.run(pubs)

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime import NoiseLearnerV3

    pubs = [...]  # Your PUBs
    estimator = EstimatorV2(backend, options)
    estimator.options.resilience.pec_mitigation = True  # or zne_mitigation + pea amplifier

    # Identify the unique layers to learn.
    layers = estimator.find_unique_layers(pubs)

    # Learn the noise model for those layers (runs as a separate job).
    learner = NoiseLearnerV3(backend)
    learner_job = learner.run(layers)
    learner_result = learner_job.result()

    # Convert results to Pauli-Lindblad noise maps.
    pauli_lindblad_maps = learner_result.to_pauli_lindblad_maps()

    # Assign the learned noise maps so PEA/PEC uses them.
    estimator.options.resilience.layer_noise_model = zip(layers, pauli_lindblad_maps)

    # Now execute the target PUBs.
    job = estimator.run(pubs)

**Step 3 — Split one job into several (if precision values were used).**

**Before:**

.. code-block:: python

    from qiskit_ibm_runtime import EstimatorV2

    # PUBs with different precision values.
    pubs = [(isa_circuit, isa_obs, None, 0.1), (isa_circuit1, isa_obs1, None, 0.5)]
    estimator = EstimatorV2(backend, options)

    job = estimator.run(pubs)

**After:**

.. code-block:: python

    from qiskit_ibm_runtime.executor_estimator import EstimatorV2
    from qiskit_ibm_runtime import Batch

    pubs = [(isa_circuit, isa_obs)]

    with Batch(backend=backend) as batch:
        estimator = EstimatorV2(mode=batch)

        # Submit every split job with different precision values.
        jobs = []
        jobs.append(estimator.run(pubs, precision=0.5))
        jobs.append(estimator.run(pubs, precision=0.1))

"""

from .estimator import EstimatorV2