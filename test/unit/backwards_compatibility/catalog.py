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
| --- | --- | --- | --- | --- |
| da66nicgd8dc73doc6mg | 0.49 | 3d3b9f5 | ibm_fez | test/integration/test_executor.py::TestExecutor::test_executor_with_samplex_item |
| dap6bu0pqrnc739at7i0 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_1__1000___auto____auto___1024_ |
| dap6c0f8gn2s739opacg | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_2__1000__5___auto___1000_ |
| dap6d602fm4c73f6bh0g | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_num_shots_3__1000__5__3__15_ |
| dap6d8dr85ps73fg68sg | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_with_parametric_circuits_1_True |
| dap6dbv8gn2s739opca0 | 0.49 | d3d1b8b | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler_with_parametric_circuits_2_False |
| dar64dbojkfs738nlrp0 | 0.50 | f64f2dc | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_pec_estimator |
| dar64kdvr3kc73eieu40 | 0.50 | f64f2dc | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_vanilla_estimator test_vanilla_estimator |
| dar64ptvr3kc73eieubg | 0.50 | f64f2dc | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator_1_gate_folding |
| dar65c5vr3kc73eieutg | 0.50 | f64f2dc | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator_2_pea |
| dbqvelujjaos73ai1ghg | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_vanilla_estimator |
| dbqveq1abdes73fp0ju0 | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_pec_estimator |
| dbqveuujjaos73ai1gt0 | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator[gate_folding] |
| dbqvf7mjjaos73ai1h7g | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator[pea] || dbq77dk4148s739vl7jg | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler[True] |
| dbq77gtt7fqc738afafg | 0.51 | 08f8f61 | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler[False] |
| dbqqjjok09pc73atna1g | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_vanilla_estimator |
| dbqqjoujjaos73ahoh9g | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_pec_estimator |
| dbqqjtnv5hds73dgh840 | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator[gate_folding] |
| dbqqk6ejjaos73ahoieg | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_estimator.py::TestEstimator::test_zne_estimator[pea] |
| dbqq3fmjjaos73ahnv60 | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler[True] |
| dbqq3j7v5hds73dggljg | 0.52 | c03e46c0 | ibm_fez | test/integration/test_executor_sampler.py::TestSampler::test_sampler[False] |
"""  # noqa: E501

ESTIMATOR_JOBS = {
    "0.50": [
        "dar64dbojkfs738nlrp0",
        "dar64kdvr3kc73eieu40",
        "dar64ptvr3kc73eieubg",
        "dar65c5vr3kc73eieutg",
    ],
    "0.51": [
        "dbqvelujjaos73ai1ghg",
        "dbqveq1abdes73fp0ju0",
        "dbqveuujjaos73ai1gt0",
        "dbqvf7mjjaos73ai1h7g",
    ],
    "0.52": [
        "dbqqjjok09pc73atna1g",
        "dbqqjoujjaos73ahoh9g",
        "dbqqjtnv5hds73dgh840",
        "dbqqk6ejjaos73ahoieg",
    ],
}

EXECUTOR_JOBS = {"0.49": ["da66nicgd8dc73doc6mg"]}

SAMPLER_JOBS = {
    "0.49": [
        "dap6bu0pqrnc739at7i0",
        "dap6c0f8gn2s739opacg",
        "dap6d602fm4c73f6bh0g",
        "dap6d8dr85ps73fg68sg",
        "dap6dbv8gn2s739opca0",
    ],
    "0.51": [
        "dbq77dk4148s739vl7jg",
        "dbq77gtt7fqc738afafg",
    ],
    "0.52": [
        "dbqq3fmjjaos73ahnv60",
        "dbqq3j7v5hds73dggljg",
    ],
}

NOISE_LEARNER_JOBS = {"0.52": ["dbqq38mjjaos73ahnusg"]}
