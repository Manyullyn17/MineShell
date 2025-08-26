import httpx, subprocess, os
from pathlib import Path
from aioshutil import rmtree
from xml.etree import ElementTree as ET
from backend.api.mojang import download_minecraft_server
from helpers import download_file

async def get_neoforge_versions(mc_version: str) -> list[dict]:
    """Get all available NeoForge versions for a given Minecraft version."""
    # NeoForge uses a different metadata structure
    url = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
    resp = httpx.get(url)
    resp.raise_for_status()
    
    # Parse XML response
    root = ET.fromstring(resp.text)
    
    parts = mc_version.split('.')
    mc_minor_version = '.'.join(parts[1:]) if len(parts) > 1 else mc_version  # e.g. "20.1" from "1.20.1"

    versions = []
    for version_elem in root.findall(".//version"):
        version = version_elem.text
        if version and version.startswith(mc_minor_version):
            neoforge_version = version[len(mc_minor_version)+1:]
            versions.append({
                "mc_version": mc_version,
                "neoforge_version": neoforge_version,
                "full_version": version
            })
    
    return versions

async def download_neoforge_installer(mc_version: str, neoforge_version: str, installers_dir: str = "installers") -> Path: # neoforge_version is like "21.1.77", minecraft version not needed
    """Download NeoForge installer."""
    os.makedirs(installers_dir, exist_ok=True)

    filename = f"neoforge-{neoforge_version}-installer.jar"
    dest = Path(installers_dir) / filename
    
    if dest.exists():
        return dest

    # Correct NeoForge URL pattern
    url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"

    await download_file(url, dest)
    return dest

async def run_neoforge_installer(install_dir: Path, installer_path: Path, mc_version_url: str): # leaves behind log file in main directory
    """Run NeoForge installer (same as Forge)."""
    cmd = ["java", "-jar", installer_path, "--installServer", install_dir]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        await download_minecraft_server(mc_version_url, install_dir)
        log_file = installer_path.name
        await rmtree(log_file, ignore_errors=True) # remove log file
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e
    
