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

"""Utility functions for options."""

from dataclasses import fields, field, make_dataclass
import copy


def _flexible(cls):  # type: ignore
    """Decorator used to allow a flexible dataclass.

    This is used to dynamically create a new dataclass with the
    arbitrary kwargs input converted to fields. It also converts
    input dictionary to objects based on the _obj_fields attribute.
    """

    def __new__(cls, *args, **kwargs):  # type: ignore
        def _to_obj(cls_, data):  # type: ignore
            if data is None:
                return cls_()
            if isinstance(data, cls_):
                return data
            if isinstance(data, dict):
                return cls_(**data)
            raise TypeError(
                f"{data} has an unspported type {type(data)}. It can only be {cls_} or a dictionary."
            )

        updated_kwargs = copy.deepcopy(kwargs)
        all_fields = []
        orig_field_names = set()
        obj_fields = getattr(cls, "_obj_fields", {})

        for fld in fields(cls):
            all_fields.append((fld.name, fld.type, fld))
            orig_field_names.add(fld.name)

        for key, val in updated_kwargs.items():
            if key not in orig_field_names:
                all_fields.append((key, type(val), field(default=None)))
            elif key in obj_fields:
                updated_kwargs[key] = _to_obj(obj_fields[key], val)

        new_cls = make_dataclass(
            cls.__name__,
            all_fields,
            bases=(cls,),
        )
        obj = object.__new__(new_cls)
        obj.__init__(*args, **updated_kwargs)
        return obj

    cls.__new__ = __new__
    return cls


class Dict:
    """Fake Dict type.

    This class is used to show dictionary as an acceptable type in docs without
    attaching all the dictionary attributes in Jupyter's auto-complete.
    """

    pass
