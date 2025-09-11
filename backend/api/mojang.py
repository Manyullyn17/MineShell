import httpx
import json
from pathlib import Path
from datetime import datetime, timedelta
from helpers import download_file

CACHE_FILE = Path("version_manifest_v2.json")
CACHE_EXPIRATION = timedelta(days=1)

async def _fetch_manifest_from_api():
    """Fetches the Minecraft version manifest from Mojang's API."""
    manifest_url = 'https://launchermeta.mojang.com/mc/game/version_manifest_v2.json'
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(manifest_url)
            resp.raise_for_status()
            return resp.json()
    except (httpx.RequestError, httpx.HTTPStatusError):
        return None

async def get_minecraft_versions() -> list[dict]:
    """
    Gets Minecraft release versions.
    It uses a local cache that expires after a day. If fetching new data fails,
    it falls back to the cache, even if it's stale.
    """
    manifest = None
    use_cache = False

    # 1. Check if a valid, non-expired cache file exists
    if CACHE_FILE.exists():
        cache_mod_time = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        if datetime.now() - cache_mod_time < CACHE_EXPIRATION:
            use_cache = True
            manifest = json.loads(CACHE_FILE.read_text())

    # 2. If no valid cache, fetch from API
    if not use_cache:
        new_manifest = await _fetch_manifest_from_api()
        if new_manifest:
            manifest = new_manifest
            CACHE_FILE.write_text(json.dumps(manifest))
        # 3. If API fails, fall back to any existing (stale) cache
        elif CACHE_FILE.exists():
            manifest = json.loads(CACHE_FILE.read_text())

    # 4. If still no manifest (no cache, no internet), we can't proceed
    if not manifest:
        return [{'id': "none"}]

    # Filter only full releases and extract relevant info
    releases = [
        {
            "id": v["id"],
            "url": v["url"],
            "releaseTime": v["releaseTime"]
        }
        for v in manifest["versions"]
        if v["type"] == "release"
    ]

    return releases

async def download_minecraft_server(version_json_url: str, dest_dir: Path):
    async with httpx.AsyncClient() as client:
        resp = await client.get(version_json_url)
        resp.raise_for_status()
        version_data = resp.json()

    server_url = version_data["downloads"]["server"]["url"]
    server_filename = "server.jar"
    dest_path = dest_dir / server_filename

    await download_file(server_url, dest_path)
    return dest_path
