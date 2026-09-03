# Agent Instructions

## Project goals

Maintain correctness, backward compatibility, and consistency with
existing Qiskit patterns.

## Before making changes

- Read surrounding code before introducing new patterns.
- Prefer extending existing implementations over creating new abstractions.
- Keep changes narrowly scoped to the requested issue.
- Keep changes to client-facing interfaces to a minimum.

## Testing

- Add or update tests when behavior changes.
- Prefer parameterized tests over individual tests.
- Run the smallest relevant test set first.
- Avoid running the entire test suite unless necessary.
- Integration tests require live IBM Quantum credentials; request permission before running and verify existence of required env variables (`QISKIT_IBM_TOKEN`, `QISKIT_IBM_INSTANCE`, `QISKIT_IBM_URL`, `QISKIT_IBM_QPU`).
- Do not use `unittest.TestCase` directly; use the project base classes in `test/ibm_test_case.py`.
- Unit tests must not contact any external service; use `FakeBackendV2` or `QiskitRuntimeLocalService` for backend interactions.

## Constraints

- Preserve public API compatibility.
- Changes to client-facing interfaces must adhere to the deprecation policy (see `DEPRECATION.md` for the full policy), and be accompanied by a release note (see `CONTRIBUTION.md` for more details).
- The package must maintain backward compatibility when it comes to loading old jobs.
- Do not introduce new dependencies without justification.
- Follow repository linting and formatting rules (use `pre-commit run` to run checks).

## Legacy vs. executor based primitives
The package offers two sets of `SamplerV2`, `EstimatorV2` primitives. Legacy primitives, directly under `qiskit_ibm_runtime/` and executor-based primitives under `qiskit_ibm_runtime/executor_*/`. Legacy primitives have their options defined in `qiskit_ibm_runtime/options`, while the executor-based have them in `qiskit_ibm_runtime/options_models`. Verify you are working on the right set. Executor-based primitives are sometimes referred to as wrappers.

## References

- README.md
- CONTRIBUTING.md
- DEPRECATION.md
