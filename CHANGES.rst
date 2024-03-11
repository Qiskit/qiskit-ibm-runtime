=======================================
Qiskit Runtime IBM Client release notes
=======================================

.. towncrier release notes start

0.21.1
======

Bug Fixes
---------

-  Fixed a bug where ``SamplerV1`` and ``EstimatorV1`` could not be
   imported because of an issue with how the aliases were defined.

.. _section-1:

0.21.0
======

Upgrade Notes
-------------

-  Circuits that do not match the target hardware definition are no
   longer supported by Qiskit Runtime primitives, unless
   ``channel_strategy="q-ctrl"`` is used. See the transpilation
   documentation (`transpile </transpile>`__) for instructions to
   transform circuits and the primitive examples
   (`run/primitives-examples </run/primitives-examples>`__) to see this
   coupled with operator transformations.

Deprecation Notes
-----------------

-  In a future release, ``backend`` will be a required parameter for
   ``qiskit_ibm_runtime.Sampler``, and ``qiskit_ibm_runtime.Estimator``
   if ``session`` is not specified, even when using the ``ibm_cloud``
   channel.

   It will also be a required parameter for
   ``qiskit_ibm_runtime.Session`` and ``qiskit_ibm_runtime.Batch``.

.. _bug-fixes-1:

Bug Fixes
---------

-  Fixed an issue with the ``IBMBackend.target`` where it would
   incorrectly exclude supported control flow operations (``IfElseOp``,
   ``WhileLoop``, etc.) if a given backend supported them.

-  Fixed a bug where retrieving a fake backend through
   ``FakeProviderForBackendV2.backend()`` would result in a type error.

-  Fixes the check for ISA circuits to allow pulse gates and circuits
   that don’t have layout.

.. _section-2:

0.20.0
======

New Features
------------

-  Add ``dd_barrier`` optional input to
   ```PadDynamicalDecoupling`` <qiskit_ibm_runtime.transpiler.passes.scheduling.PadDynamicalDecoupling>`__
   constructor to identify portions of the circuit to apply dynamical
   decoupling (dd) on selectively. If this string is contained in the
   label of a barrier in the circuit, dd is applied on the delays ending
   with it (on the same qubits); otherwise, it is not applied.

-  Python 3.12 is now supported.

-  Sessions will now be started with a new ``/sessions`` endpoint that
   allows for different execution modes. Batch mode is now supported
   through ``Batch``, and ```Session`` <qiskit_ibm_runtime.Session>`__
   will work the same as way as before. Please see
   `run/sessions </run/sessions>`__ for more information.

   Note that ``Session`` and ``Batch`` created from
   ``qiskit-ibm-runtime`` prior to this release will no longer be
   supported after March 31, 2024. Please update your
   ``qiskit-ibm-runtime`` version as soon as possible before this date.

   Also note that using simulators with sessions is no longer supported.
   Users can still start sessions with simulators without any issues but
   a session will not actually be created. There will be no session ID.

-  Sessions started with
   ```qiskit_ibm_runtime.IBMBackend.open_session()`` <qiskit_ibm_runtime.IBMBackend#open_session>`__
   will use the new ``/sessions`` endpoint.

   The sessions functionality will not change but note that
   ``backend.run()`` sessions prior to this release will no longer be
   supported after March 31, 2024. Please update your
   ``qiskit-ibm-runtime`` version as soon as possible before this date.

.. _deprecation-notes-1:

Deprecation Notes
-----------------

-  Circuits that do not match the target hardware definition will no
   longer be supported after March 1, 2024. See the transpilation
   documentation (`transpile </transpile>`__) for instructions to
   transform circuits and the primitive examples
   (`run/primitives-examples </run/primitives-examples>`__) to see this
   coupled with operator transformations.

.. _bug-fixes-2:

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

.. _section-3:

0.19.1
======

.. _upgrade-notes-1:

Upgrade Notes
-------------

-  Extend ``DynamicCircuitInstructions.from_backend()`` to extract and
   patch durations from both ``BackendV1`` and ``BackendV2`` objects.
   Also add ``DynamicCircuitInstructions.from_target()`` to use a
   ``Target`` object instead.

.. _bug-fixes-3:

Bug Fixes
---------

-  Fix the patching of ``DynamicCircuitInstructions`` for instructions
   with durations that are not in units of ``dt``.

-  Fixed an issue with the ``qpy.dump()`` function, when the
   ``use_symengine`` flag was set to a truthy object that evaluated to
   ``True`` but was not actually the boolean ``True`` the generated QPY
   payload would be corrupt.

.. _section-4:

0.19.0
======

.. _upgrade-notes-2:

Upgrade Notes
-------------

-  qiskit-ibm-provider is pending deprecation, and therefore will no
   longer be a dependency for qiskit-ibm-runtime.

-  qiskit-ibm-runtime is now compatible with Qiskit versions >= 0.45,
   including 1.0.0.

.. _section-5:

0.18.0
======

.. _new-features-1:

New Features
------------

-  Added a new parameter, dynamic_circuits to
   ```backends()`` <qiskit_ibm_runtime.QiskitRuntimeService#backends>`__
   to allow filtering of backends that support dynamic circuits.

-  Added ``max_time`` parameter to ``IBMBackend.open_session()``.

-  Added a method ``RuntimeJob.queue_info()`` to get the queue
   information from the backend. This feature was transferred from
   ``qiskit_ibm_provider``.

.. _deprecation-notes-2:

Deprecation Notes
-----------------

-  ```runtime()`` <qiskit_ibm_runtime.QiskitRuntimeService#runtime>`__
   has been deprecated.

.. _bug-fixes-4:

Bug Fixes
---------

-  Many methods in ```RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__
   require retrieving the job data from the API with ``job_get()``. This
   API call will now exclude the ``params`` field by default because
   they are only necessary in
   ```qiskit_ibm_runtime.RuntimeJob.inputs()`` <qiskit_ibm_runtime.RuntimeJob#inputs>`__.

.. _section-6:

0.17.0
======

.. _new-features-2:

New Features
------------

-  Added a new method
   ```properties()`` <qiskit_ibm_runtime.RuntimeJob#properties>`__ which
   returns the backend properties of the job at the time the job was
   run.

-  ```details()`` <qiskit_ibm_runtime.Session#details>`__ has a new
   field, activated_at, which is the timestamp of when the session was
   changed to active.

.. _bug-fixes-5:

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

.. _section-7:

0.16.0
======

Prelude
-------

Sessions are now thread-safe and allow for multiple concurrent
interactive experiments.

.. _new-features-3:

New Features
------------

-  Sessions are now thread-safe.

.. _upgrade-notes-3:

Upgrade Notes
-------------

-  Methods related to using custom programs are removed.

.. _bug-fixes-6:

Bug Fixes
---------

-  If a cloud instance that is ``q-ctrl`` enabled is used while
   ``q-ctrl`` is not passed in as the ``channel_strategy``, an error
   will be raised.

.. _section-8:

0.15.1
======

.. _bug-fixes-7:

Bug Fixes
---------

-  Reverting 0.15.0 changes to
   ```from_id()`` <qiskit_ibm_runtime.Session#from_id>`__ because it was
   a breaking change without proper deprecation.

.. _section-9:

0.15.0
======

.. _new-features-4:

New Features
------------

-  A new module
   ```qiskit_ibm_runtime.fake_provider`` <fake_provider#module-qiskit_ibm_runtime.fake_provider>`__,
   has been added to provide access to a series of fake backends derived
   from snapshots of IBM Quantum devices. This functionality was
   originally provided by the ``qiskit.providers.fake_provider`` module,
   but will soon be deprecated in favor of
   ```qiskit_ibm_runtime.fake_provider`` <fake_provider#module-qiskit_ibm_runtime.fake_provider>`__.

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

.. _deprecation-notes-3:

Deprecation Notes
-----------------

-  Usage of the ``~/.qiskit/qiskitrc.json`` file for account information
   has been deprecated. Use ``~/.qiskit/qiskit-ibm.json`` instead.

.. _bug-fixes-8:

Bug Fixes
---------

-  Fixed an issue where canceled and failed jobs would return an invalid
   result that resulted in a type error, preventing the actual error
   from being returned to the user.

-  A warning will be raised at initialization if the DE environment is
   being used since not all features are supported there.

-  The ``backend`` parameter in
   ```from_id()`` <qiskit_ibm_runtime.Session#from_id>`__ is being
   deprecated because sessions do not support multiple backends.
   Additionally, the ``service`` parameter is no longer optional.

-  The ``circuit_indices`` and ``observable_indices`` run inputs for
   ```Estimator`` <qiskit_ibm_runtime.Estimator>`__ and
   ```Sampler`` <qiskit_ibm_runtime.Sampler>`__ have been completely
   removed.

.. _other-notes-1:

Other Notes
-----------

-  Added migration code for running ``backend.run`` in
   qiskit_ibm_runtime instead of in qiskit_ibm_provider.

.. _section-10:

0.14.0
======

.. _new-features-5:

New Features
------------

-  There is a new class, ``qiskit_ibm_runtime.Batch`` that currently
   works the same way as
   ```qiskit_ibm_runtime.Session`` <qiskit_ibm_runtime.Session>`__ but
   will later be updated to better support submitting multiple jobs at
   once.

-  Arbitrary keys and values are no longer allowed in ``Options``.

.. _deprecation-notes-4:

Deprecation Notes
-----------------

-  Custom programs are being deprecated as of qiskit-ibm-runtime 0.14.0
   and will be removed on November 27, 2023. Users can instead convert
   their custom programs to use Qiskit Runtime primitives with Quantum
   Serverless. Refer to the migration guide for instructions:
   https://qiskit-extensions.github.io/quantum-serverless/migration/migration_from_qiskit_runtime_programs.html

.. _section-11:

0.13.0
======

.. _new-features-6:

New Features
------------

-  Added a new method,
   ```details()`` <qiskit_ibm_runtime.Session#details>`__ that returns
   information about a session, including: maximum session time, active
   time remaining, the current state, and whether or not the session is
   accepting jobs.

   Also added ```status()`` <qiskit_ibm_runtime.Session#status>`__,
   which returns the current status of the session.

-  At initialization, if not passed in directly, the default
   ``instance`` selected by the provider will be logged at the “INFO”
   level. When running a job, if the backend selected is not in the
   default instance but in a different instance the user also has access
   to, that instance will also be logged.

.. _upgrade-notes-4:

Upgrade Notes
-------------

-  ```qiskit_ibm_runtime.Session.close()`` <qiskit_ibm_runtime.Session#close>`__
   has been updated to mark a ``Session`` as no longer accepting new
   jobs. The session won’t accept more jobs but it will continue to run
   any queued jobs until they are done or the max time expires. This
   will also happen automatically when the session context manager is
   exited. When a session that is not accepting jobs has run out of jobs
   to run, it’s immediately closed, freeing up the backend to run more
   jobs rather than wait for the interactive timeout.

   The old close method behavior has been moved to a new method,
   ```qiskit_ibm_runtime.Session.cancel()`` <qiskit_ibm_runtime.Session#cancel>`__,
   where all queued jobs within a session are cancelled and terminated.

.. _bug-fixes-9:

Bug Fixes
---------

-  Fixed a bug where ``shots`` passed in as a numpy type were not being
   serialized correctly.

-  Fixed a bug in
   ```target_history()`` <qiskit_ibm_runtime.IBMBackend#target_history>`__
   where the datetime parameter was not being used to retrieve backend
   properties from the specified date.

.. _section-12:

0.12.2
======

.. _new-features-7:

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

.. _upgrade-notes-5:

Upgrade Notes
-------------

-  Job error messages now include the error code. Error codes can be
   found in `errors </errors>`__.

.. _section-13:

0.12.1
======

.. _new-features-8:

New Features
------------

-  Users can use a new environment variable, ``USAGE_DATA_OPT_OUT`` to
   opt out of user module usage tracking by setting this value to
   ``True``. Additionally, only certain qiskit modules will be tracked
   instead of all modules that begin with qiskit or qiskit\_.

-  Users can now pass in a value of ``default`` to the
   ``channel_strategy`` parameter in
   ```qiskit_ibm_runtime.QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__.
   Now, if an account is configured with a certain channel strategy, the
   user can override it by passing in ``default``.

-  The Sampler and Estimator primitives have been enhanced to
   incorporate custom validation procedures when the channel_strategy
   property within the :class:qiskit_ibm_runtime.QiskitRuntimeService is
   configured as “q-ctrl.” This customized validation logic effectively
   rectifies incorrect input options and safeguards users against
   inadvertently disabling Q-CTRL’s performance enhancements.

.. _bug-fixes-10:

Bug Fixes
---------

-  Retrieving backend properties with
   ```properties()`` <qiskit_ibm_runtime.IBMBackend#properties>`__ now
   supports passing a ``datetime`` parameter to retrieve properties from
   a past date.

-  The ``noise_factors`` and ``extrapolator`` options in
   ```qiskit_ibm_runtime.options.ResilienceOptions`` <qiskit_ibm_runtime.options.ResilienceOptions>`__
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

.. _section-14:

0.12.0
======

.. _new-features-9:

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
   ```qiskit_ibm_runtime.QiskitRuntimeService.instances()`` <qiskit_ibm_runtime.QiskitRuntimeService#instances>`__
   that returns all instances(hub/group/project) the user is in. This is
   only for the ``ibm_quantum`` channel since the ``ibm_cloud`` channel
   does not have multiple instances.

-  Added validations for options on the second level of the dict, i.e.,
   for each of resilience, simulator, execution, and transpilation,
   check that their options are supported. Otherwise throw an exception.

-  There is a new parameter, ``channel_strategy`` that can be set in the
   initialization of
   ```qiskit_ibm_runtime.QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   or saved in
   ```qiskit_ibm_runtime.QiskitRuntimeService.save_account()`` <qiskit_ibm_runtime.QiskitRuntimeService#save_account>`__.
   If ``channel_strategy`` is set to ``q-ctrl``, all jobs within the
   service will use the Q-CTRL error mitigation strategy.

.. _upgrade-notes-6:

Upgrade Notes
-------------

-  Circuits and other input parameters will no longer be automatically
   stored in runtime jobs. They can still be retrieved with
   ```qiskit_ibm_runtime.RuntimeJob.inputs()`` <qiskit_ibm_runtime.RuntimeJob#inputs>`__.

.. _deprecation-notes-5:

Deprecation Notes
-----------------

-  The ``noise_amplifier`` resilience options is deprecated. After the
   deprecation period, only local folding amplification will be
   supported. Refer to https://github.com/qiskit-community/prototype-zne
   for global folding amplification.

.. _bug-fixes-11:

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

.. _section-15:

0.11.3
======

.. _new-features-10:

New Features
------------

-  Added reason for failure when invoking the method
   ```error_message()`` <qiskit_ibm_runtime.RuntimeJob#error_message>`__.

-  Added a new property,
   ```usage_estimation()`` <qiskit_ibm_runtime.RuntimeJob#usage_estimation>`__
   that returns the estimated system execution time,
   ``quantum_seconds``. System execution time represents the amount of
   time that the system is dedicated to processing your job.

-  Raise an exception if the number of circuits passed to
   ``_run_primitive()`` exceeds the number of circuits supported on the
   backend.

-  There is a new method
   ```update_tags()`` <qiskit_ibm_runtime.RuntimeJob#update_tags>`__
   that can be used to update the ``job_tags`` of a job.

-  If ``instance`` is provided as parameter to
   ```qiskit_ibm_runtime.QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__,
   then this is used as a filter in ``QiskitRuntimeService.backends()``.
   If ``instance`` is not recognized as one of the provider instances,
   an exception will be raised. Previously, we only issued a warning.

.. _section-16:

0.11.2
======

.. _new-features-11:

New Features
------------

-  If a job has been cancelled, and job.result() is requested, throw an
   exception rather than returning None.

-  A new method,
   ```qiskit_ibm_runtime.options.SimulatorOptions.set_backend()`` <qiskit_ibm_runtime.options.SimulatorOptions#set_backend>`__,
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

.. _bug-fixes-12:

Bug Fixes
---------

-  Fixed infinite recursion when attempting to deepcopy an IBMBackend.
   Added a method ``qiskit_ibm_runtime.IBMBackend.deepcopy()``.

-  Fixed an issue where circuit metadata was not being serialized
   correctly resulting in a type error.

.. _section-17:

0.11.1
======

.. _deprecation-notes-6:

Deprecation Notes
-----------------

-  In
   ```qiskit_ibm_runtime.RuntimeJob.metrics()`` <qiskit_ibm_runtime.RuntimeJob#metrics>`__,
   the bss field will be replaced by usage.

.. _section-18:

0.11.0
======

.. _new-features-12:

New Features
------------

-  When retrieving a job with
   ``qiskit_ibm_runtime.IBMRuntimeService.job()`` the ``params`` will no
   longer be returned from the API. They will instead be loaded loazily
   when they are actually needed in
   ```qiskit_ibm_runtime.RuntimeJob.inputs()`` <qiskit_ibm_runtime.RuntimeJob#inputs>`__.

-  Added warning when the backend is not active in
   QiskitRuntimeService.run.

-  Support input of type ``CouplingMap`` when given as simulator option.
   Previously we supported, for example:

   .. code:: python

      options.simulator = {"coupling_map": [[0, 1], [1, 0]]}

   Now we also support the following:

   .. code:: python

      options.simulator = {"coupling_map": CouplingMap.from_line(10)}

.. _upgrade-notes-7:

Upgrade Notes
-------------

-  A default session is no longer open for you if you pass a backend
   name or backend instance to
   ```qiskit_ibm_runtime.Sampler`` <qiskit_ibm_runtime.Sampler>`__ or
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
   constructors. The primitive will instead run without a session. In
   addition, you should now use the ``backend`` parameter to pass a
   backend name or instance instead of the ``session`` parameter (which
   can continue to be used to pass a session).

-  The first parameter of the
   ```qiskit_ibm_runtime.Sampler`` <qiskit_ibm_runtime.Sampler>`__ and
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
   constructors is now ``backend`` instead of ``session``.

.. _deprecation-notes-7:

Deprecation Notes
-----------------

-  Passing a backend name or backend instance to the ``session``
   parameter when initializing a
   ```qiskit_ibm_runtime.Sampler`` <qiskit_ibm_runtime.Sampler>`__ or
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
   has been deprecated. Please use the ``backend`` parameter instead.
   You can continue to pass a session using the ``session`` parameter.

.. _section-19:

0.10.0
======

.. _new-features-13:

New Features
------------

-  Python 3.11 is now supported.

.. _upgrade-notes-8:

Upgrade Notes
-------------

-  Added error messages in case the user defines unsupported values for
   ‘max_execution_time’. Previously, this validation was done on the
   server side.

.. _bug-fixes-13:

Bug Fixes
---------

-  Added deserialization of the params of RuntimeJob.inputs. Previously,
   the circuits were returned in serialized format. Fixes issue
   `#829 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/829>`__.

-  Allow for users to retrieve all backends even if one of the backends
   has a missing configuration. The backend without a configuration will
   not be returned.

.. _section-20:

0.9.4
-----

.. _new-features-14:

New Features
------------

-  Added methods to validate input options to ``transpilation`` and
   ``environment`` options.

.. _upgrade-notes-9:

Upgrade Notes
-------------

-  When constructing a backend ``qiskit.transpiler.Target``, faulty
   qubits and gates from the backend configuration will be filtered out.

.. _deprecation-notes-8:

Deprecation Notes
-----------------

-  The deprecated arguments ``circuits``, ``parameters``, ``service``,
   and ``skip_transpilation`` have been removed from
   ```Sampler`` <qiskit_ibm_runtime.Sampler>`__.

   Similarly, the deprecated arguments ``circuits``, ``observables``,
   ``parameters``, ``service``, and ``skip_transpilation`` have been
   removed from ```Estimator`` <qiskit_ibm_runtime.Estimator>`__.

   In
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__,
   the ``auth`` parameter has been removed. Additionally, the
   ``instance``, ``job_tags``, and ``max_execution_time`` paramters have
   been removed from
   ```qiskit_ibm_runtime.QiskitRuntimeService.run()`` <qiskit_ibm_runtime.QiskitRuntimeService#run>`__.
   They can be passed in through
   ```RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__ instead.

   Within ```RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__,
   ``backend_name`` is no longer supported. Please use ``backend``
   instead.

.. _bug-fixes-14:

Bug Fixes
---------

-  Fixed a bug where retrieving a job from a backend without
   ``noise_model`` or ``seed_simulator`` options would result in a key
   error.

.. _section-21:

0.9.3
-----

.. _upgrade-notes-10:

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
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   is initialized. Instead, the configuration is only loaded and cached
   during
   ```get_backend()`` <qiskit_ibm_runtime.QiskitRuntimeService#get_backend>`__
   and
   ```backends()`` <qiskit_ibm_runtime.QiskitRuntimeService#backends>`__.

.. _bug-fixes-15:

Bug Fixes
---------

-  When creating an Option object and passing an input option to
   ``resilience_options``, this option was included in
   ``resilience_options``, but the other, default options were removed.
   This was fixed, so now inputs are handled correctly, like other
   option types.

.. _section-22:

0.9.2
-----

.. _new-features-15:

New Features
------------

-  Added a new argument called ``session_time`` to the program_run
   method and
   ```qiskit_ibm_runtime.RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__.
   Now values entered by the user for session ``max_time`` will be sent
   to the server side as ``session_time``. This allows users to specify
   different values for session ``max_time`` and ``max_execution_time``.

-  Added the method
   ```target_history()`` <qiskit_ibm_runtime.IBMBackend#target_history>`__.
   This method is similar to
   ```target()`` <qiskit_ibm_runtime.IBMBackend#target>`__. The
   difference is that the new method enables the user to pass a datetime
   parameter, to retrieve historical data from the backend.

.. _upgrade-notes-11:

Upgrade Notes
-------------

-  Accept all options on given on level 1 and assign them to the
   appropriate hierarchical option type. For example, if the user
   provides ``options = {"shots": 10}`` as input to Sampler/Estimator,
   this will be interpreted as
   ``options = {"execution: {"shots": 10}}``.

-  If a job is returned without a backend, retrieving the backend
   through
   ```qiskit_ibm_runtime.RuntimeJob.backend()`` <qiskit_ibm_runtime.RuntimeJob#backend>`__
   will re-retrieve data from the server and attempt to update the
   backend. Additionally, ``job_id`` and ``backend``, which were
   deprecated attributes of
   ```qiskit_ibm_runtime.RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__
   have now been removed.

-  Added a user warning when the user passes an option that is not
   supported in Options.

.. _bug-fixes-16:

Bug Fixes
---------

-  Fixed a bug where the default values for ``optimization_level`` and
   for ``resilience_level`` were not being set correctly.

-  Fixed an issue where if no backend was selected,
   ``optimization_level`` and ``resilience_level`` would default to
   ``None``, causing the job to fail.

-  If an instance is passed in to
   ```qiskit_ibm_runtime.QiskitRuntimeService.get_backend()`` <qiskit_ibm_runtime.QiskitRuntimeService#get_backend>`__
   and then the backend is used in a session, all jobs within the
   session will be run from the original instance passed in.

-  Removed additional decomposition of ``BlueprintCircuit``\ s in the
   JSON encoder. This was introduced as a bugfix, but has since been
   fixed. Still doing the decomposition led to possible problems if the
   decomposed circuit was not in the correct basis set of the backend
   anymore.

.. _section-23:

0.9.1
-----

.. _upgrade-notes-12:

Upgrade Notes
-------------

-  ```qiskit_ibm_runtime.QiskitRuntimeService.jobs()`` <qiskit_ibm_runtime.QiskitRuntimeService#jobs>`__
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

.. _deprecation-notes-9:

Deprecation Notes
-----------------

-  ``backend`` is no longer a supported option when using
   ```qiskit_ibm_runtime.Session.run()`` <qiskit_ibm_runtime.Session#run>`__.
   Sessions do not support multiple cross backends. Additionally, an
   exception will be raised if a backend passed in through options does
   not match the original session backend in an active session.

.. _bug-fixes-17:

Bug Fixes
---------

-  ``ECRGate`` and ``CZGate`` mappings have been added to the ``Target``
   constructor to fix a tranpile bug.

.. _other-notes-2:

Other Notes
-----------

-  Since error messages from a failing job may be long, we shortened
   them so that they begin from the last ``Traceback`` in the message.

.. _section-24:

0.9.0
-----

.. _upgrade-notes-13:

Upgrade Notes
-------------

-  Changed the default values for ``optimization_level`` and for
   ``resilience_level`` in ``qiskit_ibm_runtime.Options``. If their
   values are defined by the user, they are not modified. If not set, if
   the backend is a noiseless simulator then ``optimization_level`` is
   set to 1 and ``resilience_level`` is set to 0; Otherwise, they are be
   set to 3 and 1 respectively.

-  ```session_id()`` <qiskit_ibm_runtime.RuntimeJob#session_id>`__ and
   ```tags()`` <qiskit_ibm_runtime.RuntimeJob#tags>`__ were added for an
   easy way to return the session_id and job_tags of a job.

.. _bug-fixes-18:

Bug Fixes
---------

-  Fixed a bug where jobs that did not run before a session closes are
   not actually run as a part of that session. Jobs should run as a part
   of a session even if that session is closed by the exit of the
   context manager.

-  Fixes the issue wherein submitting a large job fails due to write
   operation timeout.

.. _section-25:

0.8.0
-----

.. _new-features-16:

New Features
------------

-  Python 3.10 is now supported.

-  Advanced resilience options can now be set under
   ``options.resilience``. See
   ```qiskit_ibm_runtime.options.ResilienceOptions`` <qiskit_ibm_runtime.options.ResilienceOptions>`__
   for all available options.

-  You can now specify a pair of result decoders for the
   ``result_decoder`` parameter of
   ```qiskit_ibm_runtime.QiskitRuntimeService.run()`` <qiskit_ibm_runtime.QiskitRuntimeService#run>`__
   method. If a pair is specified, the first one is used to decode
   interim results and the second the final results.

.. _upgrade-notes-14:

Upgrade Notes
-------------

-  The default ``resilience_level`` option for has been changed from 0
   to 1. In addition, the default ``optimization_level`` option has been
   changed from 1 to 3.

.. _deprecation-notes-10:

Deprecation Notes
-----------------

-  The transpilation options ``translation_method`` and
   ``timing_constraints`` have been deprecated.

.. _bug-fixes-19:

Bug Fixes
---------

-  If a
   ```qiskit_ibm_runtime.IBMBackend`` <qiskit_ibm_runtime.IBMBackend>`__
   instance is passed to the
   ```qiskit_ibm_runtime.Session`` <qiskit_ibm_runtime.Session>`__
   constructor, the service used to initialize the ``IBMBackend``
   instance is used for the session instead of the default account
   service.

.. _section-26:

0.7.0
-----

.. _new-features-17:

New Features
------------

-  ``qiskit_ibm_runtime.Options`` class now accepts arbitrary keyword
   arguments. This allows users to specify new options to the primitive
   programs without upgrading ``qiskit_ibm_runtime``. These arbitrary
   keyword arguments, however, are not validated.

-  The
   ```qiskit_ibm_runtime.options.EnvironmentOptions`` <qiskit_ibm_runtime.options.EnvironmentOptions>`__
   class now accepts a ``callback`` parameter. This parameter can be
   used to stream the interim and final results of the primitives.

-  The ``qiskit_ibm_runtime.Options`` class now accepts
   ``max_execution_time`` as a first level option and ``job_tags`` as an
   option under ``environment``.
   ```qiskit_ibm_runtime.RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__
   has also been updated to include these two parameters.

.. _upgrade-notes-15:

Upgrade Notes
-------------

-  This version of qiskit-ibm-runtime requires qiskit-terra version 0.22
   or higher. The ``requirements.txt`` file has been updated
   accordingly.

.. _deprecation-notes-11:

Deprecation Notes
-----------------

-  Qiskit Runtime programs ``torch-train``, ``torch-infer``,
   ``sample-expval``, ``sample-program``, and
   ``quantum_kernal_alignment`` have been deprecated due to low usage.

-  Passing ``instance`` parameter to the
   ```qiskit_ibm_runtime.QiskitRuntimeService.run()`` <qiskit_ibm_runtime.QiskitRuntimeService#run>`__
   has been deprecated. Instead, you can pass the ``instance`` parameter
   inside the ``options`` parameter.

-  Passing ``job_tags`` and ``max_execution_time`` as parameters to
   ```qiskit_ibm_runtime.QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   has been deprecated. Please pass them inside ``options``.

.. _bug-fixes-20:

Bug Fixes
---------

-  Fixes the missing section on retrieving jobs in the how-to guide.

0.7.0rc2
========

.. _upgrade-notes-16:

Upgrade Notes
-------------

-  Added a validation check to
   ```run()`` <qiskit_ibm_runtime.Sampler#run>`__. It raises an error if
   there is no classical bit.

-  ```Sampler`` <qiskit_ibm_runtime.Sampler>`__ is updated to return
   ``SamplerResult`` with ``SamplerResult.quasi_dists`` as a list of
   ``QuasiDistrbution``. It used to set a list of ``dict`` as
   ``SamplerResult.quasi_dists``, but it did not follow the design of
   ``SamplerResult``.

-  The ```RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__ class is now a
   subclass of ``qiskit.providers.Job``.

.. _deprecation-notes-12:

Deprecation Notes
-----------------

-  ``job_id`` and ``backend`` attributes of
   ```qiskit_ibm_runtime.RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__
   have been deprecated. Please use
   ```qiskit_ibm_runtime.RuntimeJob.job_id()`` <qiskit_ibm_runtime.RuntimeJob#job_id>`__
   and
   ```qiskit_ibm_runtime.RuntimeJob.backend()`` <qiskit_ibm_runtime.RuntimeJob#backend>`__
   methods instead.

-  The ``backend_name`` attribute in
   ```qiskit_ibm_runtime.RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__
   is deprecated and replaced by ``backend``.

0.7.0rc1
========

.. _prelude-1:

Prelude
-------

There are significant changes to how primitives are invoked within a
session, and the options available to the primitives. Please review the
rest of the release notes and the tutorials for full information.

.. _new-features-18:

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

-  ```qiskit_ibm_runtime.RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__
   has a new method
   ```metrics()`` <qiskit_ibm_runtime.RuntimeJob#metrics>`__. This
   method returns the metrics of a job, which includes timestamp
   information.

-  The
   ```qiskit_ibm_runtime.QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   ``channel`` can now be stored as an environment variable,
   ``QISKIT_IBM_CHANNEL``. This way, when using Runtime Primitives, the
   service does not have to be instantiated manually and can instead be
   created directly from environment variables.

.. _upgrade-notes-17:

Upgrade Notes
-------------

-  Raise ``RuntimeJobMaxTimeoutError`` when a job runs for too long so
   that it can be handled appropriately by programs.

-  The experimental parameters ``transpilation_settings``,
   ``resilience_settings``, and ``max_time`` to the
   :class:\`qiskit_ibm_runtime.Sampler and
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
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

.. _deprecation-notes-13:

Deprecation Notes
-----------------

-  Invoking
   ```qiskit_ibm_runtime.Sampler`` <qiskit_ibm_runtime.Sampler>`__ and
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
   as context managers has been deprecated. You can instead use the
   qiskit_ibm_runtime.Session class to create a new session and invoke
   one or more primitives within the session.

   As a result, passing input parameters, such as ``circuits``,
   ``observables``, and ``parameter_values``, as well as ``service`` to
   the constructors of ``Sampler`` and ``Estimator`` has also been
   deprecated. The inputs can now be passed to the ``run()`` method of
   the primitive classes, and ``service`` can be passed to
   ```qiskit_ibm_runtime.Session`` <qiskit_ibm_runtime.Session>`__ when
   starting a new session.

-  Passing ``skip_transpilation`` to the
   :class:\`qiskit_ibm_runtime.Sampler and
   ```qiskit_ibm_runtime.Estimator`` <qiskit_ibm_runtime.Estimator>`__
   constructors has been deprecated. You can instead use the
   ``qiskit_ibm_runtime.Options`` class to specify this option. For
   example:

   .. code:: python

      from qiskit_ibm_runtime import Options

      options = Options()
      # This can be done using auto-complete.
      options.transpilation.skip_transpilation = True

.. _bug-fixes-21:

Bug Fixes
---------

-  Fixes issue
   `#428 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/428>`__ by
   raising the minimum required ``qiskit-terra`` version to ``0.21.0``,
   since latest version of ``qiskit-ibm-runtime`` is not compatible with
   ``0.20.0`` or earlier of ``qiskit-terra``.

.. _section-27:

0.6.0
-----

.. _upgrade-notes-18:

Upgrade Notes
-------------

-  When migrating from ``qiskit-ibmq-provider`` your ``ibm_quantum``
   channel credentials will get automatically copied over from the
   qiskitrc file and a qiskit-ibm.json file will get created if one
   doesn’t exist. You have to just initialize
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   class without passing any parameters to use this copied over default
   ``ibm_quantum`` account.

   Ex:

   .. code:: python

      from qiskit_ibm_runtime import QiskitRuntimeService
      service = QiskitRuntimeService()

-  ``IBMEstimator`` class which was deprecated earlier is now removed.
   Use ```Estimator`` <qiskit_ibm_runtime.Estimator>`__ class going
   forward.

-  ``IBMRuntimeService`` class which was deprecated earlier is now
   removed. Use
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   class going forward.

.. _section-28:

0.5.0
-----

.. _prelude-2:

Prelude
-------

This release leverages the API and Queue enhancements to become more
runtime session aware. As a result when using the primitives (sampler
and estimator), runtime jobs in the same session will skip to the front
of the queue, thereby speeding up the runtime session, once it has
started.

.. _new-features-19:

New Features
------------

-  The ``service`` object which is an instance of
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   class can now be accessed from
   ```IBMBackend`` <qiskit_ibm_runtime.IBMBackend>`__ class using the
   ``service`` property.

   Ex:

   .. code:: python

      backend = service.get_backend("ibmq_qasm_simulator")
      backend.service  # QiskitRuntimeService instance used to instantiate the backend

.. _upgrade-notes-19:

Upgrade Notes
-------------

-  ```jobs()`` <qiskit_ibm_runtime.QiskitRuntimeService#jobs>`__ has two
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
   ```jobs()`` <qiskit_ibm_runtime.QiskitRuntimeService#jobs>`__ with
   the parameter ``session_id``.

-  ```run()`` <qiskit_ibm_runtime.QiskitRuntimeService#run>`__ now
   supports a new parameter, ``job_tags``. These tags can be used when
   filtering jobs with
   ```jobs()`` <qiskit_ibm_runtime.QiskitRuntimeService#jobs>`__.

-  ```run()`` <qiskit_ibm_runtime.QiskitRuntimeService#run>`__ now
   supports a new parameter, ``max_execution_time``, which can be used
   to override the default program maximum execution time. It should be
   less than or equal to the program maximum execution time.

-  ```jobs()`` <qiskit_ibm_runtime.QiskitRuntimeService#jobs>`__ has a
   new parameter, ``descending``. This parameter defaults to ``True``,
   where jobs will be returned in descending order based on creation
   date.

-  ``RuntimeJobTimeoutError`` is now raised when the ``timeout`` set in
   ```result()`` <qiskit_ibm_runtime.RuntimeJob#result>`__ or
   ```wait_for_final_state()`` <qiskit_ibm_runtime.RuntimeJob#wait_for_final_state>`__
   expires.

-  When initializing
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__
   and an invalid token is used, ``IBMNotAuthorizedError`` will be
   raised instead of ``RequestsApiError``.

-  ``IBMSampler`` class which was deprecated earlier is now removed. Use
   ```Sampler`` <qiskit_ibm_runtime.Sampler>`__ class going forward.

-  ```qubit_properties()`` <qiskit_ibm_runtime.IBMBackend#qubit_properties>`__
   will now return a sub class of ``QubitProperties`` called
   ``IBMQubitProperties`` and will expose anharmonicity in addition to
   the t1, t2 and frequency already exposed by the ``QubitProperties``
   class.

.. _section-29:

0.4.0
-----

.. _upgrade-notes-20:

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
   future release. Use ```Estimator`` <qiskit_ibm_runtime.Estimator>`__
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
   future release. Use ```Sampler`` <qiskit_ibm_runtime.Sampler>`__
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

.. _deprecation-notes-14:

Deprecation Notes
-----------------

-  ``IBMRuntimeService``, ``IBMEstimator`` and ``IBMSampler`` classes
   have been deprecated and will be removed in a future release. Use
   ```QiskitRuntimeService`` <qiskit_ibm_runtime.QiskitRuntimeService>`__,
   ```Estimator`` <qiskit_ibm_runtime.Estimator>`__ and
   ```Sampler`` <qiskit_ibm_runtime.Sampler>`__ classes instead. See
   upgrade notes section for a detailed explanation with examples.

.. _section-30:

0.3.0
-----

.. _upgrade-notes-21:

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

.. _deprecation-notes-15:

Deprecation Notes
-----------------

-  The ``auth`` parameter to ``qiskit_ibm_runtime.IBMRuntimeService``
   class and also to methods like ``save_account()``,
   ``saved_accounts()`` and ``delete_account()`` has now been deprecated
   and will be removed in a future release. Please use the new
   ``channel`` parameter instead.

.. _bug-fixes-22:

Bug Fixes
---------

-  Fixed
   `#291 <https://github.com/Qiskit/qiskit-ibm-runtime/issues/219>`__
   where passing a single ``QuantumCircuit`` to sampler or estimator
   primitives was throwing an error.

.. _section-31:

0.2.0
-----

.. _new-features-20:

New Features
------------

-  ``qiskit_ibm_runtime.IBMEstimator`` and
   ``qiskit_ibm_runtime.IBMSampler`` classes now allow you to easily
   interact with the ``estimator`` and ``sampler`` primitive programs.
   Refer to the examples in the respective class doc strings to learn
   more about how to use them.

.. _bug-fixes-23:

Bug Fixes
---------

-  Fixed a bug where
   ```qiskit_ibm_runtime.RuntimeJob.wait_for_final_state()`` <qiskit_ibm_runtime.RuntimeJob#wait_for_final_state>`__
   would result in a NoneType error if the job already completed and
   ```qiskit_ibm_runtime.RuntimeJob.status()`` <qiskit_ibm_runtime.RuntimeJob#status>`__
   was called beforehand.

.. _section-32:

0.1.0
-----

.. _prelude-3:

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

.. _new-features-21:

New Features
------------

-  ``qiskit_ibm_runtime.IBMRuntimeService.least_busy()`` will now allow
   you find the least busy backend.

.. _upgrade-notes-22:

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

-  ```qiskit_ibm_runtime.IBMBackend`` <qiskit_ibm_runtime.IBMBackend>`__
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
   ```qiskit_ibm_runtime.IBMBackend`` <qiskit_ibm_runtime.IBMBackend>`__
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
   ```qiskit_ibm_runtime.RuntimeOptions`` <qiskit_ibm_runtime.RuntimeOptions>`__
   class in addition to already supported Dict. backend_name, image and
   log_level are the currently available options.

-  Final result is also streamed now after interim results when you
   specify a ``callback`` to
   ``qiskit_ibm_runtime.IBMRuntimeService.run()`` or
   ```qiskit_ibm_runtime.RuntimeJob.stream_results()`` <qiskit_ibm_runtime.RuntimeJob#stream_results>`__.

.. _rc2-1:

0.1.0rc2
========

.. _new-features-22:

New Features
------------

-  For convenience, you can now set the ``IBM Cloud service name`` as a
   value for the account ``instance`` parameter. If you choose to set
   the name instead of the ``CRN``, the initialization time of the
   ``qiskit_ibm_runtime.IBMRuntimeService`` class is slightly higher
   because the required ``CRN`` value is internally resolved via IBM
   Cloud APIs.

.. _bug-fixes-24:

Bug Fixes
---------

-  ```qiskit_ibm_runtime.utils.json.RuntimeEncoder`` <qiskit_ibm_runtime.RuntimeEncoder>`__
   and
   ```qiskit_ibm_runtime.utils.json.RuntimeDecoder`` <qiskit_ibm_runtime.RuntimeDecoder>`__
   have been updated to handle instances of the Instruction class.

-  Fixed an issue where numpy ndarrays with object types could not be
   serialized.
   ```qiskit_ibm_runtime.utils.json.RuntimeEncoder`` <qiskit_ibm_runtime.RuntimeEncoder>`__
   and
   ```qiskit_ibm_runtime.utils.json.RuntimeDecoder`` <qiskit_ibm_runtime.RuntimeDecoder>`__
   have been updated to handle these ndarrays.

.. _rc1-1:

0.1.0rc1
========

.. _new-features-23:

New Features
------------

-  You can now pass ``instance`` parameter in the hub/group/project
   format to ``qiskit_ibm_runtime.IBMRuntimeService.jobs()`` to filter
   jobs. Currently only supported for legacy authentication.

-  You can now use the
   ```qiskit_ibm_runtime.RuntimeJob.interim_results()`` <qiskit_ibm_runtime.RuntimeJob#interim_results>`__
   method to retrieve runtime program interim results. Note that interim
   results will only be available for up to two days.

.. _upgrade-notes-23:

Upgrade Notes
-------------

-  In order to be consistent with other properties in
   ```qiskit_ibm_runtime.RuntimeJob`` <qiskit_ibm_runtime.RuntimeJob>`__
   class the job_id and backend methods have been converted to
   properties.

-  When uploading a program with
   ``qiskit_ibm_runtime.IBMRuntimeService.upload_program()``, the
   program description is now optional.

-  When printing programs with
   ``qiskit_ibm_runtime.IBMRuntimeService.pprint_programs()``,
   ``backend_requirements`` will now be listed.

.. _bug-fixes-25:

Bug Fixes
---------

-  Fixed an issue with JSON encoding and decoding when using
   ``ParameterExpression``\ s in conjunction with Qiskit Terra 0.19.1
   and above. Previously, the ``Parameter`` instances reconstructed from
   the JSON output would have different unique identifiers, causing them
   to seem unequal to the input. They will now have the correct backing
   identities.
