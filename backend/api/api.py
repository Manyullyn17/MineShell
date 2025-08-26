from typing import Protocol, runtime_checkable

@runtime_checkable
class SourceAPI(Protocol):
    async def search_modpacks(self, query: str, limit: int=20) -> tuple[str, list[dict[str, str | list[str]]]]:
        """Search modpacks by query."""
        ...

    async def get_modpack_versions(self, modpack_id: str) -> list[dict]:
        """Return all versions of the given modpack."""
        ...

    async def get_modlist(self, dependencies: dict) -> list[dict]:
        """Return the modlist for the given modpack version."""
        ...

