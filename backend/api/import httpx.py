import httpx

def get_quilt_versions(mc_version: str) -> list[dict]:
    """Get all available Quilt loader versions for a given Minecraft version."""
    url = f"https://meta.quiltmc.org/v3/versions/loader/{mc_version}"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    return [{
        "version": loader["loader"]["version"],
        "build": loader["loader"]["build"],
    } for loader in data]

result = get_quilt_versions('1.21.1')
print(result)
