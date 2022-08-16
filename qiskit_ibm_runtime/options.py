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

"""Primitive options."""

from typing import Optional, List, Dict, Union, Any
from dataclasses import dataclass, asdict, field
import copy

from .utils.deprecation import issue_deprecation_msg


@dataclass
class Transpilation:
    """Transpilation options."""

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
        self, noise_model: Any = None, seed_simulator: Optional[int] = None
    ) -> None:
        self.noise_model = noise_model
        self.seed_simulator = seed_simulator

    @property
    def noise_model(self) -> Dict:
        """Return the noise model.

        Returns:
            The noise model.
        """
        return self._noise_model

    @noise_model.setter
    def noise_model(self, noise_model: Any) -> None:
        """Set the noise model.

        Args:
            noise_model: Noise model to use.

        Raises:
            ValueError: If the noise model doesn't have a ``to_dict()`` method.
        """
        if isinstance(noise_model, Dict):
            self._noise_model = noise_model
        else:
            try:
                self._noise_model = noise_model.to_dict()
            except AttributeError:
                raise ValueError(
                    "Only noise models that have a to_dict() method are supported"
                )


@dataclass
class Execution:
    """Execution options."""

    shots: int = 4000
    qubit_lo_freq: Optional[List[float]] = None
    meas_lo_freq: Optional[List[float]] = None
    # TODO: need to be able to serialize schedule_los before we can support it
    rep_delay: Optional[float] = None
    init_qubits: bool = True


@dataclass
class Options:
    """Options for the primitive programs.

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

        backend: target backend to run on. This is required for ``ibm_quantum`` channel.

        log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.

        transpilation: Transpilation options.

            * skip_transpilation: Whether to skip transpilation.

            * initial_layout: Initial position of virtual qubits on physical qubits.
              See ``qiskit.compiler.transpile`` for more information.

            * layout_method: Name of layout selection pass
              ('trivial', 'dense', 'noise_adaptive', 'sabre').

            * routing_method: Name of routing pass ('basic', 'lookahead', 'stochastic', 'sabre', 'none')

            * translation_method: Name of translation pass ('unroller', 'translator', 'synthesis')

            * approximation_degree: heuristic dial used for circuit approximation
              (1.0=no approximation, 0.0=maximal approximation)

            * timing_constraints: An optional control hardware restriction on instruction time
              resolution. A quantum computer backend may report a set of restrictions, namely:

                * granularity: An integer value representing minimum pulse gate
                  resolution in units of ``dt``. A user-defined pulse gate should have
                  duration of a multiple of this granularity value.

                * min_length: An integer value representing minimum pulse gate
                  length in units of ``dt``. A user-defined pulse gate should be longer
                  than this length.

                * pulse_alignment: An integer value representing a time resolution of gate
                  instruction starting time. Gate instruction should start at time which
                  is a multiple of the alignment value.

                * acquire_alignment: An integer value representing a time resolution of measure
                  instruction starting time. Measure instruction should start at time which
                  is a multiple of the alignment value.

                  This information will be provided by the backend configuration.
                  If the backend doesn't have any restriction on the instruction time allocation,
                  then ``timing_constraints`` is None and no adjustment will be performed.

            * seed_transpiler: Sets random seed for the stochastic parts of the transpiler.

        execution: Execution time options.

            * shots: Number of repetitions of each circuit, for sampling. Default: 4000.

            * qubit_lo_freq: List of job level qubit drive LO frequencies in Hz. Overridden by
              ``schedule_los`` if specified. Must have length ``n_qubits.``

            * meas_lo_freq: List of measurement LO frequencies in Hz. Overridden by ``schedule_los`` if
              specified. Must have length ``n_qubits.``

            * schedule_los: Experiment level (ie circuit or schedule) LO frequency configurations for
              qubit drive and measurement channels. These values override the job level values from
              ``default_qubit_los`` and ``default_meas_los``. Frequencies are in Hz. Settable for qasm
              and pulse jobs.

            * rep_delay: Delay between programs in seconds. Only supported on certain
              backends (if ``backend.configuration().dynamic_reprate_enabled=True``).
              If supported, it must be from the range supplied by the backend
              (``backend.configuration().rep_delay_range``).
              Default is given by ``backend.configuration().default_rep_delay``.

            * init_qubits: Whether to reset the qubits to the ground state for each shot.
              Default: ``True``.
    """

    optimization_level: int = 1
    resilience_level: int = 0
    backend: str = None
    log_level: str = "WARNING"
    transpilation: Transpilation = field(default_factory=Transpilation)
    execution: Execution = field(default_factory=Execution)
    experimental: dict = None

    def _merge_options(self, new_options: Optional[Dict] = None) -> Dict:
        """Merge current options with the new ones.

        Args:
            new_options: New options to merge.

        Returns:
            Merged dictionary.
        """

        def _update_options(old: Dict, new: Dict) -> None:
            if not new:
                return
            for key, val in old.items():
                if key in new.keys():
                    old[key] = new.pop(key)
                if isinstance(val, Dict):
                    _update_options(val, new)

        # First combine options.
        combined = copy.deepcopy(asdict(self))
        _update_options(combined, new_options)
        return combined

    @classmethod
    def _from_dict(cls, data: Dict) -> "Options":
        data = copy.copy(data)
        experimental = None
        if "image" in data.keys():
            issue_deprecation_msg(
                msg="The 'image' option has been moved to the 'experimental' category",
                version="0.7",
                remedy="Please specify 'experimental':{'image': image} instead.",
            )
            experimental = {"image": data.pop("image")}
        if "backend_name" in data.keys():
            issue_deprecation_msg(
                msg="The keyword 'backend_name' has been deprecated",
                version="0.7",
                remedy="Please use 'backend' instead.",
            )
            data["backend"] = data.pop("backend_name")
        transp = Transpilation(**data.pop("transpilation", {}))
        execution = Execution(**data.pop("execution", {}))
        return cls(
            experimental=experimental,
            transpilation=transp,
            execution=execution,
            **data,
        )

    @staticmethod
    def _get_program_inputs(options: Dict) -> Dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitive programs.
        """
        inputs = {}
        inputs["transpilation_settings"] = options.get("transpilation", {})
        inputs["transpilation_settings"].update(
            {"optimization_settings": {"level": options.get("optimization_level")}}
        )
        inputs["resilience_settings"] = {"level": options.get("resilience_level")}
        inputs["run_options"] = options.get("execution")
        return inputs

    @staticmethod
    def _get_runtime_options(options: Dict) -> Dict:
        """Extract runtime options.

        Returns:
            Runtime options.
        """
        experimental = options.get("experimental") or {}
        return {
            "backend_name": options.get("backend"),
            "log_level": options.get("log_level"),
            "image": experimental.get("image", None),
        }
