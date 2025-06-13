"""Compatibility shim for moved 'schemas' package."""
import importlib, sys, types
_target_pkg = importlib.import_module("epic_fhir_integration.domain.schemas")
globals().update(_target_pkg.__dict__)
for _k, _v in _target_pkg.__dict__.items():
    if isinstance(_v, types.ModuleType):
        sys.modules.setdefault(f"{__name__}.{_k}", _v)
sys.modules[__name__] = _target_pkg 