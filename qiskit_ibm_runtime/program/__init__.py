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

"""
====================================================
Runtime Programs (:mod:`qiskit_ibm_runtime.program`)
====================================================

.. currentmodule:: qiskit_ibm_runtime.program

This package contains files to help you write your custom Qiskit Runtime programs.

Only authorized users can upload their custom Qiskit Runtime programs.
A Qiskit Runtime program is a piece of Python
code and its metadata that takes certain inputs, performs
quantum and maybe classical processing, and returns the results.

Each runtime program has both ``data`` and ``metadata``. Program data is
the Python code to be executed. Program metadata provides usage information,
such as program description, its inputs and outputs, and backend requirements.

Each program data needs to have a ``main(backend, user_messenger, **kwargs)``
method, which serves as the entry point to the program. The ``backend`` parameter
is a :class:`ProgramBackend` instance whose :meth:`ProgramBackend.run` method
can be used to submit circuits. The ``user_messenger`` is a :class:`UserMessenger`
instance whose :meth:`UserMessenger.publish` method can be used to publish interim and
final results.
See `qiskit_ibm_runtime/program/program_template.py` for a program data
template file.

Each program metadata must include at least the program name, description, and
maximum execution time. You can find description of each metadata field in
the :meth:`QiskitRuntimeService.upload_program` method. Instead of passing in
the metadata fields individually, you can pass in a JSON file or a dictionary
to :meth:`QiskitRuntimeService.upload_program` via the ``metadata`` parameter.
`qiskit_ibm_runtime/program/program_metadata_sample.json`
is a sample file of program metadata.

You can use the :meth:`QiskitRuntimeService.upload_program` to upload a program.
For example::

   from qiskit_ibm_runtime import QiskitRuntimeService

   service = QiskitRuntimeService()
   program_id = service.upload_program(
                  data="my_vqe.py",
                  metadata="my_vqe_metadata.json"
               )

In the example above, the file ``my_vqe.py`` contains the program data, and
``my_vqe_metadata.json`` contains the program metadata.

Method :meth:`QiskitRuntimeService.delete_program` allows you to delete a
program.


Classes
==========================
.. autosummary::
   :toctree: ../stubs/

   ProgramBackend
   UserMessenger
   ResultDecoder
"""

from .program_backend import ProgramBackend
from .user_messenger import UserMessenger
from .result_decoder import ResultDecoder
