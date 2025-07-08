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

"""Serializer for runtime annotations."""

import io
import struct
from collections import namedtuple
from typing import Any, cast

from qiskit.circuit.annotation import Annotation, QPYSerializer

from qiskit_ibm_runtime.annotations import InjectNoise, Twirl
from qiskit_ibm_runtime.annotations.decomposition_mode import DecompositionLiteral
from qiskit_ibm_runtime.annotations.dressing_mode import DressingLiteral
from qiskit_ibm_runtime.annotations.twirl import GroupLiteral

RUNTIME_ANNOTATION_PACK = "!H"
RUNTIME_ANNOTATION_SIZE = struct.calcsize(RUNTIME_ANNOTATION_PACK)
RUNTIME_ANNOTATION = namedtuple("RUNTIME_ANNOTATION", ["name_size"])

INJECT_NOISE_ANNOTATION_PACK = "!Q"
INJECT_NOISE_ANNOTATION_SIZE = struct.calcsize(INJECT_NOISE_ANNOTATION_PACK)
INJECT_NOISE_ANNOTATION = namedtuple("INJECT_NOISE_ANNOTATION", ["ref_size"])

TWIRL_ANNOTATION_PACK = "!QQQ"
TWIRL_ANNOTATION_SIZE = struct.calcsize(TWIRL_ANNOTATION_PACK)
TWIRL_ANNOTATION = namedtuple(
    "TWIRL_ANNOTATION", ["group_size", "dressing_size", "decomposition_size"]
)


class AnnotationSerializer(QPYSerializer):
    """Serializer for annotations in the 'runtime' namespace."""

    def dump_annotation(self, namespace: str, annotation: Any) -> bytes:
        annotation_name = type(annotation).__name__.encode()
        runtime_annotation = (
            struct.pack(RUNTIME_ANNOTATION_PACK, len(annotation_name)) + annotation_name
        )
        if isinstance(annotation, InjectNoise):
            ref = annotation.ref.encode()
            annotation_raw = struct.pack(INJECT_NOISE_ANNOTATION_PACK, len(ref))
            return runtime_annotation + annotation_raw + ref
        if isinstance(annotation, Twirl):
            group = annotation.group.encode()
            dressing = annotation.dressing.encode()
            decomposition = annotation.decomposition.encode()
            annotation_raw = struct.pack(
                TWIRL_ANNOTATION_PACK, len(group), len(dressing), len(decomposition)
            )
            return runtime_annotation + annotation_raw + group + dressing + decomposition
        return NotImplemented

    def load_annotation(self, payload: bytes) -> Annotation:
        buff = io.BytesIO(payload)
        annotation = RUNTIME_ANNOTATION._make(
            struct.unpack(RUNTIME_ANNOTATION_PACK, buff.read(RUNTIME_ANNOTATION_SIZE))
        )
        if (name := buff.read(annotation.name_size).decode()) == "InjectNoise":
            inject_noise = INJECT_NOISE_ANNOTATION._make(
                struct.unpack(INJECT_NOISE_ANNOTATION_PACK, buff.read(INJECT_NOISE_ANNOTATION_SIZE))
            )
            ref = buff.read(inject_noise.ref_size).decode()
            return InjectNoise(ref)
        if name == "Twirl":
            twirl = TWIRL_ANNOTATION._make(
                struct.unpack(TWIRL_ANNOTATION_PACK, buff.read(TWIRL_ANNOTATION_SIZE))
            )
            group = cast(GroupLiteral, buff.read(twirl.group_size).decode())
            dressing = cast(DressingLiteral, buff.read(twirl.dressing_size).decode())
            decomposition = cast(DecompositionLiteral, buff.read(twirl.decomposition_size).decode())
            return Twirl(group, dressing, decomposition)
