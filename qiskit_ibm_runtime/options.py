# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Primitive settings."""

from typing import Optional, List, Dict, Union, Any
from dataclasses import dataclass, asdict
import logging

from .exceptions import IBMInputValueError
from .utils.deprecation import issue_deprecation_msg


@dataclass
class Transpilation:
    """Transpilation settings.

    Args:
        skip_transpilation: Whether to skip transpilation.

        initial_layout: Initial position of virtual qubits on physical qubits.
            See :function:`qiskit.compiler.transpile` for more information.

        layout_method: Name of layout selection pass ('trivial', 'dense', 'noise_adaptive', 'sabre')

        routing_method: Name of routing pass ('basic', 'lookahead', 'stochastic', 'sabre', 'none')

        translation_method: Name of translation pass ('unroller', 'translator', 'synthesis')

        approximation_degree (float): heuristic dial used for circuit approximation
            (1.0=no approximation, 0.0=maximal approximation)

        timing_constraints: An optional control hardware restriction on instruction time resolution.
            A quantum computer backend may report a set of restrictions, namely:

            - granularity: An integer value representing minimum pulse gate
              resolution in units of ``dt``. A user-defined pulse gate should have
              duration of a multiple of this granularity value.
            - min_length: An integer value representing minimum pulse gate
              length in units of ``dt``. A user-defined pulse gate should be longer
              than this length.
            - pulse_alignment: An integer value representing a time resolution of gate
              instruction starting time. Gate instruction should start at time which
              is a multiple of the alignment value.
            - acquire_alignment: An integer value representing a time resolution of measure
              instruction starting time. Measure instruction should start at time which
              is a multiple of the alignment value.

            This information will be provided by the backend configuration.
            If the backend doesn't have any restriction on the instruction time allocation,
            then ``timing_constraints`` is None and no adjustment will be performed.

        seed_transpiler: Sets random seed for the stochastic parts of the transpiler
    """

    # TODO: Double check transpilation settings.

    skip_transpilation: bool = False
    initial_layout: Optional[Union[Dict, List]] = None  # TODO: Support Layout
    layout_method: Optional[str] = None
    routing_method: Optional[str] = None
    translation_method: Optional[str] = None
    approximation_degree: Optional[float] = None
    timing_constraints: Optional[Dict[str, int]] = None
    seed_transpiler: Optional[int] = None


@dataclass
class Resilience:
    """Resilience settings."""

    pass


@dataclass
class SimulatorOptions:
    """Simulator options.

    Args:
        noise_model: Noise model, must have a to_dict() method.
        seed_simulator: Random seed to control sampling.
    """

    def __init__(
        self,
        noise_model: Any = None,
        seed_simulator: Optional[int] = None
        ) -> None:
        self.noise_model = noise_model
        self.seed_simulator = seed_simulator

    @property
    def noise_model(self) -> Dict:
        return self._noise_model

    @noise_model.setter
    def noise_model(self, noise_model: Any) -> None:
        if isinstance(noise_model, Dict):
            self._noise_model = noise_model
        else:
            try:
                self._noise_model = noise_model.to_dict()
            except AttributeError:
                raise ValueError("Only noise models that have a to_dict() method are supported")


@dataclass
class Execution:
    """Execution options."""

    shots: int = 1024
    qubit_lo_freq: Optional[List[float]] = None
    meas_lo_freq: Optional[List[float]] = None
    # TODO: need to be able to serialize schedule_los before we can support it
    rep_delay: Optional[float] = None
    init_qubits: bool = True


@dataclass
class Options:
    """Primitive options.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times.

            * 0: no optimization
            * 1: light optimization
            * 2: heavy optimization
            * 3: even heavier optimization

        resilience_level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times.

            * 0: no resilience
            * 1: light resilience

        log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.

        backend: target backend to run on. This is required for ``ibm_quantum`` runtime.

        log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.

        transpilation: Transpilation options. See :class:`Transpilation`.


    """

    optimization_level: int = 1
    resilience_level: int = 0
    backend: str = None
    log_level: str = "WARNING"
    transpilation: Transpilation = Transpilation()
    execution: Execution = Execution()
    experimental: dict = None

    def _to_program_inputs(self, run_options: Dict = None) -> Dict:
        # TODO: Remove this once primitive program is updated to use optimization_level.
        transpilation_settings = asdict(self.transpilation)
        transpilation_settings["optimization_settings"] = {
            "level": self.optimization_level
        }
        combined_run_options = asdict(self.execution)
        if run_options:
            combined_run_options.update(run_options)
        return {
            "resilience_settings": {"level": self.resilience_level},
            "transpilation_settings": transpilation_settings,
            "run_options": combined_run_options
        }

    def _to_runtime_options(self) -> Dict:
        runtime_options =  {
            "backend_name": self.backend,
            "log_level": self.log_level,
        }
        if self.experimental:
            runtime_options["image"] = self.experimental.get("image", None)

    def _validate(self, channel: str) -> None:
        """Validate options.

        Args:
            channel: channel type.

        Raises:
            IBMInputValueError: If one or more option is invalid.
        """
        if channel == "ibm_quantum" and not self.backend:
            raise IBMInputValueError(
                '"backend" is required field in "options" for ``ibm_quantum`` runtime.'
            )

        if self.log_level and not isinstance(
            logging.getLevelName(self.log_level.upper()), int
        ):
            raise IBMInputValueError(
                f"{self.log_level} is not a valid log level. The valid log levels are: `DEBUG`, "
                f"`INFO`, `WARNING`, `ERROR`, and `CRITICAL`."
            )

    @classmethod
    def _from_dict(cls, data: Dict):
        experimental = None
        if "image" in data.keys():
            issue_deprecation_msg(
                msg="The 'image' option has been moved to the 'experimental' category",
                version="0.7",
                remedy="Please specify 'experimental':{'image': image} instead."
            )
            experimental = {"image": data.pop("image")}
        return cls(**data, experimental=experimental)
