from typing import TYPE_CHECKING
import importlib

__all__ = [
    "ContextMenu",
    "DeleteModal",
    "FilterModal",
    "FolderModal",
    "ProgressModal",
    "SelectorModal",
    "SortModal",
    "TextDisplayModal",
    "ModBrowserModal",
]

if TYPE_CHECKING:
    from .context_menu import ContextMenu
    from .delete_modal import DeleteModal
    from .filter_modal import FilterModal
    from .folder_modal import FolderModal
    from .progress_modal import ProgressModal
    from .selector_modal import SelectorModal
    from .sort_modal import SortModal
    from .text_display_modal import TextDisplayModal
    from .modbrowser_modal import ModBrowserModal

# Map attribute names to their modules
_lazy_map = {
    "ContextMenu": ".context_menu",
    "DeleteModal": ".delete_modal",
    "FilterModal": ".filter_modal",
    "FolderModal": ".folder_modal",
    "ProgressModal": ".progress_modal",
    "SelectorModal": ".selector_modal",
    "SortModal": ".sort_modal",
    "TextDisplayModal": ".text_display_modal",
    "ModBrowserModal": ".modbrowser_modal",
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
