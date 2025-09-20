from typing import TYPE_CHECKING
import importlib

__all__ = [
    "CustomSelect",
    "SmartInput",
    "CustomTable",
    "CustomModal",
    "format_date",
    "sanitize_filename",
    "download_file",
    "ModloaderType",
    "FocusNavigationMixin",
    "CustomVerticalScroll",
    "CustomSelectionList",
    "strip_images",
]

if TYPE_CHECKING:
    from .widgets import CustomSelect, SmartInput, CustomTable, CustomModal, FocusNavigationMixin, CustomVerticalScroll, CustomSelectionList
    from .utils import format_date, sanitize_filename, download_file, ModloaderType, strip_images

# Map attribute names to their modules
_lazy_map = {
    "CustomSelect": ".widgets",
    "SmartInput": ".widgets",
    "CustomTable": ".widgets",
    "CustomModal": ".widgets",
    "format_date": ".utils",
    "sanitize_filename": ".utils",
    "download_file": ".utils",
    "ModloaderType": ".utils",
    "FocusNavigationMixin": ".widgets",
    "CustomVerticalScroll": ".widgets",
    "CustomSelectionList": ".widgets",
    "strip_images": ".utils",
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
