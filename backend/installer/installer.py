import asyncio, json, zipfile, os
from aioshutil import rmtree, copy2, move
from pathlib import Path
from datetime import datetime
from backend.storage.instance import InstanceConfig, ModEntry
from backend.api.fabric import ensure_fabric_installer, run_fabric_installer
from backend.api.forge import download_forge_installer, run_forge_installer
from backend.api.neoforge import download_neoforge_installer, run_neoforge_installer
from backend.api.quilt import ensure_quilt_installer, run_quilt_installer
import backend.api.modrinth as modrinth
from helpers import sanitize_filename, download_file

installers_dir = Path("installers")

# Steps:
# 1. Download Modpack
# 2. Extract Modpack
# 3. Install Modloader
# 4. Copy Overrides
# 5. Get Modlist
# 6. Download Mods
# 7. Finalize Installation

async def install_modpack(instance: InstanceConfig, steps: list[str], dependencies: list[dict], progress_bar_callback, step_callback, cancel_event: asyncio.Event, modlist: list[dict] | None = None, mc_version_url: str | None = None) -> tuple[int, str]:
    async def smooth_step_callback(step: str, label_id: int=1):
        step_callback(step, label_id)
        await asyncio.sleep(0.1)

    if Path('downloads').exists():
        await rmtree(Path('downloads'), ignore_errors=True)

    # 1. Download Modpack
    step_callback(steps[0], 0)
    progress_bar_callback(total=100, progress=0, bar_id=0)
    progress_bar_callback(total=100, progress=0)
    await asyncio.sleep(0.1)

    modpack_url = str(instance.modpack_url)
    filename = sanitize_filename(f"{instance.modpack_name}-{instance.modpack_version}")
    modpack_path = Path(f"downloads/{filename}.zip")
    try:
        step_callback(f'Downloading {instance.modpack_name}')
        await download_file(modpack_url, modpack_path, progress_bar_callback, 1, cancel_event)
    except Exception as e:
        return 1, str(e)

    if cancel_event.is_set():
        return -1, 'cancelled'

    # 2. Extract Modpack
    step_callback(steps[1], 0)

    extract_path = Path(f"downloads/{filename}_temp")
    try:
        await async_extract_zip(modpack_path, extract_path, progress_bar_callback, step_callback, 2, cancel_event)
    except Exception as e:
        return 2, str(e)
    
    if cancel_event.is_set():
        return -1, 'cancelled'

    # 3. Install Modloader
    step_callback(steps[2], 0)

    progress_bar_callback(total=100, progress=0)
    await smooth_step_callback('Getting version info')
    mc_version = instance.minecraft_version
    instance.modloader_version = await get_modloader_version(instance.modpack_source, extract_path)
    loader_version = instance.modloader_version
    instance_path = instance.path
    instance_path.mkdir(parents=True, exist_ok=True)
    progress_bar_callback(total=100, progress=25, step=3)

    await smooth_step_callback(f'Checking for {instance.modloader.capitalize()} installer')
    installer_jar = await get_server_installer(instance)
    progress_bar_callback(total=100, progress=50, step=3)

    if cancel_event.is_set():
        return -1, 'cancelled'

    await smooth_step_callback(f'Running {instance.modloader.capitalize()} installer')
    result = await install_server(Path("instances") / instance.instance_id, installer_jar, instance.modloader, mc_version, loader_version, mc_version_url)
    if result != 0:
        return 3, str(result)
    progress_bar_callback(total=100, progress=100, step=3)
    await asyncio.sleep(0.1)

    if cancel_event.is_set():
        return -1, 'cancelled'

    # 4. Copy Overrides
    step_callback(steps[3], 0)

    await smooth_step_callback('Removing client only overrides')
    overrides_path = extract_path / "overrides"
    if overrides_path.exists():
        for folder in ['resourcepacks', 'shaderpacks']:
            bad_path = overrides_path / folder
            if bad_path.exists():
                try:
                    await rmtree(bad_path, ignore_errors=True)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    return 4, str(e)
        try:
            await copytree_with_progress(overrides_path, instance_path, True, progress_bar_callback, step_callback, 4)
        except Exception as e:
            return 4, str(e)
        
    if cancel_event.is_set():
        return -1, 'cancelled'

    # move datapacks into world folder if not there already
    datapacks_folder = instance_path / 'datapacks'
    if datapacks_folder.exists():
        await smooth_step_callback("Moving Datapacks into 'world' Folder")
        world_folder = instance_path / 'world'
        world_folder.mkdir(parents=True, exist_ok=True)
        await move(datapacks_folder, world_folder)

    if cancel_event.is_set():
        return -1, 'cancelled'

    # 5. Get Modlist
    step_callback(steps[4], 0)
    progress_bar_callback(total=100, progress=0, step=5)

    if not modlist:
        await smooth_step_callback('Getting Project Ids')
        project_ids = [dep["project_id"] for dep in dependencies if dep["project_id"]]
        projects = await modrinth.fetch_projects(project_ids)
        progress_bar_callback(total=100, progress=33, step=5)

        if cancel_event.is_set():
            return -1, 'cancelled'

        await smooth_step_callback('Getting Version Ids')
        version_ids = [dep["version_id"] for dep in dependencies if dep["project_id"] in projects]
        versions = await modrinth.fetch_versions(version_ids)
        progress_bar_callback(total=100, progress=66, step=5)

        if cancel_event.is_set():
            return -1, 'cancelled'

        await smooth_step_callback('Getting Mod Info')
        modlist = await combine_project_and_version_info(projects, versions)
    else:
        await smooth_step_callback('Getting Modlist')
    mods = [e for e in modlist if e["type"] == "mod"]
    datapacks = [e for e in modlist if e["type"] == "datapack"]
    progress_bar_callback(total=100, progress=100, step=5)
    await asyncio.sleep(0.1)

    if cancel_event.is_set():
        return -1, 'cancelled'

    # 6. Download Mods
    step_callback(steps[5], 0)
    len_mods = len(modlist)
    progress_bar_callback(total=len_mods, progress=0, step=6)
    mod_num = 0

    try:
        for mod in mods:
            await download_file(mod["download_url"], instance_path / 'mods' / mod["file_name"])
            mod_num += 1
            step_callback(f'Downloading {mod["name"]}')
            progress_bar_callback(total=len_mods, progress=mod_num, step=6)
            if cancel_event.is_set():
                return -1, 'cancelled'

        for datapack in datapacks:
            await download_file(datapack["download_url"], instance_path / 'world' / 'datapacks' / datapack["file_name"])
            mod_num += 1
            step_callback(f'Downloading {datapack["name"]}')
            progress_bar_callback(total=len_mods, progress=mod_num, step=6)
            if cancel_event.is_set():
                return -1, 'cancelled'
    except Exception as e:
        return 6, str(e)
    
    if cancel_event.is_set():
        return -1, 'cancelled'

    # 7. Finalize Installation
    step_callback(steps[6], 0)
    total = len_mods + 30
    mod_num = 20
    progress_bar_callback(total=total, progress=0, step=7)

    await smooth_step_callback('Adding Overrides to Metadata')

    # get mods from overrides
    override_mods_path = overrides_path / 'mods'
    if override_mods_path.exists():
        for mod in override_mods_path.glob('*.jar'):
            instance.mods.add_mod(ModEntry(
                    mod_id=mod.name,
                    name=mod.name,
                    source=instance.modpack_source,
                    type='mod',
                    filename=mod.name,
                    install_date=datetime.now(),
                    from_modpack=True,
                    is_override=True
                ))

    if cancel_event.is_set():
        return -1, 'cancelled'

    # get datapacks from overrides
    for folder in overrides_path.rglob('datapacks'):
        if folder.is_dir():
            for datapack in folder.glob('*.zip'):
                instance.mods.add_mod(ModEntry(
                    mod_id=datapack.name,
                    name=datapack.name,
                    source=instance.modpack_source,
                    type='datapack',
                    filename=datapack.name,
                    install_date=datetime.now(),
                    from_modpack=True,
                    is_override=True
                ))

    progress_bar_callback(total=total, progress=10, step=7)

    if cancel_event.is_set():
        return -1, 'cancelled'

    await smooth_step_callback('Removing Downloads')
    downloads_path = Path('downloads')
    if downloads_path.exists():
        await rmtree(downloads_path)

    progress_bar_callback(total=total, progress=20, step=7)

    await smooth_step_callback('Adding Mods to Metadata')
    for mod in modlist:
        instance.mods.add_mod(ModEntry(
            mod_id=mod["project_id"],
            slug=mod["slug"],
            name=mod["name"],
            version=mod["version_number"],
            version_id=mod["version_id"],
            release_date=mod["date_published"],
            source=instance.modpack_source,
            type=mod["type"],
            filename=mod["file_name"],
            install_date=datetime.now(),
            from_modpack=True
        ))
        mod_num += 1
        progress_bar_callback(total=total, progress=mod_num, step=7)
    
    await smooth_step_callback('Saving Metadata')

    instance.save()

    progress_bar_callback(total=total, progress=total, step=7)

    return 0, 'success'

# Steps:
# 1. Getting Modloader installer
# 2. Installing Modloader
# 3. Finalizing Installation

# TO-DO:
# - update modloader install logic
async def install_modloader(instance: InstanceConfig, steps: list[str], progress_bar_callback, step_callback, cancel_event: asyncio.Event, mc_version_url: str | None = None) -> tuple[int, str]:
    async def smooth_step_callback(step: str, label_id: int=1):
        step_callback(step, label_id)
        await asyncio.sleep(0.1)
    
    # 1. Get Modloader installer
    step_callback(steps[0], 0)
    progress_bar_callback(total=100, progress=0)
    progress_bar_callback(total=100, progress=0, bar_id=0)
    await asyncio.sleep(0.1)

    await smooth_step_callback('Getting Modloader info')
    mc_version = instance.minecraft_version
    loader_version = instance.modloader_version
    instance_path = instance.path
    instance_path.mkdir(parents=True, exist_ok=True)
    progress_bar_callback(total=100, progress=50)
    await asyncio.sleep(0.1)

    await smooth_step_callback(f'Checking for {instance.modloader.capitalize()} installer')
    # - make modloader agnostic
    installer_jar = await ensure_fabric_installer()
    progress_bar_callback(total=100, progress=100)
    progress_bar_callback(total=100, progress=33, bar_id=0)
    await asyncio.sleep(0.1)

    if cancel_event.is_set():
        return -1, 'cancelled'

    # 2. Install Modloader
    step_callback(steps[1], 0)
    await smooth_step_callback(f'Running {instance.modloader.capitalize()} installer')
    result = await run_fabric_installer(Path("instances") / instance.instance_id, installer_jar, mc_version, loader_version)

    if result != 0:
        return 2, str(result)
    progress_bar_callback(total=100, progress=100)
    progress_bar_callback(total=100, progress=66, bar_id=0)
    await asyncio.sleep(0.1)

    # 3. Finalize Installation
    instance.save()
    # - what else even is there to do?

    return 0, 'success'

async def async_extract_zip(zip_path: Path, extract_to: Path, progress_cb=None, item_cb=None, step=None, cancel_event=None):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _extract_zip_sync, zip_path, extract_to, progress_cb, item_cb, step, cancel_event)

def _extract_zip_sync(zip_path: Path, extract_to: Path, progress_cb=None, item_cb=None, step=None, cancel_event=None):
    with zipfile.ZipFile(zip_path, 'r') as z:
        members = z.namelist()
        total = len(members)
        for i, member in enumerate(members, start=1):
            if cancel_event and cancel_event.is_set():
                return
            z.extract(member, extract_to)
            if progress_cb and step:
                progress_cb(total, i, step=step)
            if item_cb:
                item_cb(f'Extracting: {member}')

async def combine_project_and_version_info(
    projects: dict[str, dict],
    versions: list[dict]
) -> list[dict]:
    combined = []
    for version in versions:
        project = projects.get(version["project_id"])
        if not project:
            continue
        combined.append({
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
    return combined

async def copytree_with_progress(
    src: Path,
    dst: Path,
    dirs_exist_ok: bool = False,
    progress_cb=None,
    step_cb=None,
    step=None
):
    # Count total files for progress
    total = sum(len(files) for _, _, files in os.walk(src))
    done = 0

    for root, dirs, files in os.walk(src):
        rel_path = Path(root).relative_to(src)
        target_dir = dst / rel_path
        target_dir.mkdir(parents=True, exist_ok=dirs_exist_ok)

        for file in files:
            src_file = Path(root) / file
            dst_file = target_dir / file
            if step_cb:
                step_cb(f"Copying {src_file.relative_to(src)}")
            try:
                await copy2(src_file, dst_file)
            except Exception as e:
                if step_cb:
                    # - log errors somehow?
                    step_cb(f"Failed to copy {src_file}: {e}")
                continue

            done += 1
            if progress_cb and step:
                progress_cb(total=total, progress=done, step=step)

async def get_modloader_version(source: str, extract_path: Path) -> str | None:
    match source:
        case 'modrinth':
            with open(extract_path / 'modrinth.index.json', 'r') as f:
                return next((version for key, version in json.load(f)["dependencies"].items() if key.lower() != "minecraft"), None)
        # - if api has info, remove
        case "curseforge":
            # CurseForge packs → manifest.json
            with (extract_path / "manifest.json").open("r", encoding="utf-8") as f:
                manifest = json.load(f)
                loaders = manifest.get("minecraft", {}).get("modLoaders", [])
                for loader in loaders:
                    if loader.get("primary"):  # primary loader is the one you want
                        loader_id = loader["id"]  # e.g. "fabric-0.16.14"
                        return loader_id.split("-", 1)[1] if "-" in loader_id else loader_id

async def get_server_installer(instance: InstanceConfig):
    match instance.modloader:
        case 'fabric':
            return await ensure_fabric_installer()
        case 'forge':
            return await download_forge_installer(instance.minecraft_version, str(instance.modloader_version))
        case 'neoforge':
            return await download_neoforge_installer(instance.minecraft_version, str(instance.modloader_version))
        case 'quilt':
            return await ensure_quilt_installer()

async def install_server(install_dir: Path, installer_path: Path, modloader: str, mc_version: str, loader_version: str | None, mc_version_url: str | None):
    match modloader:
        case 'fabric':
            return await run_fabric_installer(install_dir, installer_path, mc_version, loader_version)
        case 'forge':
            if mc_version_url is None:
                return -1
            return await run_forge_installer(install_dir, installer_path, mc_version_url)
        case 'neoforge':
            if mc_version_url is None:
                return -1
            return await run_neoforge_installer(install_dir, installer_path, mc_version_url)
        case 'quilt':
            return await run_quilt_installer(install_dir, installer_path, mc_version, str(loader_version))
