=======================================
Qiskit Runtime IBM Client release notes
=======================================

.. towncrier release notes start

0.43.1 (2025-10-23)
===================

Upgrade Notes
-------------

- When initializing :class:`.QiskitRuntimeService` with a saved account, the ``warning`` level log messages regarding
  the saved account name (or default account) have been lowered to the ``info`` level. (`2445 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2445>`__)

0.43 (2025-10-14)
=================

Deprecation Notes
-----------------

- Added a new ``target`` argument to the initializer following transpiler analysis and padding passes: 
  :class:`.ALAPScheduleAnalysis`, :class:`.PadDelay`, :class:`.PadDynamicalDecoupling`, :class:`.BlockBasePadder`.
  This change aligns these passes with the broader Qiskit transpiler architecture, and supersedes the use of the
  ``durations`` argument.

  The :class:`.DynamicCircuitInstructionDurations` class, used in custom scheduling passes, has been deprecated as of
  ``qiskit-ibm-runtime`` v0.43. This class was optimized for scheduling operations on Eagle processors, and it 
  has fallen out of date with the current offering of Heron processors. This class was used to define the ```durations`` 
  argument in the scheduling passes listed above 
  (:class:`.ALAPScheduleAnalysis`, :class:`.PadDelay`, :class:`.PadDynamicalDecoupling`, :class:`.BlockBasePadder`). 
  The argument is also deprecated and will be removed in a future release. Users are encouraged to migrate to 
  the ``target`` argument. (`2403 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2403>`__)
- The :class:`RuntimeOptions` class is deprecated. This class was originally only 
  meant to be used with custom programs and is no longer needed. (`2435 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2435>`__)


New Features
------------

- The :mod:`qiskit_ibm_runtime` package has been extended with two new modules: :mod:`.circuit` and 
  :mod:`.circuit.library`. These modules are designed to mirror the structure of the 
  corresponding ``qiskit`` SDK modules, while providing vendor-specific implementations of 
  circuit objects and instructions. 

  The first addition to this new circuit library is the :class:`.MidCircuitMeasure` class. 
  This class enables the creation of instructions that follow the naming convention 
  ``measure_<identifier>``, which are mapped to specific mid-circuit measurement
  hardware instructions matching that pattern. The default name for this instruction is ``"measure_2"``.
   
  
  Example usage::

      from qiskit import QuantumCircuit
      from qiskit_ibm_runtime.circuit import MidCircuitMeasure

      measure_2 = MidCircuitMeasure()
      measure_3 = MidCircuitMeasure("measure_3")
      qc = QuantumCircuit(1, 1)
      qc.append(measure_2, [0], [0])
      qc.append(measure_3, [0], [0])
      qc.measure([0], [0])

  Output::

         ┌────────────┐┌────────────┐┌─┐
      q: ┤0           ├┤0           ├┤M├
         │  Measure_2 ││  Measure_3 │└╥┘
      c: ╡0           ╞╡0           ╞═╩═
         └────────────┘└────────────┘


  The :func:`.convert_to_target` utility has been updated to support an additional ``"instruction_signatures"`` field in 
  backend configuration files (``configuration.json``). This field is intended to represent non-unitary, non-standard instructions 
  reported by the backend and should respect the following schema::

      "instruction_signatures" = [
          {
              "name": "measure_2",
              "num_qubits": 1,
              "num_clbits": 1,
              "parameters": [],
              "return_type": "Bool",
              "description": "An alternative measurement. This can be used as a mid-circuit measurement in a dynamic circuit. ",
          },
          {
              "name": "reset_2",
              "num_qubits": 1,
              "num_clbits": 1,
              "parameters": [],
              "return_type": "Bool",
              "description": "An alternative reset instruction.",
          }
      ]

  In addition to this change, the :func:`.convert_to_target` function now accepts a ``custom_name_mapping`` argument
  and exposes the ``add_delay`` and ``filter_faulty`` flags from the original core implementation. (`2316 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2316>`__)

- :meth:`.QiskitRuntimeService.backends` and :meth:`.QiskitRuntimeService.backend` have a new parameter, 
  ``calibration_id``. This custom calibration will be used for constructing the target and also used 
  when executing primitive jobs on the backend. (`2432 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2432>`__)
- Added a new function :meth:`.visualization.draw_circuit_schedule_timing` to plot circuit schedule 
  timing data returned in job result metadata. This is currently a beta feature and requires the 
  ``"scheduler_timing"`` experimental option to be set to ``True``, as shown below. This is 
  currently only available to ``Sampler`` jobs.

  .. code-block:: python

      sampler = SamplerV2(backend)
      sampler.options.experimental = { 
          "execution": {
              "scheduler_timing": True,
          },
      }

  The circuit schedule data can then be accessed from the job's result metadata as follows:

  .. code-block:: python

      job_result: SamplerPubResult = job.result()
      circuit_schedule = job_result[0].metadata["compilation"]["scheduler_timing"]
      circuit_schedule_timing = circuit_schedule["timing"]

  This function uses the new :class:`CircuitSchedule` class to load, parse, preprocess, 
  and trace the data for plotting using a Plotly supported interface. (`2328 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2328>`__)
- Virtual private endpoints for IBM Quantum Platform are now supported.
  Learn more in our `virtual private endpoints guide <https://quantum.cloud.ibm.com/docs/security/virtual-private-endpoints>`__. (`2367 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2367>`__)
- It is now possible to retrieve the job tags of a job without having to actually fetch 
  the job with :meth:`.QiskitRuntimeService.job`. (`2420 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2420>`__)
- The :class:`.~ConvertISAToClifford` pass now supports Cliffordization of circuits containing fractional gates. (`2427 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2427>`__)

0.42.0 (2025-09-15)
===================

Bug Fixes
---------

- The :meth:`.QiskitRuntimeService.least_busy` method's behavior was inconsistent because it expected a 
  fixed response from the API for the `"reason"` field, which is labeled as optional in the API schema. This has been fixed by no longer depending 
  on this field. (`2411 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2411>`__)

Upgrade notes
-------------

- When :class:`.QiskitRuntimeService` is initialized without an instance 
  and there is no saved account instance, there will now be a warning detailing 
  the current filters (``tags``, ``region``, and ``plans_preference``) and available instances. If ``plans_preference``
  is not set, free and trial plan instances are prioritized over paid instances. 

  Additional warnings have also been added to make the current active instance more clear:

      - Warning messages to tell users whether they're using a saved account or using manually specified credentials.
      - When Qiskit Runtime automatically selects an instance for the requested backend, there will be a warning with
        the instance name and plan type. 

  You can now initialize :class:`.QiskitRuntimeService` with only an API token (key). Since the ``ibm_quantum``
  channel name has been removed and both the ``ibm_cloud`` and ``ibm_quantum_platform`` channels point to the same
  API, the ``channel`` parameter is no longer required. ``ibm_quantum_platform`` is the default channel. (`2375 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2375>`__)

- Because support for streaming results was removed in ``0.32.0``, the deprecated (``0.38.0``) environment option
  ``callback``, as well as the ``BaseRuntimeJob`` parameters ``client_params`` and ``user_callback``, have been removed.

  The ``RuntimeJob`` class has also been removed. All primitives return jobs as ``RuntimeJobV2``. Type hints across the 
  codebase have been updated to reflect this change. (`2298 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2298>`__)
  
- :meth:`.RuntimeJobV2.properties` will now fetch the backend properties from when the job started running 
  instead of when the job was created. (`2369 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2369>`__)

- Fixed an inconsistency in the unit conversion of ``rep_times`` in :class:`.QasmBackendConfiguration` to maintain
  consistency between initialization and serialization. The parameter is now properly 
  converted from microseconds to seconds during initialization and back to microseconds 
  when serialized through :meth:`to_dict()`, matching the behavior of other timing parameters: 
  ``rep_delay_range`` and ``default_rep_delay``. (`2386 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2386>`__)

- A consistent error will now be raised during service initialization if an invalid API token is given to :class:`.QiskitRuntimeService`. 

  An error will also be raised if the account associated with the specified token does not have access to the given instance.
  This was the previously documented behavior in the ``0.40.0`` release notes. (`2408 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2408>`__)

New Features
------------

- Since backends now support running jobs that contain both fractional gates and dynamic circuits, control flow 
  instructions are no longer filtered out when using ``use_fractional_gates=True``. As a result, there is a new translation state plugin, 
  :class:`~.IBMDynamicFractionalTranslationPlugin`, for targeting circuits with both 
  dynamic circuits and fractional gates.

  :class:`~.IBMFractionalTranslationPlugin` is deprecated 
  since it is no longer necessary. (`2366 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2366>`__)

0.41.1 (2025-08-18)
===================

Bug Fixes
---------

- Fixed multiple bugs where having a default saved instance or passing in the instance name would result in an 
  an ``IBMInputValueError`` when creating a :class:`~.Session` / :class:`~.Batch`

  Additionally, :meth:`.QiskitRuntimeService.least_busy` now correctly returns the least busy 
  backend in the cases where the ``instance`` parameter is passed in and when there is no default instance. (`2359 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2359>`__)

0.41.0 (2025-07-24)
===================

Prelude
-------

The qiskit-ibm-runtime ``v0.41.0`` release focuses on the removal of IBM Quantum Platform Classic and improving 
the user experience for the new IBM Quantum Platform. Among new features, improvements, and minor bug fixes, 
the release highlights are:

  - The ``ibm_quantum`` channel and IQP Classic are no longer supported. 
  - :meth:`.QiskitRuntimeService.least_busy` is significantly faster. 
  - :meth:`.QiskitRuntimeService.usage` has been updated to return information regarding the current 
    instance usage limit, consumption, and time remaining. 


Upgrade Notes
-------------

- Because of the sunset of IBM Quantum Platform Classic, the ``ibm_quantum`` channel is no
  longer supported from ``qiskit-ibm-runtime``. Saved ``ibm_quantum`` channel accounts and 
  data will not be accessible. Use the ``ibm_quantum_platform`` channel instead. See our 
  `migration guide <https://docs.quantum.ibm.com/migration-guides/classic-iqp-to-cloud-iqp>`__
  for more details. (`2289 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2289>`__)


New Features
------------

- A new parameter, ``tags``, has been added to the 
  :class:`.QiskitRuntimeService` initializer and :meth:`.QiskitRuntimeService.save_account` method. 
  ``tags`` can be used to **filter** instances so only instances with the given tags are 
  returned.

  Additionally, if no valid instances are returned when using the ``tags``, ``region``, or ``plans_preference`` filters,  
  an error will now be raised at initialization. Make sure the names of the ``tags`` and ``region`` passed in  
  match the instance ``tags`` or ``region`` exactly (case-insensitive). For ``plans_preference``, as long as a matching
  plan name is passed in, instances with the matching plan name will be prioritized. (`2277 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2277>`__)
- With the migration to the new IBM Quantum Platform, there were a few inconsistencies with IBM Quantum 
  Platform Classic that needed to be addressed:

      - :meth:`.QiskitRuntimeService.usage` now returns usage information for the current active IBM Cloud instance.
      - :meth:`.QiskitRuntimeService.delete_job` is not supported on the new platform, so it has been deprecated.
      - :meth:`.RuntimeJobV2.instance` will now return the IBM Cloud instance CRN. 
      - :meth:`.RuntimeJob.queue_usage` is not supported on the new platform, so it has been deprecated. (`2296 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2296>`__)
- Support for running ``qiskit-ibm-runtime`` with Python 3.9 has been deprecated and will
  be removed in a future release. 

  Additionally, ``qiskit-ibm-runtime`` now officialy supports Python 3.13. (`2314 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2314>`__)
- When saving an account, there is now a validation check to make sure the ``region``, 
  ``plans_preference``, and ``tags`` parameters are valid. (`2319 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2319>`__)
- There is a new method, :meth:`.QiskitRuntimeService.active_instance` which returns the IBM Cloud CRN 
  of the current active instance. 

  The :meth:`.QiskitRuntimeService.jobs` method has been updated to properly accept the ``instance`` 
  parameter, which can be used to filter jobs. (`2325 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2325>`__)
- :meth:`.QiskitRuntimeService.usage` has been updated to include a ``usage_remaining_seconds`` field. 
  This field includes the difference between the reported ``usage_limit_seconds`` or ``usage_allocation_seconds`` 
  (depending on how the instance is configured) and ``usage_consumed_seconds``. 
  Learn more about instance allocation limits `here <https://quantum.cloud.ibm.com/docs/guides/allocation-limits>`__. (`2329 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2329>`__)

- :meth:`~.FakeBackendV2.refresh` has a new parameter, ``use_fractional_gates``, that can be set to ``True``
  to allow the fake backend to include fractional gates. Note that this method only works if you have access
  to the real backend. (`2342 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2342>`__)

- The :class:`.QiskitRuntimeService` has been updated to use a new API version. With the new version, 
  the :meth:`.QiskitRuntimeService.least_busy` method has been updated to take advantage of the updated ``BackendsResponseV2`` 
  which makes it significantly faster. (`2323 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2323>`__)

- Class :class:`.TwirledSliceSpan` has a new data member ``data_slice_version`` of type integer, with default value 1. 
  When set to 2, the data slice tuples contain information about the PUB shots, used in :meth:`.TwirledSliceSpan.mask` 
  to shape the returned array. The last axis will be truncated, such that its length will be shortened to ``pub_shots``. (`2312 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2312>`__)

- Added serialization for :class:`qiskit.quantum_info.PauliLindbladMap`. (`2297 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2297>`__)

- There is a new method :meth:`.convert_to_rzz_valid_pub`, which can be used to transform a PUB into an equivalent PUB that is compatible with Rzz constraints. 
  The method currently does not support dynamic circuits and does not preserve global phase. (`2126 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2126>`__)

Bug Fixes
---------

- Fixed a bug in :class:`.BasePrimitive` where primitives instantiated inside a :class:`~.Session` or :class:`~.Batch` context manager without the ``mode`` 
  parameter would fetch the backend from the service (by name) instead of using the backend passed to the :class:`~.Session` or :class:`~.Batch`. 
  This could cause issues when the :class:`~.Session` or :class:`~.Batch`
  backend was modified by users (for example, by removing a gate), because the primitives 
  would instead fetch the unmodified backend object from the service. After the fix, the
  :class:`~.Session` or :class:`~.Batch` backend object is used directly. (`2282 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2282>`__)
- Fixed an issue in :class:`.IBMBackend` where property changes, such as modifications to ``basis_gates``, persisted even after the backend object was renewed. (`2283 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2283>`__)
- Fixed the serialization of execution spans, to ensure that executions of old versions of qiskit-ibm-runtime will not crash when trying to decode newly 
  encoded execution spans. However the deserialization with old versions will now return the execution spans in the format of a dictionary, and not in 
  the form of an :class:`.ExecutionSpans` object. As part of this work, we also removed the ``data_slice_version`` field 
  from :class:`.TwirledSliceSpan`; twirled slice spans that are aware of the pub shots are now managed by a new class :class:`.TwirledSliceSpanV2`. (`2347 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2347>`__)

Other Notes
-----------

- The deprecated :class:`.IBMBackend` attributes, ``max_shots`` and 
  ``max_experiments``, have been removed and the :meth:`.IBMBackend.max_circuits` method now
  returns ``None``. See the `job limits guide <https://quantum.cloud.ibm.com/docs/guides/job-limits#job-limits>`__ for details. (`2235 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2235>`__)
- The deprecated :class:`~.IBMBackend` and :class:`~.FakeBackendV2` ``defaults()`` methods 
  have been removed. They were deprecated in the v0.38.0 release. 
  Pulse defaults have also been removed from all fake backends. (`2238 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2238>`__)
- Improved the error message returned when :meth:`.ExecutionSpan.mask` is called for a PUB that's not contained in the span. (`2311 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2311>`__)

0.40.1 (2025-06-04)
===================

Bug Fixes
---------

- Fixed an issue where if there was no instance saved nor passed in at initialization, the service could not make
  any API calls until :meth:`.QiskitRuntimeService.backend` or :meth:`.QiskitRuntimeService.backends` is called first.

- Fixed a bug where if ``use_fractional_gates`` is set but the backend configuration was already cached, 
  the incorrect configuration could be returned. (`2269 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2269>`__)


Other Notes
-----------

- Error messages related to ``rzz`` gate angles being outside of the allowed
  range of 0 to :math:`\pi/2` during circuit validation have been updated to
  clarify that the angle value requested in the circuit was the problem and not
  an angle value provided by the backend. (`2276 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2276>`__)

0.40.0 (2025-05-28)
===================

New Features
------------

- The following changes were made to support the upcoming 
  `IBM Quantum platform migration <https://docs.quantum.ibm.com/migration-guides/classic-iqp-to-cloud-iqp>`__:

  - A new channel type, ``ibm_quantum_platform``, has been introduced for service initialization  (``QiskitRuntimeService()``). 
    It joins the existing ``ibm_quantum`` (now deprecated) and ``ibm_cloud`` channels. By **default**, 
    ``ibm_quantum_platform`` is selected when no channel is specified. This new channel connects to the 
    new IBM Quantum Platform API and is intended to replace ``ibm_cloud``. In the meantime, the ``ibm_cloud`` channel will redirect to the new 
    API, but its continued use is discouraged. 

  - An ``instance`` value is **no longer required** for saving (:meth:`.QiskitRuntimeService.save_account`) or 
    initializing (``QiskitRuntimeService()``) an account on the new platform (``ibm_quantum_platform``, and temporarily, ``ibm_cloud``
    channels). If an instance is not passed in, all instances will be checked when a backend is retrieved, 
    (``service.backend("backend_name")``).  If an instance is passed 
    into :meth:`.QiskitRuntimeService.save_account`, or passed in 
    during initialization, it will be used as the **default instance** when retrieving backends.
    The instance passed in at initialization will take **precedence** over the one saved in the account. 
  
  - Note that the IBM Cloud API Token (``token``) is required for saving 
    (:meth:`.QiskitRuntimeService.save_account`) or 
    initializing (``QiskitRuntimeService()``) an account on the new platform. It's treated as the account identifier 
    and will unlock the resources associated with the account the token was created in. A list of tokens per account can be found `here <https://cloud.ibm.com/iam/apikeys>`__. 
    Only one account per API token can be used. If you want to use multiple accounts, you must create multiple API tokens.

  - The :meth:`.QiskitRuntimeService.backend` and :meth:`.QiskitRuntimeService.backends` methods have been 
    updated to accept an ``instance`` passed in explicitly when retrieving backends: 
    ``service.backend(name="...", instance="...")``.

  - New parameters, ``region``, and ``plans_preference``, have been added to the 
    :class:`.QiskitRuntimeService`   initializer and :meth:`.QiskitRuntimeService.save_account` method. 
    These can be used to **prioritize** certain instances on the new platform 
    (``ibm_quantum_platform``, and temporarily, ``ibm_cloud`` channels) without explicitly providing the CRN. In more detail:

    - ``region``: Sets a region preference. ``us-east`` or ``eu-de``.
    - ``plans_preference``: Is a list of account types, ordered by preference. An instance of the first type in the list will be prioritized.

    For example, if ``region`` is saved as ``us-east``, only instances from ``us-east`` will be checked. If ``plans_preference`` is set, 
    the instances will be prioritized in the order given, so ``['Open', 'Premium']`` would prioritize all Open Plan instances, then all
    Premium Plan instances, and then the rest. Note that the plan names in ``plans_preference`` must exactly match the API names (case insensitive).

  - The ``instance`` input parameter of :class:`.QiskitRuntimeService` has been extended to accept  
    new input types for the  ``ibm_quantum_platform`` and ``ibm_cloud`` channels. 
    In addition to the IBM Cloud Resource Name (CRN), the instance **name** can now
    be passed in as the instance value. 

  - The :meth:`~.QiskitRuntimeService.instances` method has been extended to show all 
    available instances associated to an account for the ``ibm_quantum_platform`` and ``ibm_cloud`` 
    channels, in addition to the already enabled ``ibm_quantum`` channel.

    The following code snippets show the new usage patterns enabled by the changes described above 
    (`2239 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2239>`__):

    .. code-block:: python

      # save account
      service = QiskitRuntimeService.save_account(
        # No channel needs to be specified, ibm_quantum_platform is the default
        token=token,         
        region="eu-de", # Optional
        plans_preference=['Open',...], #Optional
        set_as_default=True  #Optional
        ) 

      # initialize account
      service = QiskitRuntimeService() # defaults to ibm_quantum_platform account
      service.backend(name="...") # picks instance based on saved preferences 
      service.backend(name="...", instance="...") # can also explicity pass in an instance to use

      # initialize account with instance
      service = QiskitRuntimeService(instance = "...") # sets instance as default instance
      service.backend(name="...") # only checks default instance, fails if the backend not in the instance
      service.backend(name="...", instance="...") # can still explicity pass in a different instance

      # OR

      # save account with instance 
      service = QiskitRuntimeService.save_account(
        # No channel needs to be specified, ibm_quantum_platform is the default
        token=token,
        instance="..." # This will be the default instance 
        region="us-east", # Optional
        plans_preference=['Open',...], #Optional
        set_as_default=True  #Optional
        ) 

      # initialize account
      service = QiskitRuntimeService() # defaults to ibm_quantum_platform account
      service.backend(name="...") # only checks saved default instance from save_account
      service.backend(name="...", instance="...") # can also explicity pass in an instance which takes precendence

      # initializing account with instance works the same way 
      service = QiskitRuntimeService(instance = "...") # sets instance as default instance, overrides instance from save_account
      service.backend(name="...") # only checks default instance, fails if the backend not in the instance
      service.backend(name="...", instance="...") # can still explicity pass in a different instance 

- The ``private`` option under :class:`EnvironmentOptions` is now supported on the 
  ``ibm_cloud`` and ``ibm_quantum_platform`` channels (new IBM Quantum Platform). When this option
  is set to ``True``, the job will be returned without parameters, and results can only
  be retrieved once. 

  There is also a new :meth:`~.RuntimeJobV2.private` property that returns whether
  or not a job is private. (`2263 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2263>`__)


Bug Fixes
---------

- The call to :meth:`~.IBMBackend.defaults` in :meth:`~.IBMBackend.target` was removed
  because backend defaults are no longer used in the target generation. (`2261 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2261>`__)

0.39.0 (2025-05-13)
===================

New Features
------------

- The maximum supported QPY service version is now 14. (`2231 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2231>`__)
- Pub inputs to :class:`~.EstimatorV2` are now subject to a new validation step that checks that observables consist of Pauli operations 
  that only contain {I, X, Y, Z}. (`2254 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2254>`__)


Bug Fixes
---------

- A new parameter ``create_new`` has been added to the :class:`.Batch` and :class:`.Session` classes. This parameter allows users to control whether the POST session API endpoint should be called when initializing the class. 
  It defaults to ``True`` as this is the case for most user-facing workflows. However, methods such as :meth:`.Session.from_id` set it to ``False`` to avoid generating a new session when the original session is still active. 
  This fixed issues where multiple sessions were generated simultaneously when calling ``.from_id()``. (`2195 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2195>`__)
- Removed the incorrect ``Optional`` type hint for the ``backend`` 
  parameter in :class:`~.Session` and :class:`~.Batch`. (`2222 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2222>`__)
- :meth:`.Session.from_id` now raises an error if the session does not have a known backend.
  This is usually the case if there haven't been any jobs run in the session yet. (`2226 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2226>`__)


Other Notes
-----------

- IBM Cloud accounts will now use an access token to call the Qiskit Runtime API instead of the 
  token provided by the user. (`2102 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2102>`__)
- :class:`.IBMInputValueError` now inherits from ``ValueError``, in addition to the existing parent class :class:`.IBMError`. 
  Some validation functions that previously raised ``ValueError`` exceptions 
  now raise :class:`.IBMInputValueError` exceptions. (`2250 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2250>`__)

0.38.0 (2025-04-15)
===================

Deprecation Notes
-----------------

- :class:`~.RuntimeJob` is now deprecated and will be removed no sooner than three months from this release. :class:`~.RuntimeJob` was superseded by :class:`~.RuntimeJobV2` in all primitive implementations, so the deprecation should not have any user impact. The major difference between the two classes is that 
  :meth:`~.RuntimeJobV2.status` returns a string instead of Qiskit's ``JobStatus`` enum. (`2170 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2170>`__)
- Since pulse gates are no longer supported, the :class:`~.IBMBackend` and :class:`~.FakeBackendV2` ``defaults()`` 
  method has been deprecated and will be removed no sooner than three months from this release. While the method still exists, these pulse defaults are no longer used to construct the backend target. (`2186 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2186>`__)
- The ``ibm_quantum`` channel option is deprecated and will be sunset on 1 July. 
  After this date, ``ibm_cloud``, ``ibm_quantum_platform``, and ``local`` will be the only valid channels. 
  For help migrating to the new IBM Quantum Platform on the 
  ``ibm_cloud`` channel, read the `migration guide <https://quantum.cloud.ibm.com/docs/migration-guides/classic-iqp-to-cloud-iqp>`__. (`2205 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2205>`__)


New Features
------------

- Attributes from the configuration of fake backends can now be retrieved directly 
  with ``backend.<attribute_name>``. (`2202 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2202>`__)


Bug Fixes
---------

- Fixed a bug where :meth:`DoubleSliceSpan.mask` and :meth:`TwirledSliceSpan.mask` error
  when they contain a one-dimensional slice. (`2184 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2184>`__)


Upgrade Notes
-------------

- Since support for streaming results was removed in ``0.32.0``, the remaining related
  websocket code has been removed. As a part of this process, the environment option
  ``callback`` is deprecated, as well as the parameters ``client_params`` and ``user_callback`` 
  in ``BaseRuntimeJob``. (`2143 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2143>`__)

0.37.0 (2025-03-13)
===================

Deprecation Notes
-----------------

- The :class:`IBMBackend` attributes ``max_shots`` and ``max_experiments``, as well as the property 
  ``max_circuits`` have all been deprecated. These attribute values used to represent the maximum number of
  shots and circuits that could be submitted in one job but that is no longer the case. See 
  the `job limits guide <https://quantum.cloud.ibm.com/docs/guides/job-limits#job-limits>`__ for details. (`2166 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2166>`__)


New Features
------------

- ``qiskit-ibm-runtime`` is now compatible with Qiskit 2.0. This means that classes and methods removed in Qiskit 2.0 have also been 
  removed or handled accordingly. The ``pulse`` and ``channel`` related changes are highlighted below: 

  - ``Channel`` methods in :class:`IBMBackend` have been removed.
  -  The backend configuration class ``PulseBackendConfiguration`` has been removed, so all backends will now be returned as ``QasmBackendConfiguration``.
  - ``PulseDefaults`` (backend defaults) can still be retrieved but they are no longer necessary when creating a backend ``Target``. 

  See the `Pulse migration guide <https://quantum.cloud.ibm.com/docs/migration-guides/pulse-migration>`__ 
  for details. (`2116 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2116>`__)
- Added a warning when a primitive is initialized outside of a session or batch context manager. 
  In this scenario, the job will run in job mode instead of the session or batch. (`2152 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2152>`__)


Bug Fixes
---------

- Fixed support for custom scheduling transpiler stages with Qiskit 2.x. (`2153 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2153>`__)
- `ConvertConditionsToIfOps <https://quantum.cloud.ibm.com/docs/api/qiskit/1.4/qiskit.transpiler.passes.ConvertConditionsToIfOps>`__ now correctly runs at
  all optimization levels of the scheduling plugins for dynamic circuits, when using Qiskit 1.x. (`2154 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2154>`__)
- When retrieving jobs with :meth:`~.QiskitRuntimeService.jobs`, there is no way to distinguish 
  between v1 and v2 primitives. Since the v1 primitives were completely removed over 6 months ago 
  in ``0.28.0``, jobs returned from ``jobs()`` will now default to :class:`RuntimeJobV2`. (`2156 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2156>`__)

0.36.1 (2025-02-14)
===================

Bug Fixes
---------

- Fixed an issue where not having ``qiskit-aer`` installed would 
  cause an import error. (`2144 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2144>`__)

0.36.0 (2025-02-14)
===================

Upgrade Notes
-------------

- The minimal required ``qiskit`` version is now 1.3.  
  Qiskit 1.3 introduces QPY version 13. The minimum required Qiskit version was raised so Qiskit Runtime could use the latest QPY version 
  for serializing circuits in job
  submissions. (`2096 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2096>`__)

- The following outdated deprecations have been removed: 

      - Support for the simulator option ``noise_model`` on cloud simulators has been removed. 
        This option will still work in local testing mode. 

      - The ``NoiseLearnerResult`` properties ``generators`` and ``rates`` have been removed. They 
        can still be accessed in the ``error`` property.

      - The utility function ``get_runtime_api_base_url()`` has been removed. (`2124 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2124>`__)

0.35.0 (2025-02-04)
===================

Upgrade Notes
-------------

- Python 3.8 reached end-of-life on Oct 7th, 2024. Qiskit SDK dropped support for 3.8 in ``qiskit 1.3``. In the same vein, ``qiskit-ibm-runtime`` does not support Python 3.8 anymore. (`2097 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2097>`__)
- Support for ``backend.run()`` has been removed. Refer to the `migration guide <https://github.com/Qiskit/documentation/blob/2d2c2fcad47dd9e7ac1cc6807527dfccd796ea24/docs/migration-guides/qiskit-runtime.mdx>`__
  for instructions to migrate any existing code that uses 
  ``backend.run()`` to the new V2 primitives interface. (`1962 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1962>`__)
- Parameter expressions with RZZ gates will be checked against the values assigned to them in the PUB. An ``IBMInputValueError`` will be raised if parameter values specified in the PUB make a parameter expression evaluate to an invalid angle (negative, or greater than ``pi/2``). (`2093 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2093>`__)
- When there is a maintenance outage, an appropriate error message will be raised when trying 
  to initialize the ``QiskitRuntimeService``. (`2100 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2100>`__)

New Features
------------

- Jobs run in the local testing mode will now return an instance of a new class, 
  :class:`.LocalRuntimeJob`. This new class inherits from Qiskit's ``PrimitiveJob`` class 
  while adding the methods and properties found in :class:`.BaseRuntimeJob`. This way, running jobs 
  in the local testing mode will be more similar to running jobs on a real backend. (`2057 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2057>`__)
- Two new fake backends, ``FakeFez`` and ``FakeMarrakesh``, have been added. These are 156-qubit Heron devices. (`2112 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2112>`__)

0.34.0 (2024-12-05)
===================

New Features
------------

- Added the ``draw_zne_evs`` and ``draw_zne_extrapolators`` functions to visualize data from
  experiments using ZNE.
  Added ``EstimatorPubResult`` with methods ``draw_zne_evs`` and 
  ``draw_zne_extrapolators``, invoking the corresponding visualization functions. (`1820 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1820>`__)
- Added support for noise model and level 1 data to local sampler

  The ``simulator.noise_model`` option of :class:`~.SamplerV2` is now passed
  through to the :class:`~qiskit.primitives.BackendSamplerV2` as a `noise_model`
  option under `run_options` if the primitive supports the `run_options` option
  (support was added in Qiskit v1.3).

  Similarly, the ``execution.meas_type`` option of :class:`~.SamplerV2` is now
  translated into ``meas_level`` and ``meas_return`` options under
  ``run_options`` of the :class:`~qiskit.primitives.BackendSamplerV2` if it
  supports ``run_options``. This change allows support for level 1 data in local
  testing mode, where previously only level 2 (classified) data was
  supported. (`1990 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1990>`__)
- A new function ``validate_rzz_pubs`` was added. The function verifies that ``rzz`` parameters are in the range between ``0`` and ``pi/2``, for numeric parameters (e.g., ``rzz(np.pi/4, 0)``), and for unbounded parameters (``rzz(theta, 0)``) with values to substitute provided in the pub. Parameter expressions (e.g., ``rzz(theta + phi, 0)``) are still not validated. (`2021 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2021>`__)
- Added a new transpiler translation plugin :class:`~.IBMFractionalTranslationPlugin` 
  and a pass :class:`~.FoldRzzAngle`.
  This plugin is automatically applied for backends
  retrieved with the ``use_fractional_gates`` opt-in,
  and the folding pass is added when the backend target includes the ``RZZ`` gate.

  The new pass modifies the input quantum circuit, so that all ``RZZ`` gates in the
  circuit have an angle parameter within [0, pi/2] which is supported 
  by IBM Quantum processors. (`2043 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2043>`__)

Upgrade Notes
-------------

- The deprecations from the ``0.26.0`` release have been removed.

  - Passing a backend as a string into ``Session``, ``Batch``, 
    ``Sampler``, and ``Estimator`` is no longer valid. Use the actual backend
    object instead.
  - Previously, passing a backend as the mode into ``SamplerV2`` or ``EstimatorV2``
    ran jobs in job mode, even if a session context manager was open. These jobs will now
    run inside of the open session. Additionally, if a backend that is different
    from the session backend is passed in as the mode, an error will be raised.
  - ``Service`` is no longer a valid parameter in ``Session`` and ``Batch``. (`2027 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2027>`__) 


Bug Fixes
---------

- Fixed an issue where ``FakeBackendV2.refresh()`` wouldn't always
  refresh the backend properties, defaults, and configuration. (`2020 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2020>`__)
- ``CouplingMap`` was added to :class:`~.RuntimeEncoder` so it can now be passed to 
  the :class:`~.NoiseLearner` program. (`2026 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2026>`__)
- The behavior of the ``use_fractional_gates`` argument of
  :meth:`.QiskitRuntimeService.backend` has been changed. When the option is set
  to ``False``, it now filters all references to fractional gates out of the
  configuration and properties data from the API. Likewise, when the option is
  set to ``True``, all dynamic circuit instructions are filtered from the
  configuration and properties data. Previously, this option only impacted the
  creation of the backend's target, which meant that the instructions in the
  target were not consistent with those in the configuration and properties data.
  For the most part, this change should be transparent to users, but if there is
  code relying on the configuration and properties data containing all
  instructions, it will need to be updated (note that setting
  ``use_fractional_gates`` to ``None`` will load all instructions without
  filtering). (`2031 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2031>`__)
- Invalid or non-existing backend configurations on the server will no longer 
  prevent all backends from being retrieved with ``service.backends()``. (`2048 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2048>`__)
- Pin ``pydantic`` dependency version to ``<2.10`` to avoid a regression breaking
  the build process. (`2049 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2049>`__)

Other Notes
-----------
  
- The ``requirements.txt`` and ``setup.py`` files have been removed in favor of a new dependency management
  approach using ``pyproject``. This transition simplifies the development workflow. Dependencies
  are now managed directly through the `pyproject.toml` file.

      - Use ``pip install -e .`` to install qiskit-ibm-runtime dependencies.
      - Use ``pip install -e ".[dev]"`` to install the development dependencies.
      - Use ``pip install -e ".[visualization]"`` to install the visualization dependencies. (`2053 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2053>`__)

0.33.2 (2024-11-11)
===================

Bug Fixes
---------

- Fixed an issue where the RZZ validation did not handle 
  parameter expressions correctly. (`2035 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2035>`__)

0.33.1 (2024-11-08)
===================

Other Notes
-----------

- Added a private alias to ``decode_backend_configuration()``. (`2028 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2028>`__)

0.33.0 (2024-11-07)
===================

New Features
------------

- Added :func:`~.draw_layer_errors_swarm` which draws a swarm plot of one or more
  :class:`~.LayerError` objects. Also added the convenience method
  :meth:`~.LayerError.draw_swarm` to invoke the drawing function on a particular instance. (`1988 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1988>`__)
- Added :class:`.TwirledSliceSpan`, an :class:`ExecutionSpan` to be used when 
  twirling is enabled in the Sampler. In particular, it keeps track of an extra shape
  axis corresponding to twirling randomizations, and also whether this axis exists at
  the front of the shape tuple, or right before the shots axis. (`2011 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2011>`__)

Upgrade Notes
-------------

- The remaining fake V1 backends - ``FakeMelbourne``, ``FakePoughkeepsie``,
  ``FakeTenerife``, ``FakeTokyo``, and ``FakeRueschlikon`` have been removed. (`2012 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2012>`__)

Bug Fixes
---------

- Fixed the location of hover text on the ``draw_execution_spans()`` function. Previous to this fix,
  they were drawn on the wrong markers. (`2014 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/2014>`__)

0.32.0 (2024-10-30)
===================

New Features
------------

- Added :func:`~.draw_execution_spans`, a function for creating a Plotly figure that 
  visualizes one or more :class:`~.ExecutionSpans` objects. Also added the convenience
  method :meth:`~.ExecutionSpans.draw` to invoke the drawing function on a 
  particular instance. (`1923 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1923>`__)

  .. code-block:: python

      from qiskit_ibm_runtime.visualization import draw_execution_spans

      # use the drawing function on spans from sampler job data
      spans1 = sampler_job1.result().metadata["execution"]["execution_spans"]
      spans2 = sampler_job2.result().metadata["execution"]["execution_spans"]
      draw_execution_spans(spans1, spans2)

      # convenience to plot just spans1
      spans1.draw() 

- Added a new method, ``backend.refresh()`` that refreshes the
  current backend target with the latest updates from the server. (`1955 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1955>`__)
- Added :class:`.DoubleSliceSpan`, an :class:`ExecutionSpan` for batching with two slices. (`1982 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1982>`__)
- Each of :class:`.SamplerV2`, :class:`.EstimatorV2`, and :class:`.noise_learner.NoiseLearner` now has
  a ``backend()`` method that returns the backend that the class is configured with. (`1995 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1995>`__)


Upgrade Notes
-------------

- Deprecations from the ``0.25.0`` release have been removed. 

      - ``optimization_level`` is no longer a valid option for ``EstimatorV2``.
      - Job methods ``interim_results()`` and ``stream_results()`` have been removed. (`1965 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1965>`__)
- The ``channel_strategy`` parameter in ``QiskitRuntimeService`` has been removed.
  To continue using Q-CTRL in your workflow, please explore the following options:

      * If your organization has an existing IBM Quantum Premium Plan instance: migrate to 
        the Q-CTRL Performance Management Function, found in the 
        `Qiskit Functions Catalog <https://quantum.ibm.com/functions>`__.

      * To continue using Qiskit Runtime with IBM Cloud: migrate to Q-CTRL Fire Opal, 
        the same performance management product accessible directly through Q-CTRL. 
        You can `connect your IBM Cloud API key and Qiskit Runtime CRN <https://docs.q-ctrl.com/fire-opal/discover/hardware-providers/how-to-authenticate-with-ibm-credentials>`__
        to Fire Opal. (`1966 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1966>`__)

0.31.0 (2024-10-15)
===================

New Features
------------

- Added Noisy Estimator Analyzer Tool (NEAT), a class to help understand the expected performance of Estimator jobs. (`1950 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1950>`__)
- Updated the ISA check to validate that the ``rzz`` angle is between ``[0, pi/2]``. (`1953 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1953>`__)

Upgrade Notes
-------------
- Fake V1 backends have been removed. (`1946 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1946>`__)

Bug Fixes
---------
- Fixed an issue with ISA validation where a change related to connectivity inside control operations was not
  applied correctly. (`1954 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1954>`__)

0.30.0 (2024-09-23)
===================

Deprecation Notes
-----------------

- The utilityy function ``get_runtime_api_base_url`` has been deprecated. Use ``default_runtime_url_resolver`` instead. (`1914 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1914>`__)
- The ``channel_strategy`` parameter has been deprecated.
  The Q-CTRL Performance Management strategy will be removed on October 18th, 2024. 
  To continue using Q-CTRL in your workflow, please explore the following options:

    * If your organization has an existing IBM Quantum Premium Plan instance: migrate to 
      the Q-CTRL Performance Management Function, found in the 
      `Qiskit Functions Catalog <https://quantum.ibm.com/functions>`__.

    * To continue using Qiskit Runtime with IBM Cloud: migrate to Q-CTRL Fire Opal, 
      the same performance management product accessible directly through Q-CTRL. 
      You can `connect your IBM Cloud API key and Qiskit Runtime CRN <https://docs.q-ctrl.com/fire-opal/discover/hardware-providers/how-to-authenticate-with-ibm-credentials>`__
      to Fire Opal. (`1931 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1931>`__)

- In a future release, ``RuntimeJob.status()`` will be returned as a string instead of 
  an instance of ``JobStatus``. (`1933 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1933>`__)


New Features
------------

- Added new methods ``Session.usage()``, ``Batch.usage()``, and ``Job.usage()`` that
  all return information regarding job and session usage.
  Please find more information `here <https://quantum.cloud.ibm.com/docs/guides/choose-execution-mode>`__. (`1827 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1827>`__)
- Added ``ConvertISAToClifford`` transpilation pass to convert the gates of a circuit to Clifford gates. (`1887 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1887>`__)
- Added ``url_resolver`` optional input to :class:`.QiskitRuntimeService`
  constructor to enable custom generation of the Qiskit Runtime API URL
  based on the provided ``url``, ``instance`` and ``private_endpoint``. If
  not specified, the default resolver will be used.

  .. code-block:: python

      # Define a custom resolver. In this case returns the concatenation of the provided `url` and the `instance`
      def custom_url_resolver(url, instance, *args, **kwargs):
        return f"{url}/{instance}"

      service = QiskitRuntimeService(channel="ibm_quantum", instance="ibm-q/open/main", url="https://baseurl.org" url_resolver=custom_url_resolver)
      # resulting resolved url will be: `https://baseurl.org/ibm-q/open/main`

- Added utility function ``default_runtime_url_resolver``. (`1914 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1914>`__)
- The ``use_fractional_gates`` flag for ``QiskitRuntimeService.backend()`` and
  ``QiskitRuntimeService.backends()`` can now be ``None``. When set to ``None``,
  no instruction filtering is done, and the returned backend target may contain
  both fractional gates and control flow operations. (`1938 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1938>`__)

Upgrade Notes
-------------

- Deprecations from the ``0.24.0`` release have been removed. The following changes have beend made.

  - The arguments backend and session for Sampler and Estimator have been removed and replaced with "mode"
  - The primitive ``Session`` property has been replaced with ``mode``
  - Specifying options without the full dictionary structure is no longer supported 
  - ``Job.program_id()`` has been replaced with ``Job.primitive_id()``
  - ``Service.run()`` and ``Session.run()`` have been replaced with a private method, ``_run()``
  - In ``Service.backend()``, "name" is now a required parameter 
  - ``Service.get_backend()`` has been removed and replaced with ``backend()`` (`1907 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1907>`__)

Bug Fixes
---------

- Fixed a bug where primitives could not be run in the session context with fractional gates. (`1922 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1922>`__)

0.29.1 (2024-09-17)
===================

New Features
------------

- Added logic to encode and decode ``NoiseLearnerResult``. (`1908 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1908>`__)

0.29.0 (2024-09-04)
===================

Deprecation Notes
-----------------

- The simulator option ``noise_model`` is now deprecated for jobs running on real devices. 
  ``noise_model`` will still be an acceptable option when using the local testing mode. (`1892 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1892>`__)


New Features
------------

- We added new classes, :class:`.ExecutionSpan` and :class:`.ExecutionSpanSet`. These classes are used in the primitive result metadata, to convey information about start and stop times of batch jobs. (`1833 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1833>`__)
- Added a new ``private`` option under :class:`EnvironmentOptions`. (`1888 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1888>`__)
- Added ``fallback`` option to ZNE extrapolators. (`1902 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1902>`__)


Bug Fixes
---------

- Ported the ``Noise_model.from_dict()`` method from ``qiskit-aer`` because it was removed 
  in ``0.15.0``. (`1890 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1890>`__)
- Revert a previous change to ``backend.target`` where the target was no longer being 
  cached. (`1891 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1891>`__)
- Fixed an issue where ``Session.from_id()`` would create 
  a new empty session. (`1896 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1896>`__)

0.28.0 (2024-08-15)
===================

New Features
------------

- ``ResilienceOptionsV2`` has a new field ``layer_noise_model``. When this field is set, all the
  mitigation strategies that require noise data skip the noise learning stage, and instead gather
  the required information from ``layer_noise_model``. (`1858 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1858>`__)


Upgrade Notes
-------------

- The V1 Primitives ``SamplerV1`` and ``EstimatorV1`` have been completely removed. Please see the
  `migration guide <https://quantum.cloud.ibm.com/docs/migration-guides/v2-primitives>`__ and use the V2 Primitives instead. (`1857 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1857>`__)
- The ``service`` parameter is now required in ``Session.from_id()``. (`1868 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1868>`__)

0.27.1 (2024-08-12)
===================

New Features
------------

- Added logic to encode and decode ``PauliLindbladError`` and ``LayerError``. (`1853 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1853>`__)

0.27.0 (2024-08-08)
===================

New Features
------------

- Added ``PauliLindbladError`` and ``LayerError`` classes to represent layers noise processes. (`1844 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1844>`__)


Bug Fixes
---------

- Fixed an issue with using the aer simulator and local service mode with sessions. (`1838 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1838>`__)

0.26.0 (2024-07-31)
===================

Deprecation Notes
-----------------

- Passing in a backend as a string into ``Session``, ``Batch``, ``EstimatorV2``, and ``SamplerV2``
  has been deprecated. Use the actual backend object instead. (`1804 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1804>`__)
- Passing a backend as the mode in :class:`SamplerV2` and :class:`EstimatorV2`
  currently runs a job in job mode even if inside of a :class:`Session` or 
  :class:`Batch` context manager. This behavior is deprecated and in a future release
  the the Session/Batch will take precedence. (`1816 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1816>`__)
- Passing in ``service`` in ``Session``, ``Batch``
  has been deprecated. The ``service`` parameter is no longer necessary because the service
  can be extracted from the backend. (`1826 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1826>`__)
- Since backend modules from ``qiskit.providers.models`` including ``BackendProperties`` and ``BackendConfiguration`` are deprecated in 
  Qiskit 1.2, they have been copied into ``qiskit-ibm-runtime``. Make sure to upgrade to the latest version, ``0.26.0``,
  to use these classes. (`1803 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1803>`__)


New Features
------------

- The methods ``properties``, ``defaults``, ``configuration``,
  and ``check_faulty`` have been added to :class:`FakeBackendV2`. (`1765 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1765>`__)
- If jobs are run in a session created with :meth:`QiskitRuntimeService.Session.from_id` where the 
  session is already closed, the jobs are rejected immediately. (`1780 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1780>`__)
- The input parameters for jobs will no longer be cached. These parameters can include large circuits
  and should not be automatically kept in memory. (`1783 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1783>`__)
- :class:`QiskitRuntimeLocalService` was created to support a local
  testing mode. To avoid having to initialize a separate class, "local"
  has been added as a valid :class:`QiskitRuntimeService` channel.

  .. code-block:: python

      service = QiskitRuntimeService(channel="local")

  will return a :class:`QiskitRuntimeLocalService` instance. (`1793 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1793>`__)
- When running jobs on the open plan, there will now be a warning if the limit for the 
  maximum number of pending jobs has been reached. The service will also attempt to wait 
  for the oldest pending jobs to finish running before submitting a new job. (`1794 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1794>`__)
- Added :class:`NoiseLearner` and related functionality, such as
  :class:`NoiseLearnerOptions` and :class:`NoiseLearnerResults`. (`1805 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1805>`__)


Bug Fixes
---------

- Every circuit is checked to be ISA compliant. As part of this check, an error is raised if instructions that are not supported by the backend are detected. Previously, a bug caused some of the instructions to be skipped (those that reside inside bodies of control flow operations). We have fixed the bug in this release. (`1784 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1784>`__)
- Fixed an issue where calling :meth:`IBMBackend.target_history` would cache the backend target and
  then calling :meth:`IBMBackend.target` would incorrectly return that cached target. (`1791 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1791>`__)
- The options validation for checking if ``zne_mitigation`` or ``pec_mitigation`` are set 
  to ``True`` when using other related options has been removed. (`1792 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1792>`__)
- Fixed an issue where users were unable to retrieve job results if 
  the python library ``simplejson`` was installed in their environment. (`1800 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1800>`__)

0.25.0 (2024-07-02)
===================

Deprecation Notes
-----------------

- The ``optimization_level`` option in ``EstimatorV2`` is deprecated.
  Instead, you can perform circuit optimization using the Qiskit transpiler or Qiskit transpiler service. (`1748 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1748>`__)
- :meth:`qiskit_ibm_runtime.RuntimeJobV2.interim_results`, :meth:`qiskit_ibm_runtime.RuntimeJobV2.stream_results`,
  :meth:`qiskit_ibm_runtime.RuntimeJob.interim_results`, and :meth:`qiskit_ibm_runtime.RuntimeJob.stream_results`
  are now all deprecated. (`1776 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1776>`__)


New Features
------------

- Added ``backend``, ``backends``, and ``least_busy`` methods to ``QiskitRuntimeLocalService``. (`1764 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1764>`__)
- Added an ``instance`` property to :class:`BaseRuntimeJob` which returns the instance
  where the job was run. (`1771 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1771>`__)
- ``default_shots`` are now a supported option when using ``EstimatorV2`` in 
  local testing mode. (`1773 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1773>`__)

0.24.1 (2024-06-18)
===================

Bug Fixes
---------

- Disallowing fractional gates by default, so backend target would not exclude control flow. (`1755 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1755>`__)

0.24.0 (2024-06-10)
===================

Deprecation Notes
-----------------

- ``name`` will now be a required parameter in 
  `backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#backend>`__.
  ``backend()`` will no longer return the first backend out of all backends if ``name`` is not provided. (`1147 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1147>`__)
- After the removal of custom programs, the following methods are being deprecated and renamed.
  :meth:`qiskit_ibm_runtime.QiskitRuntimeService.run` is deprecated and will be replaced by a private method
  :meth:`qiskit_ibm_runtime.QiskitRuntimeService._run`.

  :meth:`qiskit_ibm_runtime.Session.run` is deprecated and will be replaced by a private method
  :meth:`qiskit_ibm_runtime.Session._run`.

  :meth:`qiskit_ibm_runtime.RuntimeJob.program_id` is deprecated and will be replaced by
  :meth:`qiskit_ibm_runtime.RuntimeJob.primitive_id`. (`1238 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1238>`__)
- The ``backend`` argument in `Sampler <https://quantum.cloud.ibm.com/docs/guides/get-started-with-primitives#3-initialize-the-qiskit-runtime-sampler>`__ 
  and `Estimator <https://quantum.cloud.ibm.com/docs/guides/get-started-with-primitives#3-initialize-qiskit-runtime-estimator>`__ has been deprecated. 
  Please use ``mode`` instead.
  The ``session`` argument in `Sampler <https://quantum.cloud.ibm.com/docs/guides/get-started-with-primitives#3-initialize-the-qiskit-runtime-sampler>`__ 
  and `Estimator <https://quantum.cloud.ibm.com/docs/guides/get-started-with-primitives#3-initialize-qiskit-runtime-estimator>`__ has also been deprecated. 
  Please use ``mode`` instead. (`1556 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1556>`__)
- :meth:`qiskit_ibm_runtime.QiskitRuntimeService.get_backend` is deprecated. Please
  :meth:`qiskit_ibm_runtime.QiskitRuntimeService.backend` use instead.
  The V1 fake backends, :class:`.FakeBackend`, along with :class:`.FakeProvider` are also
  being deprecated in favor of the V2 fake backends and :class:`.FakeProviderForBackendV2`. (`1689 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1689>`__)
- Specifying options without the full dictionary structure is deprecated. Instead, pass
  in a fully structured dictionary. For example, use ``{'environment': {'log_level': 'INFO'}}``
  instead of ``{'log_level': 'INFO'}``. (`1731 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1731>`__)


New Features
------------

- Related to the execution modes, Sampler and Estimator now include a ``mode`` argument. The ``mode`` parameter
  can be a Backend, Session, Batch, or None. As a result, the backend name has been deprecated, and will
  no longer be supported as a valid execution mode. (`1556 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1556>`__)
- The `ZneOptions.amplifier` option was added, which can be one of these strings:

  * ``"gate_folding"`` (default) uses 2-qubit gate folding to amplify noise. If the noise
    factor requires amplifying only a subset of the gates, then these gates are chosen
    randomly.
  * ``"gate_folding_front"`` uses 2-qubit gate folding to amplify noise. If the noise
    factor requires amplifying only a subset of the gates, then these gates are selected
    from the front of the topologically ordered DAG circuit.
  * ``"gate_folding_back"`` uses 2-qubit gate folding to amplify noise. If the noise
    factor requires amplifying only a subset of the gates, then these gates are selected
    from the back of the topologically ordered DAG circuit. (`1679 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1679>`__)

- When saving an account, there is a new parameter, ``private_endpoint`` that if set to ``True``, allows
  users to connect to a private IBM Cloud API. This parameter can also be used when the service is initialized, for example: 
  ``QiskitRuntimeService(private_endpoint = True)``. (`1699 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1699>`__)
- New opt-in feature to support fractional gates is added to :class:`.IBMBackend`.
  IBM backends currently support dynamic circuits and fractional gates exclusively and
  the two features cannot be used in the same primitive job.
  In addition, some error mitigation protocols you can use with the estimator primitive, 
  such as PEC or PEA, may not support gate twirling with the fractional gates.
  Since Qiskit Target model doesn't represent such constraint,
  we adopted the opt-in approach, where your backend target includes only 
  fractional gates (control flow instructions) when the backend is (not) opted.
  This feature is controlled when you retrieve the target backend from the :class:`.QiskitRuntimeService`.

  .. code-block:: python

      from qiskit_ibm_runtime import QiskitRuntimeService

      backend = QiskitRuntimeService(channel="ibm_quantum").backends(
          "name_of_your_backend", 
          use_fractional_gates=True,
      )[0]

  When the fractional feature is enabled, transpiled circuits may have
  shorter depth compared with the conventional IBM basis gates, e.g. [sx, rz, ecr].

  When you use control flow instructions, e.g. ``if_else``, in your circuit,
  you must disable the fractional gate feature to get executable ISA circuits.
  The choice of the instruction set is now responsibility of users.

  Note that this pattern may be modified or removed without deprecation
  when the IBM backends is updated in future development. (`1715 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1715>`__)
- You can now use the experimental option in :class:`qiskit_ibm_runtime.options.EstimatorOptions` to enable Probabilistic Error Amplification (PEA) error mitigation method for your estimator jobs. (`1728 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1728>`__)
- Qiskit version ``1.1`` is now supported and required. (`1700 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1700>`__)

Upgrade Notes
-------------

- :meth:`.QiskitRuntimeService.backends` now always returns a
  new :class:`IBMBackend` instance even when the same query is used.
  The backend properties and defaults data are retrieved from the server
  for every instance when they are accessed for the first time,
  while the configuration data is cached internally in the service instance. (`1732 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1732>`__)


Bug Fixes
---------

- Fixed an issue where retrieving jobs with 
  `job() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#job>`__
  and `jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__
  would only return ``RuntimeJob`` instances, even if the job was run with a V2 primitive. Now, 
  V2 primitive jobs will be returned correctly as ``RuntimeJobV2`` instances. (`1471 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1471>`__)
- To avoid network disruptions during long job processes, websocket errors will no longer be raised. (`1518 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1518>`__)
- Fixed the combination of ``insert_multiple_cycles`` and ``coupling_map`` options in
  :class:`.PadDynamicalDecoupling`. This combination allows to select staggered 
  dynamical decoupling with multiple sequence cycles in each delay that crosses 
  the threshold set by ``sequence_min_length_ratios``. (`1630 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1630>`__)
- Fixed a serialization issue where decoding job metadata resulted in an error. (`1682 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1682>`__)
- Fixed measurement twirling docstring which incorrectly indicated it's enabled by default for Sampler. (`1722 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1722>`__)
- Fixed nested experimental suboptions override non-experimental suboptions. (`1731 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1731>`__)
- The backend utils method ``convert_to_target`` has been replaced with the 
  `convert_to_target <https://quantum.cloud.ibm.com/docs/api/qiskit/1.4/qiskit.providers.convert_to_target>`__ method from Qiskit.
  This fixes some issues related to target generation and calibration data. (`1600 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1600>`__)

0.23.0 (2024-04-15)
===================

Deprecation Notes
-----------------

- `backend.run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#run>`__ has been deprecated. Please use the primitives instead. More details
  can be found in the `migration guide <https://github.com/Qiskit/documentation/blob/2d2c2fcad47dd9e7ac1cc6807527dfccd796ea24/docs/migration-guides/qiskit-runtime.mdx>`__ . (`1561 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1561>`__)
- In a future release, the ``service`` parameter in `from_id() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#from_id>`__ 
  will be required. (`1311 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1311>`__)

New Features
------------

- Printing :class:`.Options` and :class:`.OptionsV2` will now be formatted as a table. (`1490 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1490>`__)
- Add ``block_ordering_callable`` argument to 
  :class:`.BlockBasePadder`, :class:`.PadDynamicalDecoupling`, :class:`.PadDelay`, and 
  :class:`.BaseDynamicCircuitAnalysis`. This allows the user to construct blocks using an algorithm of their 
  choosing. No assumptions or checks are made on the validity of the output that the ``block_ordering_callable`` produces. The motivation for this argument is
  that for some families of circuits, the existing function ``block_order_op_nodes`` can be very slow. (`1531 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1531>`__)
- The Sampler and Estimator V2 Primitives have been enhanced to incorporate custom validation procedures when
  the channel_strategy property is set as "q-ctrl."
  This customized validation logic effectively rectifies incorrect input options and safeguards users against
  inadvertently disabling Q-CTRL's performance enhancements. (`1550 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1550>`__)
- :class:`.SamplerV2` now supports twirling.
  Twirling will only be applied to those measurement registers not involved within a conditional logic. (`1557 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1557>`__)
- Session `details() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#details>`__ 
  now includes a new field, ``usage_time``. Usage is defined as the time a quantum system 
  is committed to complete a job. (`1567 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1567>`__)


Bug Fixes
---------

- :class:`.RuntimeJobV2` will no longer 
  error when the API returns an unknown status. Instead, the status 
  from the API will directly be returned. (`1476 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1476>`__)
- Fixed a bug where custom headers were not being sent in the ``/jobs`` request. (`1508 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1508>`__)
- Fixed a bug with encoding/decoding ``ParameterExpression``. (`1521 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1521>`__)
- Fixed an issue where the `in_final_state() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-job-v2#in_final_state>`__ 
  method in :class:`.RuntimeJobV2` would not
  update the status when called. (`1547 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1547>`__)

0.22.0 (2024-03-21)
===================

Upgrade Notes
-------------

- Modify ``skip_reset_qubits`` optional flag to the constructor for
  :class:`.PadDynamicalDecoupling`. If ``False``, dynamical decoupling is applied on 
  qubits regardless of their state, even on delays that are at the beginning 
  of a circuit. This option now matches the behavior in Qiskit. (`1409 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1409>`__)


New Features
------------

- A new local testing mode is added. It allows you to
  validate your quantum prorams before sending them to a physical system.
  The local testing mode is activated if one of the fake
  backends in ``qiskit_ibm_runtime.fake_provider`` or a Qiskit Aer backend
  instance is used when instantiating a primitive or a session. (`1495 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1495>`__)


Bug Fixes
---------

- Fix a bug that caused setting of ``resilience_level=0`` in ``EstimatorV2``
  to be ignored (and the default value used instead). (`1541 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1541>`__)

0.21.2 (2024-03-18)
===================

Bug Fixes
---------

- Fixed a bug where ``RuntimeDecoder`` could import arbitrary classes. (`1527 <https://github.com/Qiskit/qiskit-ibm-runtime/pull/1527>`__)

0.21.1
======

Bug Fixes
---------

-  Fixed a bug where ``SamplerV1`` and ``EstimatorV1`` could not be
   imported because of an issue with how the aliases were defined.

0.21.0
======

Upgrade Notes
-------------

-  Circuits that do not match the target hardware definition are no
   longer supported by Qiskit Runtime primitives, unless
   ``channel_strategy="q-ctrl"`` is used. See the transpilation
   documentation (`transpile <https://quantum.cloud.ibm.com/docs/guides/transpile>`__) for instructions to
   transform circuits and the primitive examples
   (`run/primitives-examples <https://quantum.cloud.ibm.com/docs/guides/primitives-examples>`__) to see this
   coupled with operator transformations.

Deprecation Notes
-----------------

-  In a future release, ``backend`` will be a required parameter for
   ``qiskit_ibm_runtime.Sampler``, and ``qiskit_ibm_runtime.Estimator``
   if ``session`` is not specified, even when using the ``ibm_cloud``
   channel.

   It will also be a required parameter for
   ``qiskit_ibm_runtime.Session`` and ``qiskit_ibm_runtime.Batch``.

Bug Fixes
---------

-  Fixed an issue with the ``IBMBackend.target`` where it would
   incorrectly exclude supported control flow operations (``IfElseOp``,
   ``WhileLoop``, etc.) if a given backend supported them.

-  Fixed a bug where retrieving a fake backend through
   ``FakeProviderForBackendV2.backend()`` would result in a type error.

-  Fixes the check for ISA circuits to allow pulse gates and circuits
   that don’t have layout.

0.20.0
======

New Features
------------

-  Add ``dd_barrier`` optional input to
   `PadDynamicalDecoupling <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/transpiler-passes-scheduling-pad-dynamical-decoupling>`__
   constructor to identify portions of the circuit to apply dynamical
   decoupling (dd) on selectively. If this string is contained in the
   label of a barrier in the circuit, dd is applied on the delays ending
   with it (on the same qubits); otherwise, it is not applied.

-  Python 3.12 is now supported.

-  Sessions will now be started with a new ``/sessions`` endpoint that
   allows for different execution modes. Batch mode is now supported
   through ``Batch``, and `Session <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session>`__
   will work the same as way as before. Please see
   `run/sessions <https://quantum.cloud.ibm.com/docs/guides/execution-modes#session-mode>`__ for more information.

   Note that ``Session`` and ``Batch`` created from
   ``qiskit-ibm-runtime`` prior to this release will no longer be
   supported after March 31, 2024. Please update your
   ``qiskit-ibm-runtime`` version as soon as possible before this date.

   Also note that using simulators with sessions is no longer supported.
   Users can still start sessions with simulators without any issues but
   a session will not actually be created. There will be no session ID.

-  Sessions started with
   `qiskit_ibm_runtime.IBMBackend.open_session() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.34/ibm-backend#open_session>`__
   will use the new ``/sessions`` endpoint.

   The sessions functionality will not change but note that
   ``backend.run()`` sessions prior to this release will no longer be
   supported after March 31, 2024. Please update your
   ``qiskit-ibm-runtime`` version as soon as possible before this date.

Deprecation Notes
-----------------

-  Circuits that do not match the target hardware definition will no
   longer be supported after March 1, 2024. See the transpilation
   documentation (`transpile <https://quantum.cloud.ibm.com/docs/guides/transpile>`__) for instructions to
   transform circuits and the primitive examples
   (`run/primitives-examples <https://quantum.cloud.ibm.com/docs/guides/primitives-examples>`__) to see this
   coupled with operator transformations.

Bug Fixes
---------

-  Fix assignment of instruction durations when scheduling circuits with
   control flow. Prior to this fix, the indices for instructions on
   inner blocks were not mapped to the physical indices in the outer
   dag.

Other Notes
-----------

-  The ``InstructionDurations`` durations input is now also required for
   the constructor of ``PadDelay``.

0.19.1
======

Upgrade Notes
-------------

-  Extend ``DynamicCircuitInstructions.from_backend()`` to extract and
   patch durations from both ``BackendV1`` and ``BackendV2`` objects.
   Also add ``DynamicCircuitInstructions.from_target()`` to use a
   ``Target`` object instead.

Bug Fixes
---------

-  Fix the patching of ``DynamicCircuitInstructions`` for instructions
   with durations that are not in units of ``dt``.

-  Fixed an issue with the ``qpy.dump()`` function, when the
   ``use_symengine`` flag was set to a truthy object that evaluated to
   ``True`` but was not actually the boolean ``True`` the generated QPY
   payload would be corrupt.

0.19.0
======

Upgrade Notes
-------------

-  qiskit-ibm-provider is pending deprecation, and therefore will no
   longer be a dependency for qiskit-ibm-runtime.

-  qiskit-ibm-runtime is now compatible with Qiskit versions >= 0.45,
   including 1.0.0.

0.18.0
======

New Features
------------

-  Added a new parameter, dynamic_circuits to
   `backends() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#backends>`__
   to allow filtering of backends that support dynamic circuits.

-  Added ``max_time`` parameter to ``IBMBackend.open_session()``.

-  Added a method ``RuntimeJob.queue_info()`` to get the queue
   information from the backend. This feature was transferred from
   ``qiskit_ibm_provider``.

Deprecation Notes
-----------------

-  ``QiskitRuntimeService.runtime()`` has been deprecated.

Bug Fixes
---------

-  Many methods in `RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__
   require retrieving the job data from the API with ``job_get()``. This
   API call will now exclude the ``params`` field by default because
   they are only necessary in
   `qiskit_ibm_runtime.RuntimeJob.inputs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#inputs>`__.

0.17.0
======

New Features
------------

-  Added a new method
   `properties() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#properties>`__ which
   returns the backend properties of the job at the time the job was
   run.

-  `details() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#details>`__ has a new
   field, activated_at, which is the timestamp of when the session was
   changed to active.

Bug Fixes
---------

-  When a single backend is retrieved with the ``instance`` parameter,

   .. code:: python

      service.backend('ibm_torino', instance='ibm-q/open/main')
      # raises error if torino is not in ibm-q/open/main but in a different instance
      # the user has access to
      service = QiskitRuntimeService(channel="ibm_quantum", instance="ibm-q/open/main")
      service.backend('ibm_torino') # raises the same error

   if the backend is not in the instance but in a different one the user
   has access to, an error will be raised. The same error will now be
   raised if an instance is passed in at initialization and then a
   backend not in that instance is retrieved.

-  Fixed an issue where retrieving the coupling_map of some backends
   would result in a NameError.

0.16.0
======

Prelude
-------

Sessions are now thread-safe and allow for multiple concurrent
interactive experiments.

New Features
------------

-  Sessions are now thread-safe.

Upgrade Notes
-------------

-  Methods related to using custom programs are removed.

Bug Fixes
---------

-  If a cloud instance that is ``q-ctrl`` enabled is used while
   ``q-ctrl`` is not passed in as the ``channel_strategy``, an error
   will be raised.

0.15.1
======

Bug Fixes
---------

-  Reverting 0.15.0 changes to
   `from_id() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#from_id>`__ because it was
   a breaking change without proper deprecation.

0.15.0
======

New Features
------------

-  A new module
   `qiskit_ibm_runtime.fake_provider <fake_provider#module-qiskit_ibm_runtime.fake_provider>`__,
   has been added to provide access to a series of fake backends derived
   from snapshots of IBM Quantum devices. This functionality was
   originally provided by the ``qiskit.providers.fake_provider`` module,
   but will soon be deprecated in favor of
   `qiskit_ibm_runtime.fake_provider <fake_provider#module-qiskit_ibm_runtime.fake_provider>`__.

   The snapshots provided by the fake backends are useful for local
   testing of the transpiler and performing local noisy simulations of
   the system before running on real devices. Here is an example of
   using a fake backend for transpilation and simulation:

   .. code:: python

      from qiskit import QuantumCircuit
      from qiskit import transpile
      from qiskit_ibm_runtime.fake_provider import FakeManilaV2

      # Get a fake backend from the fake provider
      backend = FakeManilaV2()

      # Create a simple circuit
      circuit = QuantumCircuit(3)
      circuit.h(0)
      circuit.cx(0,1)
      circuit.cx(0,2)
      circuit.measure_all()

      # Transpile the ideal circuit to a circuit that can be directly executed by the backend
      transpiled_circuit = transpile(circuit, backend)

      # Run the transpiled circuit using the simulated fake backend
      job = backend.run(transpiled_circuit)
      counts = job.result().get_counts()

-  Added support for ``backend.run()``. The functionality is similar to
   that in ``qiskit-ibm-provider``.

-  An error will be raised during initialization if ``q-ctrl`` is passed
   in as the ``channel_strategy`` and the account instance does not have
   ``q-ctrl`` enabled.

-  Removed storing result in ``RuntimeJob._results``. Instead retrieve
   results every time the ``results()`` method is called.

Deprecation Notes
-----------------

-  Usage of the ``~/.qiskit/qiskitrc.json`` file for account information
   has been deprecated. Use ``~/.qiskit/qiskit-ibm.json`` instead.

Bug Fixes
---------

-  Fixed an issue where canceled and failed jobs would return an invalid
   result that resulted in a type error, preventing the actual error
   from being returned to the user.

-  A warning will be raised at initialization if the DE environment is
   being used since not all features are supported there.

-  The ``backend`` parameter in
   `from_id() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#from_id>`__ is being
   deprecated because sessions do not support multiple backends.
   Additionally, the ``service`` parameter is no longer optional.

-  The ``circuit_indices`` and ``observable_indices`` run inputs for
   `Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__ and
   `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ have been completely
   removed.

Other Notes
-----------

-  Added migration code for running ``backend.run`` in
   qiskit_ibm_runtime instead of in qiskit_ibm_provider.

0.14.0
======

New Features
------------

-  There is a new class, ``qiskit_ibm_runtime.Batch`` that currently
   works the same way as
   `qiskit_ibm_runtime.Session <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session>`__ but
   will later be updated to better support submitting multiple jobs at
   once.

-  Arbitrary keys and values are no longer allowed in ``Options``.

Deprecation Notes
-----------------

-  Custom programs are being deprecated as of qiskit-ibm-runtime 0.14.0
   and will be removed on November 27, 2023. Users can instead convert
   their custom programs to use Qiskit Runtime primitives with Qiskit
   Serverless. Refer to the migration guide for instructions:
   https://qiskit.github.io/qiskit-serverless/migration/migration_from_qiskit_runtime_programs.html

0.13.0
======

New Features
------------

-  Added a new method,
   `details() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#details>`__ that returns
   information about a session, including: maximum session time, active
   time remaining, the current state, and whether or not the session is
   accepting jobs.

   Also added `status() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#status>`__,
   which returns the current status of the session.

-  At initialization, if not passed in directly, the default
   ``instance`` selected by the provider will be logged at the “INFO”
   level. When running a job, if the backend selected is not in the
   default instance but in a different instance the user also has access
   to, that instance will also be logged.

Upgrade Notes
-------------

-  `qiskit_ibm_runtime.Session.close() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#close>`__
   has been updated to mark a ``Session`` as no longer accepting new
   jobs. The session won’t accept more jobs but it will continue to run
   any queued jobs until they are done or the max time expires. This
   will also happen automatically when the session context manager is
   exited. When a session that is not accepting jobs has run out of jobs
   to run, it’s immediately closed, freeing up the backend to run more
   jobs rather than wait for the interactive timeout.

   The old close method behavior has been moved to a new method,
   `qiskit_ibm_runtime.Session.cancel() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session#cancel>`__,
   where all queued jobs within a session are cancelled and terminated.

Bug Fixes
---------

-  Fixed a bug where ``shots`` passed in as a numpy type were not being
   serialized correctly.

-  Fixed a bug in
   `target_history() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#target_history>`__
   where the datetime parameter was not being used to retrieve backend
   properties from the specified date.

0.12.2
======

New Features
------------

-  If using a ``channel_strategy``, only backends that support that
   ``channel_strategy`` will be accessible to the user.

-  Added the option to define a default account in the account json
   file. To select an account as default, define ``set_as_default=True``
   in ``QiskitRuntimeService.save_account()``.

-  Added new method ``Session.from_id`` which creates a new session with
   a given id.

-  There will now be a warning if a user submits a job that is predicted
   to exceed their system execution time monthly quota of 10 minutes.
   This only applies to jobs run on real hardware in the instance
   ``ibm-q/open/main``. If the job does end up exceeding the quota, it
   will be canceled.

Upgrade Notes
-------------

-  Job error messages now include the error code. Error codes can be
   found in `errors <https://quantum.cloud.ibm.com/docs/errors>`__.

0.12.1
======

New Features
------------

-  Users can use a new environment variable, ``USAGE_DATA_OPT_OUT`` to
   opt out of user module usage tracking by setting this value to
   ``True``. Additionally, only certain qiskit modules will be tracked
   instead of all modules that begin with qiskit or qiskit\_.

-  Users can now pass in a value of ``default`` to the
   ``channel_strategy`` parameter in
   `qiskit_ibm_runtime.QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__.
   Now, if an account is configured with a certain channel strategy, the
   user can override it by passing in ``default``.

-  The Sampler and Estimator primitives have been enhanced to
   incorporate custom validation procedures when the channel_strategy
   property within the :class:qiskit_ibm_runtime.QiskitRuntimeService is
   configured as “q-ctrl.” This customized validation logic effectively
   rectifies incorrect input options and safeguards users against
   inadvertently disabling Q-CTRL’s performance enhancements.

Bug Fixes
---------

-  Retrieving backend properties with
   `properties() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#properties>`__ now
   supports passing a ``datetime`` parameter to retrieve properties from
   a past date.

-  The ``noise_factors`` and ``extrapolator`` options in
   ``qiskit_ibm_runtime.options.ResilienceOptions``
   will now default to ``None`` unless ``resilience_level`` is set to 2.
   Only options relevant to the resilience level will be set, so when
   using ``resilience_level`` 2, ``noise_factors`` will still default to
   ``(1, 3, 5)`` and ``extrapolator`` will default to
   ``LinearExtrapolator``. Additionally, options with a value of
   ``None`` will no longer be sent to the server.

-  Job error messages will no longer be returned in all uppercase.

-  The max_execution_time option is now based on system execution time
   instead of wall clock time. System execution time is the amount of
   time that the system is dedicated to processing your job. If a job
   exceeds this time limit, it is forcibly cancelled. Simulator jobs
   continue to use wall clock time.

0.12.0
======

New Features
------------

-  Added a ``global_service``, so that if the user defines a
   QiskitRuntimeService, it will be used by the primitives, even if the
   service is not passed to them explicitly. For example:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
      service = QiskitRuntimeService(channel="ibm_quantum")
      # Sampler._service field will be initialized to ``service``
      sampler = Sampler(backend="ibmq_qasm_simulator")

-  Added a new method,
   `qiskit_ibm_runtime.QiskitRuntimeService.instances() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#instances>`__
   that returns all instances(hub/group/project) the user is in. This is
   only for the ``ibm_quantum`` channel since the ``ibm_cloud`` channel
   does not have multiple instances.

-  Added validations for options on the second level of the dict, i.e.,
   for each of resilience, simulator, execution, and transpilation,
   check that their options are supported. Otherwise throw an exception.

-  There is a new parameter, ``channel_strategy`` that can be set in the
   initialization of
   `qiskit_ibm_runtime.QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   or saved in
   `qiskit_ibm_runtime.QiskitRuntimeService.save_account() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#save_account>`__.
   If ``channel_strategy`` is set to ``q-ctrl``, all jobs within the
   service will use the Q-CTRL error mitigation strategy.

Upgrade Notes
-------------

-  Circuits and other input parameters will no longer be automatically
   stored in runtime jobs. They can still be retrieved with
   `qiskit_ibm_runtime.RuntimeJob.inputs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#inputs>`__.


Deprecation Notes
-----------------

-  The ``noise_amplifier`` resilience options is deprecated. After the
   deprecation period, only local folding amplification will be
   supported. Refer to https://github.com/qiskit-community/prototype-zne
   for global folding amplification.

Bug Fixes
---------

-  When running on channel “ibm_cloud”, it is possible not to specify
   the backend. In this case, the system selects one of the available
   backends for this service. Issue #625
   https://github.com/Qiskit/qiskit-ibm-runtime/issues/625 reported that
   the the backend returned by ``job.backend()`` was not always the
   actual backend on which the job was run. This PR fixes this bug.

-  Fixes a race condition in the test test_cancel_running_job() in
   test_job.py where job cancellation could not be performed. Refer to
   #1019 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/1019>\_
   for more details.

-  Previously we added validation when jobs were run to make sure the
   number of circuits was not greater than the maximum for that backend,
   ``backend.max_circuits``. This limit isn’t actually necessary for
   primtives run from within a session.

0.11.3
======

New Features
------------

-  Added reason for failure when invoking the method
   `error_message() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#error_message>`__.

-  Added a new property,
   `usage_estimation() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#usage_estimation>`__
   that returns the estimated system execution time,
   ``quantum_seconds``. System execution time represents the amount of
   time that the system is dedicated to processing your job.

-  Raise an exception if the number of circuits passed to
   ``_run_primitive()`` exceeds the number of circuits supported on the
   backend.

-  There is a new method
   `update_tags() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#update_tags>`__
   that can be used to update the ``job_tags`` of a job.

-  If ``instance`` is provided as parameter to
   `qiskit_ibm_runtime.QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__,
   then this is used as a filter in ``QiskitRuntimeService.backends()``.
   If ``instance`` is not recognized as one of the provider instances,
   an exception will be raised. Previously, we only issued a warning.

0.11.2
======

New Features
------------

-  If a job has been cancelled, and job.result() is requested, throw an
   exception rather than returning None.

-  A new method,
   `qiskit_ibm_runtime.options.SimulatorOptions.set_backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/options-simulator-options#set_backend>`__,
   allows users to more easily set simulator options for a backend.

   .. code:: python

      from qiskit.providers.fake_provider import FakeManila
      from qiskit_aer.noise import NoiseModel

      # Make a noise model
      fake_backend = FakeManila()

      # Set options to include the noise model
      options = Options()
      options.simulator.set_backend(fake_backend)
      options.simulator.seed_simulator = 42

Bug Fixes
---------

-  Fixed infinite recursion when attempting to deepcopy an IBMBackend.
   Added a method ``qiskit_ibm_runtime.IBMBackend.deepcopy()``.

-  Fixed an issue where circuit metadata was not being serialized
   correctly resulting in a type error.

0.11.1
======

Deprecation Notes
-----------------

-  In
   `qiskit_ibm_runtime.RuntimeJob.metrics() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#metrics>`__,
   the bss field will be replaced by usage.

0.11.0
======

New Features
------------

-  When retrieving a job with
   ``qiskit_ibm_runtime.IBMRuntimeService.job()`` the ``params`` will no
   longer be returned from the API. They will instead be loaded loazily
   when they are actually needed in
   `qiskit_ibm_runtime.RuntimeJob.inputs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#inputs>`__.

-  Added warning when the backend is not active in
   QiskitRuntimeService.run.

-  Support input of type ``CouplingMap`` when given as simulator option.
   Previously we supported, for example:

   .. code:: python

      options.simulator = {"coupling_map": [[0, 1], [1, 0]]}

   Now we also support the following:

   .. code:: python

      options.simulator = {"coupling_map": CouplingMap.from_line(10)}

Upgrade Notes
-------------

-  A default session is no longer open for you if you pass a backend
   name or backend instance to
   `qiskit_ibm_runtime.Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ or
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   constructors. The primitive will instead run without a session. In
   addition, you should now use the ``backend`` parameter to pass a
   backend name or instance instead of the ``session`` parameter (which
   can continue to be used to pass a session).

-  The first parameter of the
   `qiskit_ibm_runtime.Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ and
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   constructors is now ``backend`` instead of ``session``.

Deprecation Notes
-----------------

-  Passing a backend name or backend instance to the ``session``
   parameter when initializing a
   `qiskit_ibm_runtime.Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ or
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   has been deprecated. Please use the ``backend`` parameter instead.
   You can continue to pass a session using the ``session`` parameter.

0.10.0
======

New Features
------------

-  Python 3.11 is now supported.

Upgrade Notes
-------------

-  Added error messages in case the user defines unsupported values for
   ‘max_execution_time’. Previously, this validation was done on the
   server side.

Bug Fixes
---------

-  Added deserialization of the params of RuntimeJob.inputs. Previously,
   the circuits were returned in serialized format. Fixes issue
   `#829 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/829>`__.

-  Allow for users to retrieve all backends even if one of the backends
   has a missing configuration. The backend without a configuration will
   not be returned.

0.9.4
=====

New Features
------------

-  Added methods to validate input options to ``transpilation`` and
   ``environment`` options.

Upgrade Notes
-------------

-  When constructing a backend ``qiskit.transpiler.Target``, faulty
   qubits and gates from the backend configuration will be filtered out.

Deprecation Notes
-----------------

-  The deprecated arguments ``circuits``, ``parameters``, ``service``,
   and ``skip_transpilation`` have been removed from
   `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__.

   Similarly, the deprecated arguments ``circuits``, ``observables``,
   ``parameters``, ``service``, and ``skip_transpilation`` have been
   removed from `Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__.

   In
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__,
   the ``auth`` parameter has been removed. Additionally, the
   ``instance``, ``job_tags``, and ``max_execution_time`` paramters have
   been removed from
   `qiskit_ibm_runtime.QiskitRuntimeService.run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#run>`__.
   They can be passed in through
   ``RuntimeOptions`` instead.

   Within ``RuntimeOptions``
   ``backend_name`` is no longer supported. Please use ``backend``
   instead.

Bug Fixes
---------

-  Fixed a bug where retrieving a job from a backend without
   ``noise_model`` or ``seed_simulator`` options would result in a key
   error.

0.9.3
=====

Upgrade Notes
-------------

-  Added error messages in case the user defines unsupported values for
   ‘optimization_level’ or for ‘resilience_level’. Added validation
   checking for options given as input to ``resilience``. Previously,
   this validation was done on the server side. By adding them on the
   client side, response will be much faster upon failure. The
   environment variable ``QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION`` is
   used to control validation. If set, validation will be skipped.

-  Backend configurations are no longer loaded when
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   is initialized. Instead, the configuration is only loaded and cached
   during
   `get_backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#get_backend>`__
   and
   `backends() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#backends>`__.

Bug Fixes
---------

-  When creating an Option object and passing an input option to
   ``resilience_options``, this option was included in
   ``resilience_options``, but the other, default options were removed.
   This was fixed, so now inputs are handled correctly, like other
   option types.

0.9.2
=====

New Features
------------

-  Added a new argument called ``session_time`` to the program_run
   method and
   ``qiskit_ibm_runtime.RuntimeOptions``.
   Now values entered by the user for session ``max_time`` will be sent
   to the server side as ``session_time``. This allows users to specify
   different values for session ``max_time`` and ``max_execution_time``.

-  Added the method
   `target_history() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#target_history>`__.
   This method is similar to
   `target() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#target>`__. The
   difference is that the new method enables the user to pass a datetime
   parameter, to retrieve historical data from the backend.

Upgrade Notes
-------------

-  Accept all options on given on level 1 and assign them to the
   appropriate hierarchical option type. For example, if the user
   provides ``options = {"shots": 10}`` as input to Sampler/Estimator,
   this will be interpreted as
   ``options = {"execution: {"shots": 10}}``.

-  If a job is returned without a backend, retrieving the backend
   through
   `qiskit_ibm_runtime.RuntimeJob.backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#backend>`__
   will re-retrieve data from the server and attempt to update the
   backend. Additionally, ``job_id`` and ``backend``, which were
   deprecated attributes of
   `qiskit_ibm_runtime.RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__
   have now been removed.

-  Added a user warning when the user passes an option that is not
   supported in Options.

Bug Fixes
---------

-  Fixed a bug where the default values for ``optimization_level`` and
   for ``resilience_level`` were not being set correctly.

-  Fixed an issue where if no backend was selected,
   ``optimization_level`` and ``resilience_level`` would default to
   ``None``, causing the job to fail.

-  If an instance is passed in to
   `qiskit_ibm_runtime.QiskitRuntimeService.get_backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#get_backend>`__
   and then the backend is used in a session, all jobs within the
   session will be run from the original instance passed in.

-  Removed additional decomposition of ``BlueprintCircuit``\ s in the
   JSON encoder. This was introduced as a bugfix, but has since been
   fixed. Still doing the decomposition led to possible problems if the
   decomposed circuit was not in the correct basis set of the backend
   anymore.

0.9.1
=====

Upgrade Notes
-------------

-  `qiskit_ibm_runtime.QiskitRuntimeService.jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__
   now has a ``backend_name`` parameter that can be used to only return
   jobs run with the specified backend.

-  Allow the user to store account details in a file specified by the
   user in the parameter. ``filename``. The default remains
   ~/.qiskit/qiskit-ibm.json. Example of usage: Ex:

   .. code:: python

      QiskitRuntimeService.save_account(channel="ibm_quantum",
                                        filename="~/my_account_file.json",
                                        name = "my_account",
                                        token="my_token")
      service = QiskitRuntimeService(channel="ibm_quantum", 
                                     filename="~/my_account_file.json", 
                                     name = "my_account",)

Deprecation Notes
-----------------

-  ``backend`` is no longer a supported option when using
   `qiskit_ibm_runtime.Session.run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/session#run>`__.
   Sessions do not support multiple cross backends. Additionally, an
   exception will be raised if a backend passed in through options does
   not match the original session backend in an active session.

Bug Fixes
---------

-  ``ECRGate`` and ``CZGate`` mappings have been added to the ``Target``
   constructor to fix a tranpile bug.

Other Notes
-----------

-  Since error messages from a failing job may be long, we shortened
   them so that they begin from the last ``Traceback`` in the message.

0.9.0
=====

Upgrade Notes
-------------

-  Changed the default values for ``optimization_level`` and for
   ``resilience_level`` in ``qiskit_ibm_runtime.Options``. If their
   values are defined by the user, they are not modified. If not set, if
   the backend is a noiseless simulator then ``optimization_level`` is
   set to 1 and ``resilience_level`` is set to 0; Otherwise, they are be
   set to 3 and 1 respectively.

-  `session_id() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#session_id>`__ and
   `tags() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#tags>`__ were added for an
   easy way to return the session_id and job_tags of a job.

Bug Fixes
---------

-  Fixed a bug where jobs that did not run before a session closes are
   not actually run as a part of that session. Jobs should run as a part
   of a session even if that session is closed by the exit of the
   context manager.

-  Fixes the issue wherein submitting a large job fails due to write
   operation timeout.

0.8.0
=====

New Features
------------

-  Python 3.10 is now supported.

-  Advanced resilience options can now be set under
   ``options.resilience``. See
   ``qiskit_ibm_runtime.options.ResilienceOptions``
   for all available options.

-  You can now specify a pair of result decoders for the
   ``result_decoder`` parameter of
   `qiskit_ibm_runtime.QiskitRuntimeService.run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#run>`__
   method. If a pair is specified, the first one is used to decode
   interim results and the second the final results.

Upgrade Notes
-------------

-  The default ``resilience_level`` option for has been changed from 0
   to 1. In addition, the default ``optimization_level`` option has been
   changed from 1 to 3.

Deprecation Notes
-----------------

-  The transpilation options ``translation_method`` and
   ``timing_constraints`` have been deprecated.

Bug Fixes
---------

-  If a
   `qiskit_ibm_runtime.IBMBackend <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend>`__
   instance is passed to the
   `qiskit_ibm_runtime.Session <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session>`__
   constructor, the service used to initialize the ``IBMBackend``
   instance is used for the session instead of the default account
   service.

0.7.0
=====

New Features
------------

-  ``qiskit_ibm_runtime.Options`` class now accepts arbitrary keyword
   arguments. This allows users to specify new options to the primitive
   programs without upgrading ``qiskit_ibm_runtime``. These arbitrary
   keyword arguments, however, are not validated.

-  The
   `qiskit_ibm_runtime.options.EnvironmentOptions <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/options-environment-options>`__
   class now accepts a ``callback`` parameter. This parameter can be
   used to stream the interim and final results of the primitives.

-  The ``qiskit_ibm_runtime.Options`` class now accepts
   ``max_execution_time`` as a first level option and ``job_tags`` as an
   option under ``environment``.
   ``qiskit_ibm_runtime.RuntimeOptions``
   has also been updated to include these two parameters.

Upgrade Notes
-------------

-  This version of qiskit-ibm-runtime requires qiskit-terra version 0.22
   or higher. The ``requirements.txt`` file has been updated
   accordingly.

Deprecation Notes
-----------------

-  Qiskit Runtime programs ``torch-train``, ``torch-infer``,
   ``sample-expval``, ``sample-program``, and
   ``quantum_kernal_alignment`` have been deprecated due to low usage.

-  Passing ``instance`` parameter to the
   `qiskit_ibm_runtime.QiskitRuntimeService.run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#run>`__
   has been deprecated. Instead, you can pass the ``instance`` parameter
   inside the ``options`` parameter.

-  Passing ``job_tags`` and ``max_execution_time`` as parameters to
   `qiskit_ibm_runtime.QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   has been deprecated. Please pass them inside ``options``.

Bug Fixes
---------

-  Fixes the missing section on retrieving jobs in the how-to guide.

0.7.0rc2
========

Upgrade Notes
-------------

-  Added a validation check to
   ``Sampler.run()``. It raises an error if
   there is no classical bit.

-  `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ is updated to return
   ``SamplerResult`` with ``SamplerResult.quasi_dists`` as a list of
   ``QuasiDistrbution``. It used to set a list of ``dict`` as
   ``SamplerResult.quasi_dists``, but it did not follow the design of
   ``SamplerResult``.

-  The `RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__ class is now a
   subclass of ``qiskit.providers.Job``.

Deprecation Notes
-----------------

-  ``job_id`` and ``backend`` attributes of
   `qiskit_ibm_runtime.RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__
   have been deprecated. Please use
   `qiskit_ibm_runtime.RuntimeJob.job_id() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#job_id>`__
   and
   `qiskit_ibm_runtime.RuntimeJob.backend() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#backend>`__
   methods instead.

-  The ``backend_name`` attribute in
   ``qiskit_ibm_runtime.RuntimeOptions``
   is deprecated and replaced by ``backend``.

0.7.0rc1
========

Prelude
-------

There are significant changes to how primitives are invoked within a
session, and the options available to the primitives. Please review the
rest of the release notes and the tutorials for full information.

New Features
------------

-  You can now invoke the same or different primitive programs multiple
   times within a session. For example:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
      from qiskit.test.reference_circuits import ReferenceCircuits
      from qiskit.circuit.library import RealAmplitudes
      from qiskit.quantum_info import SparsePauliOp

      # Initialize account.
      service = QiskitRuntimeService()

      # Set options, which can be overwritten at job level.
      options = Options(optimization_level=1)

      # Prepare inputs.
      bell = ReferenceCircuits.bell()
      psi = RealAmplitudes(num_qubits=2, reps=2)
      H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
      theta = [0, 1, 1, 2, 3, 5]

      with Session(service=service, backend="ibmq_qasm_simulator") as session:
          # Submit a request to the Sampler primitive within the session.
          sampler = Sampler(session=session, options=options)
          job = sampler.run(circuits=bell)
          print(f"Sampler results: {job.result()}")

          # Submit a request to the Estimator primitive within the session.
          estimator = Estimator(session=session, options=options)
          job = estimator.run(
              circuits=[psi], observables=[H1], parameter_values=[theta]
          )
          print(f"Estimator results: {job.result()}")

-  A new ``qiskit_ibm_runtime.Options`` class is introduced. This class
   allows you to auto-complete options related to primitive programs.
   For example:

   .. code:: python

      from qiskit_ibm_runtime import Session, Sampler, Options
      from qiskit.test.reference_circuits import ReferenceCircuits

      options = Options()
      options.optimization_level = 3  # This can be done using auto-complete.

      with Session(backend="ibmq_qasm_simulator") as session:
        # Pass the options to Sampler.
        sampler = Sampler(session=session, options=options)

        # Or at job level.
        job = sampler.run(circuits=ReferenceCircuits.bell(), shots=4000)

-  `qiskit_ibm_runtime.RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__
   has a new method
   `metrics() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#metrics>`__. This
   method returns the metrics of a job, which includes timestamp
   information.

-  The
   `qiskit_ibm_runtime.QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   ``channel`` can now be stored as an environment variable,
   ``QISKIT_IBM_CHANNEL``. This way, when using Runtime Primitives, the
   service does not have to be instantiated manually and can instead be
   created directly from environment variables.

Upgrade Notes
-------------

-  Raise ``RuntimeJobMaxTimeoutError`` when a job runs for too long so
   that it can be handled appropriately by programs.

-  The experimental parameters ``transpilation_settings``,
   ``resilience_settings``, and ``max_time`` to the
   :class:\`qiskit_ibm_runtime.Sampler and
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   constructors have been removed. You can instead use the
   ``qiskit_ibm_runtime.Options`` class to specify the settings, and
   ``max_time`` can be specified when starting a new session. For
   example:

   .. code:: python

      from qiskit_ibm_runtime import Session, Sampler, Options

      options = Options()
      # This can be done using auto-complete.
      option.optimization_level = 3
      options.resilience_level = 1

      with Session(max_time="2h") as session:
        # Pass the options to Sampler.
        sampler = Sampler(session=session, options=options)

-  Since some accounts have many runtime programs, caching a list of all
   programs on the first call of ``programs()`` has been removed.
   Instead, programs will only be cached up to the ``limit`` given,
   which has a default value of 20.

Deprecation Notes
-----------------

-  Invoking
   `qiskit_ibm_runtime.Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ and
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   as context managers has been deprecated. You can instead use the
   qiskit_ibm_runtime.Session class to create a new session and invoke
   one or more primitives within the session.

   As a result, passing input parameters, such as ``circuits``,
   ``observables``, and ``parameter_values``, as well as ``service`` to
   the constructors of ``Sampler`` and ``Estimator`` has also been
   deprecated. The inputs can now be passed to the ``run()`` method of
   the primitive classes, and ``service`` can be passed to
   `qiskit_ibm_runtime.Session <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/session>`__ when
   starting a new session.

-  Passing ``skip_transpilation`` to the
   :class:\`qiskit_ibm_runtime.Sampler and
   `qiskit_ibm_runtime.Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   constructors has been deprecated. You can instead use the
   ``qiskit_ibm_runtime.Options`` class to specify this option. For
   example:

   .. code:: python

      from qiskit_ibm_runtime import Options

      options = Options()
      # This can be done using auto-complete.
      options.transpilation.skip_transpilation = True

Bug Fixes
---------

-  Fixes issue
   `#428 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/428>`__ by
   raising the minimum required ``qiskit-terra`` version to ``0.21.0``,
   since latest version of ``qiskit-ibm-runtime`` is not compatible with
   ``0.20.0`` or earlier of ``qiskit-terra``.

0.6.0
=====

Upgrade Notes
-------------

-  When migrating from ``qiskit-ibmq-provider`` your ``ibm_quantum``
   channel credentials will get automatically copied over from the
   qiskitrc file and a qiskit-ibm.json file will get created if one
   doesn’t exist. You have to just initialize
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   class without passing any parameters to use this copied over default
   ``ibm_quantum`` account.

   Ex:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService
      service = QiskitRuntimeService()

-  ``IBMEstimator`` class which was deprecated earlier is now removed.
   Use `Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__ class going
   forward.

-  ``IBMRuntimeService`` class which was deprecated earlier is now
   removed. Use
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   class going forward.

0.5.0
=====

Prelude
-------

This release leverages the API and Queue enhancements to become more
runtime session aware. As a result when using the primitives (sampler
and estimator), runtime jobs in the same session will skip to the front
of the queue, thereby speeding up the runtime session, once it has
started.

New Features
------------

-  The ``service`` object which is an instance of
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   class can now be accessed from
   `IBMBackend <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend>`__ class using the
   ``service`` property.

   Ex:

   .. code:: python

      backend = service.get_backend("ibmq_qasm_simulator")
      backend.service  # QiskitRuntimeService instance used to instantiate the backend

Upgrade Notes
-------------

-  `jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__ has two
   new parameters, ``created_after`` and ``created_before``. These can
   be used to filter jobs by creation date in local time.

-  The parameters ``circuit_indices`` and ``observable_indices`` when
   calling ``estimator`` are now deprecated and will be removed in a
   future release. You can now pass either indices or objects using the
   ``circuits`` and ``observables`` parameters.

   Ex:

   .. code:: python

      with Estimator(
        circuits=[qc1, qc2],
        observables=[H1, H2, H3],
        service=service,
        options=options
      ) as estimator:
        # pass circuits and observables as indices
        result = estimator(circuits=[0, 1], observables=[0, 1], parameter_values=[theta1, theta2])

        # pass circuits and observables as objects
        result = estimator(circuits=[qc1, qc2], observables=[H1, H3], parameter_values=[theta1, theta3])

-  The parameters ``circuit_indices`` and ``observable_indices`` when
   calling ``estimator`` are now deprecated and will be removed in a
   future release. You can now pass either indices or objects using the
   ``circuits`` and ``observables`` parameters.

   Ex:

   .. code:: python

      with Sampler(
        circuits=[qc1, qc2],
        service=service,
        options=options
      ) as sampler:
        # pass circuits as indices
        result = sampler(circuits=[0, 1], parameter_values=[theta1, theta2])

        # pass circuit as objects
        result = sampler(circuits=[qc1, qc2], parameter_values=[theta2, theta3])

-  The ``session_id``, which is the Job ID of the first job in a runtime
   session can now be used as a filter in
   `jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__ with
   the parameter ``session_id``.

-  `run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#run>`__ now
   supports a new parameter, ``job_tags``. These tags can be used when
   filtering jobs with
   `jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__.

-  `run() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.29/qiskit-runtime-service#run>`__ now
   supports a new parameter, ``max_execution_time``, which can be used
   to override the default program maximum execution time. It should be
   less than or equal to the program maximum execution time.

-  `jobs() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service#jobs>`__ has a
   new parameter, ``descending``. This parameter defaults to ``True``,
   where jobs will be returned in descending order based on creation
   date.

-  ``RuntimeJobTimeoutError`` is now raised when the ``timeout`` set in
   `result() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#result>`__ or
   `wait_for_final_state() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#wait_for_final_state>`__
   expires.

-  When initializing
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__
   and an invalid token is used, ``IBMNotAuthorizedError`` will be
   raised instead of ``RequestsApiError``.

-  ``IBMSampler`` class which was deprecated earlier is now removed. Use
   `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ class going forward.

-  `qubit_properties() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend#qubit_properties>`__
   will now return a sub class of ``QubitProperties`` called
   ``IBMQubitProperties`` and will expose anharmonicity in addition to
   the t1, t2 and frequency already exposed by the ``QubitProperties``
   class.

0.4.0
=====

Upgrade Notes
-------------

-  ``IBMRuntimeService`` has been renamed to ``QiskitRuntimeSerice``.
   ``IBMRuntimeService`` class is now deprecated and will be removed in
   a future release.

   Example:

   Before:

   .. code:: python

      from qiskit_ibm_runtime import IBMRuntimeService
      service = IBMRuntimeService(channel="ibm_cloud", token="...", instance="...")

   After:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService
      service = QiskitRuntimeService(channel="ibm_cloud", token="...", instance="...")

-  ``IBMEstimator`` class is now deprecated and will be removed in a
   future release. Use `Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__
   class going forward.

   Example:

   Before:

   .. code:: python

      from qiskit_ibm_runtime import IBMRuntimeService, IBMEstimator
      service = IBMRuntimeService(channel="ibm_cloud", token="...", instance="...")

      estimator_factory = IBMEstimator(service=service, backend="ibmq_qasm_simulator")

      with estimator_factory(circuits=[qc], observables="...", parameters="...") as estimator:
          result = estimator(circuit_indices=[0], ...)

   After:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService, Estimator
      service = QiskitRuntimeService(channel="ibm_cloud", token="...", instance="...")

      with Estimator(
        circuits=[qc],
        observables="...",
        parameters="...",
        service=service,
        options={ "backend": "ibmq_qasm_simulator" },  # or IBMBackend<"ibmq_qasm_simulator">
      ) as estimator:
          result = estimator(circuit_indices=[0], ...)

-  ``IBMSampler`` class is now deprecated and will be removed in a
   future release. Use `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__
   class going forward.

   Example:

   Before:

   .. code:: python

      from qiskit_ibm_runtime import IBMRuntimeService, IBMSampler
      service = IBMRuntimeService(channel="ibm_cloud", token="...", instance="...")

      sampler_factory = IBMSampler(service=service, backend="ibmq_qasm_simulator")

      with sampler_factory(circuits=[qc], parameters="...") as sampler:
          result = sampler(circuit_indices=[0], ...)

   After:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
      service = QiskitRuntimeService(channel="ibm_cloud", token="...", instance="...")

      with Sampler(
        circuits=[qc],
        parameters="...",
        service=service,
        options={ "backend": "ibmq_qasm_simulator" },  # or IBMBackend<"ibmq_qasm_simulator">
      ) as sampler:
          result = sampler(circuit_indices=[0], ...)

Deprecation Notes
-----------------

-  ``IBMRuntimeService``, ``IBMEstimator`` and ``IBMSampler`` classes
   have been deprecated and will be removed in a future release. Use
   `QiskitRuntimeService <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service>`__,
   `Estimator <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator>`__ and
   `Sampler <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler>`__ classes instead. See
   upgrade notes section for a detailed explanation with examples.

0.3.0
=====

Upgrade Notes
-------------

-  A new parameter ``channel`` has now been added to
   ``qiskit_ibm_runtime.IBMRuntimeService`` class and also to methods
   like ``save_account()``, ``saved_accounts()`` and
   ``delete_account()``. It can be set to ``ibm_quantum`` or
   ``ibm_cloud`` to authenticate to either of the two different channels
   through which Qiskit Runtime service is currently offered.
   ``channel`` replaces the ``auth`` parameter which has now been
   deprecated.

Deprecation Notes
-----------------

-  The ``auth`` parameter to ``qiskit_ibm_runtime.IBMRuntimeService``
   class and also to methods like ``save_account()``,
   ``saved_accounts()`` and ``delete_account()`` has now been deprecated
   and will be removed in a future release. Please use the new
   ``channel`` parameter instead.

Bug Fixes
---------

-  Fixed
   `#291 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/219>`__
   where passing a single ``QuantumCircuit`` to sampler or estimator
   primitives was throwing an error.

0.2.0
=====

New Features
------------

-  ``qiskit_ibm_runtime.IBMEstimator`` and
   ``qiskit_ibm_runtime.IBMSampler`` classes now allow you to easily
   interact with the ``estimator`` and ``sampler`` primitive programs.
   Refer to the examples in the respective class doc strings to learn
   more about how to use them.

Bug Fixes
---------

-  Fixed a bug where
   `qiskit_ibm_runtime.RuntimeJob.wait_for_final_state() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#wait_for_final_state>`__
   would result in a NoneType error if the job already completed and
   `qiskit_ibm_runtime.RuntimeJob.status() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job#status>`__
   was called beforehand.

0.1.0
=====

Prelude
-------

qiskit-ibm-runtime is a new Python API client for accessing the quantum
programs, systems and simulators at IBM Quantum via the Qiskit Runtime
Service.

This new package is built upon the work already done in
qiskit.providers.ibmq.runtime module in the qiskit-ibmq-provider package
and replaces it going forward. The runtime module in
qiskit-ibmq-provider package is now deprecated.

qiskit-ibm-runtime is not included as part of Qiskit meta package and
thereby you have to install it separately using
``pip install qiskit-ibm-runtime``.

New Features
------------

-  ``qiskit_ibm_runtime.IBMRuntimeService.least_busy()`` will now allow
   you find the least busy backend.

Upgrade Notes
-------------

-  qiskit-ibm-runtime package no longer uses the $HOME/.qiskit/qiskitrc
   file used by qiskit-ibmq-provider to save credentials. Credentials
   are now stored in a JSON format in $HOME/.qiskit/qiskit-ibm.json file
   when you use ``qiskit_ibm_runtime.IBMRuntimeService.save_account()``
   method.

   You can now save multiple credentials and give an optional name for
   each credential.

-  Qiskit Runtime service is accessible using an IBM Quantum (legacy)
   account or an IBM Cloud (cloud) account. qiskit-ibm-runtime enables
   you to connect to either of these accounts:

   .. code:: python

      # Legacy
      from qiskit_ibm_runtime import IBMRuntimeService
      service = IBMRuntimeService(auth="legacy", token="abc")

      # Cloud
      from qiskit_ibm_runtime import IBMRuntimeService
      service = IBMRuntimeService(auth="cloud", token="abc", instance="IBM Cloud CRN or Service instance name")

-  `qiskit_ibm_runtime.IBMBackend <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend>`__
   class now implements the ``qiskit.providers.BackendV2`` interface and
   provides flatter access to the configuration of a backend, for
   example:

   .. code:: python

      # BackendV1:
      backend.configuration().n_qubits

      # BackendV2:
      backend.num_qubits

   Only breaking change when compared to BackendV1 is backend.name is
   now an attribute instead of a method.

   Refer to the
   `qiskit_ibm_runtime.IBMBackend <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/ibm-backend>`__
   class doc string for a list of all available attributes.

-  If you used qiskit.providers.ibmq.AccountProvider.get_backend method
   (for example, ``provider.get_backend("ibmq_qasm_simulator")``) in the
   qiskit-ibmq-provider package, it’s equivalent method in this new
   package is ``qiskit_ibm_runtime.IBMRuntimeService.backend()``:

   .. code:: python

      service = IBMRuntimeService()
      backend = service.backend("ibmq_qasm_simulator")

-  It is now optional to specify a hub/group/project upfront when
   connecting to the legacy IBM Quantum account. The hub/group/project
   is selected in the following order.

      -  hub/group/project if passed via ``instance`` parameter when
         initializing ``qiskit_ibm_runtime.IBMRuntimeService``
      -  the specific hub/group/project required by the backend
         specified when calling
         ``qiskit_ibm_runtime.IBMRuntimeService.run()``
      -  the default set previously via
         ``qiskit_ibm_runtime.IBMRuntimeService.save_account()``
      -  a premium hub/group/project in your account
      -  open access hub/group/project

-  It is now optional to specify backend_name in options when executing
   ``qiskit_ibm_runtime.IBMRuntimeService.run()`` method when using
   cloud runtime (IBM Cloud only). The server will automatically pick a
   backend and return the name.

-  qiskit.providers.ibmq.runtime.IBMRuntimeService.logout method in
   qiskit-ibmq-provider which was used to clear authorization cache on
   the server has been removed.

-  Python 3.6 has reached end of life and will no longer be supported in
   the new qiskit-ibm-runtime package.

-  qiskit.providers.ibmq.runtime.IBMRuntimeService.run_circuits method
   in qiskit-ibmq-provider has been removed and will be replaced by the
   ``Sampler`` primitive program.

-  ``qiskit_ibm_runtime.IBMRuntimeService.run()`` method now accepts
   runtime execution options as
   ``qiskit_ibm_runtime.RuntimeOptions``
   class in addition to already supported Dict. backend_name, image and
   log_level are the currently available options.

-  Final result is also streamed now after interim results when you
   specify a ``callback`` to
   ``qiskit_ibm_runtime.IBMRuntimeService.run()`` or
   `qiskit_ibm_runtime.RuntimeJob.stream_results() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.30/runtime-job#stream_results>`__.

0.1.0rc2
========

New Features
------------

-  For convenience, you can now set the ``IBM Cloud service name`` as a
   value for the account ``instance`` parameter. If you choose to set
   the name instead of the ``CRN``, the initialization time of the
   ``qiskit_ibm_runtime.IBMRuntimeService`` class is slightly higher
   because the required ``CRN`` value is internally resolved via IBM
   Cloud APIs.

Bug Fixes
---------

-  `qiskit_ibm_runtime.utils.json.RuntimeEncoder <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-encoder>`__
   and
   `qiskit_ibm_runtime.utils.json.RuntimeDecoder <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-decoder>`__
   have been updated to handle instances of the Instruction class.

-  Fixed an issue where numpy ndarrays with object types could not be
   serialized.
   `qiskit_ibm_runtime.utils.json.RuntimeEncoder <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-encoder>`__
   and
   `qiskit_ibm_runtime.utils.json.RuntimeDecoder <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-decoder>`__
   have been updated to handle these ndarrays.

0.1.0rc1
========

New Features
------------

-  You can now pass ``instance`` parameter in the hub/group/project
   format to ``qiskit_ibm_runtime.IBMRuntimeService.jobs()`` to filter
   jobs. Currently only supported for legacy authentication.

-  You can now use the
   `qiskit_ibm_runtime.RuntimeJob.interim_results() <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.30/runtime-job#interim_results>`__
   method to retrieve runtime program interim results. Note that interim
   results will only be available for up to two days.

Upgrade Notes
-------------

-  In order to be consistent with other properties in
   `qiskit_ibm_runtime.RuntimeJob <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/0.41/runtime-job>`__
   class the job_id and backend methods have been converted to
   properties.

-  When uploading a program with
   ``qiskit_ibm_runtime.IBMRuntimeService.upload_program()``, the
   program description is now optional.

-  When printing programs with
   ``qiskit_ibm_runtime.IBMRuntimeService.pprint_programs()``,
   ``backend_requirements`` will now be listed.

Bug Fixes
---------

-  Fixed an issue with JSON encoding and decoding when using
   ``ParameterExpression``\ s in conjunction with Qiskit Terra 0.19.1
   and above. Previously, the ``Parameter`` instances reconstructed from
   the JSON output would have different unique identifiers, causing them
   to seem unequal to the input. They will now have the correct backing
   identities.
