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

"""Catalog of jobs for backwards compatibility tests.

List of stored jobs:

| Job ID | Version | Commit hash | Backend | Notes |
| --- | --- | --- | --- |
| da66nicgd8dc73doc6mg | 0.49 | 3d3b9f5 | ibm_fez | test/integration/test_executor.py::TestExecutor::test_executor_with_samplex_item |
| dap6ae82fm4c73f6bd80 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_pec_estimator |
| dap6aj0pqrnc739at5v0 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_vanilla_estimator test_vanilla_estimator |
| dap6anlr85ps73fg65kg | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator_1_gate_folding |
| dap6b002fm4c73f6bdug | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator_2_pea |
| dap6bu0pqrnc739at7i0 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_1__1000___auto____auto___1024_ |
| dap6c0f8gn2s739opacg | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_2__1000__5___auto___1000_ |
| dap6d602fm4c73f6bh0g | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_3__1000__5__3__15_ |
| dap6d8dr85ps73fg68sg | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_with_parametric_circuits_1_True |
| dap6dbv8gn2s739opca0 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_with_parametric_circuits_2_False |
"""  # noqa: E501

ESTIMATOR_JOBS = {
    "0.49": [
        "dap6ae82fm4c73f6bd80",
        "dap6aj0pqrnc739at5v0",
        "dap6anlr85ps73fg65kg",
        "dap6b002fm4c73f6bdug",
    ]
}

EXECUTOR_JOBS = {"0.49": ["da66nicgd8dc73doc6mg"]}

SAMPLER_JOBS = {
    "0.49": [
        "dap6bu0pqrnc739at7i0",
        "dap6c0f8gn2s739opacg",
        "dap6d602fm4c73f6bh0g",
        "dap6d8dr85ps73fg68sg",
        "dap6dbv8gn2s739opca0",
    ]
}
