from typing import TYPE_CHECKING
import importlib

__all__ = [
    "CustomInput",
    "CustomModal",
    "CustomSelect",
    "CustomSelectionList",
    "CustomTable",
    "CustomVerticalScroll",
    "DebounceMixin",
    "NavigationMixin",
    "download_file",
    "format_date",
    "ModloaderType",
    "sanitize_filename",
    "strip_images",
]

if TYPE_CHECKING:
    from .custominput import CustomInput
    from .custommodal import CustomModal
    from .customselect import CustomSelect
    from .customselectionlist import CustomSelectionList
    from .customtable import CustomTable
    from .customverticalscroll import CustomVerticalScroll
    from .debouncemixin import DebounceMixin
    from .navigationmixin import NavigationMixin
    from .utils import format_date, sanitize_filename, download_file, ModloaderType, strip_images

# Map attribute names to their modules
_lazy_map = {
    "CustomInput": ".custominput",
    "CustomModal": ".custommodal",
    "CustomSelect": ".customselect",
    "CustomSelectionList": ".customselectionlist",
    "CustomTable": ".customtable",
    "CustomVerticalScroll": ".customverticalscroll",
    "DebounceMixin": ".debouncemixin",
    "NavigationMixin": ".navigationmixin",
    "format_date": ".utils",
    "sanitize_filename": ".utils",
    "download_file": ".utils",
    "ModloaderType": ".utils",
    "strip_images": ".utils",
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
