from typing import TYPE_CHECKING
import importlib

__all__ = [
    "FilterSidebar",
    "CustomList",
    "Card",
    "ModList",
    "ModCard",
]

if TYPE_CHECKING:
    from .filtersidebar import FilterSidebar
    from .customlist import CustomList, Card
    from .modlist import ModList, ModCard

# Map attribute names to their modules
_lazy_map = {
    "FilterSidebar": ".filtersidebar",
    "CustomList": ".customlist",
    "Card": ".customlist",
    "ModList": ".modlist",
    "ModCard": ".modlist",
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
