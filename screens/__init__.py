from typing import TYPE_CHECKING
import importlib

__all__ = [
    "InstanceDetailScreen",
    "MainMenu",
    "ManageInstancesScreen",
    "ModListScreen",
    "NewInstanceScreen",
]

if TYPE_CHECKING:
    from .instance_detail import InstanceDetailScreen
    from .main_menu import MainMenu
    from .manage_instances import ManageInstancesScreen
    from .mod_list import ModListScreen
    from .new_instance import NewInstanceScreen
    from .modbrowser import ModBrowserScreen

# Map attribute names to their modules
_lazy_map = {
    "InstanceDetailScreen": ".instance_detail",
    "MainMenu": ".main_menu",
    "ManageInstancesScreen": ".manage_instances",
    "ModListScreen": ".mod_list",
    "NewInstanceScreen": ".new_instance",
    "ModBrowserScreen": ".modbrowser"
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
