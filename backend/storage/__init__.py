from typing import TYPE_CHECKING
import importlib

__all__ = [
    "ModEntry",
    "ModList",
    "InstanceConfig",
    "InstanceSummary",
    "InstanceRegistry",
]

if TYPE_CHECKING:
    from .instance import ModEntry, ModList, InstanceConfig, InstanceSummary, InstanceRegistry

# Map attribute names to their modules
_lazy_map = {
    "ModEntry": ".instance",
    "ModList": ".instance",
    "InstanceConfig": ".instance",
    "InstanceSummary": ".instance",
    "InstanceRegistry": ".instance",

}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
