# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Constants used in testing."""

QASM2_SIMPLE = """
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[3];
            creg c[3];
            h q[0];
            cz q[0],q[1];
            cx q[0],q[2];
            measure q[0] -> c[0];
            measure q[1] -> c[1];
            measure q[2] -> c[2];
        """


QASM3_SIMPLE = """
            OPENQASM 3;
            include "stdgates.inc";
            bit[3] c;
            h $0;
            cz $0, $1;
            cx $0, $2;
            c[0] = measure $0;
            c[1] = measure $1;
            c[2] = measure $2;
        """


QASM3_WITH_PARAMS = """
            OPENQASM 3;
            include "stdgates.inc";
            input angle theta1;
            input angle theta2;
            bit[3] c;
            rz(theta1) $0;
            sx $0;
            rz(theta2) $0;
            cx $0, $1;
            h $1;
            cx $1, $2;
            c[0] = measure $0;
            c[1] = measure $1;
            c[2] = measure $2;
        """
