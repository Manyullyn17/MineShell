import httpx
from backend.api.api import SourceAPI

FTB_API = ""
MODLOADERS = {"fabric", "forge", "quilt", "neoforge"}

class FTBAPI(SourceAPI):
    async def search_modpacks(self, query: str, limit: int=20) -> dict[str, str | list[str]]:
        """Search modpacks on FTB and return data for the selector modal."""
        

        # Return data for the modal
        return {
            "title": f"Select Modpack (search: {query})",
            "rows": '',
            "columns": '',
        }

    def get_modloader_from_categories(self, categories: list[str]) -> str:
        return "Unknown"

    async def get_modpack_versions(self, modpack_id: str) -> list[dict]:
        """
        Returns a list of versions for a given FTB project ID.
        Each item is [version_name, date_published].
        Sorted newest first.
        """
        
        # Build simplified list
        return [{}]

    async def get_modlist(self, dependencies: dict) -> list[dict]:
        """Given a FTB modpack version object, fetch and return a list of server-side mods."""
        return [{}]
    