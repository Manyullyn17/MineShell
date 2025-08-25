import os
import httpx
import json
from pathlib import Path
from typing import Optional, Callable

CACHE_FILE = Path("version_manifest_v2.json")

def fetch_manifest():
    # Fetch the Minecraft version manifest
    manifest_url = 'https://launchermeta.mojang.com/mc/game/version_manifest_v2.json'
    try:
        with httpx.Client(timeout=10) as client:
            return client.get(manifest_url).json()
    except Exception as e:
        print('Failed to fetch manifest: ', e)
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
        return None

def get_minecraft_versions():
    # Filter only full releases and extract relevant info
    manifest = fetch_manifest()
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

async def download_file(url: str, dest: str, on_progress: Optional[Callable[[int, int], None]] = None):
    """Download a file with optional progress callback."""
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)

async def download_minecraft_server(version_json_url: str, dest_dir: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(version_json_url)
        resp.raise_for_status()
        version_data = resp.json()

    server_url = version_data["downloads"]["server"]["url"]
    server_filename = f"minecraft_server_{version_data['id']}.jar"
    dest_path = os.path.join(dest_dir, server_filename)

    print(f"Downloading Minecraft server {version_data['id']}...")
    await download_file(server_url, dest_path)
    print("Download complete:", dest_path)
    return dest_path

