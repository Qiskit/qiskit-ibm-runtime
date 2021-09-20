# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


.PHONY: lint style test mypy test1 test2 test3 runtime_integration experiment_integration

lint:
	pylint -rn qiskit_ibm test
	tools/verify_headers.py qiskit_ibm test

mypy:
	mypy --module qiskit_ibm

style:
	pycodestyle qiskit_ibm test

test:
	python -m unittest -v

test1:
	python -m unittest -v test/ibm/test_ibm_backend.py test/ibm/test_account_client.py test/ibm/test_ibm_job_states.py test/ibm/test_tutorials.py test/ibm/test_basic_server_paths.py test/ibm/test_proxies.py test/ibm/test_ibm_integration.py test/ibm/test_ibm_logger.py test/ibm/test_filter_backends.py test/ibm/test_registration.py

test2:
	python -m unittest -v test/ibm/test_ibm_qasm_simulator.py test/ibm/test_serialization.py test/ibm/test_jupyter.py test/ibm/test_composite_job.py test/ibm/test_random.py test/ibm/test_ibm_provider.py

test3:
	python -m unittest -v test/ibm/test_ibm_job_attributes.py test/ibm/test_ibm_job.py test/ibm/websocket/test_websocket.py test/ibm/websocket/test_websocket_integration.py

runtime_integration:
	python -m unittest -v test/ibm/runtime/test_runtime_integration.py

experiment_integration:
	python -m unittest -v test/ibm/experiment/test_experiment_data_integration.py test/ibm/experiment/test_experiment_server_integration.py