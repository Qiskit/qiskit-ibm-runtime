#########################################
Manage job time limits
#########################################

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If a job exceeds this time limit, it is forcibly ended. The maximum execution time is the smaller of 1) the system limit and 2) the "max_execution_time" defined by the program. The system limit is three hours for simulator jobs and eight hours for jobs that are running on a physical system.

The maximum execution time for the Sampler primitive is 10000 seconds (2.78 hours). The maximum execution time for the Estimator primitive is 18000 seconds (5 hours).

In part, the time your job takes depends on how many iterations you make in a session and how many shots are run in each iteration. Thus, you can limit your job time by running only as many iterations and shots as you need.