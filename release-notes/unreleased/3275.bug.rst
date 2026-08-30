Fixed :meth:`.QiskitRuntimeService.backend` so that retrieving a backend without a
``calibration_id`` after retrieving it with a custom calibration returns the default backend
configuration and supported instructions. Custom calibration data no longer replaces the cached
default backend configuration.
