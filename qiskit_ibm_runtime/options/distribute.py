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

"Distribute." ""

from typing import Any, Generic, Iterable, Tuple, TypeVar, Union

import numpy as np

T = TypeVar("T")


class Distribute(Generic[T]):
    """Distribute option values across PUBs.
    
    Args:
        values: The value to use for each PUB.
    """

    def __init__(self, *values: Union[T, np.ndarray[T]]):
        self.values = [np.array(val) if isinstance(val, Iterable) else val for val in values]

    def shape(self, pub_idx: int) -> Tuple[int, ...]:
        """Return the shape of the value for the PUB at index `pub_idx`.
        
        Args:
            pub_idx: The index of the PUB.
            
        Returns:
            The shape of the value.
        """
        if isinstance(value := self[pub_idx], np.ndarray):
            return value.shape
        return ()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Distribute):
            return False
        if len(self) != len(other):
            return False
        for self_value, other_value in zip(self, other):  # type: ignore[call-overload]
            if not np.array_equal(self_value, other_value):
                return False
        return True

    def __getitem__(self, idx: int) -> Union[T, np.ndarray[T]]:
        return self.values[idx]

    def __iter__(self) -> Iterable[Union[T, np.ndarray[T]]]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<{len(self)}>)"
