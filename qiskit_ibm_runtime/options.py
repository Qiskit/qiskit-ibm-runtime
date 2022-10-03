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

from typing import Optional, List, Union, Any, ClassVar, TYPE_CHECKING
from typing import Dict as DictType
from dataclasses import dataclass, asdict, fields, field, make_dataclass
import copy

from .utils.deprecation import issue_deprecation_msg
from .runtime_options import RuntimeOptions

if TYPE_CHECKING:
    try:
        import qiskit_aer
        HAS_AER = True
    except ImportError:
        HAS_AER = False


def _flexible(cls):  # type: ignore
    """Decorator used to allow a flexible dataclass.

    This is used to dynamically create a new dataclass with the
    arbitrary kwargs input converted to fields. It also converts
    input dictionary to objects based on the _obj_fields attribute.
    """

    def __new__(cls, *args, **kwargs):  # type: ignore
        def _to_obj(cls_, data):  # type: ignore
            if data is None:
                return cls_()
            if isinstance(data, cls_):
                return data
            if isinstance(data, dict):
                return cls_(**data)
            raise TypeError(
                f"{data} has an unspported type {type(data)}. It can only be {cls_} or a dictionary."
            )

        updated_kwargs = copy.deepcopy(kwargs)
        all_fields = []
        orig_field_names = set()
        obj_fields = getattr(cls, "_obj_fields", {})

        for fld in fields(cls):
            all_fields.append((fld.name, fld.type, fld))
            orig_field_names.add(fld.name)

        for key, val in updated_kwargs.items():
            if key not in orig_field_names:
                all_fields.append((key, type(val), field(default=None)))
            elif key in obj_fields:
                updated_kwargs[key] = _to_obj(obj_fields[key], val)

        new_cls = make_dataclass(
            cls.__name__,
            all_fields,
            bases=(cls,),
        )
        obj = object.__new__(new_cls)
        obj.__init__(*args, **updated_kwargs)
        return obj

    cls.__new__ = __new__
    return cls


class Dict:
    """Fake Dict type.

    This class is used to show dictionary as an acceptable type in docs without
    attaching all the dictionary attributes in Jupyter's auto-complete.
    """
    pass


@_flexible
@dataclass
class TranspilationOptions:
    """Transpilation options."""

    # TODO: Double check transpilation settings.

    skip_transpilation: bool = False
    initial_layout: Optional[Union[dict, List]] = None  # TODO: Support Layout
    layout_method: Optional[str] = None
    routing_method: Optional[str] = None
    translation_method: Optional[str] = None
    approximation_degree: Optional[float] = None
    timing_constraints: Optional[DictType[str, int]] = None
    seed_transpiler: Optional[int] = None


@_flexible
@dataclass
class ResilienceOptions:
    """Resilience options."""

    pass


@_flexible
@dataclass()
class SimulatorOptions:
    """Simulator options.

    For best practice in simulating a backend make sure to pass the
    basis gates and coupling map of that backend.

    Args:
        noise_model: Noise model for the simulator.
        seed_simulator: Random seed to control sampling.
        coupling_map: Directed coupling map to target in mapping. If
            the coupling map is symmetric, both directions need to be specified.
            Each entry in the list specifies a directed two-qubit interactions,
               e.g: ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``
        basis_gates: List of basis gate names to unroll to
            (e.g: ``['u1', 'u2', 'u3', 'cx']``). If ``None``, do not unroll.
    """

    noise_model: Optional[Union[dict, "qiskit_aer.noise.noise_model.NoiseModel"]] = None
    seed_simulator: Optional[int] = None
    coupling_map: Optional[List[List[int]]] = None
    basis_gates: Optional[List[str]] = None


@_flexible
@dataclass
class ExecutionOptions:
    """Execution options."""

    shots: int = 4000
    qubit_lo_freq: Optional[List[float]] = None
    meas_lo_freq: Optional[List[float]] = None
    # TODO: need to be able to serialize schedule_los before we can support it
    rep_delay: Optional[float] = None
    init_qubits: bool = True


@_flexible
@dataclass
class EnvironmentOptions:
    """Options related to the execution environment."""

    log_level: str = "WARNING"
    image: Optional[str] = None
    instance: Optional[str] = None


@_flexible
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

        environment: Options related to the execution environment.

            * log_level: logging level to set in the execution environment. The valid
              log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
              The default level is ``WARNING``.

            * image: The runtime image used to execute the program, specified in
              the form of ``image_name:tag``. Not all accounts are
              authorized to select a different image.

            * instance: The hub/group/project to use, in that format. This is only supported
                for ``ibm_quantum`` channel. If ``None``, a hub/group/project that provides
                access to the target backend is randomly selected.
    """

    optimization_level: int = 1
    resilience_level: int = 0
    transpilation: Union[TranspilationOptions, Dict] = field(
        default_factory=TranspilationOptions
    )
    execution: Union[ExecutionOptions, Dict] = field(default_factory=ExecutionOptions)
    environment: Union[EnvironmentOptions, Dict] = field(
        default_factory=EnvironmentOptions
    )
    simulator: Union[SimulatorOptions, Dict] = field(default_factory=SimulatorOptions)

    _obj_fields: ClassVar[dict] = {
        "transpilation": TranspilationOptions,
        "execution": ExecutionOptions,
        "environment": EnvironmentOptions,
        "simulator": SimulatorOptions,
    }

    @classmethod
    def _from_dict(cls, data: dict) -> "Options":
        data = copy.copy(data)
        if "image" in data.keys():
            issue_deprecation_msg(
                msg="The 'image' option has been moved to the 'environment' category",
                version="0.7",
                remedy="Please specify 'environment':{'image': image} instead.",
            )
        environment = EnvironmentOptions(image=data.pop("image", None))
        transp = TranspilationOptions(**data.pop("transpilation", {}))
        execution = ExecutionOptions(**data.pop("execution", {}))
        return cls(
            environment=environment,
            transpilation=transp,
            execution=execution,
            **data,
        )

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
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
        inputs["run_options"].update(options.get("simulator"))

        known_keys = Options.__dataclass_fields__.keys()
        # Add additional unknown keys.
        for key in options.keys():
            if key not in known_keys:
                inputs[key] = options[key]
        return inputs

    @staticmethod
    def _get_runtime_options(options: dict) -> dict:
        """Extract runtime options.

        Returns:
            Runtime options.
        """
        # default_env = asdict(EnvironmentOptions())
        environment = options.get("environment") or {}
        out = {}

        for fld in fields(RuntimeOptions):
            if fld.name in environment:
                out[fld.name] = environment[fld.name]

        return out

    def _merge_options(self, new_options: Optional[dict] = None) -> dict:
        """Merge current options with the new ones.

        Args:
            new_options: New options to merge.

        Returns:
            Merged dictionary.
        """

        def _update_options(old: dict, new: dict) -> None:
            if not new:
                return
            for key, val in old.items():
                if key in new.keys():
                    old[key] = new.pop(key)
                if isinstance(val, dict):
                    _update_options(val, new)

        combined = asdict(self)
        # First update values of the same key.
        _update_options(combined, new_options)
        # Add new keys.
        for key, val in new_options.items():
            if key not in combined:
                combined[key] = val
        return combined
