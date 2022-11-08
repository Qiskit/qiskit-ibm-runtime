Configure error mitigation
=============================

Error mitigation techniques allow users to mitigate circuit errors by modeling the device noise at the time of execution. This typically results in quantum pre-processing overhead related to model training and classical post-processing overhead to mitigate errors in the raw results by using the generated model.  

The error mitigation techniques built in to primitives are advanced resilience options.   To specify these options, use the `resilience_level` option when submitting your job.  

The resilience level specifies how much resilience to build against errors. Higher levels generate more accurate results, at the expense of longer processing times. Resilience levels can be used to configure the cost/accuracy trade-off when applying error mitigation to your primitive query. Error mitigation reduces errors (bias) in results by processing the outputs from a collection, or ensemble, of related circuits. The degree of error reduction depends on the method applied. The resilience level abstracts the detailed choice of error mitigation method to allow users to reason about the cost/accuracy trade that is appropriate to their application.

Given this, each level corresponds to a method or methods with increasing level of quantum sampling overhead to enable you experiment with different time-accuracy tradeoffs.  The following table shows you which levels and corresponding methods are available for each of the primitives. 

.. note::
    Error mitigation is task specific so the techniques you are able to apply vary based whether you are sampling a distribution or generating expectation values. 

+------------------+-------------------------------------------------------+------------------------------------------+---------+
| Resilience Level | Definition                                            | Estimator                                | Sampler |
+==================+=======================================================+==========================================+=========+
| 0                | No mitigation                                         | None                                     | None    |
+------------------+-------------------------------------------------------+------------------------------------------+---------+
| 1 [Default]      | Minimal mitigation costs: Mitigate error associated   | Twirled Readout Error eXtinction (TREX)  | M3      |
|                  | with readout errors                                   | {Hyperlink to description}               |         |
+------------------+-------------------------------------------------------+------------------------------------------+---------+
| 2                | Medium mitigation costs. Typically reduces bias       | Zero Noise Extrapolation (ZNE)           | ---     |
|                  | in estimators, but is not guaranteed to be zero bias. | {Hyperlink to description}               |         |
+------------------+-------------------------------------------------------+------------------------------------------+---------+
| 3                | Heavy mitigation with layer sampling. Theoretically   | Probabilistic Error Cancellation (PEC)   | ---     |
|                  | expected to deliver zero bias estimators.             | {Hyperlink to description}               |         |
+------------------+-------------------------------------------------------+------------------------------------------+---------+

.. note::
    Resilience levels are currently in beta so sampling overhead and solution quality will vary from circuit to circuit. New features, advanced options and management tools will be released on a rolling basis. Specific error mitigation methods are not guaranteed to be applied at each resilience level.

Configure the Estimator with resilience levels 
-----------------------------------------------

.. raw:: html

  <details>
  <summary>Resilience Level 0</summary>

**Resilience Level 0** | No error mitigation is applied to the user program

.. raw:: html

   </details>

