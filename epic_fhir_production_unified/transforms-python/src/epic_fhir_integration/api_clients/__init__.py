"""Compatibility shim: redirects legacy 'epic_fhir_integration.api_clients'
package import paths to the new location under
'epic_fhir_integration.infrastructure.api_clients'.

KEEP THIS FILE TEMPORARILY to avoid breaking downstream code while the
team finishes refactoring import paths.
"""
from types import ModuleType
import importlib
import sys

_target = importlib.import_module("epic_fhir_integration.infrastructure.api_clients")

# Copy all attributes so `from epic_fhir_integration.api_clients import X` works
globals().update(_target.__dict__)

# Ensure sub-modules are mapped for `import epic_fhir_integration.api_clients.foo`
for _name, _mod in _target.__dict__.items():
    if isinstance(_mod, ModuleType):
        sys.modules.setdefault(f"{__name__}.{_name}", _mod)

# Point the parent module reference at the target to satisfy `isinstance`
sys.modules[__name__] = _target 