# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fake circuit schedule timing data input."""

from qiskit.primitives.containers import DataBin, SamplerPubResult


class FakeCircuitScheduleInputData:
    """Circuit schedule timing mock data for testing."""

    sampler_pub_result_large = SamplerPubResult(
        data=DataBin(),
        metadata={
            "compilation": {
                "scheduler_timing": {
                    "timing": (
                        "main,barrier,Qubit 0,7,0,barrier\n"
                        "main,barrier,Qubit 1,7,0,barrier\n"
                        "main,barrier,Qubit 2,7,0,barrier\n"
                        "main,barrier,Qubit 3,7,0,barrier\n"
                        "main,barrier,Qubit 4,7,0,barrier\n"
                        "main,barrier,Qubit 5,7,0,barrier\n"
                        "main,reset_0,Qubit 0,7,64,play\n"
                        "main,reset_0,Qubit 0,71,108,play\n"
                        "main,reset_0,AWGR0_0,118,325,capture\n"
                        "main,reset_0,Qubit 0,179,64,play\n"
                        "main,reset_0,Qubit 0,243,64,play\n"
                        "main,reset_0,Qubit 0,577,8,play\n"
                        "main,reset_1,Qubit 1,7,64,play\n"
                        "main,reset_1,Qubit 1,71,108,play\n"
                        "main,reset_1,AWGR0_1,118,325,capture\n"
                        "main,reset_1,Qubit 1,179,64,play\n"
                        "main,reset_1,Qubit 1,243,64,play\n"
                        "main,reset_1,Qubit 1,577,8,play\n"
                        "main,reset_2,Qubit 2,7,64,play\n"
                        "main,reset_2,Qubit 2,71,108,play\n"
                        "main,reset_2,AWGR0_2,118,325,capture\n"
                        "main,reset_2,Qubit 2,179,64,play\n"
                        "main,reset_2,Qubit 2,243,64,play\n"
                        "main,reset_2,Qubit 2,577,8,play\n"
                        "main,reset_3,Qubit 3,7,64,play\n"
                        "main,reset_3,Qubit 3,71,108,play\n"
                        "main,reset_3,AWGR0_3,118,325,capture\n"
                        "main,reset_3,Qubit 3,179,64,play\n"
                        "main,reset_3,Qubit 3,243,64,play\n"
                        "main,reset_3,Qubit 3,577,8,play\n"
                        "main,reset_4,Qubit 4,7,64,play\n"
                        "main,reset_4,Qubit 4,71,108,play\n"
                        "main,reset_4,AWGR1_0,118,325,capture\n"
                        "main,reset_4,Qubit 4,179,64,play\n"
                        "main,reset_4,Qubit 4,243,64,play\n"
                        "main,reset_4,Qubit 4,577,8,play\n"
                        "main,reset_5,Qubit 5,7,64,play\n"
                        "main,reset_5,Qubit 5,71,108,play\n"
                        "main,reset_5,AWGR1_1,118,325,capture\n"
                        "main,reset_5,Qubit 5,179,64,play\n"
                        "main,reset_5,Qubit 5,243,64,play\n"
                        "main,reset_5,Qubit 5,577,8,play\n"
                        "main,barrier,Qubit 0,585,0,barrier\n"
                        "main,barrier,Qubit 1,585,0,barrier\n"
                        "main,barrier,Qubit 2,585,0,barrier\n"
                        "main,barrier,Qubit 3,585,0,barrier\n"
                        "main,barrier,Qubit 4,585,0,barrier\n"
                        "main,barrier,Qubit 5,585,0,barrier\n"
                        "main,x_0,Qubit 0,585,8,play\n"
                        "main,x_2,Qubit 2,585,8,play\n"
                        "main,x_4,Qubit 4,585,8,play\n"
                        "main,barrier,Qubit 0,593,0,barrier\n"
                        "main,barrier,Qubit 2,593,0,barrier\n"
                        "main,barrier,Qubit 4,593,0,barrier\n"
                        "main,measure_0,Qubit 0,593,64,play\n"
                        "main,measure_0,Qubit 0,657,108,play\n"
                        "main,measure_0,AWGR0_0,704,325,capture\n"
                        "main,measure_0,Qubit 0,765,64,play\n"
                        "main,measure_0,Qubit 0,829,64,play\n"
                        "main,measure_2,Qubit 2,593,64,play\n"
                        "main,measure_2,Qubit 2,657,108,play\n"
                        "main,measure_2,AWGR0_2,704,325,capture\n"
                        "main,measure_2,Qubit 2,765,64,play\n"
                        "main,measure_2,Qubit 2,829,64,play\n"
                        "main,measure_4,Qubit 4,593,64,play\n"
                        "main,measure_4,Qubit 4,657,108,play\n"
                        "main,measure_4,AWGR1_0,704,325,capture\n"
                        "main,measure_4,Qubit 4,765,64,play\n"
                        "main,measure_4,Qubit 4,829,64,play\n"
                        "main,barrier,Qubit 0,1668,0,barrier\n"
                        "main,barrier,Qubit 2,1668,0,barrier\n"
                        "main,barrier,Qubit 4,1668,0,barrier\n"
                        "main,broadcast,Hub,704,964,broadcast\n"
                        "main,receive,Receive,1668,7,receive\n"
                        "then,x_1,Qubit 1,1695,8,play\n"
                        "else,sx_0,Qubit 0,1699,8,play\n"
                        "else,sx_0,Qubit 0,1707,0,shift_phase\n"
                        "main,x_3,Qubit 3,1704,8,play\n"
                        "main,x_5,Qubit 5,1704,8,play\n"
                        "main,barrier,Qubit 1,1712,0,barrier\n"
                        "main,barrier,Qubit 3,1712,0,barrier\n"
                        "main,barrier,Qubit 5,1712,0,barrier\n"
                        "main,measure_1,Qubit 1,1712,64,play\n"
                        "main,measure_1,Qubit 1,1776,108,play\n"
                        "main,measure_1,AWGR0_1,1823,325,capture\n"
                        "main,measure_1,Qubit 1,1884,64,play\n"
                        "main,measure_1,Qubit 1,1948,64,play\n"
                        "main,measure_3,Qubit 3,1712,64,play\n"
                        "main,measure_3,Qubit 3,1776,108,play\n"
                        "main,measure_3,AWGR0_3,1823,325,capture\n"
                        "main,measure_3,Qubit 3,1884,64,play\n"
                        "main,measure_3,Qubit 3,1948,64,play\n"
                        "main,measure_5,Qubit 5,1712,64,play\n"
                        "main,measure_5,Qubit 5,1776,108,play\n"
                        "main,measure_5,AWGR1_1,1823,325,capture\n"
                        "main,measure_5,Qubit 5,1884,64,play\n"
                        "main,measure_5,Qubit 5,1948,64,play\n"
                        "main,barrier,Qubit 1,2282,0,barrier\n"
                        "main,barrier,Qubit 3,2282,0,barrier\n"
                        "main,barrier,Qubit 5,2282,0,barrier\n"
                        "else,sx_2,Qubit 2,2274,8,play\n"
                        "else,sx_2,Qubit 2,2282,0,shift_phase\n"
                        "else,sx_4,Qubit 4,2274,8,play\n"
                        "else,sx_4,Qubit 4,2282,0,shift_phase\n"
                    )
                }
            }
        },
    )

    sampler_pub_result_small = SamplerPubResult(
        data=DataBin(),
        metadata={
            "compilation": {
                "scheduler_timing": {
                    "timing": (
                        "main,barrier,Qubit 0,7,0,barrier\n"
                        "main,barrier,Qubit 1,7,0,barrier\n"
                        "main,barrier,Qubit 2,7,0,barrier\n"
                        "main,barrier,Qubit 3,7,0,barrier\n"
                        "main,barrier,Qubit 4,7,0,barrier\n"
                    )
                }
            }
        },
    )
