import httpx
import json
from pathlib import Path
from helpers import download_file

CACHE_FILE = Path("version_manifest_v2.json")

async def fetch_manifest():
    # Fetch the Minecraft version manifest
    manifest_url = 'https://launchermeta.mojang.com/mc/game/version_manifest_v2.json'
    try:
        with httpx.Client(timeout=10) as client:
            return client.get(manifest_url).json()
    except Exception as e:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
        return None

async def get_minecraft_versions():
    # Filter only full releases and extract relevant info
    manifest = await fetch_manifest()
    if not manifest:
        return [{'id': "none"}]
    
    CACHE_FILE.write_text(json.dumps(manifest))

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

