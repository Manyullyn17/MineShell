import httpx
from backend.api import SourceAPI

FTB_API = ""
MODLOADERS = {"fabric", "forge", "quilt", "neoforge"}

class FTBAPI(SourceAPI):
    async def search_modpacks(self, query: str, limit: int=20) -> tuple[str, list[dict[str, str | list[str]]]]:
        """Search modpacks by query."""
        ...

    async def get_modpack_versions(self, modpack_id: str) -> list[dict]:
        """Return all versions of the given modpack."""
        ...

    async def get_modlist(self, dependencies: dict) -> list[dict]:
        """Return the modlist for the given modpack version."""
        ...

    async def search_mods(self, query: str, limit: int=20, filters: dict | None = None) -> list[dict[str, str | list[str]]]:
        """Search mods and return data for the selector modal."""
        ...
    
    async def get_mod(self, project_id: str) -> dict:
        """Fetch project info for a given project ID from Modrinth."""
        ...

    async def get_mod_versions(self, project_id: str, mc_version: list[str] | None = None, modloader: list[str] | None = None) -> list[dict]:
        """
        Returns a list of versions for a given project ID.
        If no Minecraft version or Modloader is provided returns all versions.
        Sorted newest first.
        """
        ...

    async def fetch_projects(self, project_ids: list[str], filter_server_side: bool = True) -> dict[str, dict]:
        """
        Fetch project info for a list of project IDs.

        Args:
            project_ids: List of project_id strings
            filter_server_side: If True, only return server-side compatible projects.
 
        Returns:
            Dictionary mapping project_id -> project JSON object
        """
        ...

    async def fetch_versions(self, version_ids: list[str]) -> list[dict]:
        """
        Fetch version info for a list of version IDs from Modrinth.

        Args:
            version_ids: List of version_id strings

        Returns:
            Dictionary mapping version_id -> version JSON object
        """
        ...

    async def get_categories(self) -> list[str]:
        """Get a list of mod categories."""
        ...
