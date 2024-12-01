"""Compatibility shim for moved 'bronze' package."""
import importlib, sys, types
_target_pkg = importlib.import_module("epic_fhir_integration.domain.bronze")
# expose attributes
globals().update(_target_pkg.__dict__)
# register submodules
for _name, _mod in _target_pkg.__dict__.items():
    if isinstance(_mod, types.ModuleType):
        sys.modules.setdefault(f"{__name__}.{_name}", _mod)
# point self to target
sys.modules[__name__] = _target_pkg 