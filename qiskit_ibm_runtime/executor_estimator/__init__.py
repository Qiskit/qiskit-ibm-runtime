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

The key architectural difference from the legacy server-side
:class:`~qiskit_ibm_runtime.EstimatorV2` is that **all pre- and post-processing runs on the
client machine**. This includes circuit preparation (twirling, gate folding, dynamical decoupling,
noise injection) and result post-processing (TREX readout-error mitigation, ZNE extrapolation, PEC
quasi-probability weighting). Running these steps locally provides faster debugging feedback and
greater user control, at the cost of local compute during the preparation phase.

The end-to-end processing pipeline is:

1. :meth:`~.EstimatorV2.run` coerces PUBs, calls :meth:`~.EstimatorV2.finalize_options` to
   resolve resilience-level defaults, and determines the shot count.
2. The ``prepare()`` pipeline converts the PUBs into a
   :class:`~qiskit_ibm_runtime.quantum_program.QuantumProgram`, applying circuit transformations
   (twirling, gate folding, DD, noise injection) according to the active options.
3. The :class:`~qiskit_ibm_runtime.executor.Executor` submits the quantum program to the backend.
4. When the job completes, the post-processor runs locally: it reconstructs expectation values from
   raw measurement data, applies TREX, and performs ZNE / PEA / PEC post-processing as needed.

.. note::

    For moderate and complex workloads the client-side preparation step can be resource intensive
    and may cause a delay before the job is submitted. Set your Python logging level to ``INFO``
    to monitor preparation progress::

        import logging
        logging.basicConfig(level=logging.INFO)

Basic usage
===========

The estimator takes ISA circuits (circuits transpiled for the target backend). Use
:func:`~qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager` to obtain an ISA
circuit before calling :meth:`~.EstimatorV2.run`.

**Example 1 — Minimal (no error mitigation, resilience level 0)**

.. code-block:: python

    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.executor_estimator import EstimatorV2

    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    observable = SparsePauliOp("ZZ")

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_qc = pm.run(qc)
    isa_obs = observable.apply_layout(isa_qc.layout)

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience_level = 0
    job = estimator.run([(isa_qc, isa_obs)])
    result = job.result()
    print(result[0].data.evs)   # expectation value

**Example 2 — Resilience level 2 (measurement error mitigation + ZNE)**

.. code-block:: python

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience_level = 2  # TREX + ZNE (gate folding)
    job = estimator.run([(isa_qc, isa_obs)])
    result = job.result()
    print(result[0].data.evs)                 # zero-noise extrapolated expectation value
    print(result[0].data.evs_noise_factors)   # raw values at each noise amplification level

**Example 3 — PEC (requires prior noise learning)**

PEC mitigation requires a learned noise model. Use :meth:`~.EstimatorV2.find_unique_layers` to
extract the unique gate layers from your PUBs, run
:class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3` as a separate job to learn their
noise, then assign the result to :attr:`~.ResilienceOptions.noise_model_mapping`.

.. code-block:: python

    from samplomatic import InjectNoise
    from samplomatic.utils import get_annotation
    from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3

    pubs = [(isa_qc, isa_obs)]

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.pec_mitigation = True

    # Step 1 — extract the unique boxed gate layers from your PUBs
    layers = estimator.find_unique_layers(pubs)
    noise_layers = [l for l in layers if get_annotation(l.operation, InjectNoise)]

    # Step 2 — learn the noise model for those layers
    nl_result = NoiseLearnerV3(mode=backend).run(noise_layers).result()

    # Step 3 — build the noise_model_mapping and assign it
    estimator.options.resilience.noise_model_mapping = {
        get_annotation(layer.operation, InjectNoise).ref: nl_result[i].data.error
        for i, layer in enumerate(noise_layers)
    }

    job = estimator.run(pubs)
    result = job.result()
    print(result[0].data.evs)

**Example 4 — ZNE with PEA amplifier (requires prior noise learning)**

.. code-block:: python

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience.zne_mitigation = True
    estimator.options.resilience.zne.amplifier = "pea"

    layers = estimator.find_unique_layers(pubs)
    noise_layers = [l for l in layers if get_annotation(l.operation, InjectNoise)]
    nl_result = NoiseLearnerV3(mode=backend).run(noise_layers).result()

    estimator.options.resilience.noise_model_mapping = {
        get_annotation(layer.operation, InjectNoise).ref: nl_result[i].data.error
        for i, layer in enumerate(noise_layers)
    }

    job = estimator.run(pubs)
    result = job.result()
    print(result[0].data.evs)                  # zero-noise extrapolated expectation value
    print(result[0].data.evs_extrapolated)     # values at each extrapolated noise point

Inputs
======

Constructor
-----------

* **mode** (:class:`~qiskit.providers.BackendV2` | :class:`~qiskit_ibm_runtime.Session` |
  :class:`~qiskit_ibm_runtime.Batch` | ``None``) —
  The execution mode. Use a :class:`~qiskit.providers.BackendV2` for job mode, a
  :class:`~qiskit_ibm_runtime.Session` for session mode, or a
  :class:`~qiskit_ibm_runtime.Batch` for batch mode. Refer to the
  `IBM Quantum Compute documentation <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
  for guidance on choosing an execution mode.

* **options** (:class:`~.EstimatorOptions` | ``dict`` | ``None``) —
  Estimator options. If ``None``, a default :class:`~.EstimatorOptions` instance with
  ``resilience_level=1`` is used. A plain ``dict`` is coerced to :class:`~.EstimatorOptions`.

``run()``
---------

Each call to :meth:`~.EstimatorV2.run` takes a list of PUBs (Primitive Unified Blocs). Each PUB
has the format::

    (<circuit>, <observables>, <optional parameter values>, <optional precision>)

Elements from observables and parameter values are combined by following NumPy broadcasting rules
as described in the
`Primitive inputs and outputs <https://quantum.cloud.ibm.com/docs/guides/primitive-input-output>`_
topic, and one expectation value estimate is returned for each element of the broadcasted shape.
If the circuit contains measurements, they are ignored.

**Circuit** (:class:`~qiskit.circuit.QuantumCircuit`)

A single ISA circuit (transpiled for the target backend), which may contain one or more
:class:`~qiskit.circuit.Parameter` objects.

**Observables** (``ObservablesArrayLike``)

One or more observables specifying the expectation values to estimate, arranged into an array.
The data can be in any ``ObservablesArrayLike`` format such as
:class:`~qiskit.quantum_info.Pauli`, :class:`~qiskit.quantum_info.SparsePauliOp`,
:class:`~qiskit.quantum_info.PauliList`, or ``str``.

The array shape controls how observables are broadcast against parameter values:

* A single observable (0-d array) is evaluated for every parameter value set.
* A 1-d array of ``n`` observables is broadcast against parameter values according to NumPy
  broadcasting rules.

.. note::

    Commuting observables in the same PUB are grouped together and measured in a single
    execution. Commuting observables in *different* PUBs, even with the same circuit, require
    separate measurements. To share a measurement across commuting observables, place them in
    the same PUB.

**Parameter values** (array-like, optional)

A collection of parameter value sets to bind the circuit against. Specified as a single
array-like object where the last index is over circuit :class:`~qiskit.circuit.Parameter`
objects. Omit (or set to ``None``) if the circuit has no parameters.

**Precision** (``float``, optional)

Per-PUB target precision. Overrides both the call-level ``precision`` argument and
``options.default_precision`` for this PUB only.

**Vectorised example**

The following example sweeps 100 parameter values against 3 observables, producing a result of
shape ``(3, 100)``:

.. code-block:: python

    import numpy as np
    from qiskit.circuit import Parameter, QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.executor_estimator import EstimatorV2

    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)

    # Define a circuit with two parameters.
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.ry(Parameter("a"), 0)
    circuit.rz(Parameter("b"), 0)
    circuit.cx(0, 1)
    circuit.h(0)

    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled_circuit = pm.run(circuit)
    layout = transpiled_circuit.layout

    # Sweep over 100 (a, b) pairs. Shape: (100, 2).
    params = np.vstack([
        np.linspace(-np.pi, np.pi, 100),
        np.linspace(-4 * np.pi, 4 * np.pi, 100),
    ]).T

    # Three observables, each wrapped in an inner list to give shape (3, 1).
    # Broadcasting (3, 1) against (100, 2) -> result shape (3, 100).
    observables = [
        [SparsePauliOp(["XX", "IY"], [0.5, 0.5])],
        [SparsePauliOp("XX")],
        [SparsePauliOp("IY")],
    ]
    observables = [
        [obs.apply_layout(layout) for obs in obs_set]
        for obs_set in observables
    ]

    estimator = EstimatorV2(mode=backend)
    job = estimator.run([(transpiled_circuit, observables, params)])
    result = job.result()
    print(result[0].data.evs.shape)  # (3, 100)

**``precision`` argument**

The call-level ``precision`` argument sets the target precision for every PUB in the call that
does not specify its own. It overrides ``options.default_precision`` for this call only.

Options
=======

All options are set on the :attr:`~.EstimatorV2.options` attribute, which is an instance of
:class:`~.EstimatorOptions`. Options can also be passed as a ``dict`` to the constructor.

**Resilience level** (``options.resilience_level``, default ``1``)

The primary dial for error mitigation. The three supported levels are:

* ``0`` — No mitigation. No twirling.
* ``1`` — Measurement error mitigation via TREX. Measurement twirling is on; gate twirling is off.
* ``2`` — TREX + Zero-Noise Extrapolation (gate-folding method). Both gate and measurement
  twirling are on.

Individual :class:`~.ResilienceOptions` sub-options override the level defaults when explicitly
set to a non-``None`` value. See :class:`~.EstimatorOptions` for the full description of all
level defaults.

**Shot and precision controls** (``options.default_precision``, ``options.default_shots``)

``default_precision`` sets the target statistical accuracy for expectation value estimates.
``default_shots`` overrides ``default_precision`` when set (shots take priority). See
:class:`~.EstimatorOptions` for details and defaults.

**Twirling** (``options.twirling``)

Controls randomised Pauli twirling of 2-qubit gates and measurements. Twirling is a prerequisite
for TREX measurement mitigation and for PEA/PEC noise injection. Several twirling parameters
(``enable_gates``, ``enable_measure``) are forced on automatically when the corresponding
mitigation technique is enabled. See :class:`~.TwirlingOptions` for all options.

**Resilience / error mitigation** (``options.resilience``)

The sub-group that enables and configures individual mitigation techniques:

* *Measurement error mitigation (TREX)* — enabled via ``resilience.measure_mitigation``. Fine-tuned
  with ``resilience.measure_noise_learning``. See :class:`~.MeasureNoiseLearningOptions`.
* *Zero-Noise Extrapolation (ZNE)* — enabled via ``resilience.zne_mitigation``. The noise
  amplifier, noise factors, and extrapolation models are configured in ``resilience.zne``.
  See :class:`~.ZneOptions`.
* *Probabilistic Error Cancellation (PEC)* — enabled via ``resilience.pec_mitigation``. Requires
  a ``resilience.noise_model_mapping``. Fine-tuned with ``resilience.pec``.
  See :class:`~.PecOptions`.
* *Noise model mapping* — ``resilience.noise_model_mapping`` is a
  ``dict[str, PauliLindbladMap]`` required for PEC and PEA-based ZNE. Obtain it by running
  :class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3` (see Examples above).

.. note::

    PEC mitigation and ZNE mitigation are mutually exclusive. Enabling both raises an error.

See :class:`~.ResilienceOptions` for the complete reference.

**Dynamical decoupling** (``options.dynamical_decoupling``)

Inserts DD pulse sequences on idle qubits to suppress decoherence during circuit execution.
See :class:`~.DynamicalDecouplingOptions` for sequence types and scheduling options.

**Execution** (``options.execution``)

Low-level controls such as qubit initialisation before each shot and repetition delay.
See :class:`~.ExecutionOptions` for all options.

Outputs
=======

:meth:`~.EstimatorV2.run` returns a :class:`~qiskit_ibm_runtime.RuntimeJobV2`. Calling
``job.result()`` returns a :class:`~qiskit.primitives.PrimitiveResult` of
:class:`~qiskit_ibm_runtime.results.EstimatorPubResult` objects — one per input PUB::

    result = job.result()
    pub_result = result[0]        # EstimatorPubResult for the first PUB
    pub_result.data               # DataBin holding numerical arrays
    pub_result.metadata           # dict with per-PUB metadata
    result.metadata               # dict with program-level metadata

The contents of ``pub_result.data`` depend on the active mitigation technique.

No mitigation / measurement mitigation only (resilience levels 0 and 1)
------------------------------------------------------------------------

* **``data.evs``** — Expectation values. Shape: ``broadcast(param_shape, obs_shape)``.
* **``data.stds``** — Standard deviations. Same shape as ``evs``.
  Reflects the spread across twirling randomisations when twirling is enabled; equals
  ``ensemble_standard_error`` when twirling is disabled.
* **``data.ensemble_standard_error``** — Standard error under the i.i.d. shot-noise assumption
  (no drift contribution). Same shape as ``evs``.

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
  extrapolator is chosen per-term for multi-term observables). Shape: ``pub_shape``.
* **``data.stds``** — Standard deviations of the extrapolated values. Same shape as ``evs``.
  Derived from the spread over twirling randomisations when twirling is on.
* **``data.evs_noise_factors``** — Raw (non-extrapolated) expectation values at each noise
  amplification level. Shape: ``(*pub_shape, num_noise_factors)``.
* **``data.stds_noise_factors``** — Standard deviations at each noise factor. Same shape.
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

Program-level metadata
-----------------------

``result.metadata`` is a ``dict`` containing:

* The finalised :class:`~.EstimatorOptions` — inactive resilience sub-options are pruned (for
  example, the ``zne`` sub-dict is omitted when ``zne_mitigation=False``).
* **``"target_precision"``** — the resolved precision for this run, or ``None`` when the shot
  count was specified directly via ``default_shots``.
* **``"shots"``** — the total shot count used for execution.

Differences from the legacy EstimatorV2
========================================

The following differences exist between this executor-based
:class:`~qiskit_ibm_runtime.executor_estimator.EstimatorV2` and the legacy server-side
:class:`~qiskit_ibm_runtime.EstimatorV2`:

* **Client-side pre- and post-processing** — In the legacy estimator all circuit transformations
  (twirling, gate folding, noise injection) and result post-processing (ZNE extrapolation, TREX,
  PEC weighting) are performed server-side. In the executor estimator these steps run entirely
  on the client machine.

* **Noise learning is a separate step** — In the legacy estimator, noise learning for PEC and PEA
  was integrated into the estimator job itself: the server handled it automatically. In the
  executor estimator, noise learning is an independent workflow. The user must call
  :meth:`~.EstimatorV2.find_unique_layers` to extract gate layers, run
  :class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3` as a separate job, and assign the
  result to ``options.resilience.noise_model_mapping`` before calling :meth:`~.EstimatorV2.run`.

* **Different import path** — ``from qiskit_ibm_runtime.executor_estimator import EstimatorV2``
  vs. ``from qiskit_ibm_runtime import EstimatorV2``.

* **Different options module** — This estimator uses
  :class:`~qiskit_ibm_runtime.options_models.estimator.EstimatorOptions`
  (from ``qiskit_ibm_runtime.options_models``) rather than the legacy
  ``qiskit_ibm_runtime.options.EstimatorOptions``.

.. todo::

    Additional differences will be listed here.

Migration guide
================

Follow these steps to migrate from the legacy
:class:`~qiskit_ibm_runtime.EstimatorV2` to this executor-based version.

**Step 1 — Update the import**

.. code-block:: python

    # Before
    from qiskit_ibm_runtime import EstimatorV2

    # After
    from qiskit_ibm_runtime.executor_estimator import EstimatorV2

**Step 2 — Update the options import** (if you instantiate options directly)

.. code-block:: python

    # Before
    from qiskit_ibm_runtime.options import EstimatorOptions

    # After
    from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

**Step 3 — Separate out noise learning for PEC / PEA**

If your code uses PEC (``pec_mitigation=True``) or ZNE with PEA (``zne.amplifier="pea"``), the
noise learning that was previously handled automatically by the server must now be done explicitly
before calling ``run()``. See Example 3 above for the full workflow using
:meth:`~.EstimatorV2.find_unique_layers` and
:class:`~qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3`.

**Step 4 — No other changes required**

The constructor signature (``mode``, ``options``), the ``run()`` signature (``pubs``,
``precision``), the resilience levels (0–2), and the structure of the returned
:class:`~qiskit.primitives.PrimitiveResult` are all compatible with the legacy estimator.
"""

from .estimator import EstimatorV2
