import httpx, subprocess, os
from pathlib import Path
from typing import Optional
from helpers import download_file

async def get_quilt_versions(mc_version: str) -> list[dict]:
    """Get all available Quilt loader versions for a given Minecraft version."""
    url = f"https://meta.quiltmc.org/v3/versions/loader/{mc_version}"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    return [{
        "version": loader["loader"]["version"],
        "build": loader["loader"]["build"],
    } for loader in data]

async def get_latest_quilt_installer():
    """Get latest Quilt installer."""
    url = "https://meta.quiltmc.org/v3/versions/installer"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    # Get latest stable installer
    stable = [i for i in data if i.get("stable")]
    stable.sort(key=lambda x: list(map(int, x["version"].split("."))))
    return stable[-1] if stable else data[-1]

async def ensure_quilt_installer(installers_dir: str = "installers") -> Path:
    """Download Quilt installer if not exists."""
    os.makedirs(installers_dir, exist_ok=True)
    
    latest = await get_latest_quilt_installer()
    version = latest["version"]
    filename = f"quilt-installer-{version}.jar"
    dest = Path(installers_dir) / filename
    
    if dest.exists():
        return dest
    
    await download_file(latest["url"], dest)
    return dest

async def run_quilt_installer(
    install_dir: Path,
    installer_path: Path,
    mc_version: str,
    loader_version: str=''
):
    """Run Quilt installer."""
    cmd = [
        "java", "-jar", installer_path,
        "install", "server",
        mc_version, loader_version,
        f"--install-dir={install_dir}",
        "--download-server",
        "--create-scripts" # creates launch scripts, doesn't seem to do anything though
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e

