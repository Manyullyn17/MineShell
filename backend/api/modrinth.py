import httpx, json
from backend.api.api import SourceAPI

MODRINTH_API = "https://api.modrinth.com/v2"
MODLOADERS = {"fabric", "forge", "quilt", "neoforge"}
USER_AGENT = "manyullyn/mineshell/0.1.0 (https://github.com/manyullyn)"
HEADERS={"User-Agent": USER_AGENT}

class ModrinthAPI(SourceAPI):
    async def search_modpacks(self, query: str, limit: int=20) -> tuple[str, list[dict[str, str | list[str]]]]:
        """Search modpacks on Modrinth and return data for the selector modal."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MODRINTH_API}/search",
                params={
                    "query": query,
                    "facets": '[["project_type:modpack"]]',
                    "limit": limit
                },
                timeout=30.0,
                headers=HEADERS
            )
            resp.raise_for_status()
            results = resp.json()["hits"]

        # Build rows for the modal: [project_id, title, slug, downloads, client/server]
        rows = []
        for hit in results:
            rows.append({
                "name": hit["title"],             # name to show
                "author": hit["author"],
                "downloads": f"{hit['downloads']:,}",  # format downloads with commas
                "modloader": await self.get_modloader_from_categories(hit["categories"]),
                "categories": await self.get_only_categories_from_categories(hit["categories"]),
                "slug": hit["slug"],
                "description": hit["description"],
            })

        # Define columns
        #columns = ["Name", "Author", "Downloads", "Modloader", "Categories", "Slug", "Description"] # refactor data to be dict, lotta work

        # Return data for the modal
        return f"Select Modpack (Search: {query})", rows

    async def get_modloader_from_categories(self, categories: list[str]) -> list[str]:
        loaders: list = []
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower in MODLOADERS:
                # Capitalize nicely for display
                loaders.append(cat_lower.capitalize())
        return loaders
    
    async def get_only_categories_from_categories(self, categories: list[str]) -> list[str]:
        categories_list: list = []
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower not in MODLOADERS:
                # Capitalize nicely for display
                categories_list.append(cat_lower.capitalize())
        return categories_list

    async def get_modpack_versions(self, modpack_id: str) -> list[dict]:
        """
        Returns a list of versions for a given Modrinth project ID.
        Each item is [version_name, date_published].
        Sorted newest first.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{MODRINTH_API}/project/{modpack_id}/version", headers=HEADERS)
            resp.raise_for_status()
            versions = resp.json()

        # Sort newest first
        versions.sort(key=lambda v: v["date_published"], reverse=True)

        # Build simplified list
        return versions
    
async def fetch_projects(project_ids: list[str]) -> dict[str, dict]:
    """
    Fetch project info for a list of project IDs from Modrinth.

    Args:
        project_ids: List of project_id strings

    Returns:
        Dictionary mapping project_id -> project JSON object
    """
    if not project_ids:
        return {}

    url = f"{MODRINTH_API}/projects?ids={json.dumps(project_ids)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=HEADERS)
        resp.raise_for_status()
        projects_list = resp.json()

    # Filter server-side mods
    server_projects = {
        proj["id"]: proj
        for proj in projects_list
        if proj.get("server_side") in ("required", "optional")
    }

    return server_projects
    
async def fetch_versions(version_ids: list[str]) -> list[dict]:
    """
    Fetch version info for a list of version IDs from Modrinth.

    Args:
        version_ids: List of version_id strings

    Returns:
        Dictionary mapping version_id -> version JSON object
    """
    if not version_ids:
        return []

    url = f"{MODRINTH_API}/versions?ids={json.dumps(version_ids)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=HEADERS)
        resp.raise_for_status()
        versions_list = resp.json()

    return versions_list

