"""Compatibility shim for moved 'gold' package."""
import importlib, sys, types
_target_pkg = importlib.import_module("epic_fhir_integration.domain.gold")
# expose
globals().update(_target_pkg.__dict__)
for _n, _m in _target_pkg.__dict__.items():
    if isinstance(_m, types.ModuleType):
        sys.modules.setdefault(f"{__name__}.{_n}", _m)
sys.modules[__name__] = _target_pkg 