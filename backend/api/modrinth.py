import httpx, json
from aiocache import cached
from backend.api.sourceapi import SourceAPI

MODRINTH_API = "https://api.modrinth.com/v2"
MODLOADERS = {"fabric", "forge", "quilt", "neoforge"}
USER_AGENT = "manyullyn/mineshell/0.1.0 (https://github.com/manyullyn)"
HEADERS={"User-Agent": USER_AGENT}

@cached(ttl=600, key_builder=lambda f, endpoint, params: (endpoint, tuple(sorted(params.items()))))
async def cached_request(endpoint: str, params: dict):
    # convert dict to tuple for hashable cache key
    return await _modrinth_request(endpoint, params)

async def _modrinth_request(endpoint: str, params: dict) -> dict:
    """Core API request, returns raw JSON."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MODRINTH_API}/{endpoint}",
                params=params,
                timeout=15.0,
                headers=HEADERS
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.ReadTimeout, httpx.TimeoutException):
        return {}

class ModrinthAPI(SourceAPI):
    async def search_modpacks(self, query: str, limit: int=20) -> tuple[str, list[dict[str, str | list[str]]]]:
        """Search modpacks on Modrinth and return data for the selector modal."""
        try:
            params = {
                "query": query,
                "facets": '[["project_type:modpack"]]',
                "limit": limit
            }
            results: list[dict] = (await cached_request("search", params))["hits"]
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return '', []

        # Build rows for the modal: [project_id, title, slug, downloads, client/server]
        rows = []
        for hit in results:
            rows.append({
                "name": hit["title"], # name to show
                "author": hit["author"],
                "downloads": f"{hit['downloads']:,}", # format downloads with commas
                "modloader": await self._get_modloader_from_categories(hit["categories"]),
                "categories": await self._get_only_categories_from_categories(hit["categories"]),
                "slug": hit["slug"],
                "description": hit["description"],
            })

        # Return data for the modal
        return f"Select Modpack (Search: {query})", rows

    async def _get_modloader_from_categories(self, categories: list[str]) -> list[str]:
        loaders: list = []
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower in MODLOADERS:
                # Capitalize nicely for display
                loaders.append(cat_lower.title())
        return loaders
    
    async def _get_only_categories_from_categories(self, categories: list[str]) -> list[str]:
        categories_list: list = []
        all_categories = await self.get_categories()
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower in all_categories:
                # Capitalize nicely for display
                categories_list.append(cat_lower.title())
        return categories_list

    async def get_modpack_versions(self, modpack_id: str) -> list[dict]:
        """
        Returns a list of versions for a given Modrinth project ID.
        Each item is [version_name, date_published].
        Sorted newest first.
        """
        try:
            versions: list[dict] = await cached_request(f"project/{modpack_id}/version", {})
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return []
        # Sort newest first
        versions.sort(key=lambda v: v["date_published"], reverse=True)

        # Build simplified list
        return versions
    
    async def get_modlist(self, dependencies: dict) -> list[dict]:
        """
        Given a Modrinth modpack version object, fetch and return a list of server-side mods.

        Each item in the returned list is a dictionary with keys:
            - name
            - project_id
            - version_id
            - version_number
            - download_url

        Args:
            modpack_version: A Modrinth version JSON object for a modpack

        Returns:
            List of dictionaries representing server-side mods in the modpack
        """
        # Extract project IDs from the modpack version's dependencies
        project_ids = [dep["project_id"] for dep in dependencies if dep["project_id"]]

        # Fetch project info for these IDs
        projects = await self.fetch_projects(project_ids)
        if not projects:
            return []

        # Collect all version IDs to fetch
        version_ids = [dep["version_id"] for dep in dependencies if dep["version_id"]]

        # Fetch specific versions by ID
        versions = await self.fetch_versions(version_ids)

        modlist = []
        for version in versions:
            project = projects.get(version["project_id"])
            if not project:
                continue
            modlist.append({
                "project_id": version["project_id"],
                "version_id": version["id"],
                "slug": project.get("slug"),
                "name": project.get("title"),
                "description": project.get("description"),
                "version_number": version.get("version_number"),
                "date_published": version.get("date_published"),
                "file_name": version["files"][0]["filename"] if version.get("files") else None,
                "download_url": version["files"][0]["url"] if version.get("files") else None,
                "loaders": project.get("loaders"),
                "type": 'datapack' if 'datapack' in project.get("loaders", []) else 'mod'
            })

        return modlist
    
    async def search_mods(self, query: str, limit: int=20, filters: dict | None = None) -> list[dict[str, str | list[str]]]:
        """Search mods on Modrinth and return data for the selector modal."""
        try:
            async with httpx.AsyncClient() as client:
                facets = [
                    ["server_side:required", "server_side:optional", "server_side:unknown"]
                ]

                if filters:
                    project_types = [pt.lower() for pt in filters.get('type', ['mod', 'datapack'])]
                    facets.append([f"project_type:{pt}" for pt in project_types])

                    if 'version' in filters:
                        facets.append([f"versions:{v}" for v in filters['version']])

                    # This handles the logic for "(mod AND modloader) OR datapack".
                    # By adding 'categories:datapack' to the modloader filter group, we ensure that
                    # projects can match if they are either a mod with the correct modloader OR a datapack.
                    if 'modloader' in filters:
                        modloader_facets = [f"categories:{v}" for v in filters['modloader']] if project_types != ['datapack'] else []
                        if 'datapack' in project_types:
                            modloader_facets.append("categories:datapack")
                        facets.append(modloader_facets)

                    if 'category' in filters:
                        facets.append([f"categories:{v}" for v in filters['category']])


                params = {
                    "query": query,
                    "facets": json.dumps(facets),
                    "limit": limit,
                }

                results: list[dict] = (await cached_request("search", params))["hits"]
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return []

        # Build rows for the modal: [project_id, title, slug, downloads, client/server]
        rows = []
        for hit in results:
            type = set()
            for cat in hit["categories"]:
                if cat in MODLOADERS:
                    type.add('mod')
                elif cat == 'datapack':
                    type.add('datapack')
            if not type:
                type.add(hit["project_type"] or "mod")
            
            rows.append({
                "name": hit["title"], # name to show
                "author": hit["author"],
                "downloads": f"{hit['downloads']:,}", # format downloads with commas
                "modloader": await self._get_modloader_from_categories(hit["categories"]),
                "categories": await self._get_only_categories_from_categories(hit["categories"]),
                "slug": hit["slug"],
                "description": hit["description"],
                "type": sorted(type),
                "server_side": hit["server_side"],
                "versions": hit["versions"],
                "project_id": hit["project_id"],
            })

        # Return data for the modal
        return rows

    async def get_mod_versions(self, project_id: str, mc_version: str, modloader: str) -> list[dict]:
        """
        Returns a list of versions for a given Modrinth project ID.
        Each item is [version_name, date_published].
        Sorted newest first.
        """
        try:
            params={
                "game_versions": f'["{mc_version}"]',
                "loaders": f'["{modloader}"]',
            }
            versions: list[dict] = await cached_request(f"project/{project_id}/version", params)
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return []
        # Sort newest first
        versions.sort(key=lambda v: v["date_published"], reverse=True)

        # Build simplified list
        return versions

    async def fetch_projects(self, project_ids: list[str], filter_server_side: bool = True) -> dict[str, dict]:
        """
        Fetch project info for a list of project IDs from Modrinth.

        Args:
            project_ids: List of project_id strings
            filter_server_side: If True, only return server-side compatible projects.
 
        Returns:
            Dictionary mapping project_id -> project JSON object
        """
        if not project_ids:
            return {}

        try:
            params = {
                "ids": json.dumps(project_ids),
            }
            projects_list: list[dict] = await cached_request("projects", params)
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return {}
        
        projects_dict = {proj["id"]: proj for proj in projects_list}

        if filter_server_side:
            # Filter server-side mods
            server_projects = {
                proj_id: proj for proj_id, proj in projects_dict.items()
                if proj.get("server_side") in ("required", "optional", "unknown")
            }
            return server_projects

        return projects_dict
        
    async def fetch_versions(self, version_ids: list[str]) -> list[dict]:
        """
        Fetch version info for a list of version IDs from Modrinth.

        Args:
            version_ids: List of version_id strings

        Returns:
            Dictionary mapping version_id -> version JSON object
        """
        if not version_ids:
            return []

        try:
            params = {
                "ids": json.dumps(version_ids),
            }
            versions_list: list[dict] = await cached_request("versions", params)
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return []

        return versions_list

    async def get_categories(self) -> list[str]:
        """Get a list of mod categories from Modrinth."""
        try:
            raw_categories = await cached_request("tag/category", {})

            categories: list[str] = [
                cat.get("name")
                for cat in raw_categories
                if cat.get("project_type") in ("mod", "datapack")
            ]
        except (httpx.ReadTimeout, httpx.TimeoutException):
            return []
        
        return categories
