End to end example
==================

As a comprehensive example, we will walk through a common use case that
would require the user to migrate code to use the Qiskit Runtime
execution model. 

Overview
--------

Recall that When choosing which primitive to use we first need to
understand whether our algorithm needs to to use a quasi-probability
distribution sampled from a quantum state (a list of
quasi-probabilities), or an expectation value of a certain observable
with respect to a quantum state (a real number). 

In our use case, the iterative amplitude estimation (IAE), we want to
discover one of the probability amplitudes of a quantum state. Thus, the
algorithm should rely on the Sampler primitive.

.. _amplitude:

Amplitude estimation use case
-----------------------------

In this example, we look at the case that uses IAE approach to solve an
estimation problem. Historically, on IBM Quantum Platform, users could
achieve this by configuring epsilon and alpha parameters on the
``QuantumInstance`` object, as shown in the code example without
primitives.

Code example without primitives
-------------------------------

.. code-block:: python

   from qiskit import BasicAer
   from qiskit.algorithms import IterativeAmplitudeEstimation, EstimationProblem
   from qiskit.utils import QuantumInstance
   from test.python.algorithms.test_amplitude_estimators import BernoulliStateIn, BernoulliGrover

   alpha = 0.05
   epsilon = 0.01
   shots = 4096
   prob = 0.3

   problem = EstimationProblem(BernoulliStateIn(prob), [0], BernoulliGrover(prob))

   quantum_instance = QuantumInstance(BasicAer.get_backend("qasm_simulator"), shots=shots)

   ae = IterativeAmplitudeEstimation(epsilon, alpha=alpha, quantum_instance=quantum_instance)

   result = ae.estimate(problem)
   print(result)

   {   'alpha': 0.05,
       'circuit_results': None,
       'confidence_interval': (0.2987743379992934, 0.30032818635526687),
       'confidence_interval_processed': (0.2987743379992934, 0.30032818635526687),
       'epsilon_estimated': 0.0007769241779867209,
       'epsilon_estimated_processed': 0.0007769241779867209,
       'epsilon_target': None,
       'estimate_intervals': [   [0.0, 1.0],
                                 [0.28906859038466726, 0.3281172229468823],
                                 [0.2987743379992934, 0.30032818635526687]],
       'estimation': 0.2995512621772801,
       'estimation_processed': 0.2995512621772801,
       'num_oracle_queries': 49152,
       'powers': [0, 0, 12],
       'ratios': [1.0, 25.0],
       'shots': None,
       'theta_intervals': [   [0, 0.25],
                              [0.09034409579253426, 0.0970743627675479],
                              [0.09203956626822991, 0.09230951130133282]]}


Migrating the code to use primitives (locally)
----------------------------------------------

.. code-block:: python

   from qiskit.algorithms import IterativeAmplitudeEstimation, EstimationProblem
   from qiskit.primitives import Sampler
   from test.python.algorithms.test_amplitude_estimators import BernoulliStateIn, BernoulliGrover


   alpha = 0.05
   epsilon = 0.01
   shots = 4096
   prob = 0.3


   problem = EstimationProblem(BernoulliStateIn(prob), [0], BernoulliGrover(prob))


   sampler = Sampler(options={"shots": shots})
   ae = IterativeAmplitudeEstimation(epsilon, alpha=alpha, sampler=sampler)


   result = ae.estimate(problem)
   print(result)


   {   'alpha': 0.05,
       'circuit_results': None,
       'confidence_interval': (0.299362359799064, 0.30061213376177465),
       'confidence_interval_processed': (0.299362359799064, 0.30061213376177465),
       'epsilon_estimated': 0.0006248869813553215,
       'epsilon_estimated_processed': 0.0006248869813553215,
       'epsilon_target': None,
       'estimate_intervals': [   [0.0, 1.0],
                                 [0.2828417741377001, 0.3216648682822661],
                                 [0.299362359799064, 0.30061213376177465]],
       'estimation': 0.2999872467804193,
       'estimation_processed': 0.2999872467804193,
       'num_oracle_queries': 61440,
       'powers': [0, 0, 15],
       'ratios': [1.0, 31.0],
       'shots': None,
       'theta_intervals': [   [0, 0.25],
                              [0.08924749081234563, 0.09597799202522334],
                              [0.09214176853962333, 0.09235879737893671]]}



Code description
----------------

The code with primitives assumes that the user is running their code
locally, hence the reference to import
``from qiskit.primitives import Sampler``. After the algorithm is
adjusted to use a primitive, we initialize the primitive and then pass
it to the algorithm.

Step 1. Decide which package to import the primitive from
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Following are some common possibilities that are currently supported:

* ``from qiskit.primitives import Sampler``

   This code imports a Sampler primitive from a reference implementation
   package. It allows for an exact or shot-based classical simulation of
   quantum circuits. For the shot-based case, a normal probability
   distribution is fixed. This is typically used  for testing purposes.

* ``from qiskit.providers.aer.primitives import Sampler``

   This code imports a Sampler primitive from Qiskit Aer ,which gives
   access to an array of quantum circuit classical simulators that are
   better optimized and more customizable than the previous option. This
   is recommended for running advanced classical simulations of quantum
   algorithms.

* ``from qiskit_ibm_runtime import Sampler``    ``from qiskit_ibm_runtime import QiskitRuntimeService``

   These imports allow us to use IBM Cloud resources for simulating
   quantum circuits classically or running them on real quantum
   hardware. This Sampler import also requires that you import
   ``QiskitRuntimeService``. 

.. note::
   
   Similar import options exist for the Estimator primitive. 

Step 2. Create the primitive instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use default settings we use the following code:

``sampler = Sampler()``

We can modify run options which are passed to the primitive as
a Python dictionary. For example, setting the number of shots, which can
be done as follows:

.. code-block:: python

   options = {"shots": 1024}
   sampler = Sampler(options=options)



To learn about other options and the Sampler primitive in general, refer
to `Getting started with the sampler
primitive <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/tutorials/how-to-getting-started-with-sampler.html>`__. 

Step 3. Use Sampler to initialize the algorithm and solve
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After we set up the Sampler, we use it to initialize the Iterative
Amplitude Estimation algorithm and run the solve method with an
estimation problem instance, as follows:

.. code-block:: python

   problem = EstimationProblem(
       state_preparation=...,
       objective_qubits=[...],
       post_processing=...,
   )

   ae = IterativeAmplitudeEstimation(epsilon, alpha=alpha, sampler=sampler)

   result = ae.estimate(problem)



Step 4. Run the program
~~~~~~~~~~~~~~~~~~~~~~~

To run the program in the cloud, we proceed as follows.

.. code-block:: python

   from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session


   from qiskit.algorithms import IterativeAmplitudeEstimation, EstimationProblem
   from test.python.algorithms.test_amplitude_estimators import BernoulliStateIn, BernoulliGrover


   QiskitRuntimeService.save_account(
       channel="ibm_cloud",
       token="",   # to be copied from the IBM Cloud account
       instance="crn:v1:bluemix:public:...",  # to be copied from the IBM Cloud account
       overwrite=True)


   service = QiskitRuntimeService()


   alpha = 0.05
   epsilon = 0.01
   shots = 4096
   prob = 0.3


   problem = EstimationProblem(BernoulliStateIn(prob), [0], BernoulliGrover(prob))


   with Session(service=service, backend="ibmq_qasm_simulator") as session:


       sampler = Sampler(session=session, options={"shots": shots})
       ae = IterativeAmplitudeEstimation(epsilon, alpha=alpha, sampler=sampler)


       result = ae.estimate(problem)
       print(result)


   {   'alpha': 0.05,
       'circuit_results': None,
       'confidence_interval': (0.29885318626264995, 0.3002060512686424),
       'confidence_interval_processed': (0.29885318626264995, 0.3002060512686424),
       'epsilon_estimated': 0.0006764325029962326,
       'epsilon_estimated_processed': 0.0006764325029962326,
       'epsilon_target': None,
       'estimate_intervals': [   [0.0, 1.0],
                                 [0.27305972046977295, 0.31198052934187037],
                                 [0.29885318626264995, 0.3002060512686424]],
       'estimation': 0.2995296187656462,
       'estimation_processed': 0.2995296187656462,
       'num_oracle_queries': 56000,
       'powers': [0, 0, 14],
       'ratios': [1.0, 29.0],
       'shots': None,
       'theta_intervals': [   [0, 0.25],
                              [0.08750981870058824, 0.09432147178617936],
                              [0.09205327398996327, 0.09228830765493014]]}



Related links
-------------

You can download the updated code here: - `Primitive-enabled Iterative Quantum Amplitude Estimation algorithm <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/amplitude_estimators/iae.py>`__
