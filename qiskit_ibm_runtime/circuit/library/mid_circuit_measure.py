# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from qiskit.circuit import annotation, Measure

class MidCircMeasurementAnnotation(annotation.Annotation):
    namespace = "qcf.mid_circ_measure"

class MCMSerializer(annotation.OpenQASM3Serializer):

    def dump(self, annotation):
        pass

    def load(self, namespace, payload):
        pass

class MidCircuitMeasure(Measure):
    """A custom specialized measurement."""

    def __init__(self, annotation_str=None):
        super().__init__()
        if annotation_str:
            if not annotation_str.startswith("measure_"):
                raise ValueError("Invalid annotation string for mid-circuit measure. It must start with `measure_`")
            self.name = annotation_str
        else:
            self.name = "measure_2"
        
        a = MidCircMeasurementAnnotation()
        a.namespace += "." + str(self.name)
        self.annotations = [a]

    def qasm3_annotation_handlers():
        return {"qcf": MCMSerializer()}

