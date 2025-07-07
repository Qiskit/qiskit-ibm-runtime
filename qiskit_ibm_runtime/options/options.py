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

from abc import abstractmethod
from typing import Iterable, Tuple, Union, Any
from dataclasses import dataclass, fields, asdict, is_dataclass
import copy

from qiskit.transpiler import CouplingMap
from pydantic import Field

from .utils import (
    Dict,
    UnsetType,
    Unset,
    remove_dict_unset_values,
    merge_options_v2,
    primitive_dataclass,
    remove_empty_dict,
)
from .environment_options import EnvironmentOptions
from .simulator_options import SimulatorOptions
from ..runtime_options import RuntimeOptions


def _make_data_row(indent: int, name: str, value: Any, is_section: bool) -> Iterable[str]:
    """Yield HTML table rows to format an options entry."""
    tag = "th" if is_section else "td"

    weight = " font-weight: bold;" if is_section else ""
    style = f"style='text-align: left; vertical-align: top;{weight}'"

    marker = "▸" if is_section else ""
    spacer_style = "display: inline-block; text-align: right; margin-right: 10px;"
    spacer = f"<div style='width: {20*(1 + indent)}px; {spacer_style}'>{marker}</div>"

    yield "  <tr>"
    yield f"    <{tag} {style}>{spacer}{name}</{tag}>"
    yield f"    <{tag} {style}>{type(value).__name__ if is_section else repr(value)}</{tag}>"
    yield "  </tr>"


def _iter_all_fields(
    data_cls: Any, indent: int = 0, dict_form: Union[dict, None] = None
) -> Iterable[Tuple[int, str, Any, bool]]:
    """Recursively iterate over a dataclass, yielding (indent, name, value, is_dataclass) fields."""
    # we pass dict_form through recursion simply to avoid calling asdict() more than once
    dict_form = dict_form or asdict(data_cls)

    suboptions = []
    for name, val in dict_form.items():
        if is_dataclass(subopt := getattr(data_cls, name)):
            suboptions.append((name, subopt))
        elif name != "_VERSION":
            yield (indent, name, val, False)

    # put all of the nested options at the bottom
    for name, subopt in suboptions:
        yield (indent, name, subopt, True)
        yield from _iter_all_fields(subopt, indent + 1, dict_form[name])


@dataclass
class BaseOptions:
    """Base options class."""

    @staticmethod
    @abstractmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs."""
        raise NotImplementedError()

    @staticmethod
    def _get_runtime_options(options: dict) -> dict:
        """Extract runtime options.

        Returns:
            Runtime options.
        """
        options_copy = copy.deepcopy(options)
        remove_dict_unset_values(options_copy)
        environment = options_copy.get("environment") or {}
        out = {"max_execution_time": options_copy.get("max_execution_time", None)}

        for fld in fields(RuntimeOptions):
            if fld.name in environment:
                out[fld.name] = environment[fld.name]

        if "image" in options_copy:
            out["image"] = options_copy["image"]
        elif "image" in options_copy.get("experimental", {}):
            out["image"] = options_copy["experimental"]["image"]

        return out

    def _repr_html_(self) -> str:
        """Return a string that formats this instance as an HTML table."""
        table_html = [f"<pre>{type(self).__name__}<{hex(id(self))}></pre>", "<table>"]
        for row in _iter_all_fields(self):
            table_html.extend(_make_data_row(*row))
        table_html.append("</table>")
        return "\n".join(table_html)


@primitive_dataclass
class OptionsV2(BaseOptions):
    """Base primitive options, used by v2 primitives.

    Args:
        max_execution_time: Maximum execution time in seconds, which is based
            on system execution time (not wall clock time). System execution time is
            the amount of time that the system is dedicated to processing your job.
            If a job exceeds this time limit, it is forcibly cancelled.
            Simulator jobs continue to use wall clock time.

            Refer to the
            `Max execution time documentation
            <https://quantum.cloud.ibm.com/docs/guides/max-execution-time>`_.
            for more information.

        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options.

        simulator: Simulator options. See
            :class:`SimulatorOptions` for all available options.
    """

    _VERSION: int = Field(2, frozen=True)  # pylint: disable=invalid-name

    # Options not really related to primitives.
    max_execution_time: Union[UnsetType, int] = Unset
    environment: Union[EnvironmentOptions, Dict] = Field(default_factory=EnvironmentOptions)
    simulator: Union[SimulatorOptions, Dict] = Field(default_factory=SimulatorOptions)

    def update(self, **kwargs: Any) -> None:
        """Update the options."""

        def _set_attr(_merged: dict) -> None:
            for key, val in _merged.items():
                if not key.startswith("_"):
                    setattr(self, key, val)

        merged = merge_options_v2(self, kwargs)
        _set_attr(merged)

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """

        def _set_if_exists(name: str, _inputs: dict, _options: dict) -> None:
            if name in _options:
                _inputs[name] = _options[name]

        options_copy = copy.deepcopy(options)
        output_options: dict[str, Any] = {}
        sim_options = options_copy.get("simulator", {})
        coupling_map = sim_options.get("coupling_map", Unset)
        # TODO: We can just move this to json encoder
        if isinstance(coupling_map, CouplingMap):
            sim_options["coupling_map"] = list(map(list, coupling_map.get_edges()))

        for fld in [
            "default_precision",
            "default_shots",
            "seed_estimator",
            "dynamical_decoupling",
            "resilience",
            "twirling",
            "simulator",
            "execution",
        ]:
            _set_if_exists(fld, output_options, options_copy)

        # Add arbitrary experimental options
        experimental = options_copy.get("experimental", None)
        if isinstance(experimental, dict):
            new_keys = {}
            for key in list(experimental.keys()):
                if key not in output_options:
                    new_keys[key] = experimental.pop(key)
            output_options = merge_options_v2(output_options, experimental)
            if new_keys:
                output_options["experimental"] = new_keys

        # Remove image
        output_options.get("experimental", {}).pop("image", None)

        remove_dict_unset_values(output_options)
        remove_empty_dict(output_options)

        inputs = {"options": output_options, "version": OptionsV2._VERSION, "support_qiskit": True}
        if options_copy.get("resilience_level", Unset) != Unset:
            inputs["resilience_level"] = options_copy["resilience_level"]

        return inputs
