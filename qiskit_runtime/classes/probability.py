# This code is part of mthree.
#
# (C) Copyright IBM Quantum 2021.
#
# This code is for internal IBM Quantum use only.
# pylint: disable=no-name-in-module
"""Class for probability distributions."""

from math import sqrt


class ProbDistribution(dict):
    """A generic dict-like class for probability distributions.
    """
    def __init__(self, data, shots=None):
        """Builds a probability distribution object.

        Parameters:
            data (dict): Input probability data.
            shots (int): Number of shots the distribution was derived from.
        """
        self.shots = shots
        super().__init__(data)
