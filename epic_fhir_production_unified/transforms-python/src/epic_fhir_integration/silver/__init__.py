"""Compatibility shim for moved 'silver' package."""
import importlib, sys, types
_target_pkg = importlib.import_module("epic_fhir_integration.domain.silver")
# expose attributes
globals().update(_target_pkg.__dict__)
for _name, _mod in _target_pkg.__dict__.items():
    if isinstance(_mod, types.ModuleType):
        sys.modules.setdefault(f"{__name__}.{_name}", _mod)
sys.modules[__name__] = _target_pkg 