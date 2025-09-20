from typing import TYPE_CHECKING
import importlib

__all__ = [
    "SourceAPI",
    "CurseforgeAPI",
    "FTBAPI",
    "ModrinthAPI",
    "SourceAPI",
    "get_minecraft_versions",
    "get_fabric_versions",
    "get_forge_versions",
    "get_neoforge_versions",
    "get_quilt_versions",
]

if TYPE_CHECKING:
    from .sourceapi import SourceAPI
    from .curseforge import CurseforgeAPI
    from .ftb import FTBAPI
    from .modrinth import ModrinthAPI
    from .sourceapi import SourceAPI
    from .mojang import get_minecraft_versions
    from .fabric import get_fabric_versions
    from .forge import get_forge_versions
    from .neoforge import get_neoforge_versions
    from .quilt import get_quilt_versions

# Map attribute names to their modules
_lazy_map = {
    "SourceAPI": ".sourceapi",
    "CurseforgeAPI": ".curseforge",
    "FTBAPI": ".ftb",
    "ModrinthAPI": ".modrinth",
    "SourceAPI": ".sourceapi",
    "get_minecraft_versions": ".mojang",
    "get_fabric_versions": ".fabric",
    "get_forge_versions": ".forge",
    "get_neoforge_versions": ".neoforge",
    "get_quilt_versions": ".quilt",
}

def __getattr__(name: str):
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
