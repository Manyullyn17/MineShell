import os, httpx, subprocess
from pathlib import Path
from typing import Optional
from helpers import download_file

async def get_latest_stable_fabric_installer():
    url = "https://meta.fabricmc.net/v2/versions/installer"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()

    # pick newest stable
    stable = [i for i in data if i.get("stable")]
    stable.sort(key=lambda x: list(map(int, x["version"].split("."))))
    return stable[-1]

async def ensure_fabric_installer(installers_dir="installers") -> Path:
    os.makedirs(installers_dir, exist_ok=True)

    latest = await get_latest_stable_fabric_installer()
    version = latest["version"]
    filename = f"fabric-installer-{version}.jar"
    dest = Path(installers_dir) / filename

    if os.path.exists(dest):
        return dest

    await download_file(latest["url"], dest)
    return dest

async def get_fabric_versions(mc_version: str) -> list[dict]:
    """Return all Fabric loader versions for a given Minecraft version."""
    url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()

    return [{"version": v["loader"]["version"], "stable": v["loader"]["stable"]} for v in data]

async def run_fabric_installer(
    install_dir: Path,
    installer_path: Path,
    mc_version: str,
    loader_version: Optional[str] = None
):
    """Run the Fabric installer to set up a server.

    Args:
        installer_path: Path to the fabric-installer-<ver>.jar
        mc_version: Target Minecraft version (e.g. "1.20.1")
        loader_version: Optional Fabric loader version
        install_dir: Directory where to install the server
    """
    cmd = [
        "java", "-jar", installer_path,
        "server",
        "-mcversion", mc_version,
        "-downloadMinecraft",
        "-dir", install_dir
    ]
    if loader_version:
        cmd += ["-loader", loader_version]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except Exception as e:
        print(e)
        return e
    return result.returncode
