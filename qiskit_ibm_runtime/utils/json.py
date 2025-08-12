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
# pylint: disable=method-hidden
# pylint: disable=too-many-return-statements

"""Utility functions for the runtime service."""

import base64
import copy
import importlib
import inspect
import io
import json
import warnings
import zlib
from datetime import date

from typing import Any, Callable, Dict, List, Union, get_args

import dateutil.parser
import numpy as np

try:
    import scipy.sparse

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import qiskit_aer

    HAS_AER = True
except ImportError:
    HAS_AER = False

try:
    from qiskit.quantum_info import PauliLindbladMap

    HAS_PAULI_LINDBLAD_MAP = True
except ImportError:
    HAS_PAULI_LINDBLAD_MAP = False

from qiskit.circuit import (
    Instruction,
    Parameter,
    QuantumCircuit,
    QuantumRegister,
)
from qiskit.transpiler import CouplingMap
from qiskit.circuit.parametertable import ParameterView
from qiskit.result import Result
from qiskit.qpy import QPY_VERSION as QISKIT_QPY_VERSION
from qiskit.qpy import (
    load,
    dump,
)
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.qpy.binary_io.value import _write_parameter, _read_parameter
from qiskit.primitives.containers.bindings_array import BindingsArray
from qiskit.primitives.containers.observables_array import ObservablesArray
from qiskit.primitives.containers import (
    BitArray,
    DataBin,
    PubResult,
    SamplerPubResult,
    PrimitiveResult,
)

from qiskit_ibm_runtime.options.zne_options import (  # pylint: disable=ungrouped-imports
    ExtrapolatorType,
)
from qiskit_ibm_runtime.execution_span import (
    DoubleSliceSpan,
    SliceSpan,
    ExecutionSpans,
    TwirledSliceSpan,
    TwirledSliceSpanV2,
)
from qiskit_ibm_runtime.utils.estimator_pub_result import EstimatorPubResult

from .noise_learner_result import NoiseLearnerResult

SERVICE_MAX_SUPPORTED_QPY_VERSION = 14


def to_base64_string(data: str) -> str:
    """Convert string to base64 string.

    Args:
        data: string to convert

    Returns:
        data as base64 string
    """
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def _serialize_and_encode(
    data: Any, serializer: Callable, compress: bool = True, **kwargs: Any
) -> str:
    """Serialize the input data and return the encoded string.

    Args:
        data: Data to be serialized.
        serializer: Function used to serialize data.
        compress: Whether to compress the serialized data.
        kwargs: Keyword arguments to pass to the serializer.

    Returns:
        String representation.
    """
    with io.BytesIO() as buff:
        serializer(buff, data, **kwargs)
        buff.seek(0)
        serialized_data = buff.read()

    if compress:
        serialized_data = zlib.compress(serialized_data)
    return base64.standard_b64encode(serialized_data).decode("utf-8")


def _decode_and_deserialize(data: str, deserializer: Callable, decompress: bool = True) -> Any:
    """Decode and deserialize input data.

    Args:
        data: Data to be deserialized.
        deserializer: Function used to deserialize data.
        decompress: Whether to decompress.

    Returns:
        Deserialized data.
    """
    buff = io.BytesIO()
    decoded = base64.standard_b64decode(data)
    if decompress:
        decoded = zlib.decompress(decoded)

    with io.BytesIO() as buff:
        buff.write(decoded)
        buff.seek(0)
        return deserializer(buff)


def _deserialize_from_settings(mod_name: str, class_name: str, settings: Dict) -> Any:
    """Deserialize an object from its settings.

    Args:
        mod_name: Name of the module.
        class_name: Name of the class.
        settings: Object settings.

    Returns:
        Deserialized object.

    Raises:
        ValueError: If unable to find the class.
    """
    mod = importlib.import_module(mod_name)
    for name, clz in inspect.getmembers(mod, inspect.isclass):
        if name == class_name:
            return clz(**settings)
    raise ValueError(f"Unable to find class {class_name} in module {mod_name}")


def _deserialize_from_json(mod_name: str, class_name: str, json_dict: Dict) -> Any:
    """Deserialize an object from its ``_json`` dictionary.

    Args:
        mod_name: Name of the module.
        class_name: Name of the class.
        json_dict: json dictionary.

    Returns:
        Deserialized object.

    Raises:
        ValueError: If unable to find the class.
    """
    mod = importlib.import_module(mod_name)
    if clz := getattr(mod, class_name, None):
        return clz(**json_dict)
    raise ValueError(f"Unable to find class {class_name} in module {mod_name}")


def _set_int_keys_flag(obj: Dict) -> Union[Dict, List]:
    """Recursively sets '__int_keys__' flag if dictionary uses integer keys

    Args:
        obj: dictionary

    Returns:
        obj with the '__int_keys__' flag set if dictionary uses integer key
    """
    if isinstance(obj, dict):
        for k, val in list(obj.items()):
            if isinstance(k, int):
                obj["__int_keys__"] = True
            _set_int_keys_flag(val)
    return obj


def _cast_strings_keys_to_int(obj: Dict) -> Dict:
    """Casts string to int keys in dictionary when '__int_keys__' flag is set

    Args:
        obj: dictionary

    Returns:
        obj with string keys cast to int keys and '__int_keys__' flags removed
    """
    if isinstance(obj, dict):
        int_keys: List[int] = []
        for k, val in list(obj.items()):
            if "__int_keys__" in obj:
                try:
                    int_keys.append(int(k))
                except ValueError:
                    pass
            _cast_strings_keys_to_int(val)
        while len(int_keys) > 0:
            key = int_keys.pop()
            obj[key] = obj[str(key)]
            obj.pop(str(key))
        if "__int_keys__" in obj:
            del obj["__int_keys__"]
    return obj


class RuntimeEncoder(json.JSONEncoder):
    """JSON Encoder used by runtime service."""

    def default(self, obj: Any) -> Any:  # pylint: disable=arguments-differ
        if isinstance(obj, CouplingMap):
            return list(obj)
        if isinstance(obj, date):
            return {"__type__": "datetime", "__value__": obj.isoformat()}
        if isinstance(obj, complex):
            return {"__type__": "complex", "__value__": [obj.real, obj.imag]}
        if isinstance(obj, np.ndarray):
            if obj.dtype == object:
                return {"__type__": "ndarray", "__value__": obj.tolist()}
            value = _serialize_and_encode(obj, np.save, allow_pickle=False)
            return {"__type__": "ndarray", "__value__": value}
        if isinstance(obj, np.int64):
            return obj.item()
        if isinstance(obj, set):
            return {"__type__": "set", "__value__": list(obj)}
        if isinstance(obj, Result):
            return {"__type__": "Result", "__value__": obj.to_dict()}
        if hasattr(obj, "to_json"):
            return {"__type__": "to_json", "__value__": obj.to_json()}
        if isinstance(obj, QuantumCircuit):
            kwargs: Dict[str, object] = {
                "version": min(SERVICE_MAX_SUPPORTED_QPY_VERSION, QISKIT_QPY_VERSION)
            }
            value = _serialize_and_encode(
                data=obj,
                serializer=lambda buff, data: dump(
                    data, buff, RuntimeEncoder, **kwargs
                ),  # type: ignore[no-untyped-call]
            )
            return {"__type__": "QuantumCircuit", "__value__": value}
        if isinstance(obj, Parameter):
            value = _serialize_and_encode(
                data=obj,
                serializer=_write_parameter,
                compress=False,
            )
            return {"__type__": "Parameter", "__value__": value}
        if isinstance(obj, ParameterView):
            return obj.data
        if isinstance(obj, Instruction):
            kwargs = {"version": min(SERVICE_MAX_SUPPORTED_QPY_VERSION, QISKIT_QPY_VERSION)}
            # Append instruction to empty circuit
            quantum_register = QuantumRegister(obj.num_qubits)
            quantum_circuit = QuantumCircuit(quantum_register)
            quantum_circuit.append(obj, quantum_register)
            value = _serialize_and_encode(
                data=quantum_circuit,
                serializer=lambda buff, data: dump(
                    data, buff, **kwargs
                ),  # type: ignore[no-untyped-call]
            )
            return {"__type__": "Instruction", "__value__": value}
        if isinstance(obj, ObservablesArray):
            return {"__type__": "ObservablesArray", "__value__": obj.tolist()}
        if isinstance(obj, BindingsArray):
            out_val = {"shape": obj.shape}
            encoded_data = {}
            for key, val in obj.data.items():
                encoded_data[json.dumps(key, cls=RuntimeEncoder)] = val
            out_val["data"] = encoded_data
            return {"__type__": "BindingsArray", "__value__": out_val}
        if isinstance(obj, BitArray):
            out_val = {"array": obj.array, "num_bits": obj.num_bits}
            return {"__type__": "BitArray", "__value__": out_val}
        if isinstance(obj, DataBin):
            out_val = {
                "field_names": list(obj),
                "shape": obj.shape,
                "fields": dict(obj.items()),
            }
            return {"__type__": "DataBin", "__value__": out_val}
        if isinstance(obj, EstimatorPub):
            return (
                obj.circuit,
                obj.observables.tolist(),
                obj.parameter_values.as_array(obj.circuit.parameters),
                obj.precision,
            )
        if isinstance(obj, SamplerPub):
            return (
                obj.circuit,
                obj.parameter_values.as_array(obj.circuit.parameters),
                obj.shots,
            )
        if isinstance(obj, EstimatorPubResult):
            out_val = {"data": obj.data, "metadata": obj.metadata}
            return {"__type__": "EstimatorPubResult", "__value__": out_val}
        if isinstance(obj, SamplerPubResult):
            out_val = {"data": obj.data, "metadata": obj.metadata}
            return {"__type__": "SamplerPubResult", "__value__": out_val}
        if isinstance(obj, PubResult):
            out_val = {"data": obj.data, "metadata": obj.metadata}
            return {"__type__": "PubResult", "__value__": out_val}
        if isinstance(obj, PrimitiveResult):
            out_val = {"pub_results": obj._pub_results, "metadata": obj.metadata}
            return {"__type__": "PrimitiveResult", "__value__": out_val}
        if isinstance(obj, NoiseLearnerResult):
            out_val = {"data": obj.data, "metadata": obj.metadata}
            return {"__type__": "NoiseLearnerResult", "__value__": out_val}
        if isinstance(obj, DoubleSliceSpan):
            out_val = {
                "start": obj.start,
                "stop": obj.stop,
                "data_slices": {
                    idx: (shape, arg_sl.start, arg_sl.stop, shot_sl.start, shot_sl.stop)
                    for idx, (shape, arg_sl, shot_sl) in obj._data_slices.items()
                },
            }
            return {"__type__": "DoubleSliceSpan", "__value__": out_val}
        if isinstance(obj, TwirledSliceSpanV2):
            out_val = {
                "start": obj.start,
                "stop": obj.stop,
                "data_slices": {
                    idx: (x[0], x[1], x[2].start, x[2].stop, x[3].start, x[3].stop, y)
                    for idx, x, y in zip(
                        obj._data_slices.keys(), obj._data_slices.values(), obj._pub_shots.values()
                    )
                },
            }

            return {"__type__": "TwirledSliceSpanV2", "__value__": out_val}
        if isinstance(obj, TwirledSliceSpan):
            out_val = {
                "start": obj.start,
                "stop": obj.stop,
                "data_slices": {
                    idx: (x[0], x[1], x[2].start, x[2].stop, x[3].start, x[3].stop)
                    for idx, x in obj._data_slices.items()
                },
            }

            return {"__type__": "TwirledSliceSpan", "__value__": out_val}

        if isinstance(obj, SliceSpan):
            out_val = {
                "start": obj.start,
                "stop": obj.stop,
                "data_slices": {
                    idx: (shape, data_slice.start, data_slice.stop)
                    for idx, (shape, data_slice) in obj._data_slices.items()
                },
            }
            return {"__type__": "ExecutionSpan", "__value__": out_val}
        if isinstance(obj, ExecutionSpans):
            obj_type = "ExecutionSpans"
            out_val = {"spans": list(obj)}
            return {"__type__": obj_type, "__value__": out_val}
        if HAS_PAULI_LINDBLAD_MAP and isinstance(obj, PauliLindbladMap):
            out_val = {"paulis": obj.to_sparse_list(), "num_qubits": obj.num_qubits}
            return {"__type__": "PauliLindbladMap", "__value__": out_val}
        if HAS_AER and isinstance(obj, qiskit_aer.noise.NoiseModel):
            return {"__type__": "NoiseModel", "__value__": obj.to_dict()}
        if hasattr(obj, "settings"):
            return {
                "__type__": "settings",
                "__module__": obj.__class__.__module__,
                "__class__": obj.__class__.__name__,
                "__value__": _set_int_keys_flag(copy.deepcopy(obj.settings)),
            }
        if hasattr(obj, "_json"):
            return {
                "__type__": "_json",
                "__module__": obj.__class__.__module__,
                "__class__": obj.__class__.__name__,
                "__value__": _set_int_keys_flag(copy.deepcopy(obj._json())),
            }
        if callable(obj):
            warnings.warn(f"Callable {obj} is not JSON serializable and will be set to None.")
            return None
        if HAS_SCIPY and isinstance(obj, scipy.sparse.spmatrix):
            value = _serialize_and_encode(obj, scipy.sparse.save_npz, compress=False)
            return {"__type__": "spmatrix", "__value__": value}
        return super().default(obj)


class RuntimeDecoder(json.JSONDecoder):
    """JSON Decoder used by runtime service."""

    def __init__(self, *args: Any, **kwargs: Any):
        if "encoding" in kwargs:
            kwargs.pop("encoding")
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj: Any) -> Any:
        """Called to decode object."""
        if "__type__" in obj:
            obj_type = obj["__type__"]
            obj_val = obj["__value__"]

            if obj_type == "datetime":
                return dateutil.parser.parse(obj_val)
            if obj_type == "complex":
                return obj_val[0] + 1j * obj_val[1]
            if obj_type == "ndarray":
                if obj_val in get_args(ExtrapolatorType):
                    return obj_val
                if isinstance(obj_val, (int, list)):
                    return np.array(obj_val)
                return _decode_and_deserialize(obj_val, np.load)
            if obj_type == "set":
                return set(obj_val)
            if obj_type == "QuantumCircuit":
                return _decode_and_deserialize(obj_val, load)[0]
            if obj_type == "Parameter":
                return _decode_and_deserialize(obj_val, _read_parameter, False)
            if obj_type == "Instruction":
                # Standalone instructions are encoded as the sole instruction in a QPY serialized circuit
                # to deserialize load qpy circuit and return first instruction object in that circuit.
                circuit = _decode_and_deserialize(obj_val, load)[0]
                return circuit.data[0][0]
            if obj_type == "settings":
                if obj["__module__"].startswith(
                    "qiskit.quantum_info.operators",
                ):
                    return _deserialize_from_settings(
                        mod_name=obj["__module__"],
                        class_name=obj["__class__"],
                        settings=_cast_strings_keys_to_int(obj_val),
                    )
            if obj_type == "_json":
                if obj["__module__"] == "qiskit_ibm_runtime.utils.noise_learner_result":
                    return _deserialize_from_json(
                        mod_name=obj["__module__"],
                        class_name=obj["__class__"],
                        json_dict=_cast_strings_keys_to_int(obj_val),
                    )
            if obj_type == "Result":
                return Result.from_dict(obj_val)
            if obj_type == "spmatrix":
                return _decode_and_deserialize(obj_val, scipy.sparse.load_npz, False)
            if obj_type == "ObservablesArray":
                return ObservablesArray(obj_val)
            if obj_type == "BindingsArray":
                ba_kwargs = {"shape": obj_val.get("shape", None)}
                data = obj_val.get("data", None)
                if isinstance(data, dict):
                    decoded_data = {}
                    for key, val in data.items():
                        # Convert to tuple or it can't be a key
                        decoded_key = tuple(json.loads(key, cls=RuntimeDecoder))
                        decoded_data[decoded_key] = val
                    ba_kwargs["data"] = decoded_data
                elif data:
                    raise ValueError(f"Unexpected data type {type(data)} in BindingsArray.")
                return BindingsArray(**ba_kwargs)
            if obj_type == "BitArray":
                return BitArray(**obj_val)
            if obj_type == "DataBin":
                shape = obj_val["shape"]
                if shape is not None and isinstance(shape, list):
                    shape = tuple(shape)
                return DataBin(shape=shape, **obj_val["fields"])
            if obj_type == "EstimatorPubResult":
                return EstimatorPubResult(**obj_val)
            if obj_type == "SamplerPubResult":
                return SamplerPubResult(**obj_val)
            if obj_type == "PubResult":
                return PubResult(**obj_val)
            if obj_type == "PrimitiveResult":
                return PrimitiveResult(**obj_val)
            if obj_type == "NoiseLearnerResult":
                return NoiseLearnerResult(**obj_val)
            if obj_type == "DoubleSliceSpan":
                obj_val["data_slices"] = {
                    int(idx): (tuple(shape), slice(arg0, arg1), slice(shot0, shot1))
                    for idx, (shape, arg0, arg1, shot0, shot1) in obj_val["data_slices"].items()
                }
                return DoubleSliceSpan(**obj_val)
            if obj_type == "TwirledSliceSpanV2":
                obj_val["data_slices"] = {
                    int(idx): (
                        tuple(shape),
                        at_start,
                        slice(arg0, arg1),
                        slice(shot0, shot1),
                        pub_shots,
                    )
                    for idx, (shape, at_start, arg0, arg1, shot0, shot1, pub_shots) in obj_val[
                        "data_slices"
                    ].items()
                }
                return TwirledSliceSpanV2(**obj_val)
            if obj_type == "TwirledSliceSpan":
                obj_val["data_slices"] = {
                    int(idx): (tuple(shape), at_start, slice(arg0, arg1), slice(shot0, shot1))
                    for idx, (shape, at_start, arg0, arg1, shot0, shot1) in obj_val[
                        "data_slices"
                    ].items()
                }
                return TwirledSliceSpan(**obj_val)
            if obj_type == "ExecutionSpan":
                new_slices = {
                    int(idx): (tuple(shape), slice(*sl_args))
                    for idx, (shape, *sl_args) in obj_val["data_slices"].items()
                }
                obj_val["data_slices"] = new_slices
                return SliceSpan(**obj_val)
            if obj_type == "ExecutionSpanCollection":
                # this is the old name of the class that we still maintain support for
                return ExecutionSpans(**obj_val)
            if obj_type == "ExecutionSpans":
                return ExecutionSpans(**obj_val)
            if HAS_PAULI_LINDBLAD_MAP and obj_type == "PauliLindbladMap":
                return PauliLindbladMap.from_sparse_list(
                    [tuple(pauli) for pauli in obj_val["paulis"]], num_qubits=obj_val["num_qubits"]
                )
            if obj_type == "to_json":
                return obj_val
            if obj_type == "NoiseModel":
                if HAS_AER:
                    return qiskit_aer.noise.NoiseModel.from_dict(obj_val)
                warnings.warn("Qiskit Aer is needed to restore noise model.")
                return obj_val
        return obj
