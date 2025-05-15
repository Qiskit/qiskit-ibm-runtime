# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Model and schema for pulse defaults."""
from typing import Any, Dict, TypeVar, Type

MeasurementKernelT = TypeVar("MeasurementKernelT", bound="MeasurementKernel")
DiscriminatorT = TypeVar("DiscriminatorT", bound="Discriminator")
CommandT = TypeVar("CommandT", bound="Command")


class MeasurementKernel:
    """Class representing a Measurement Kernel."""

    def __init__(self, name: str, params: Any) -> None:
        """Initialize a MeasurementKernel object

        Args:
            name (str): The name of the measurement kernel
            params: The parameters of the measurement kernel
        """
        self.name = name
        self.params = params

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the MeasurementKernel.

        Returns:
            dict: The dictionary form of the MeasurementKernel.
        """
        return {"name": self.name, "params": self.params}

    @classmethod
    def from_dict(cls: Type[MeasurementKernelT], data: Dict[str, Any]) -> MeasurementKernelT:
        """Create a new MeasurementKernel object from a dictionary.

        Args:
            data (dict): A dictionary representing the MeasurementKernel
                         to create. It will be in the same format as output by
                         :meth:`to_dict`.

        Returns:
            MeasurementKernel: The MeasurementKernel from the input dictionary.
        """
        return cls(**data)


class Discriminator:
    """Class representing a Discriminator."""

    def __init__(self, name: str, params: Any):
        """Initialize a Discriminator object

        Args:
            name (str): The name of the discriminator
            params: The parameters of the discriminator
        """
        self.name = name
        self.params = params

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the Discriminator.

        Returns:
            dict: The dictionary form of the Discriminator.
        """
        return {"name": self.name, "params": self.params}

    @classmethod
    def from_dict(cls: Type[DiscriminatorT], data: Dict[str, Any]) -> DiscriminatorT:
        """Create a new Discriminator object from a dictionary.

        Args:
            data (dict): A dictionary representing the Discriminator
                         to create. It will be in the same format as output by
                         :meth:`to_dict`.

        Returns:
            Discriminator: The Discriminator from the input dictionary.
        """
        return cls(**data)


class Command:
    """Class representing a Command.

    Attributes:
        name: Pulse command name.
    """

    _data: Dict[Any, Any] = {}

    def __init__(self, name: str, qubits: Any = None, sequence: Any = None, **kwargs: Any):
        """Initialize a Command object

        Args:
            name (str): The name of the command
            qubits: The qubits for the command
            sequence (PulseQobjInstruction): The sequence for the Command
            kwargs: Optional additional fields
        """
        self._data = {}
        self.name = name
        if qubits is not None:
            self.qubits = qubits
        if sequence is not None:
            self.sequence = sequence
        self._data.update(kwargs)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as ex:
            raise AttributeError(f"Attribute {name} is not defined") from ex

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the Command.

        Returns:
            dict: The dictionary form of the Command.
        """
        out_dict: Dict[str, Any] = {"name": self.name}
        if hasattr(self, "qubits"):
            out_dict["qubits"] = self.qubits
        if hasattr(self, "sequence"):
            out_dict["sequence"] = [x.to_dict() for x in self.sequence]
        out_dict.update(self._data)
        return out_dict

    @classmethod
    def from_dict(cls: Type[CommandT], data: Dict[str, Any]) -> CommandT:
        """Create a new Command object from a dictionary.

        Args:
            data (dict): A dictionary representing the ``Command``
                         to create. It will be in the same format as output by
                         :meth:`to_dict`.

        Returns:
            Command: The ``Command`` from the input dictionary.
        """
        # Pulse command data is nested dictionary.
        # To avoid deepcopy and avoid mutating the source object, create new dict here.
        in_data: Dict[str, Any] = {}
        for key, value in data.items():
            in_data[key] = value
        return cls(**in_data)
