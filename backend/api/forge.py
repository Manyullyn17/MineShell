import httpx, subprocess, os
from pathlib import Path
from aioshutil import rmtree
from backend.api.mojang import download_minecraft_server
from helpers import download_file

async def get_forge_versions(mc_version: str) -> list[dict]:
    """Get all available Forge versions for a given Minecraft version."""
    url = f"https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    versions = []
    for version in data[mc_version]:
        versions.append({
            "mc_version": mc_version,
            "forge_version": version[len(mc_version)+1:],
            "full_version": version
        })
    
    return versions

async def download_forge_installer(mc_version: str, forge_version: str, installers_dir: str = "installers") -> Path:
    """Download Forge installer."""
    os.makedirs(installers_dir, exist_ok=True)
    filename = f"forge-{mc_version}-{forge_version}-installer.jar"
    dest = Path(installers_dir) / filename
    
    if dest.exists():
        return dest
    
    # Forge download URL pattern
    url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar"
    
    await download_file(url, dest)
    return dest

async def run_forge_installer(install_dir: Path, installer_path: Path, mc_version_url: str): # leaves behind log file in main directory
    """Run Forge installer."""
    cmd = ["java", "-jar", installer_path, "--installServer", install_dir]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        await download_minecraft_server(mc_version_url, install_dir)
        log_file = installer_path.name
        await rmtree(log_file, ignore_errors=True) # remove log file
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e
    
