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


.PHONY: lint style test mypy test1 test2 test3

lint:
	ruff check qiskit_ibm_runtime test
	pylint -rn qiskit_ibm_runtime test
	tools/verify_headers.py qiskit_ibm_runtime test
	tools/verify_images.py

mypy:
	mypy --module qiskit_ibm_runtime --package test

style:
	black --check qiskit_ibm_runtime test

unit-test:
	python -m unittest discover --verbose --top-level-directory . --start-directory test/unit

integration-test:
	python -m unittest discover --verbose --top-level-directory . --start-directory test/integration

smoke-test:
	python -m unittest discover --verbose --top-level-directory . --start-directory test/smoke

docs-test:
	./test/docs/vale.sh

unit-test-coverage:
	coverage run -m unittest discover --verbose --top-level-directory . --start-directory test/unit
	coverage lcov

black:
	black qiskit_ibm_runtime test

ruff:
	ruff check qiskit_ibm_runtime test --fix
