Create a new channel `generic`. This channel allows to use an alternative
and custom channel platform implementation, i.e. neither IBM Quantum Platform
nor IBM Cloud. The url parameter can be used to describe how the channel
platform is reached. It will not be further modified as with other channel
options.
While `token` and `instance` can be used if the HTTP headers match what the
custom channel platform expects, additional headers can be set through the
environment variable `QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER`.