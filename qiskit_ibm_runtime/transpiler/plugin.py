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

"""Plugin for IBM provider backend transpiler stages."""

import re
from typing import Optional

from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler import passes

from qiskit.version import __version__ as _terra_version_string

from qiskit_ibm_runtime.transpiler.passes.basis import (
    ConvertIdToDelay,
    FoldRzzAngle,
)

_TERRA_VERSION = tuple(
    int(x) for x in re.match(r"\d+\.\d+\.\d", _terra_version_string).group(0).split(".")[:3]
)


class IBMTranslationPlugin(PassManagerStagePlugin):
    """A translation stage plugin for targeting Qiskit circuits
    to IBM Quantum systems."""

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: Optional[int] = None,
    ) -> PassManager:
        """Build IBMTranslationPlugin PassManager."""

        if _TERRA_VERSION[0] == 1:
            legacy_options = {"backend_props": pass_manager_config.backend_properties}
        else:
            legacy_options = {}

        translator_pm = common.generate_translation_passmanager(
            target=pass_manager_config.target,
            basis_gates=pass_manager_config.basis_gates,
            approximation_degree=pass_manager_config.approximation_degree,
            coupling_map=pass_manager_config.coupling_map,
            unitary_synthesis_method=pass_manager_config.unitary_synthesis_method,
            unitary_synthesis_plugin_config=pass_manager_config.unitary_synthesis_plugin_config,
            hls_config=pass_manager_config.hls_config,
            qubits_initially_zero=pass_manager_config.qubits_initially_zero,
            **legacy_options,
        )

        plugin_passes = []
        instruction_durations = pass_manager_config.instruction_durations
        if instruction_durations:
            plugin_passes.append(ConvertIdToDelay(instruction_durations))

        return PassManager(plugin_passes) + translator_pm


class IBMDynamicTranslationPlugin(PassManagerStagePlugin):
    """A translation stage plugin for targeting Qiskit circuits
    to IBM Quantum systems."""

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: Optional[int] = None,
    ) -> PassManager:
        """Build IBMTranslationPlugin PassManager."""

        if _TERRA_VERSION[0] == 1:
            legacy_options = {"backend_props": pass_manager_config.backend_properties}
        else:
            legacy_options = {}

        translator_pm = common.generate_translation_passmanager(
            target=pass_manager_config.target,
            basis_gates=pass_manager_config.basis_gates,
            approximation_degree=pass_manager_config.approximation_degree,
            coupling_map=pass_manager_config.coupling_map,
            unitary_synthesis_method=pass_manager_config.unitary_synthesis_method,
            unitary_synthesis_plugin_config=pass_manager_config.unitary_synthesis_plugin_config,
            hls_config=pass_manager_config.hls_config,
            **legacy_options,
        )

        instruction_durations = pass_manager_config.instruction_durations
        plugin_passes = []
        if pass_manager_config.target is not None:
            id_supported = "id" in pass_manager_config.target
        else:
            id_supported = "id" in pass_manager_config.basis_gates

        if instruction_durations and not id_supported:
            plugin_passes.append(ConvertIdToDelay(instruction_durations))

        if (convert_pass := getattr(passes, "ConvertConditionsToIfOps", None)) is not None:
            # If `None`, we're dealing with Qiskit 2.0+ where it's unnecessary anyway.
            plugin_passes += [convert_pass()]  # pylint: disable=not-callable

        return PassManager(plugin_passes) + translator_pm


class IBMFractionalTranslationPlugin(PassManagerStagePlugin):
    """A translation stage plugin for targeting Qiskit circuits
    to IBM Quantum systems with fractional gate support.

    Currently coexistence of fractional gate operations and
    dynamic circuits is not assumed.
    """

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: Optional[int] = None,
    ) -> PassManager:
        """Build IBMTranslationPlugin PassManager."""

        if _TERRA_VERSION[0] == 1:
            legacy_options = {"backend_props": pass_manager_config.backend_properties}
        else:
            legacy_options = {}

        translator_pm = common.generate_translation_passmanager(
            target=pass_manager_config.target,
            basis_gates=pass_manager_config.basis_gates,
            approximation_degree=pass_manager_config.approximation_degree,
            coupling_map=pass_manager_config.coupling_map,
            unitary_synthesis_method=pass_manager_config.unitary_synthesis_method,
            unitary_synthesis_plugin_config=pass_manager_config.unitary_synthesis_plugin_config,
            hls_config=pass_manager_config.hls_config,
            **legacy_options,
        )

        instruction_durations = pass_manager_config.instruction_durations
        pre_passes = []
        post_passes = []
        target = pass_manager_config.target or pass_manager_config.basis_gates
        if instruction_durations and not "id" in target:
            pre_passes.append(ConvertIdToDelay(instruction_durations))
        if "rzz" in target:
            # Apply this pass after SU4 is translated.
            post_passes.append(FoldRzzAngle())
        return PassManager(pre_passes) + translator_pm + PassManager(post_passes)
