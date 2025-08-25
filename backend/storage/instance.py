from pydantic import BaseModel, ValidationError
from typing import List, Optional, Literal, ClassVar
from datetime import datetime
from pathlib import Path
from helpers import format_date
from config import DATE_FORMAT

# ----------------------------
# Mod metadata for an instance
# ----------------------------
class ModEntry(BaseModel):
    mod_id: str = '' # project_id
    slug: Optional[str] = None
    name: str
    version: Optional[str] = None # version_number
    version_id: Optional[str] = None # version_id
    release_date: Optional[datetime] = None
    source: str # "modrinth", "curseforge", "local"
    type: Literal["mod", "datapack"]
    filename: str
    enabled: bool = True
    install_date: datetime
    from_modpack: bool = False
    is_override: bool = False


class ModList(BaseModel):
    mods: List[ModEntry] = []

    @classmethod
    def load(cls, path: Path) -> "ModList":
        return cls.model_validate_json(path.read_text(encoding='utf-8'))

    def save(self, path: Path):
        path.write_text(self.model_dump_json(indent=4), encoding='utf-8')

    def get_mod(self, mod_id: str) -> Optional[ModEntry]:
        return next((m for m in self.mods if m.mod_id == mod_id), None)

    def has_mod(self, mod_id: str) -> bool:
        return any(m.mod_id == mod_id for m in self.mods)

    def add_mod(self, mod: ModEntry) -> bool:
        if self.has_mod(mod.mod_id):
            return False
        self.mods.append(mod)
        return True

    def remove_mod(self, mod_id: str) -> bool:
        before = len(self.mods)
        self.mods = [m for m in self.mods if m.mod_id != mod_id]
        return len(self.mods) < before

    def enable_mod(self, mod_id: str) -> bool:
        mod = self.get_mod(mod_id)
        if not mod:
            return False
        mod.enabled = True
        return True

    def disable_mod(self, mod_id: str) -> bool:
        mod = self.get_mod(mod_id)
        if not mod:
            return False
        mod.enabled = False
        return True

# ----------------------------
# Instance configuration
# ----------------------------
class InstanceConfig(BaseModel):
    instance_id: str # id of the instance
    name: str # display name of the instance
    install_date: datetime # instance creation time
    minecraft_version: str
    modloader: Literal["fabric", "forge", "neoforge", "quilt"]
    modloader_version: Optional[str] = None
    modpack_name: Optional[str] = None
    modpack_id: Optional[str] = None # slug for modrinth, project id for curseforge and ftb
    modpack_url: Optional[str] = None # url for modpack file
    modpack_version: Optional[str] = None # modpack version number
    modpack_date: Optional[datetime] = None # release date of current modpack version
    modpack_source: Literal['modrinth', 'curseforge', 'ftb', 'modloader'] = 'modloader' # None if modloader only
    jvm_args: List[str] = []
    java_version: Optional[str] = None
    memory_min: Optional[int] = None
    memory_max: Optional[int] = None
    overwrite_global_settings: bool = False
    mods: ModList = ModList()
    # Optional per-instance settings overriding global config
    update_disabled_mods: Literal["update_keep_disabled", "skip_update", "update_enable"] = "update_keep_disabled"
    downgrade_behavior: Literal["ask", "keep", "downgrade"] = "ask"
    backup_marker: Optional[str] = None    # path or timestamp of last backup
    notes: Optional[str] = None            # extra notes about instance
    path: Path

    # ----------------------------
    # Save/load methods
    # ----------------------------
    @classmethod
    def load(cls, path: Path) -> "InstanceConfig":
        instance_json = path / "instance.json"
        mods_json = path / "mods" / "mods.json"

        if not instance_json.exists():
            raise FileNotFoundError(f"No instance.json found in {path}")

        try:
            instance = cls.model_validate_json(instance_json.read_text(encoding='utf-8'))
        except ValidationError as e:
            raise ValueError(f"Invalid instance.json: {e}")

        if mods_json.exists():
            try:
                instance.mods = ModList.load(mods_json)
            except ValidationError as e:
                raise ValueError(f"Invalid mods.json: {e}")
        else:
            instance.mods = ModList()
            instance.mods.save(mods_json)

        instance.path = path
        return instance

    def save(self):
        # Ensure instance folder exists
        self.path.mkdir(parents=True, exist_ok=True)

        # Save instance.json
        instance_json = self.path / "instance.json"
        instance_json.write_text(self.model_dump_json(indent=4, exclude={"mods"}), encoding='utf-8')

        # Ensure mods folder exists
        mods_dir = self.path / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)

        # Save mods.json
        mods_json = self.path / "mods" / "mods.json"
        self.mods.save(mods_json)

class InstanceSummary(BaseModel):
    instance_id: str
    name: str
    status: Literal["stopped", "running", "starting"] = "stopped"
    created: datetime | None = None
    pack_version: str | None = None
    modloader: Literal["fabric", "forge", "neoforge", "quilt"] | None = None
    minecraft_version: str | None = None
    path: Path | None = None  # path to instance folder

    MODLOADER_DISPLAY: ClassVar = {
        "fabric": "Fabric",
        "forge": "Forge",
        "quilt": "Quilt",
        "neoforge": "NeoForge"
    }

    def formatted_modloader(self) -> str:
        if not self.modloader:
            return ''
        return self.MODLOADER_DISPLAY.get(self.modloader, self.modloader.capitalize())
    
    def formatted_date(self, format=DATE_FORMAT) -> str:
        if not self.created:
            return ''
        return format_date(self.created.isoformat(), format)

class InstanceRegistry(BaseModel):
    instances: List[InstanceSummary] = []
    last_updated: datetime | None = None

    @classmethod
    def load(cls, folder: Path=Path('instances')) -> "InstanceRegistry":
        registry_json = folder / "registry.json"
        if registry_json.exists():
            registry = cls.model_validate_json(registry_json.read_text(encoding="utf-8"))
            return registry
        return cls(instances=[])

    def save(self, folder: Path=Path('instances')):
        self.last_updated = datetime.now()
        registry_json = folder / "registry.json"
        registry_json.write_text(self.model_dump_json(indent=2))

    def add_instance(
        self,
        instance_id: str,
        name: str,
        status: Literal["stopped", "running", "starting"] = "stopped",
        created: datetime | None = None,
        pack_version: str | None = None,
        modloader: Literal["fabric", "forge", "neoforge", "quilt"] | None = None,
        minecraft_version: str | None = None,
        path: Path | None = None
    ):
        self.instances.append(InstanceSummary(
            instance_id=instance_id,
            name=name,
            status=status,
            created=created or datetime.now(),
            pack_version=pack_version,
            modloader=modloader,
            minecraft_version=minecraft_version,
            path=path
        ))
        self.last_updated = datetime.now()

    def remove_instance(self, instance_id: str):
        self.instances = [i for i in self.instances if i.instance_id != instance_id]
        self.last_updated = datetime.now()

